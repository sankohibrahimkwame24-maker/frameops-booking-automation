import resend

class EmailDeliveryError(Exception): pass

class EmailService:
    def __init__(self, api_key: str, sender: str):
        if not api_key: raise ValueError("RESEND_API_KEY is not configured.")
        resend.api_key = api_key
        self.sender = sender

    async def send_booking_confirmation(self, *, recipient: str, client_name: str, scheduled_time: str) -> str:
        html = f"""<div style="font-family:Arial,sans-serif;line-height:1.6;color:#111"><p>Hey {client_name},</p><p>Thanks for booking a FrameOps discovery call for <strong>{scheduled_time}</strong>.</p><p>Before the call, please reply with one or two of your latest video links. I'll take a look beforehand so we can spend the call discussing your actual content workflow rather than starting from zero.</p><p>Best,<br>Ibrahim<br>Founder, FrameOps</p></div>"""
        try:
            result = await resend.Emails.send_async({"from": self.sender, "to": [recipient], "subject": "Received — a quick step before our FrameOps call", "html": html})
            return str(getattr(result, "id", "") or result.get("id", ""))
        except Exception as exc:
            raise EmailDeliveryError(str(exc)) from exc
