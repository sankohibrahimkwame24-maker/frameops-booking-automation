import asyncio
from datetime import datetime,timezone
from sqlalchemy import delete,select
from app import worker
from app.database import BookingEvent,EmailOutbox

class FakeCalendly:
    def __init__(self,token): pass
    async def get_invitee(self,uri): return {"name":"Demo Client","email":"client@example.com"}
    async def get_scheduled_event(self,uri): return {"uri":uri,"start_time":"2026-10-01T10:00:00Z"}

class FakeEmailService:
    def __init__(self,api_key,sender): pass
    async def send_client_confirmation(self,**kwargs): return "client-message"
    async def send_owner_notification(self,**kwargs): return "owner-message"

def test_worker_delivers_two_jobs(monkeypatch):
    monkeypatch.setattr(worker,"CalendlyClient",FakeCalendly)
    monkeypatch.setattr(worker,"EmailService",FakeEmailService)
    with worker.SessionLocal() as session:
        session.execute(delete(EmailOutbox)); session.execute(delete(BookingEvent)); session.commit()
        event=BookingEvent(event_id="worker-event",event_type="invitee.created",invitee_uri="https://api.calendly.com/invitees/i",event_uri="https://api.calendly.com/events/e",created_at=datetime.now(timezone.utc))
        session.add(event); session.flush()
        session.add_all([
          EmailOutbox(event_id="worker-event",kind="client_confirmation",invitee_uri=event.invitee_uri,event_uri=event.event_uri,max_attempts=5),
          EmailOutbox(event_id="worker-event",kind="owner_notification",recipient="owner@example.com",invitee_uri=event.invitee_uri,event_uri=event.event_uri,max_attempts=5)
        ])
        session.commit()
    assert asyncio.run(worker.process_pending_emails())==2
    with worker.SessionLocal() as session:
        jobs=session.scalars(select(EmailOutbox).where(EmailOutbox.event_id=="worker-event")).all()
        event=session.scalar(select(BookingEvent).where(BookingEvent.event_id=="worker-event"))
        assert all(j.sent for j in jobs)
        assert event.client_email=="client@example.com"
        assert event.email_sent is True
