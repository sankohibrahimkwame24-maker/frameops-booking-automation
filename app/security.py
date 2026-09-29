import hashlib
import hmac
import time


class InvalidWebhookSignature(ValueError):
    pass


def verify_calendly_signature(
    raw_body: bytes,
    signature_header: str,
    signing_key: str,
    tolerance_seconds: int = 180,
) -> None:
    if not signing_key:
        raise InvalidWebhookSignature("Webhook signing key is not configured.")
    if not signature_header:
        raise InvalidWebhookSignature("Missing Calendly webhook signature.")

    parts = {}
    for chunk in signature_header.split(","):
        if "=" in chunk:
            key, value = chunk.split("=", 1)
            parts[key.strip()] = value.strip()

    timestamp = parts.get("t")
    provided = parts.get("v1")
    if not timestamp or not provided:
        raise InvalidWebhookSignature("Malformed Calendly webhook signature.")

    try:
        timestamp_int = int(timestamp)
    except ValueError as exc:
        raise InvalidWebhookSignature("Invalid webhook timestamp.") from exc

    if abs(time.time() - timestamp_int) > tolerance_seconds:
        raise InvalidWebhookSignature("Webhook timestamp is outside the allowed tolerance.")

    signed_payload = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(signing_key.encode(), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise InvalidWebhookSignature("Invalid Calendly webhook signature.")
