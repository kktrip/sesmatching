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
