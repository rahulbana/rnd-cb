"""Email tools — send over SMTP, read over IMAP.

Sending honours ``EMAIL_DRY_RUN`` (default true): when dry-run is on, the
composed message is returned for review instead of being sent, so you can wire
up credentials and exercise the agent without accidentally emailing anyone.

Reading is always read-only: the IMAP mailbox is opened with ``readonly=True``
so fetching a message never marks it as seen.
"""

from __future__ import annotations

import email
import imaplib
import smtplib
import ssl
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.message import EmailMessage

from .base import Tool, ToolRegistry

_SNIPPET_LEN = 300
_MAX_BODY_LEN = 8000


def _decode(value: str | None) -> str:
    """Decode an RFC 2047 encoded header (e.g. '=?utf-8?...?=') to plain text."""
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001
        return value


def _extract_text(msg: email.message.Message) -> str:
    """Pull a readable text body out of a parsed email (prefers text/plain)."""
    if msg.is_multipart():
        html_fallback = ""
        for part in msg.walk():
            ctype = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in disposition:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if ctype == "text/plain":
                return text
            if ctype == "text/html" and not html_fallback:
                html_fallback = text
        return html_fallback
    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")


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

    # -- Reading (IMAP) -----------------------------------------------------
    def _imap_config_error() -> str | None:
        if not (config.imap_host and config.imap_user and config.imap_password):
            return (
                "Email reading is not configured. Set IMAP_HOST (and IMAP_USER / "
                "IMAP_PASSWORD, or reuse the SMTP ones) to enable it."
            )
        return None

    def _open_mailbox(folder: str) -> imaplib.IMAP4_SSL:
        conn = imaplib.IMAP4_SSL(config.imap_host, config.imap_port)
        conn.login(config.imap_user, config.imap_password)
        # readonly=True guarantees fetching never flags messages as \\Seen.
        status, _ = conn.select(folder, readonly=True)
        if status != "OK":
            conn.logout()
            raise ValueError(f"cannot open folder '{folder}'")
        return conn

    def _build_criteria(query, from_addr, subject, unread_only, since_days) -> list[str]:
        criteria: list[str] = []
        if unread_only:
            criteria.append("UNSEEN")
        if from_addr:
            criteria += ["FROM", f'"{from_addr}"']
        if subject:
            criteria += ["SUBJECT", f'"{subject}"']
        if query:
            criteria += ["TEXT", f'"{query}"']
        if since_days:
            since = (datetime.now() - timedelta(days=int(since_days))).strftime("%d-%b-%Y")
            criteria += ["SINCE", since]
        return criteria or ["ALL"]

    def search_emails(
        query: str | None = None,
        from_addr: str | None = None,
        subject: str | None = None,
        unread_only: bool = False,
        since_days: int | None = None,
        folder: str = "INBOX",
        limit: int = 10,
    ) -> str:
        err = _imap_config_error()
        if err:
            return err
        limit = max(1, min(int(limit), 50))
        try:
            conn = _open_mailbox(folder)
        except Exception as exc:  # noqa: BLE001
            return f"Failed to open mailbox: {exc}"
        try:
            criteria = _build_criteria(query, from_addr, subject, unread_only, since_days)
            status, data = conn.uid("SEARCH", None, *criteria)
            if status != "OK":
                return "IMAP search failed."
            uids = data[0].split()
            if not uids:
                return "No matching emails found."
            uids = uids[-limit:][::-1]  # most recent first
            results = []
            for uid in uids:
                status, msg_data = conn.uid(
                    "FETCH", uid,
                    "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])",
                )
                if status != "OK" or not msg_data or msg_data[0] is None:
                    continue
                header = email.message_from_bytes(msg_data[0][1])
                results.append({
                    "uid": uid.decode(),
                    "from": _decode(header.get("From")),
                    "subject": _decode(header.get("Subject")),
                    "date": _decode(header.get("Date")),
                })
        except Exception as exc:  # noqa: BLE001
            return f"Error searching email: {exc}"
        finally:
            try:
                conn.logout()
            except Exception:  # noqa: BLE001
                pass

        import json

        return json.dumps({"folder": folder, "count": len(results), "emails": results})

    def read_email(uid: str, folder: str = "INBOX") -> str:
        err = _imap_config_error()
        if err:
            return err
        try:
            conn = _open_mailbox(folder)
        except Exception as exc:  # noqa: BLE001
            return f"Failed to open mailbox: {exc}"
        try:
            status, msg_data = conn.uid("FETCH", str(uid), "(BODY.PEEK[])")
            if status != "OK" or not msg_data or msg_data[0] is None:
                return f"Email with uid {uid} not found in '{folder}'."
            msg = email.message_from_bytes(msg_data[0][1])
        except Exception as exc:  # noqa: BLE001
            return f"Error reading email: {exc}"
        finally:
            try:
                conn.logout()
            except Exception:  # noqa: BLE001
                pass

        body = _extract_text(msg).strip()
        truncated = len(body) > _MAX_BODY_LEN
        if truncated:
            body = body[:_MAX_BODY_LEN] + "\n... (body truncated)"

        import json

        return json.dumps({
            "uid": str(uid),
            "from": _decode(msg.get("From")),
            "to": _decode(msg.get("To")),
            "cc": _decode(msg.get("Cc")),
            "subject": _decode(msg.get("Subject")),
            "date": _decode(msg.get("Date")),
            "body": body or "(no readable text body)",
        })

    registry.register(
        Tool(
            name="search_emails",
            description=(
                "Search a mailbox over IMAP (read-only) and return a list of "
                "matching messages with their uid, sender, subject and date. "
                "Filter by free-text query, sender, subject, unread status, or "
                "how recent (since_days). Use the returned uid with read_email to "
                "get the full message. Reading never marks messages as read."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Free-text to match in the message."},
                    "from_addr": {"type": "string", "description": "Filter by sender address/name."},
                    "subject": {"type": "string", "description": "Filter by subject text."},
                    "unread_only": {"type": "boolean", "description": "Only unread messages.", "default": False},
                    "since_days": {"type": "integer", "description": "Only messages from the last N days."},
                    "folder": {"type": "string", "description": "Mailbox folder.", "default": "INBOX"},
                    "limit": {"type": "integer", "description": "Max results (1-50, default 10).", "default": 10},
                },
                "additionalProperties": False,
            },
            handler=search_emails,
        )
    )
    registry.register(
        Tool(
            name="read_email",
            description=(
                "Read a single email's full content by its uid (from "
                "search_emails), returning sender, recipients, subject, date and "
                "the text body. Read-only — does not mark the message as seen."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "uid": {"type": "string", "description": "The message uid from search_emails."},
                    "folder": {"type": "string", "description": "Mailbox folder.", "default": "INBOX"},
                },
                "required": ["uid"],
                "additionalProperties": False,
            },
            handler=read_email,
        )
    )
