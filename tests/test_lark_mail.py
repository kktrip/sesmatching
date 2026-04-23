import pytest
from unittest.mock import patch, MagicMock
import time


def make_token_response(token="test_token", expire=7200):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        "code": 0,
        "app_access_token": token,
        "expire": expire,
    }
    return mock


def test_get_app_access_token_returns_token():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = None
    lark_mail._token_cache["expires_at"] = 0

    with patch("src.lark_mail.LARK_APP_ID", "test_app_id"), \
         patch("src.lark_mail.LARK_APP_SECRET", "test_app_secret"), \
         patch("src.lark_mail.requests.post", return_value=make_token_response("tok123")) as mock_post:
        token = lark_mail.get_app_access_token()

    assert token == "tok123"
    mock_post.assert_called_once()


def test_get_app_access_token_uses_cache():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = "cached_token"
    lark_mail._token_cache["expires_at"] = time.time() + 3600

    with patch("src.lark_mail.requests.post") as mock_post:
        token = lark_mail.get_app_access_token()

    assert token == "cached_token"
    mock_post.assert_not_called()


def test_get_app_access_token_refreshes_expired_cache():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = "old_token"
    lark_mail._token_cache["expires_at"] = time.time() - 1  # 期限切れ

    with patch("src.lark_mail.LARK_APP_ID", "test_app_id"), \
         patch("src.lark_mail.LARK_APP_SECRET", "test_app_secret"), \
         patch("src.lark_mail.requests.post", return_value=make_token_response("new_token")):
        token = lark_mail.get_app_access_token()

    assert token == "new_token"


def test_get_app_access_token_raises_on_lark_error():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = None
    lark_mail._token_cache["expires_at"] = 0

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"code": 99991663, "msg": "invalid app_id"}

    with patch("src.lark_mail.LARK_APP_ID", "test_app_id"), \
         patch("src.lark_mail.LARK_APP_SECRET", "test_app_secret"), \
         patch("src.lark_mail.requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Lark auth error"):
            lark_mail.get_app_access_token()


def make_messages_response(items):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"code": 0, "data": {"items": items, "has_more": False}}
    return mock


def make_empty_response():
    return make_messages_response([])


def make_item(msg_id, subject, sender_mail, date=1000):
    return {
        "message_id": msg_id,
        "subject": subject,
        "from": {"mail_address": sender_mail},
        "date": date,
    }


def test_get_latest_reply_returns_newest_reply():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = "tok"
    lark_mail._token_cache["expires_at"] = time.time() + 3600

    replies = [
        make_item("reply_old", "Re: 案件A", "sender@example.com", date=100),
        make_item("reply_new", "Re: 案件A", "sender@example.com", date=999),
    ]

    with patch("src.lark_mail.requests.get", return_value=make_messages_response(replies)):
        result = lark_mail.get_latest_reply_lark_id(
            email_id=1, subject="案件A", sender="sender@example.com", cached_lark_id=None
        )

    assert result == "reply_new"


def test_get_latest_reply_uses_cached_id_when_no_reply():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = "tok"
    lark_mail._token_cache["expires_at"] = time.time() + 3600

    with patch("src.lark_mail.requests.get", return_value=make_empty_response()):
        result = lark_mail.get_latest_reply_lark_id(
            email_id=1, subject="案件A", sender="sender@example.com", cached_lark_id="cached_id_123"
        )

    assert result == "cached_id_123"


def test_get_latest_reply_searches_original_when_no_cache():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = "tok"
    lark_mail._token_cache["expires_at"] = time.time() + 3600

    original = make_item("orig_id", "案件A", "sender@example.com")

    def side_effect(*args, **kwargs):
        params = kwargs.get("params", {})
        if params.get("subject", "").startswith("Re:"):
            return make_empty_response()
        return make_messages_response([original])

    with patch("src.lark_mail.requests.get", side_effect=side_effect):
        with patch("src.lark_mail.update_lark_message_id") as mock_update:
            result = lark_mail.get_latest_reply_lark_id(
                email_id=5, subject="案件A", sender="sender@example.com", cached_lark_id=None
            )

    assert result == "orig_id"
    mock_update.assert_called_once_with(5, "orig_id")


def test_get_latest_reply_returns_none_when_nothing_found():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = "tok"
    lark_mail._token_cache["expires_at"] = time.time() + 3600

    with patch("src.lark_mail.requests.get", return_value=make_empty_response()):
        result = lark_mail.get_latest_reply_lark_id(
            email_id=1, subject="案件A", sender="sender@example.com", cached_lark_id=None
        )

    assert result is None


def test_get_lark_url_with_message_id():
    from src.lark_mail import get_lark_url
    url = get_lark_url("msg_abc123", "案件A")
    assert url == "https://ajps62h9zjoo.jp.larksuite.com/mail/detail/msg_abc123"


def test_get_lark_url_fallback_without_message_id():
    from src.lark_mail import get_lark_url
    url = get_lark_url(None, "案件A テスト")
    assert "ajps62h9zjoo.jp.larksuite.com/mail/" in url
    assert "%E6%A1%88%E4%BB%B6" in url  # URL-encoded "案件"


def test_get_latest_reply_returns_none_on_token_error():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = None
    lark_mail._token_cache["expires_at"] = 0

    with patch("src.lark_mail.LARK_APP_ID", "test_app_id"), \
         patch("src.lark_mail.LARK_APP_SECRET", "test_app_secret"), \
         patch("src.lark_mail.requests.post", side_effect=RuntimeError("network error")):
        result = lark_mail.get_latest_reply_lark_id(
            email_id=1, subject="案件A", sender="sender@example.com", cached_lark_id="cached_id"
        )
    assert result is None


def test_get_latest_reply_returns_cached_id_on_reply_search_error():
    import src.lark_mail as lark_mail
    import requests as req
    lark_mail._token_cache["token"] = "tok"
    lark_mail._token_cache["expires_at"] = time.time() + 3600

    with patch("src.lark_mail.requests.get", side_effect=req.exceptions.RequestException("400 Bad Request")):
        result = lark_mail.get_latest_reply_lark_id(
            email_id=1, subject="案件A", sender="sender@example.com", cached_lark_id="cached_id_123"
        )
    assert result == "cached_id_123"


def test_get_latest_reply_returns_none_on_original_search_error():
    import src.lark_mail as lark_mail
    import requests as req
    lark_mail._token_cache["token"] = "tok"
    lark_mail._token_cache["expires_at"] = time.time() + 3600

    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return make_empty_response()  # reply search returns empty
        raise req.exceptions.RequestException("400 Bad Request")  # original search fails

    with patch("src.lark_mail.requests.get", side_effect=side_effect):
        result = lark_mail.get_latest_reply_lark_id(
            email_id=1, subject="案件A", sender="sender@example.com", cached_lark_id=None
        )
    assert result is None


def test_get_app_access_token_raises_on_empty_credentials():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = None
    lark_mail._token_cache["expires_at"] = 0

    with patch("src.lark_mail.LARK_APP_ID", ""), \
         patch("src.lark_mail.LARK_APP_SECRET", ""):
        with pytest.raises(RuntimeError, match="LARK_APP_ID and LARK_APP_SECRET must be set"):
            lark_mail.get_app_access_token()


def test_search_messages_raises_on_empty_mailbox_user():
    import src.lark_mail as lark_mail
    with patch("src.lark_mail.LARK_MAILBOX_USER", ""):
        with pytest.raises(RuntimeError, match="IMAP_USER"):
            lark_mail._search_messages("some_token", "subject")


def test_get_latest_reply_raises_on_empty_mailbox_user():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = "tok"
    lark_mail._token_cache["expires_at"] = time.time() + 3600

    with patch("src.lark_mail.LARK_MAILBOX_USER", ""):
        with pytest.raises(RuntimeError, match="IMAP_USER"):
            lark_mail.get_latest_reply_lark_id(
                email_id=1, subject="案件A", sender="sender@example.com", cached_lark_id=None
            )


def test_get_latest_reply_falls_back_to_unfiltered_when_sender_mismatch():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = "tok"
    lark_mail._token_cache["expires_at"] = time.time() + 3600

    # No reply matches sender "original@example.com" → filtered list is empty → fallback to all replies.
    # Three items at different dates: fallback must sort descending and return newest.
    replies = [
        make_item("reply_newest", "Re: 案件B", "other@example.com", date=999),
        make_item("reply_mid",    "Re: 案件B", "other@example.com", date=500),
        make_item("reply_oldest", "Re: 案件B", "other@example.com", date=100),
    ]

    with patch("src.lark_mail.requests.get", return_value=make_messages_response(replies)):
        result = lark_mail.get_latest_reply_lark_id(
            email_id=1, subject="案件B", sender="original@example.com", cached_lark_id=None
        )

    # All senders mismatch → fallback to unfiltered list → newest (date=999) wins.
    assert result == "reply_newest"
