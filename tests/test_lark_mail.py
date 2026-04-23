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

    with patch("src.lark_mail.requests.post", return_value=make_token_response("tok123")) as mock_post:
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

    with patch("src.lark_mail.requests.post", return_value=make_token_response("new_token")):
        token = lark_mail.get_app_access_token()

    assert token == "new_token"


def test_get_app_access_token_raises_on_lark_error():
    import src.lark_mail as lark_mail
    lark_mail._token_cache["token"] = None
    lark_mail._token_cache["expires_at"] = 0

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"code": 99991663, "msg": "invalid app_id"}

    with patch("src.lark_mail.requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Lark auth error"):
            lark_mail.get_app_access_token()
