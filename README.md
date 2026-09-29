# FrameOps Booking Automation M1

A production-oriented FastAPI webhook service for FrameOps/Calendly booking automation.

## What it does

1. Receives Calendly `invitee.created` and `invitee.canceled` webhooks.
2. Verifies the Calendly HMAC signature and rejects replayed requests.
3. Stores accepted events.
4. Prevents duplicate processing using an event ID.
5. Optionally enriches invitee name/email through the Calendly API.
6. Queues confirmation email work in a durable outbox.
7. Sends confirmation emails through Resend via a worker.
8. Exposes `/health` for deployment monitoring.

## Architecture

Calendly → HTTPS webhook → FastAPI → signature verification → PostgreSQL → durable email outbox → Resend worker

## Why this is not a desktop .exe

A webhook endpoint must be reachable by Calendly over the public internet. The production service therefore runs on a hosted HTTPS platform. A future FrameOps admin app can monitor it.

## Setup on Windows

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Health: `http://127.0.0.1:8000/health`

## Production

Use the included `render.yaml` with managed PostgreSQL. Store secrets in the host secret manager; never commit `.env`.

## Testing

```powershell
pytest -q
```

## Security

Do not disable signature verification, log webhook secrets, commit API tokens, or expose SQLite publicly.
