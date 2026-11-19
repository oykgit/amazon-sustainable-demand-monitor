# Brevo email verification update

Adds one-time test-email button to existing **Overview** workspace, without changing the 24 navigation buttons.

Render variables: `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `REPORT_RECIPIENT_EMAIL`.

After deployment: Overview > V2.0: Email delivery verification > Send one Brevo test email. Brevo message ID indicates API acceptance, not inbox delivery. Check Gmail inbox/spam and Brevo transaction logs.

This update does **not** enable scheduled emails, automatic product discovery, data collection, database writes or purchasing. These require separately configured scheduled execution and authorized data sources. Never commit secrets.
