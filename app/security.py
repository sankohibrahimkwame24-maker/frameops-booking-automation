import hashlib, hmac, time

class InvalidWebhookSignature(Exception): pass

def verify_calendly_signature(raw_body: bytes, signature_header: str, signing_key: str, tolerance_seconds: int = 180) -> None:
    if not signing_key: raise InvalidWebhookSignature("Webhook signing key is not configured.")
    if not signature_header: raise InvalidWebhookSignature("Missing Calendly-Webhook-Signature header.")
    parts = {}
    for item in signature_header.split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            parts[key.strip()] = value.strip()
    timestamp, received_signature = parts.get("t"), parts.get("v1")
    if not timestamp or not received_signature: raise InvalidWebhookSignature("Malformed webhook signature.")
    try: timestamp_int = int(timestamp)
    except ValueError as exc: raise InvalidWebhookSignature("Invalid webhook timestamp.") from exc
    if abs(time.time() - timestamp_int) > tolerance_seconds: raise InvalidWebhookSignature("Webhook signature is outside the replay window.")
    signed_payload = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(signing_key.encode(), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_signature): raise InvalidWebhookSignature("Invalid webhook signature.")
