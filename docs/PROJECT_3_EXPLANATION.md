# FrameOps Booking Automation — explained simply

Imagine you hired a receptionist.

When somebody books a call:
1. Calendly tells the receptionist.
2. The receptionist checks the secret stamp.
3. If fake, it is rejected.
4. If real, the booking is written to a database.
5. The system checks whether the event was already handled.
6. A new booking creates a durable email job.
7. A worker sends the email and records success.

## Why FastAPI?
Calendly needs a public HTTPS endpoint.

## Why PostgreSQL in production?
The booking and email job must survive service restarts.

## Why signature verification?
It prevents arbitrary callers from pretending to be Calendly.

## Why an event ID?
Webhook systems can retry events. The unique event ID prevents duplicate processing.

## Why an email worker?
The webhook should respond quickly. Email delivery can fail or take longer, so it is stored as an outbox job and retried later.

## Why isn't this an .exe?
Calendly needs to reach the service while your PC may be off. The production service therefore lives online.
