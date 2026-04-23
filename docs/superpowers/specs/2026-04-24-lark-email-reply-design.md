# Larkメール返信ボタン 設計書

**日付:** 2026-04-24  
**対象ブランチ:** claude/ai-talent-project-matching-lozLt

---

## 概要

案件一覧・人材一覧・マッチング結果の各画面に「↩️ メール返信」ボタンを追加する。ボタン押下時、Lark Mail APIで該当メールのスレッドを検索し、最新の返信メールがあればそれを、なければ元メールをLarkウェブクライアントで新タブ表示する。

---

## アーキテクチャ

```
[Streamlit UI]
  → ↩️ メール返信ボタン押下
  → src/lark_mail.py に問い合わせ
      → App Access Token 取得（メモリキャッシュ、2時間有効）
      → Lark Mail API でスレッド検索（常に最新返信を検索）
          1. "Re: {subject}" で返信メールを検索 → 最新1件
          2. 返信なし → キャッシュ済み lark_message_id or 元件名+送信者で元メール検索
      → emails.lark_message_id に元メールIDをキャッシュ保存
  → Lark ディープリンクURL生成
  → st.link_button で新タブを開く

[フォールバック]
  API失敗 or メール未発見
  → https://ajps62h9zjoo.jp.larksuite.com/mail/?q={encoded_subject}
```

---

## DB変更

### `emails` テーブル カラム追加

```sql
ALTER TABLE emails ADD COLUMN lark_message_id TEXT;
```

**用途:** 元メールのLark内部IDをキャッシュし、2回目以降の元メール検索をスキップする。返信の最新確認は毎回APIで行う（キャッシュしない）。

### `get_all_projects()` / `get_all_candidates()` クエリ拡張

以下のカラムを追加でJOIN取得する：

| カラム | 用途 |
|--------|------|
| `e.message_id` | IMAP Message-ID（スレッド検索キー） |
| `e.subject` | 件名（返信メール検索に使用） |
| `e.lark_message_id` | キャッシュ済みLark ID |
| `e.id as email_id` | `update_lark_message_id()` 呼び出し用 |

### `database.py` 新関数

```python
def update_lark_message_id(email_id: int, lark_message_id: str) -> None
```

---

## `src/lark_mail.py` モジュール設計

### 定数

```python
LARK_BASE_URL = "https://open.larksuite.com/open-apis"
LARK_TENANT = "https://ajps62h9zjoo.jp.larksuite.com"
LARK_APP_ID = os.getenv("LARK_APP_ID", "cli_a960e5c64835de17")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET")
```

### 関数

#### `get_app_access_token() -> str`

- `POST /auth/v3/app_access_token/internal` でtokenを取得
- メモリキャッシュ（有効期限 - 5分のマージン）
- 失敗時は例外を投げる

#### `get_latest_reply_lark_id(email_id, subject, sender, cached_lark_id) -> str | None`

```
1. Lark API で "Re: {subject}" を検索（page_size=20、日付降順）
   → 返信があれば最新1件のlark_message_idを返す

2. 返信なし:
   a. cached_lark_id があればそれを返す
   b. なければ Lark API で subject + from:{sender} で元メールを検索
      → 見つかったら emails テーブルの lark_message_id を更新してキャッシュ
      → 見つからなければ None を返す
```

**使用するLark Mail API:**
```
GET /mail/v1/user_mailboxes/me/messages
    ?subject={subject}
    &page_size=20
Authorization: Bearer {app_access_token}
```

#### `get_lark_url(lark_message_id, subject) -> str`

```python
if lark_message_id:
    return f"{LARK_TENANT}/mail/detail/{lark_message_id}"
else:
    return f"{LARK_TENANT}/mail/?q={urllib.parse.quote(subject)}"
```

---

## UI変更（`app.py`）

### 共通ヘルパー `_render_reply_button(email_id, subject, sender, cached_lark_id, key)`

```
押下 → spinner表示 → get_latest_reply_lark_id() 呼び出し
     → get_lark_url() でURL生成
     → st.session_state[f"reply_url_{key}"] に保存
     → st.link_button("Larkで開く →", url=...) を表示
     → 失敗時: st.warning("メールが見つかりませんでした")
```

`st.session_state` にURLを保存することで、rerun後もリンクが消えない。

### `show_projects()` 変更

各案件のExpanderに追加：
```python
# 既存
if email_body:
    with st.expander("📧 メール全文を見る"):
        st.text(email_body)

# 新規追加
_render_reply_button(
    email_id=p["email_id"],
    subject=p["subject"],
    sender=p["sender"],
    cached_lark_id=p["lark_message_id"],
    key=f"project_{p['id']}"
)
```

### `show_candidates()` 変更

同様に各人材カードに `_render_reply_button()` を追加。

### `_render_match_results(results, all_candidates, project_row)` 変更

引数に `project_row` を追加（現在の案件情報を受け取る）。各候補者カードに2ボタン追加：

```python
col_proj, col_cand = st.columns(2)
with col_proj:
    _render_reply_button(
        email_id=project_row["email_id"],
        subject=project_row["subject"],
        ...
        key=f"match_project_{project_row['id']}_{i}"
    )
with col_cand:
    _render_reply_button(
        email_id=candidate_row["email_id"],
        subject=candidate_row["subject"],
        ...
        key=f"match_cand_{cid}_{i}"
    )
```

### `show_matching()` 変更

`_render_match_results()` 呼び出し時に `project_row` を渡す。

---

## エラーハンドリング

| 状況 | 対応 |
|------|------|
| App Token取得失敗 | `st.error()` でメッセージ表示、ボタン無効化 |
| メール未発見 | フォールバック検索URLで開く |
| API呼び出し失敗（5xx等） | フォールバック検索URLで開く |
| `lark_message_id` が空 | フォールバック検索URLで開く |
| Auth失敗（user token必要） | `st.warning()` で「Lark設定を確認してください」表示 |

---

## 環境変数追加（`.env`）

```
LARK_APP_ID=cli_a960e5c64835de17
LARK_APP_SECRET=otyvJOtD006vZEemqyfQUdfFjmwdGJuq
```

---

## 未確定事項

- **Lark Mail APIのURL形式:** `/mail/detail/{lark_message_id}` が正しいか実装後に検証が必要
- **`user_mailboxes/me` のスコープ:** `tenant_access_token` で外部接続済みアカウント（info@falcs.jp）にアクセスできるか実装後に検証。NGの場合はOAuth `user_access_token` フローを追加実装する
