import imaplib
import email
import os
from email.header import decode_header
from dotenv import load_dotenv

load_dotenv()


def _decode_str(value):
    if value is None:
        return ""
    parts = []
    for fragment, charset in decode_header(value):
        if isinstance(fragment, bytes):
            parts.append(fragment.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(fragment)
    return "".join(parts)


def _get_body(msg):
    """Extract plain text body from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body += payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
    return body


def _get_attachments(msg):
    """Extract attachments as list of {filename, data}."""
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            disposition = str(part.get("Content-Disposition", ""))
            filename = part.get_filename()
            if filename or "attachment" in disposition:
                filename = _decode_str(filename or "unknown")
                data = part.get_payload(decode=True)
                if data:
                    attachments.append({"filename": filename, "data": data})
    return attachments


def fetch_emails(max_count=100):
    """Fetch emails from IMAP server. Returns list of email dicts."""
    host = os.getenv("IMAP_HOST", "").strip()
    port = int(os.getenv("IMAP_PORT", "993"))
    user = os.getenv("IMAP_USER", "").strip()
    password = os.getenv("IMAP_PASSWORD", "").strip()

    if not host or not user or not password:
        raise ValueError("IMAP設定が不完全です。サイドバーの「設定」からIMAPサーバー情報を入力してください。")

    conn = imaplib.IMAP4_SSL(host, port)
    conn.login(user, password)
    conn.select("INBOX")

    _, message_ids = conn.search(None, "ALL")
    all_ids = message_ids[0].split()
    target_ids = all_ids[-max_count:]  # newest N emails

    results = []
    for uid in target_ids:
        try:
            _, msg_data = conn.fetch(uid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            results.append({
                "message_id": msg.get("Message-ID", f"no-id-{uid.decode()}"),
                "subject": _decode_str(msg.get("Subject")),
                "sender": _decode_str(msg.get("From")),
                "received_at": msg.get("Date", ""),
                "body": _get_body(msg),
                "attachments": _get_attachments(msg),
            })
        except Exception:
            continue

    conn.close()
    conn.logout()
    return results
