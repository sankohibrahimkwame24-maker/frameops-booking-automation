# FrameOps Booking Automation v2

Production-oriented Calendly booking automation for FrameOps.

## Ships

- FastAPI webhook with Calendly HMAC verification and replay protection.
- PostgreSQL event store and durable email outbox.
- Calendly API enrichment in the worker.
- Client confirmation + owner notification through Resend.
- Retry/backoff and dead-letter handling.
- Protected /admin dashboard with luxury black, silver/white and gold accents.
- Alembic database migrations.
- Render Blueprint for web + cron + Postgres.
- GitHub Actions CI.
- Raw webhook storage disabled by default.

Architecture: Calendly -> HTTPS webhook -> FastAPI -> PostgreSQL -> Email Outbox -> Cron Worker -> Calendly API + Resend

The webhook verifies and queues work quickly. The worker handles enrichment and delivery.

## Local

Python 3.12+:

    py -3.12 -m venv .venv
    .\\.venv\\Scripts\\Activate.ps1
    pip install -r requirements.txt
    Copy-Item .env.example .env
    alembic upgrade head
    uvicorn app.main:app --reload

Open /health and /admin on the local server.

## Production

Deploy the Render Blueprint. It creates an always-on web service, cron worker and managed Postgres.

Set these secrets in Render: CALENDLY_API_TOKEN, CALENDLY_WEBHOOK_SIGNING_KEY, RESEND_API_KEY, EMAIL_FROM (verified Resend sender), OWNER_EMAIL, ADMIN_PASSWORD.

Create Calendly webhooks for invitee.created and invitee.canceled pointing to https://YOUR-SERVICE.onrender.com/webhooks/calendly.

Do not commit .env or API keys.

## Verification

1. /health returns status=ok.
2. /admin loads with authentication.
3. A real Calendly booking creates the booking and two email jobs.
4. Client receives the confirmation.
5. Owner receives the notification.
6. Cancellation/reschedule events appear correctly.
7. Resend and Render logs show successful delivery.
