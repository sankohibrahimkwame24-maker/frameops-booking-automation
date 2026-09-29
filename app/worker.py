import asyncio, logging
from datetime import datetime, timezone
from sqlalchemy import select
from .config import get_settings
from .database import BookingEvent, EmailOutbox, build_database
from .emailer import EmailDeliveryError, EmailService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("frameops.worker")
settings = get_settings()
SessionLocal = build_database(settings.database_url)

async def process_pending_emails(limit: int = 25) -> int:
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY is not configured.")
        return 0
    service = EmailService(settings.resend_api_key, settings.email_from)
    with SessionLocal() as session:
        rows = session.scalars(select(EmailOutbox).where(EmailOutbox.sent.is_(False)).order_by(EmailOutbox.created_at).limit(limit)).all()
        processed = 0
        for row in rows:
            row.attempts += 1
            try:
                await service.send_booking_confirmation(recipient=row.recipient, client_name=row.client_name, scheduled_time=row.scheduled_time)
                row.sent = True
                row.sent_at = datetime.now(timezone.utc)
                event = session.scalar(select(BookingEvent).where(BookingEvent.event_id == row.event_id))
                if event: event.email_sent = True
                row.last_error = None
                processed += 1
            except EmailDeliveryError as exc:
                row.last_error = str(exc)
                logger.exception("Email failed for outbox %s", row.id)
        session.commit()
        return processed

if __name__ == "__main__":
    count = asyncio.run(process_pending_emails())
    logger.info("Processed %d pending email(s)", count)
