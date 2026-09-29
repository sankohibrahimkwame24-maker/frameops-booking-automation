import html
import httpx


class EmailDeliveryError(Exception):
    pass


def _escape(value: str) -> str:
    return html.escape(str(value), quote=True)


class EmailService:
    """Small Resend API client with deterministic idempotency keys for safe retries."""

    API_URL = "https://api.resend.com/emails"

    def __init__(self, api_key: str, sender: str):
        if not api_key:
            raise ValueError("RESEND_API_KEY is not configured.")
        if not sender:
            raise ValueError("EMAIL_FROM is not configured.")
        self.api_key = api_key
        self.sender = sender

    async def send(self, *, recipient: str, subject: str, html_body: str, idempotency_key: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        payload = {
            "from": self.sender,
            "to": [recipient],
            "subject": subject,
            "html": html_body,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.API_URL, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise EmailDeliveryError(f"Resend request failed: {exc}") from exc

        if response.is_error:
            detail = response.text[:1000]
            raise EmailDeliveryError(f"Resend returned HTTP {response.status_code}: {detail}")

        try:
            return str(response.json().get("id", ""))
        except ValueError as exc:
            raise EmailDeliveryError("Resend returned invalid JSON.") from exc

    async def send_client_confirmation(self, *, recipient: str, name: str, scheduled_time: str, idempotency_key: str) -> str:
        safe_name = _escape(name or "there")
        safe_time = _escape(scheduled_time or "your scheduled time")
        body = f"""<!doctype html><html><body style="margin:0;background:#0b0b0c;color:#f4f4f5;font-family:Arial,sans-serif">
<div style="max-width:620px;margin:40px auto;padding:36px;background:#151517;border:1px solid #34343a;border-radius:18px">
<div style="color:#d9a441;font-size:12px;letter-spacing:2px;font-weight:700">FRAMEOPS</div>
<h1 style="font-size:28px;margin:14px 0">Your call is booked.</h1>
<p style="color:#c7c7cc;line-height:1.7">Hey {safe_name}, thanks for booking a FrameOps discovery call for <strong style="color:#fff">{safe_time}</strong>.</p>
<p style="color:#c7c7cc;line-height:1.7">Before the call, reply with one or two of your latest video links. I’ll review them beforehand so we can spend the call talking about your actual content workflow.</p>
<p style="color:#c7c7cc;line-height:1.7">Best,<br><strong style="color:#fff">Ibrahim</strong><br>Founder, FrameOps</p>
</div></body></html>"""
        return await self.send(
            recipient=recipient,
            subject="Booked — one quick step before our FrameOps call",
            html_body=body,
            idempotency_key=idempotency_key,
        )

    async def send_owner_notification(self, *, recipient: str, name: str, email: str, scheduled_time: str, idempotency_key: str) -> str:
        body = f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#111;line-height:1.6">
<h2>New FrameOps discovery call</h2>
<p><strong>Client:</strong> {_escape(name or 'Unknown')}</p>
<p><strong>Email:</strong> {_escape(email or 'Unknown')}</p>
<p><strong>Scheduled:</strong> {_escape(scheduled_time or 'Unknown')}</p>
<p>Open the FrameOps admin dashboard to review recent bookings and email delivery status.</p>
</body></html>"""
        return await self.send(
            recipient=recipient,
            subject="New FrameOps discovery call booked",
            html_body=body,
            idempotency_key=idempotency_key,
        )
