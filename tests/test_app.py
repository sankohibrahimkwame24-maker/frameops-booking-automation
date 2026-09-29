import hashlib,hmac,json,time
from fastapi.testclient import TestClient
from app.main import app

def signed(body):
    ts=int(time.time())
    digest=hmac.new(b"test-secret",f"{ts}.".encode()+body,hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"

def test_health():
    with TestClient(app) as client:
        assert client.get("/health").status_code==200

def test_missing_signature_rejected():
    with TestClient(app) as client:
        assert client.post("/webhooks/calendly",json={"event":"invitee.created"}).status_code==401

def test_booking_is_idempotent():
    payload={"id":"event-001","event":"invitee.created","payload":{"invitee":{"uri":"https://api.calendly.com/invitees/i"},"event":"https://api.calendly.com/events/e","status":"active"}}
    body=json.dumps(payload).encode()
    with TestClient(app) as client:
        first=client.post("/webhooks/calendly",content=body,headers={"Content-Type":"application/json","Calendly-Webhook-Signature":signed(body)})
        second=client.post("/webhooks/calendly",content=body,headers={"Content-Type":"application/json","Calendly-Webhook-Signature":signed(body)})
        assert first.status_code==202
        assert second.json()["status"]=="duplicate_ignored"
