import os, hashlib, hmac, time, json
os.environ["CALENDLY_WEBHOOK_SIGNING_KEY"]="test-secret"
os.environ["RESEND_API_KEY"]="re_test"
os.environ["DATABASE_URL"]="sqlite:///./test_frameops.db"
from fastapi.testclient import TestClient
from app.main import app

def signed(body: bytes):
    ts=int(time.time())
    digest=hmac.new(b"test-secret",f"{ts}.".encode()+body,hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"

def test_health():
    with TestClient(app) as client:
        response=client.get("/health")
        assert response.status_code==200
        assert response.json()["status"]=="ok"

def test_invalid_webhook_signature():
    with TestClient(app) as client:
        response=client.post("/webhooks/calendly",json={"event":"invitee.created"},headers={"Calendly-Webhook-Signature":"t=1,v1=bad"})
        assert response.status_code==401

def test_signed_booking_is_accepted_and_duplicate_is_ignored():
    payload={"id":"test-event-001","event":"invitee.created","payload":{"invitee":"https://api.calendly.com/scheduled_events/x/invitees/y","email":"client@example.com","name":"Test Client","scheduled_time":"2026-09-29T10:00:00Z"}}
    body=json.dumps(payload).encode()
    with TestClient(app) as client:
        first=client.post("/webhooks/calendly",content=body,headers={"Content-Type":"application/json","Calendly-Webhook-Signature":signed(body)})
        assert first.status_code==202
        second=client.post("/webhooks/calendly",content=body,headers={"Content-Type":"application/json","Calendly-Webhook-Signature":signed(body)})
        assert second.status_code==200
        assert second.json()["status"]=="duplicate_ignored"
