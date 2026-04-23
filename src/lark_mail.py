import os
import time
import urllib.parse
import requests
from dotenv import load_dotenv
from src.database import update_lark_message_id

load_dotenv()

LARK_BASE_URL = "https://open.larksuite.com/open-apis"
LARK_TENANT = "https://ajps62h9zjoo.jp.larksuite.com"
LARK_APP_ID = os.getenv("LARK_APP_ID", "")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "")
LARK_MAILBOX_USER = os.getenv("IMAP_USER", "")

_token_cache: dict = {"token": None, "expires_at": 0.0}
# Note: not thread-safe; assumes single-threaded Streamlit execution


def get_app_access_token() -> str:
    if not LARK_APP_ID or not LARK_APP_SECRET:
        raise RuntimeError("LARK_APP_ID and LARK_APP_SECRET must be set in environment")
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    resp = requests.post(
        f"{LARK_BASE_URL}/auth/v3/app_access_token/internal",
        json={"app_id": LARK_APP_ID, "app_secret": LARK_APP_SECRET},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Lark auth error: {data.get('msg')}")

    token = data["app_access_token"]
    expire = data.get("expire", 7200)
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + expire - 300
    return token


def _search_messages(token: str, subject: str) -> list:
    if not LARK_MAILBOX_USER:
        raise RuntimeError("IMAP_USER (LARK_MAILBOX_USER) must be set in environment")
    mailbox_id = urllib.parse.quote(LARK_MAILBOX_USER, safe="")
    resp = requests.get(
        f"{LARK_BASE_URL}/mail/v1/user_mailboxes/{mailbox_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={"subject": subject, "page_size": 20},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        return []
    return data.get("data", {}).get("items", [])


def get_latest_reply_lark_id(
    email_id: int,
    subject: str,
    sender: str,
    cached_lark_id: str | None,
) -> str | None:
    try:
        token = get_app_access_token()
    except Exception:
        return None

    try:
        reply_items = _search_messages(token, f"Re: {subject}")
    except requests.exceptions.RequestException:
        return cached_lark_id  # API失敗 → キャッシュかNone

    if reply_items:
        # 送信者でフィルター（異なる会社の同件名メールを除外）
        sender_lower = sender.lower()
        filtered = [
            item for item in reply_items
            if item.get("from", {}).get("mail_address", "").lower() in sender_lower
            or sender_lower in item.get("from", {}).get("mail_address", "").lower()
        ]
        candidates = filtered if filtered else reply_items
        candidates.sort(key=lambda x: x.get("date", 0), reverse=True)
        return candidates[0]["message_id"]

    # 2. 返信なし → キャッシュ済みIDがあれば使用
    if cached_lark_id:
        return cached_lark_id

    # 3. 元メールを検索してキャッシュ
    try:
        original_items = _search_messages(token, subject)
    except requests.exceptions.RequestException:
        return None

    if original_items:
        for item in original_items:
            item_sender = item.get("from", {}).get("mail_address", "")
            if item_sender and item_sender.lower() in sender.lower():
                lark_id = item["message_id"]
                update_lark_message_id(email_id, lark_id)
                return lark_id
        lark_id = original_items[0]["message_id"]
        update_lark_message_id(email_id, lark_id)
        return lark_id

    return None


def get_lark_url(lark_message_id: str | None, subject: str) -> str:
    if lark_message_id:
        return f"{LARK_TENANT}/mail/detail/{lark_message_id}"
    return f"{LARK_TENANT}/mail/?q={urllib.parse.quote(subject)}"
