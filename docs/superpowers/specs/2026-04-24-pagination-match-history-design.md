# ページネーション & マッチング履歴一覧 設計

**日付:** 2026-04-24  
**対象ファイル:** `app.py`, `src/database.py`

---

## 概要

2つの機能を同一スコープで実装する。

1. **ページネーション** — 案件一覧・人材一覧・マッチング履歴一覧に共通のページャーUIを追加。1ページ表示件数を 10/20/50/100 件から選択可能（デフォルト 10 件）。
2. **マッチング履歴一覧** — サイドバーに「📜 マッチング履歴」を新メニューとして追加し、過去のマッチング実行結果を一覧表示する。

---

## アーキテクチャ

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| `app.py` | `_paginate()` ヘルパー追加、`show_projects()`/`show_candidates()` にページャー適用、`show_match_history()` 新規追加、サイドバーメニューとルーターに履歴ページを追加 |
| `src/database.py` | `get_all_matches()` 関数追加 |

---

## 詳細設計

### 1. `_paginate(items, key)` — `app.py`

**責務:** リストのスライスとページャーUIの描画を一括で担う共通ヘルパー。

**シグネチャ:**
```python
def _paginate(items: list, key: str) -> list:
    ...
    return items[start:start + page_size]
```

**セッションステート:**
- `st.session_state[f"page_size_{key}"]` — 選択中のページサイズ（デフォルト 10）
- `st.session_state[f"page_{key}"]` — 現在のページ番号（0始まり）

**UIレイアウト（上部）:**
```
[ 件数: N件 ]        [ selectbox: 10 / 20 / 50 / 100件 ]
[ ← 前へ ]  [ ページ X / Y ]  [ 次へ → ]
```

- ページサイズ変更時は `st.session_state[f"page_{key}"] = 0` にリセットして `st.rerun()`
- 現在ページが総ページ数を超えた場合は自動的に最終ページにクランプ
- `key` で名前空間を分けるため、異なるページ間でセッション状態が混ざらない

**ページャー適用対象:**

| ページ関数 | `key` |
|------------|-------|
| `show_projects()` | `"projects"` |
| `show_candidates()` | `"candidates"` |
| `show_match_history()` | `"history"` |

ダッシュボードの「最近の案件/人材」（5件固定）には適用しない。

---

### 2. `get_all_matches()` — `src/database.py`

```python
def get_all_matches():
    with get_connection() as conn:
        return conn.execute(
            "SELECT m.*, p.title as project_title "
            "FROM matches m LEFT JOIN projects p ON m.project_id = p.id "
            "ORDER BY m.created_at DESC"
        ).fetchall()
```

返すカラム: `id`, `project_id`, `results`(JSON文字列), `created_at`, `project_title`

---

### 3. `show_match_history()` — `app.py`

**表示仕様:**

- ページ上部に `_paginate(matches, "history")` を呼び出す
- 各履歴エントリは `st.container()` + `st.markdown("---")` で区切る（エクスパンダーなし、常時表示）
- エントリのヘッダー: `📋 {project_title}　｜　{created_at[:16]}`（`st.subheader` または `st.markdown`）
- TOP5を縦に列挙。各行のカラム構成:

```
| 順位ラベル | 人材名 | 総合スコア | スキルマッチスコア |
```

- 順位ラベル: `["🥇", "🥈", "🥉", "4位", "5位"]`
- `results` は `json.loads()` でパース。`score`, `skill_match_score`, `name` フィールドを使用
- 履歴が0件の場合: `st.info("マッチング履歴がありません。")` を表示して return

---

### 4. サイドバーとルーターの変更 — `app.py`

**サイドバー `st.radio` オプションに追加:**
```python
["📊 ダッシュボード", "📋 案件一覧", "👤 人材一覧", "🔍 マッチング", "📜 マッチング履歴", "⚙️ 設定"]
```

**ルーターに追加:**
```python
elif page == "📜 マッチング履歴":
    show_match_history()
```

---

## 完了基準

- [ ] 案件一覧でページサイズ 10/20/50/100 を切り替えられる
- [ ] 人材一覧でページサイズ 10/20/50/100 を切り替えられる
- [ ] ページ切り替え時に表示内容が正しく更新される
- [ ] ページサイズ変更時に1ページ目にリセットされる
- [ ] サイドバーに「📜 マッチング履歴」が表示される
- [ ] マッチング履歴一覧にページャーが機能する
- [ ] 各履歴エントリに案件名・日時・TOP5（名前+スコア）が表示される
- [ ] 履歴が0件の場合にinfoメッセージが表示される
