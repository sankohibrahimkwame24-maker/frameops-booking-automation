import hashlib, hmac, time, pytest
from app.security import InvalidWebhookSignature, verify_calendly_signature

def signature(body,key,ts):
    digest=hmac.new(key.encode(),f"{ts}.".encode()+body,hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"

def test_valid_signature():
    body=b'{"event":"invitee.created"}'
    verify_calendly_signature(body,signature(body,"secret",int(time.time())),"secret")

def test_bad_signature_rejected():
    with pytest.raises(InvalidWebhookSignature):
        verify_calendly_signature(b"{}",signature(b"{}","secret",int(time.time())),"wrong")

def test_old_signature_rejected():
    with pytest.raises(InvalidWebhookSignature):
        verify_calendly_signature(b"{}",signature(b"{}","secret",int(time.time())-1000),"secret")
