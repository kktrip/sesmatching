import imaplib
import email
import os
import re
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


def _connect():
    host = os.getenv("IMAP_HOST", "").strip()
    port = int(os.getenv("IMAP_PORT", "993"))
    user = os.getenv("IMAP_USER", "").strip()
    password = os.getenv("IMAP_PASSWORD", "").strip()

    if not host or not user or not password:
        raise ValueError("IMAP設定が不完全です。サイドバーの「設定」からIMAPサーバー情報を入力してください。")

    conn = imaplib.IMAP4_SSL(host, port)
    conn.login(user, password)
    conn.select("INBOX")
    return conn


def _batch_fetch_message_ids(conn, seq_nums):
    """
    Batch-fetch just Message-ID headers for seq_nums.
    Returns {seq_bytes: message_id_str}.
    """
    result = {}
    CHUNK = 200

    for i in range(0, len(seq_nums), CHUNK):
        chunk = seq_nums[i:i + CHUNK]
        seq_str = b",".join(chunk)
        try:
            _, data = conn.fetch(seq_str, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
            for item in data:
                if not isinstance(item, tuple) or len(item) < 2:
                    continue
                # item[0] = b'42 (BODY[HEADER.FIELDS ("MESSAGE-ID")] {nn}'
                m = re.match(rb"^(\d+)\s", item[0])
                if not m:
                    continue
                seq = m.group(1)
                msg = email.message_from_bytes(item[1])
                msg_id = msg.get("Message-ID", "").strip()
                result[seq] = msg_id or f"no-id-{seq.decode()}"
        except Exception:
            # Fallback: individual fetches
            for seq in chunk:
                try:
                    _, hdr_data = conn.fetch(seq, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
                    if hdr_data and isinstance(hdr_data[0], tuple):
                        msg = email.message_from_bytes(hdr_data[0][1])
                        msg_id = msg.get("Message-ID", "").strip()
                        result[seq] = msg_id or f"no-id-{seq.decode()}"
                except Exception:
                    result[seq] = f"no-id-{seq.decode()}"

    return result


def fetch_emails(max_count=100, skip_ids=None):
    """
    Fetch emails from IMAP server.

    Two-phase: first batch-fetch Message-ID headers to identify new emails,
    then download full RFC822 only for those not in skip_ids.

    skip_ids: set/frozenset of message_id strings already in DB.
    """
    skip_ids = frozenset(skip_ids or [])
    conn = _connect()

    try:
        _, search_data = conn.search(None, "ALL")
        all_seq = search_data[0].split()
        target_seq = all_seq[-max_count:]

        if not target_seq:
            return []

        # Phase 1: fast batch header fetch to find new emails
        seq_to_msgid = _batch_fetch_message_ids(conn, target_seq)

        # Only download full content for emails not already in DB
        new_seqs = [
            s for s in target_seq
            if seq_to_msgid.get(s, f"no-id-{s.decode()}") not in skip_ids
        ]

        # Phase 2: full RFC822 fetch for new emails only
        results = []
        for seq in new_seqs:
            try:
                _, msg_data = conn.fetch(seq, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                results.append({
                    "message_id": seq_to_msgid.get(seq, f"no-id-{seq.decode()}"),
                    "subject": _decode_str(msg.get("Subject")),
                    "sender": _decode_str(msg.get("From")),
                    "received_at": msg.get("Date", ""),
                    "body": _get_body(msg),
                    "attachments": _get_attachments(msg),
                })
            except Exception:
                continue
    finally:
        conn.close()
        conn.logout()

    return results
