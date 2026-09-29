# Deploy FrameOps Booking Automation

## Fastest production path: Render

1. Connect this GitHub repository to Render and create a Blueprint.
2. Render will create a FastAPI web service, PostgreSQL database, and 1-minute email worker.
3. Add the required secrets:
   - CALENDLY_WEBHOOK_SIGNING_KEY
   - CALENDLY_API_TOKEN
   - RESEND_API_KEY
   - EMAIL_FROM
4. Deploy and open `/health`.
5. Create a Calendly webhook subscription for `invitee.created` and `invitee.canceled`.
6. Point it at `https://YOUR-SERVICE.onrender.com/webhooks/calendly`.
7. Use the same webhook signing key in Render.

## Before production

- Verify the sending domain in Resend.
- Test a real booking, cancellation, reschedule, duplicate delivery, and email retry.
