import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .calendly import CalendlyClient
from .config import get_settings
from .database import BookingEvent, EmailOutbox, build_database
from .emailer import EmailService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("frameops.worker")
settings = get_settings()
engine, SessionLocal = build_database(settings.database_url)


async def _enrich_booking(row: EmailOutbox, session):
    booking = session.scalar(select(BookingEvent).where(BookingEvent.event_id == row.event_id))
    if not booking:
        raise RuntimeError("Booking event no longer exists")

    client = CalendlyClient(settings.calendly_api_token)
    invitee = await client.get_invitee(row.invitee_uri) if row.invitee_uri else {}
    event = await client.get_scheduled_event(row.event_uri) if row.event_uri else {}

    email = invitee.get("email") or booking.client_email
    name = invitee.get("name") or booking.client_name or "there"
    scheduled_time = booking.scheduled_time or event.get("start_time") or "your scheduled time"

    booking.client_email = email
    booking.client_name = name
    booking.scheduled_time = scheduled_time
    session.flush()
    return booking, email, name, scheduled_time


async def process_pending_emails(limit: int = 25) -> int:
    if settings.environment.lower() == "production":
        settings.validate_production()

    service = EmailService(settings.resend_api_key, settings.email_from)
    now = datetime.now(timezone.utc)
    processed = 0

    with SessionLocal() as session:
        rows = session.scalars(
            select(EmailOutbox)
            .where(
                EmailOutbox.sent.is_(False),
                EmailOutbox.dead_letter.is_(False),
                EmailOutbox.next_attempt_at <= now,
            )
            .order_by(EmailOutbox.created_at)
            .limit(limit)
        ).all()

        for row in rows:
            row.attempts += 1
            try:
                booking, email, name, scheduled_time = await _enrich_booking(row, session)
                if row.kind == "client_confirmation":
                    if not email:
                        raise RuntimeError("Calendly did not return an invitee email address")
                    row.recipient = email
                    await service.send_client_confirmation(
                        recipient=email,
                        name=name,
                        scheduled_time=scheduled_time,
                        idempotency_key=f"frameops/{row.kind}/{row.event_id}",
                    )
                    booking.email_sent = True
                elif row.kind == "owner_notification":
                    if not row.recipient:
                        raise RuntimeError("Owner notification email is not configured")
                    await service.send_owner_notification(
                        recipient=row.recipient,
                        name=name,
                        email=email or "Unknown",
                        scheduled_time=scheduled_time,
                        idempotency_key=f"frameops/{row.kind}/{row.event_id}",
                    )
                else:
                    raise RuntimeError(f"Unknown email job type: {row.kind}")

                row.sent = True
                row.sent_at = datetime.now(timezone.utc)
                row.last_error = None
                processed += 1
            except Exception as exc:
                row.last_error = str(exc)[:2000]
                if row.attempts >= row.max_attempts:
                    row.dead_letter = True
                    logger.error("Email outbox %s moved to dead-letter: %s", row.id, exc)
                else:
                    delay_minutes = min(60, 2 ** max(row.attempts - 1, 0))
                    row.next_attempt_at = now + timedelta(minutes=delay_minutes)
                    logger.warning("Email outbox %s failed; retry in %s minute(s): %s", row.id, delay_minutes, exc)

        session.commit()
    return processed


if __name__ == "__main__":
    count = asyncio.run(process_pending_emails())
    logger.info("Processed %d pending email(s)", count)
