"""Notify Advancement staff when a visitor leaves a follow-up request (Story 10).

leads.save_request() calls notify() after the request is stored. The delivery channel depends on
where the assistant is hosted, which the Engineering web team decides, so it is chosen by env var:

    NOTIFY_CHANNEL=none     (default) nothing is sent; requests are only stored
    NOTIFY_CHANNEL=email    send an email through SMTP_HOST to NOTIFY_TO
    NOTIFY_CHANNEL=webhook  POST JSON to NOTIFY_WEBHOOK_URL (Teams / Power Automate / Slack flow)

Who receives notifications is an Advancement decision (Story 13). By default they go only to
NOTIFY_TO; set NOTIFY_ROUTED_STAFF=1 to also email the staff member the visitor asked for.

A failed notification never fails the visitor's request: the request is already stored, and the
error is logged so staff can check the requests file.
"""

import logging
import smtplib
import threading
from email.message import EmailMessage

import httpx

import config

log = logging.getLogger(__name__)


def message_text(request: dict) -> tuple[str, str]:
    """Subject and body for one request. Only the fields the visitor typed are included."""
    name = f"{request['first_name']} {request['last_name']}"
    staff = request.get("staff") or "the Engineering Advancement team"
    subject = f"Giving assistant: follow-up request from {name}"
    lines = [
        f"{name} asked for a follow-up from {staff} through the giving assistant.",
        "",
        f"Email: {request['email']}",
        f"Phone: {request.get('phone') or '(not given)'}",
        f"Received: {request['received']} (UTC)",
        "",
        "Message:",
        request.get("message") or "(none)",
        "",
        "The visitor consented to being contacted. The chat conversation is not stored or attached.",
    ]
    return subject, "\n".join(lines)


def recipients(request: dict, staff_emails: dict[str, str] | None = None) -> list[str]:
    to = [a for a in config.NOTIFY_TO if a]
    if config.NOTIFY_ROUTED_STAFF and request.get("staff") and staff_emails:
        email = staff_emails.get(request["staff"])
        if email and email not in to:
            to.append(email)
    return to


def send_email(request: dict, to: list[str]) -> None:
    subject, body = message_text(request)
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, config.NOTIFY_FROM, ", ".join(to)
    msg["Reply-To"] = request["email"]  # staff can reply straight to the visitor
    msg.set_content(body)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as smtp:
        if config.SMTP_STARTTLS:
            smtp.starttls()
        if config.SMTP_USER:
            smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
        smtp.send_message(msg)


def send_webhook(request: dict) -> None:
    subject, body = message_text(request)
    # "text" is what Teams/Slack incoming webhooks display; "request" is for Power Automate flows.
    r = httpx.post(config.NOTIFY_WEBHOOK_URL, timeout=20,
                   json={"title": subject, "text": body, "request": request})
    r.raise_for_status()


def deliver(request: dict, staff_emails: dict[str, str] | None = None) -> str:
    """Send one notification on the configured channel. Returns the channel used."""
    channel = config.NOTIFY_CHANNEL
    if channel == "email":
        to = recipients(request, staff_emails)
        if not to:
            raise ValueError("NOTIFY_CHANNEL=email but NOTIFY_TO is empty")
        send_email(request, to)
    elif channel == "webhook":
        send_webhook(request)
    elif channel != "none":
        raise ValueError(f"Unknown NOTIFY_CHANNEL {channel!r}")
    return channel


def notify(request: dict, staff_emails: dict[str, str] | None = None, wait: bool = False) -> None:
    """Deliver in the background so the visitor isn't kept waiting on SMTP or a webhook."""
    def run():
        try:
            deliver(request, staff_emails)
        except Exception:
            log.exception("Follow-up notification failed; the request is still stored in %s",
                          config.CONTACT_REQUESTS_FILE)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    if wait:
        t.join()
