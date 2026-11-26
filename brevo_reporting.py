"""Brevo transactional email, no data collection or purchases."""
import json
import os
import re
from urllib.request import Request, urlopen, build_opener
from brevo_diagnostic import NoRedirect
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
        with (opener or build_opener(NoRedirect()).open)(req, timeout=15) as response:
            raw = response.read(65537)
            if response.status != 201 or len(raw) > 65536:
                raise RuntimeError("Email acceptance unconfirmed")
            result = json.loads(raw)
            if not isinstance(result, dict) or not isinstance(result.get("messageId"), str) or not result["messageId"].strip():
                raise RuntimeError("Email acceptance unconfirmed")
            return {"accepted": True, "message_id": result["messageId"]}
    except HTTPError as exc:
        # Brevo error bodies can contain sensitive details. Only expose a short,
        # restricted error code; never display the raw response or credentials.
        error_code = "unavailable"
        try:
            raw = exc.read(8192)
            parsed = json.loads(raw.decode("utf-8", errors="replace"))
            candidate = parsed.get("code", "") if isinstance(parsed, dict) else ""
            if isinstance(candidate, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", candidate):
                error_code = candidate
        except (ValueError, UnicodeError, OSError, AttributeError):
            pass
        raise RuntimeError(
            f"Brevo API request rejected: HTTP {exc.code}; error code: {error_code}. "
            "No email was confirmed sent. Check API key permissions/account access "
            "or contact Brevo support with this status and code."
        ) from None
    except URLError:
        raise RuntimeError("Email service unavailable; delivery not confirmed.") from None
