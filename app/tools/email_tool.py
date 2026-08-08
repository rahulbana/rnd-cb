"""Email tool — send-only over SMTP.

Honours ``EMAIL_DRY_RUN`` (default true): when dry-run is on, the composed
message is returned for review instead of being sent, so you can wire up
credentials and exercise the agent without accidentally emailing anyone.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from .base import Tool, ToolRegistry


def register(registry: ToolRegistry, config) -> None:
    def send_email(to: str, subject: str, body: str, cc: str | None = None) -> str:
        if not config.email_from:
            return "Email is not configured (missing EMAIL_FROM / SMTP_USER)."

        msg = EmailMessage()
        msg["From"] = config.email_from
        msg["To"] = to
        if cc:
            msg["Cc"] = cc
        msg["Subject"] = subject
        msg.set_content(body)

        recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
        if cc:
            recipients += [addr.strip() for addr in cc.split(",") if addr.strip()]

        if config.email_dry_run:
            return (
                "DRY RUN — email not sent (set EMAIL_DRY_RUN=false to send).\n"
                f"From: {config.email_from}\nTo: {to}\n"
                + (f"Cc: {cc}\n" if cc else "")
                + f"Subject: {subject}\n\n{body}"
            )

        if not (config.smtp_host and config.smtp_user and config.smtp_password):
            return "Cannot send: SMTP host/user/password are not fully configured."

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as server:
                server.starttls(context=context)
                server.login(config.smtp_user, config.smtp_password)
                server.send_message(msg, to_addrs=recipients)
        except Exception as exc:  # noqa: BLE001
            return f"Failed to send email: {exc}"
        return f"Email sent to {', '.join(recipients)} (subject: {subject!r})."

    registry.register(
        Tool(
            name="send_email",
            description=(
                "Send an email via SMTP. Supports comma-separated recipients and "
                "an optional Cc. If dry-run mode is on, returns the composed "
                "message for review instead of sending. Confirm recipient and "
                "content with the user before sending real email."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient(s), comma-separated."},
                    "subject": {"type": "string", "description": "Email subject line."},
                    "body": {"type": "string", "description": "Plain-text email body."},
                    "cc": {"type": "string", "description": "Optional Cc recipient(s)."},
                },
                "required": ["to", "subject", "body"],
                "additionalProperties": False,
            },
            handler=send_email,
        )
    )
