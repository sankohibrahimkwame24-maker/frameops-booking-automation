import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .config import get_settings
from .database import BookingEvent, EmailOutbox, build_database, check_database
from .security import InvalidWebhookSignature, verify_calendly_signature

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("frameops.booking")
settings = get_settings()
engine, SessionLocal = build_database(settings.database_url)
security = HTTPBasic()
template_env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment.lower() == "production":
        settings.validate_production()
    logger.info("FrameOps Booking Automation started in %s mode", settings.environment)
    yield
    logger.info("FrameOps Booking Automation stopped")


app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.mount(" /static".strip(), StaticFiles(directory=Path(__file__).resolve().parent.parent / "static"), name="static")


@app.get("/health")
async def health():
    try:
        check_database(engine)
        return {"status": "ok", "service": settings.app_name, "environment": settings.environment}
    except Exception as exc:
        logger.exception("Health check failed")
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


def extract_payload(payload: dict) -> dict:
    value = payload.get("payload", {})
    return value if isinstance(value, dict) else {}


def extract_invitee_uri(payload: dict) -> str | None:
    data = extract_payload(payload)
    invitee = data.get("invitee")
    if isinstance(invitee, dict):
        return invitee.get("uri")
    if isinstance(invitee, str):
        return invitee
    return data.get("invitee_uri") or data.get("uri")


def extract_event_uri(payload: dict) -> str | None:
    data = extract_payload(payload)
    event = data.get("event") or data.get("scheduled_event")
    if isinstance(event, dict):
        return event.get("uri")
    return event if isinstance(event, str) else None


def extract_reschedule_uris(payload: dict) -> tuple[str | None, str | None]:
    data = extract_payload(payload)
    invitee = data.get("invitee")
    if not isinstance(invitee, dict):
        return None, None
    old = invitee.get("old_invitee")
    new = invitee.get("new_invitee")
    old_uri = old.get("uri") if isinstance(old, dict) else old
    new_uri = new.get("uri") if isinstance(new, dict) else new
    return old_uri, new_uri


def extract_status(payload: dict) -> str | None:
    status_value = extract_payload(payload).get("status")
    return status_value if isinstance(status_value, str) else None


def extract_scheduled_time(payload: dict) -> str | None:
    data = extract_payload(payload)
    direct = data.get("scheduled_time") or data.get("start_time") or data.get("event_start_time")
    if direct:
        return str(direct)
    event = data.get("scheduled_event")
    if isinstance(event, dict) and event.get("start_time"):
        return str(event["start_time"])
    return None


def _basic_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    import secrets
    valid_user = secrets.compare_digest(credentials.username, settings.admin_username)
    valid_password = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (valid_user and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid dashboard credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(_: str = Depends(_basic_auth)):
    with SessionLocal() as session:
        bookings = session.scalars(select(BookingEvent).order_by(BookingEvent.created_at.desc()).limit(40)).all()
        emails = session.scalars(select(EmailOutbox).order_by(EmailOutbox.created_at.desc()).limit(40)).all()
    template = template_env.get_template("dashboard.html")
    return template.render(
        app_name=settings.app_name,
        environment=settings.environment,
        bookings=bookings,
        emails=emails,
        now=datetime.now(timezone.utc),
    )


@app.post("/webhooks/calendly")
async def calendly_webhook(
    request: Request,
    calendly_webhook_signature: str | None = Header(default=None, alias="Calendly-Webhook-Signature"),
):
    raw_body = await request.body()
    if len(raw_body) > settings.max_body_bytes:
        raise HTTPException(status_code=413, detail="Webhook body too large.")

    try:
        verify_calendly_signature(
            raw_body,
            calendly_webhook_signature or "",
            settings.calendly_webhook_signing_key,
            settings.signature_tolerance_seconds,
        )
    except InvalidWebhookSignature as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook JSON must be an object.")

    event_type = payload.get("event", "")
    if event_type not in {"invitee.created", "invitee.canceled"}:
        return JSONResponse({"status": "ignored", "event": event_type}, status_code=202)

    data = extract_payload(payload)
    invitee_uri = extract_invitee_uri(payload)
    event_uri = extract_event_uri(payload)
    old_invitee_uri, new_invitee_uri = extract_reschedule_uris(payload)
    event_id = payload.get("id") or payload.get("event_id") or data.get("uri") or f"{event_type}:{payload.get('created_at')}:{invitee_uri}"

    with SessionLocal() as session:
        try:
            if session.scalar(select(BookingEvent.id).where(BookingEvent.event_id == str(event_id))):
                return {"status": "duplicate_ignored", "event_id": str(event_id)}

            session.add(
                BookingEvent(
                    event_id=str(event_id),
                    event_type=event_type,
                    invitee_uri=invitee_uri,
                    event_uri=event_uri,
                    old_invitee_uri=old_invitee_uri,
                    new_invitee_uri=new_invitee_uri,
                    scheduled_time=extract_scheduled_time(payload),
                    status=extract_status(payload),
                    canceled=event_type == "invitee.canceled",
                    raw_payload=raw_body.decode("utf-8") if settings.store_raw_payload else None,
                )
            )

            if event_type == "invitee.created":
                session.add(EmailOutbox(event_id=str(event_id), kind="client_confirmation", recipient="", invitee_uri=invitee_uri, event_uri=event_uri, max_attempts=settings.outbox_max_attempts))
                if settings.owner_email:
                    session.add(EmailOutbox(event_id=str(event_id), kind="owner_notification", recipient=settings.owner_email, invitee_uri=invitee_uri, event_uri=event_uri, max_attempts=settings.outbox_max_attempts))
            session.commit()
        except IntegrityError:
            session.rollback()
            return {"status": "duplicate_ignored", "event_id": str(event_id)}

    return JSONResponse({"status": "accepted", "event_id": str(event_id)}, status_code=202)
