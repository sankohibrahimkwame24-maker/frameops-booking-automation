# Production deployment

## Render
Create a Blueprint from this repository. Use the supplied render.yaml.

## Resend
Verify your sending domain and set EMAIL_FROM to a verified address. Do not use the Resend development sender for the real business workflow.

## Calendly
Create the webhook subscription for invitee.created and invitee.canceled. Use the deployed callback URL and keep the webhook signing key in Render.

## Dashboard
Open https://YOUR-SERVICE.onrender.com/admin and authenticate with ADMIN_USERNAME / ADMIN_PASSWORD.

## Live test
Book a real FrameOps discovery call with a test email. Verify Calendly -> webhook -> database -> worker -> Resend -> inbox. Then test cancellation or rescheduling.

Never paste API tokens or webhook signing keys into GitHub issues, README files, or chat.
