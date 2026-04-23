# Larkメール返信ボタン 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 案件一覧・人材一覧・マッチング結果に「↩️ メール返信」ボタンを追加し、押下時にLark Mail APIで最新返信メールを検索して新タブで開く。

**Architecture:** Lark App Access TokenをメモリキャッシュしてLark Mail APIを呼び出し、返信スレッドの最新メールIDを取得する。LarkのメールIDはSQLiteにキャッシュして元メール検索の2回目以降をスキップ。返信検索は毎回最新を確認。API失敗時はLark受信箱検索URLにフォールバック。

**Tech Stack:** Python, requests, Streamlit (`st.link_button`, `st.session_state`), SQLite (ALTER TABLE), Lark Open API v1 (mail)

---

## ファイル構成

| ファイル | 変更種別 | 責務 |
|---------|----------|------|
| `requirements.txt` | 修正 | `requests` 追加 |
| `.env` | 修正 | `LARK_APP_ID` / `LARK_APP_SECRET` 追加 |
| `.env.example` | 修正 | 同上 |
| `src/database.py` | 修正 | `init_db()` に `lark_message_id` カラム追加、クエリ更新、`update_lark_message_id()` 追加 |
| `src/lark_mail.py` | 新規作成 | Token取得・メール検索・URL生成 |
| `tests/test_lark_mail.py` | 新規作成 | `lark_mail.py` のユニットテスト |
| `app.py` | 修正 | `_render_reply_button()` 追加、各画面にボタン追加、`_render_match_results()` 引数変更 |

---

## Task 1: 依存パッケージと環境変数の追加

**Files:**
- Modify: `requirements.txt`
- Modify: `.env`
- Modify: `.env.example`

- [ ] **Step 1: `requests` を requirements.txt に追加**

`requirements.txt` を以下に変更：
```
streamlit>=1.32.0
anthropic>=0.25.0
pdfplumber>=0.10.0
openpyxl>=3.1.0
python-dotenv>=1.0.0
pandas>=2.0.0
requests>=2.31.0
```

- [ ] **Step 2: `.env` に Lark 認証情報を追加**

`.env` の末尾に追加：
```
LARK_APP_ID=cli_a960e5c64835de17
LARK_APP_SECRET=otyvJOtD006vZEemqyfQUdfFjmwdGJuq
```

- [ ] **Step 3: `.env.example` に Lark 認証情報のプレースホルダーを追加**

`.env.example` の末尾に追加：
```
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
```

- [ ] **Step 4: requests をインストール**

```bash
pip install requests>=2.31.0
```

Expected output: Successfully installed requests-2.x.x（またはすでにインストール済みのメッセージ）

- [ ] **Step 5: コミット**

```bash
git add requirements.txt .env.example
git commit -m "chore: add requests dependency and Lark env vars"
```

（`.env` はコミット対象外）

---

## Task 2: DB変更 — `lark_message_id` カラムとクエリ更新

**Files:**
- Modify: `src/database.py`

- [ ] **Step 1: `init_db()` にカラム追加マイグレーションを追記**

`src/database.py` の `init_db()` 関数の `conn.executescript(...)` の直後（`with` ブロック内）に以下を追加：

```python
def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                subject TEXT,
                sender TEXT,
                received_at TEXT,
                body TEXT,
                email_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER REFERENCES emails(id),
                title TEXT,
                data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER REFERENCES emails(id),
                name TEXT,
                data TEXT,
                skill_sheet_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id),
                results TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # マイグレーション: lark_message_id カラムを追加（既存DB対応）
        try:
            conn.execute("ALTER TABLE emails ADD COLUMN lark_message_id TEXT")
        except Exception:
            pass  # カラムが既に存在する場合はスキップ
```

- [ ] **Step 2: `get_all_projects()` クエリを更新**

`src/database.py` の `get_all_projects()` を以下に変更：

```python
def get_all_projects():
    with get_connection() as conn:
        return conn.execute(
            "SELECT p.*, e.sender, e.received_at, e.body as email_body, "
            "e.message_id as imap_message_id, e.subject as email_subject, "
            "e.lark_message_id "
            "FROM projects p LEFT JOIN emails e ON p.email_id = e.id "
            "ORDER BY p.created_at DESC"
        ).fetchall()
```

- [ ] **Step 3: `get_all_candidates()` クエリを更新**

`src/database.py` の `get_all_candidates()` を以下に変更：

```python
def get_all_candidates():
    with get_connection() as conn:
        return conn.execute(
            "SELECT c.*, e.sender, e.received_at, e.body as email_body, "
            "e.message_id as imap_message_id, e.subject as email_subject, "
            "e.lark_message_id "
            "FROM candidates c LEFT JOIN emails e ON c.email_id = e.id "
            "ORDER BY c.created_at DESC"
        ).fetchall()
```

- [ ] **Step 4: `get_project_by_id()` クエリを更新**

マッチング画面からも案件のメール情報が必要なため更新：

```python
def get_project_by_id(project_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT p.*, e.sender, e.received_at, e.body as email_body, "
            "e.message_id as imap_message_id, e.subject as email_subject, "
            "e.lark_message_id "
            "FROM projects p LEFT JOIN emails e ON p.email_id = e.id "
            "WHERE p.id=?",
            (project_id,),
        ).fetchone()
```

- [ ] **Step 5: `update_lark_message_id()` を追加**

`src/database.py` のファイル末尾に追加：

```python
def update_lark_message_id(email_id: int, lark_message_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE emails SET lark_message_id=? WHERE id=?",
            (lark_message_id, email_id),
        )
```

- [ ] **Step 6: アプリ起動でマイグレーションが通ることを確認**

```bash
python -c "from src.database import init_db; init_db(); print('OK')"
```

Expected output: `OK`

- [ ] **Step 7: コミット**

```bash
git add src/database.py
git commit -m "feat: add lark_message_id column and update email join queries"
```

---

## Task 3: `src/lark_mail.py` — App Access Token 取得

**Files:**
- Create: `src/lark_mail.py`
- Create: `tests/test_lark_mail.py`

- [ ] **Step 1: テストファイルを作成し、Token取得のテストを書く**

`tests/test_lark_mail.py` を新規作成：

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_lark_mail.py -v
```

Expected: `ImportError` または `ModuleNotFoundError`（`src/lark_mail.py` が未作成のため）

- [ ] **Step 3: `src/lark_mail.py` を作成し、Token取得部分を実装**

```python
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


def get_app_access_token() -> str:
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
```

- [ ] **Step 4: Token取得テストが通ることを確認**

```bash
pytest tests/test_lark_mail.py::test_get_app_access_token_returns_token tests/test_lark_mail.py::test_get_app_access_token_uses_cache tests/test_lark_mail.py::test_get_app_access_token_refreshes_expired_cache tests/test_lark_mail.py::test_get_app_access_token_raises_on_lark_error -v
```

Expected: 4 tests PASSED

- [ ] **Step 5: コミット**

```bash
git add src/lark_mail.py tests/test_lark_mail.py
git commit -m "feat: add Lark app access token with memory cache"
```

---

## Task 4: `src/lark_mail.py` — メール検索とURL生成

**Files:**
- Modify: `src/lark_mail.py`
- Modify: `tests/test_lark_mail.py`

- [ ] **Step 1: メール検索・URL生成のテストを追記**

`tests/test_lark_mail.py` の末尾に追加：

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_lark_mail.py -v
```

Expected: 新しい8テストが `AttributeError` または `ImportError` で FAILED

- [ ] **Step 3: `src/lark_mail.py` にメール検索・URL生成を追記**

`src/lark_mail.py` の末尾（`get_app_access_token` の後）に追加：

```python
def _search_messages(token: str, subject: str) -> list:
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
    token = get_app_access_token()

    # 1. 常に最新の返信メールを検索
    reply_items = _search_messages(token, f"Re: {subject}")
    if reply_items:
        reply_items.sort(key=lambda x: x.get("date", 0), reverse=True)
        return reply_items[0]["message_id"]

    # 2. 返信なし → キャッシュ済みIDがあれば使用
    if cached_lark_id:
        return cached_lark_id

    # 3. 元メールを検索してキャッシュ
    original_items = _search_messages(token, subject)
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
```

- [ ] **Step 4: 全テストが通ることを確認**

```bash
pytest tests/test_lark_mail.py -v
```

Expected: 12 tests PASSED

- [ ] **Step 5: コミット**

```bash
git add src/lark_mail.py tests/test_lark_mail.py
git commit -m "feat: add Lark mail search and URL generation"
```

---

## Task 5: `app.py` — 共通ヘルパー `_render_reply_button()` 追加

**Files:**
- Modify: `app.py`

- [ ] **Step 1: `_render_reply_button()` を `app.py` に追加**

`app.py` の `_paginate()` 関数定義の直前（`PAGE_SIZES = [10, 20, 50, 100]` の直後）に追加：

```python
def _render_reply_button(
    email_id: int | None,
    subject: str | None,
    sender: str | None,
    cached_lark_id: str | None,
    key: str,
):
    """Larkメール返信ボタンを描画する。押下時にAPIでURL取得し st.link_button で表示。"""
    from src.lark_mail import get_latest_reply_lark_id, get_lark_url

    if not email_id or not subject:
        return

    url_key = f"reply_url_{key}"

    if st.button("↩️ メール返信", key=f"reply_btn_{key}"):
        with st.spinner("Larkメールを検索中..."):
            try:
                lark_id = get_latest_reply_lark_id(
                    email_id=email_id,
                    subject=subject,
                    sender=sender or "",
                    cached_lark_id=cached_lark_id,
                )
                st.session_state[url_key] = get_lark_url(lark_id, subject)
            except Exception:
                st.session_state[url_key] = get_lark_url(None, subject)

    if url_key in st.session_state:
        st.link_button("↗ Larkで開く", url=st.session_state[url_key])
```

- [ ] **Step 2: アプリが起動することを確認**

```bash
streamlit run app.py --server.headless true &
sleep 3
curl -s http://localhost:8501 | head -5
kill %1
```

Expected: HTMLが返ってくる（エラーなし）

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: add _render_reply_button helper"
```

---

## Task 6: `app.py` — 案件一覧に返信ボタンを追加

**Files:**
- Modify: `app.py`

- [ ] **Step 1: `show_projects()` にボタンを追加**

`app.py` の `show_projects()` 関数内、以下のブロック：

```python
            email_body = p["email_body"] if "email_body" in p.keys() else None
            if email_body:
                with st.expander("📧 メール全文を見る"):
                    st.text(email_body)
```

を以下に変更：

```python
            email_body = p["email_body"] if "email_body" in p.keys() else None
            if email_body:
                with st.expander("📧 メール全文を見る"):
                    st.text(email_body)
            _render_reply_button(
                email_id=p["email_id"] if "email_id" in p.keys() else None,
                subject=p["email_subject"] if "email_subject" in p.keys() else p["title"],
                sender=p["sender"] if "sender" in p.keys() else None,
                cached_lark_id=p["lark_message_id"] if "lark_message_id" in p.keys() else None,
                key=f"project_{p['id']}",
            )
```

- [ ] **Step 2: 案件一覧ページを手動確認**

```bash
streamlit run app.py
```

ブラウザで「📋 案件一覧」を開き、各案件カードに「↩️ メール返信」ボタンが表示されることを確認。

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: add reply button to project list"
```

---

## Task 7: `app.py` — 人材一覧に返信ボタンを追加

**Files:**
- Modify: `app.py`

- [ ] **Step 1: `show_candidates()` にボタンを追加**

`app.py` の `show_candidates()` 関数内、以下のブロック：

```python
            email_body = c["email_body"] if "email_body" in c.keys() else None
            if email_body:
                with st.expander("📧 メール全文を見る"):
                    st.text(email_body)
```

を以下に変更：

```python
            email_body = c["email_body"] if "email_body" in c.keys() else None
            if email_body:
                with st.expander("📧 メール全文を見る"):
                    st.text(email_body)
            _render_reply_button(
                email_id=c["email_id"] if "email_id" in c.keys() else None,
                subject=c["email_subject"] if "email_subject" in c.keys() else c["name"],
                sender=c["sender"] if "sender" in c.keys() else None,
                cached_lark_id=c["lark_message_id"] if "lark_message_id" in c.keys() else None,
                key=f"candidate_{c['id']}",
            )
```

- [ ] **Step 2: 人材一覧ページを手動確認**

ブラウザで「👤 人材一覧」を開き、各人材カードに「↩️ メール返信」ボタンが表示されることを確認。

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: add reply button to candidate list"
```

---

## Task 8: `app.py` — マッチング結果に返信ボタンを追加

**Files:**
- Modify: `app.py`

- [ ] **Step 1: `_render_match_results()` の引数に `project_row` を追加**

`app.py` の `_render_match_results` 関数シグネチャを変更：

```python
def _render_match_results(results: list, all_candidates, project_row=None):
```

- [ ] **Step 2: `_render_match_results()` 内の各候補者カードに2つのボタンを追加**

`_render_match_results()` 内の `st.markdown("---")` の直前（`if concerns:` ブロックの後）に追加：

```python
            if project_row is not None and candidate_row is not None:
                col_proj_btn, col_cand_btn = st.columns(2)
                with col_proj_btn:
                    _render_reply_button(
                        email_id=project_row["email_id"] if "email_id" in project_row.keys() else None,
                        subject=project_row["email_subject"] if "email_subject" in project_row.keys() else project_row["title"],
                        sender=project_row["sender"] if "sender" in project_row.keys() else None,
                        cached_lark_id=project_row["lark_message_id"] if "lark_message_id" in project_row.keys() else None,
                        key=f"match_proj_{project_row['id']}_{i}",
                    )
                with col_cand_btn:
                    _render_reply_button(
                        email_id=candidate_row["email_id"] if "email_id" in candidate_row.keys() else None,
                        subject=candidate_row["email_subject"] if "email_subject" in candidate_row.keys() else candidate_row["name"],
                        sender=candidate_row["sender"] if "sender" in candidate_row.keys() else None,
                        cached_lark_id=candidate_row["lark_message_id"] if "lark_message_id" in candidate_row.keys() else None,
                        key=f"match_cand_{cid}_{i}",
                    )
```

- [ ] **Step 3: `show_matching()` の `_render_match_results()` 呼び出しに `project_row` を渡す**

`show_matching()` 内の2箇所の `_render_match_results()` 呼び出しを変更：

```python
    # キャッシュ結果の表示（既存）
    if latest_match:
        st.info(f"前回のマッチング結果（{latest_match['created_at'][:16]}）を表示中")
        _render_match_results(json.loads(latest_match["results"]), candidates, project_row)

    # ...（中略）...

    if run_button:
        # ...（中略）...
            try:
                results = match_candidates(project_data, candidate_dicts)
                insert_match(selected_project_id, json.dumps(results, ensure_ascii=False))
                st.success("マッチング完了！上位5名を表示します。")
                _render_match_results(results, candidates, project_row)
```

- [ ] **Step 4: マッチング画面を手動確認**

ブラウザで「🔍 マッチング」を開き、マッチング結果の各候補者カードに「↩️ 案件メール返信」と「↩️ 人材メール返信」ボタンが横並びで表示されることを確認。

- [ ] **Step 5: 既存テストを実行して回帰がないことを確認**

```bash
pytest tests/ -v
```

Expected: 全テスト PASSED

- [ ] **Step 6: コミット**

```bash
git add app.py
git commit -m "feat: add reply buttons to match results"
```

---

## Task 9: Lark API 動作確認と必要に応じた修正

**Files:**
- Modify: `src/lark_mail.py`（必要な場合）

- [ ] **Step 1: App Access Token が実際に取得できることを確認**

```bash
python -c "
from src.lark_mail import get_app_access_token
try:
    token = get_app_access_token()
    print('Token OK:', token[:20], '...')
except Exception as e:
    print('Error:', e)
"
```

Expected: `Token OK: t-xxx...`

- [ ] **Step 2: メール検索APIが通るか確認**

```bash
python -c "
from src.lark_mail import get_app_access_token, _search_messages
token = get_app_access_token()
results = _search_messages(token, 'テスト')
print('Search result count:', len(results))
print('First item keys:', list(results[0].keys()) if results else 'No results')
"
```

Expected: エラーなし。結果0件でも可（メールが存在しない場合）。  
**403 / auth error の場合:** Step 3へ進む。

- [ ] **Step 3: API認証エラーの場合 — user_access_token フローを追加（必要な場合のみ）**

403エラーが出た場合、`src/lark_mail.py` の `get_latest_reply_lark_id()` を以下のように修正してフォールバック動作にする：

```python
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
    except Exception:
        return cached_lark_id  # API失敗 → キャッシュかNone

    if reply_items:
        reply_items.sort(key=lambda x: x.get("date", 0), reverse=True)
        return reply_items[0]["message_id"]

    if cached_lark_id:
        return cached_lark_id

    try:
        original_items = _search_messages(token, subject)
    except Exception:
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
```

- [ ] **Step 4: Lark ディープリンク URL 形式を確認・修正**

アプリでメール返信ボタンを押し、生成されたURLをブラウザで開く。リンク先が存在しない（404）の場合は、`src/lark_mail.py` の `LARK_TENANT` またはURLパスを以下の候補で試す：

```python
# 試す候補
f"{LARK_TENANT}/mail/detail/{lark_message_id}"   # デフォルト
f"{LARK_TENANT}/mail/inbox/{lark_message_id}"
f"{LARK_TENANT}/mail/message/{lark_message_id}"
```

正しい形式が判明したら `get_lark_url()` を修正し、`test_get_lark_url_with_message_id` のアサーションも合わせて修正する。

- [ ] **Step 5: 最終コミット**

```bash
git add src/lark_mail.py tests/test_lark_mail.py
git commit -m "fix: adjust Lark API error handling and URL format"
```

---

## 補足：フォールバック動作の確認

ボタン押下時にLark APIが使えない状況での期待動作：
- `get_latest_reply_lark_id()` が `None` を返す
- `get_lark_url(None, subject)` が `https://ajps62h9zjoo.jp.larksuite.com/mail/?q={subject}` を返す
- ユーザーはLark受信箱の検索結果ページへ遷移（手動で該当メールを探せる）
