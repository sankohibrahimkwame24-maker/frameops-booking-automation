import json, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from .calendly import CalendlyClient
from .config import get_settings
from .database import BookingEvent, EmailOutbox, build_database, event_exists
from .security import InvalidWebhookSignature, verify_calendly_signature

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("frameops.booking")
settings = get_settings()
SessionLocal = build_database(settings.database_url)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FrameOps Booking Automation starting in %s mode", settings.environment)
    yield
    logger.info("FrameOps Booking Automation stopping")

app = FastAPI(title=settings.app_name, version="1.1.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}

def extract_invitee_uri(payload: dict) -> str | None:
    data = payload.get("payload", {})
    invitee = data.get("invitee")
    if isinstance(invitee, dict): return invitee.get("uri")
    if isinstance(invitee, str): return invitee
    return data.get("invitee_uri")

def extract_event_uri(payload: dict) -> str | None:
    data = payload.get("payload", {})
    event = data.get("event") or data.get("scheduled_event")
    if isinstance(event, dict): return event.get("uri")
    return event

def extract_direct_contact(payload: dict) -> tuple[str | None, str | None]:
    data = payload.get("payload", {})
    return data.get("name") or data.get("invitee_name"), data.get("email") or data.get("invitee_email")

async def enrich_contact(payload: dict) -> tuple[str | None, str | None]:
    name, email = extract_direct_contact(payload)
    invitee_uri = extract_invitee_uri(payload)
    if email or not invitee_uri or not settings.calendly_api_token: return name, email
    try:
        invitee = await CalendlyClient(settings.calendly_api_token).get_invitee(invitee_uri)
        return invitee.get("name") or name, invitee.get("email") or email
    except Exception:
        logger.exception("Could not enrich invitee %s", invitee_uri)
        return name, email

@app.post("/webhooks/calendly")
async def calendly_webhook(request: Request, calendly_webhook_signature: str | None = Header(default=None, alias="Calendly-Webhook-Signature")):
    raw_body = await request.body()
    if len(raw_body) > settings.max_body_bytes: raise HTTPException(status_code=413, detail="Webhook body too large.")
    try:
        verify_calendly_signature(raw_body, calendly_webhook_signature or "", settings.calendly_webhook_signing_key, settings.signature_tolerance_seconds)
    except InvalidWebhookSignature as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try: payload = json.loads(raw_body)
    except json.JSONDecodeError as exc: raise HTTPException(status_code=400, detail="Invalid JSON.") from exc
    event_type = payload.get("event", "")
    if event_type not in {"invitee.created", "invitee.canceled"}:
        return JSONResponse({"status": "ignored", "event": event_type}, status_code=202)
    data = payload.get("payload", {})
    event_id = payload.get("id") or payload.get("event_id") or data.get("uri") or f"{event_type}:{payload.get('created_at')}:{extract_invitee_uri(payload)}"
    if event_exists(SessionLocal, event_id): return {"status": "duplicate_ignored", "event_id": event_id}
    name, email = await enrich_contact(payload)
    scheduled_time = data.get("scheduled_time") or data.get("start_time") or data.get("event_start_time")
    with SessionLocal() as session:
        session.add(BookingEvent(event_id=event_id,event_type=event_type,invitee_uri=extract_invitee_uri(payload),client_name=name,client_email=email,scheduled_time=scheduled_time,event_uri=extract_event_uri(payload),canceled=event_type == "invitee.canceled",raw_payload=raw_body.decode("utf-8")))
        if event_type == "invitee.created" and email and settings.resend_api_key:
            session.add(EmailOutbox(event_id=event_id,recipient=email,client_name=name or "there",scheduled_time=scheduled_time or "your scheduled time"))
        session.commit()
    return JSONResponse({"status":"accepted","event_id":event_id,"email_queued":bool(event_type == "invitee.created" and email and settings.resend_api_key)},status_code=202)
