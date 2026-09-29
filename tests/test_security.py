import hashlib, hmac, time, pytest
from app.security import InvalidWebhookSignature, verify_calendly_signature

def make_signature(body: bytes, key: str, timestamp: int) -> str:
    digest = hmac.new(key.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"

def test_valid_signature():
    body=b'{"event":"invitee.created"}'
    verify_calendly_signature(body,make_signature(body,"secret",int(time.time())),"secret")

def test_bad_signature_rejected():
    body=b'{}'
    with pytest.raises(InvalidWebhookSignature):
        verify_calendly_signature(body,make_signature(body,"secret",int(time.time())),"wrong")

def test_replay_rejected():
    body=b'{}'
    old=int(time.time())-1000
    with pytest.raises(InvalidWebhookSignature):
        verify_calendly_signature(body,make_signature(body,"secret",old),"secret",180)
