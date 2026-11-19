"""Brevo transactional email, no data collection or purchases."""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API_URL = "https://api.brevo.com/v3/smtp/email"
REQUIRED = ("BREVO_API_KEY", "BREVO_SENDER_EMAIL", "REPORT_RECIPIENT_EMAIL")

def configuration_status(env=None):
    env = os.environ if env is None else env
    return {name: bool(str(env.get(name, "")).strip()) for name in REQUIRED}

def send_report(subject, body, env=None, opener=None):
    env = os.environ if env is None else env
    missing = [key for key, ready in configuration_status(env).items() if not ready]
    if missing:
        raise ValueError("Missing email configuration: " + ", ".join(missing))
    if not isinstance(subject, str) or not subject.strip() or len(subject)>180:
        raise ValueError("Invalid subject")
    if not isinstance(body, str) or not body.strip() or len(body)>100000:
        raise ValueError("Invalid body")
    sender = str(env["BREVO_SENDER_EMAIL"]).strip()
    recipient = str(env["REPORT_RECIPIENT_EMAIL"]).strip()
    if "@" not in sender or "@" not in recipient:
        raise ValueError("Invalid email address")
    payload = {"sender": {"name": "Smart Product Monitor", "email": sender},
               "to": [{"email": recipient}], "subject": subject.strip(), "textContent": body}
    req = Request(API_URL, data=json.dumps(payload).encode("utf-8"),
                  headers={"api-key": str(env["BREVO_API_KEY"]).strip(),
                           "accept": "application/json", "content-type": "application/json"},
                  method="POST")
    try:
        with (opener or urlopen)(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            return {"accepted": True, "message_id": result.get("messageId", "")}
    except HTTPError as exc:
        raise RuntimeError(f"Brevo rejected the email (HTTP {exc.code}); check sender and Brevo logs.") from None
    except URLError:
        raise RuntimeError("Email service unavailable; delivery not confirmed.") from None
