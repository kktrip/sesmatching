# ページネーション & マッチング履歴一覧 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 案件一覧・人材一覧・新規マッチング履歴ページに共通ページャーを追加し、サイドバーに「📜 マッチング履歴」メニューを新設する。

**Architecture:** `_paginate(items, key)` ヘルパーを `app.py` に追加して全ページで再利用する。`src/database.py` に `get_all_matches()` を追加して過去の全マッチング結果を取得する。UI はすべて `st.session_state` で状態管理し、ページサイズ変更・ページ遷移は `st.rerun()` で反映する。

**Tech Stack:** Python 3.x / Streamlit / SQLite (`sqlite3.Row`)

---

### 変更ファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `src/database.py` | `get_all_matches()` 追加（line 124 付近） |
| `app.py` | import に `get_all_matches` 追加、`_paginate()` ヘルパー追加（line 714 付近）、`show_projects()` と `show_candidates()` にページャー適用、`show_match_history()` 新規追加（line 1006 付近）、サイドバー radio + ルーターに履歴ページ追加 |

---

### Task 1: `get_all_matches()` を `src/database.py` に追加

**Files:**
- Modify: `src/database.py:118-123`（`get_latest_match` の直後）

- [ ] **Step 1: `get_all_matches()` を追加する**

`src/database.py` の `get_latest_match()` 関数（line 118 終わり）の直後に追記する：

```python
def get_all_matches():
    with get_connection() as conn:
        return conn.execute(
            "SELECT m.*, p.title as project_title "
            "FROM matches m LEFT JOIN projects p ON m.project_id = p.id "
            "ORDER BY m.created_at DESC"
        ).fetchall()
```

- [ ] **Step 2: Python で関数をインポートできることを確認する**

```bash
cd C:\Users\kazua\app\sesmatching
python -c "from src.database import get_all_matches; print('OK')"
```

期待出力: `OK`

- [ ] **Step 3: コミットする**

```bash
git add src/database.py
git commit -m "feat: get_all_matches()を追加"
```

---

### Task 2: `_paginate()` ヘルパーを `app.py` に追加し import を更新

**Files:**
- Modify: `app.py:13-28`（import ブロック）
- Modify: `app.py:714`（`# ── Pages ──` コメント直前、`show_dashboard()` 定義の前）

- [ ] **Step 1: import に `get_all_matches` を追加する**

`app.py` の `from src.database import (` ブロック（line 13-28）を以下に置き換える：

```python
from src.database import (
    init_db,
    get_stats,
    get_all_projects,
    get_all_candidates,
    get_project_by_id,
    get_candidate_by_id,
    get_latest_match,
    get_all_matches,
    insert_email,
    insert_project,
    insert_candidate,
    insert_match,
    get_all_message_ids,
    project_exists,
    candidate_exists,
)
```

- [ ] **Step 2: `_paginate()` 関数を追加する**

`app.py` の `# ────────────────────────────────────────────` / `# Pages` コメント（line 712-714 付近）の直後、`def show_dashboard():` の直前に以下を挿入する：

```python
def _paginate(items: list, key: str) -> list:
    size_key = f"page_size_{key}"
    page_key = f"page_{key}"

    if size_key not in st.session_state:
        st.session_state[size_key] = 10
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    total = len(items)
    page_size = st.session_state[size_key]
    total_pages = max(1, (total + page_size - 1) // page_size)

    if st.session_state[page_key] >= total_pages:
        st.session_state[page_key] = total_pages - 1

    col_count, col_size = st.columns([3, 2])
    with col_count:
        st.caption(f"{total} 件")
    with col_size:
        new_size = st.selectbox(
            "表示件数",
            [10, 20, 50, 100],
            index=[10, 20, 50, 100].index(page_size),
            key=f"selectbox_{key}",
            label_visibility="collapsed",
        )
        if new_size != page_size:
            st.session_state[size_key] = new_size
            st.session_state[page_key] = 0
            st.rerun()

    current_page = st.session_state[page_key]
    col_prev, col_label, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("← 前へ", key=f"prev_{key}", disabled=(current_page == 0)):
            st.session_state[page_key] -= 1
            st.rerun()
    with col_label:
        st.caption(f"ページ {current_page + 1} / {total_pages}")
    with col_next:
        if st.button("次へ →", key=f"next_{key}", disabled=(current_page >= total_pages - 1)):
            st.session_state[page_key] += 1
            st.rerun()

    start = current_page * page_size
    return items[start : start + page_size]
```

- [ ] **Step 3: 構文エラーがないか確認する**

```bash
python -c "import py_compile; py_compile.compile('app.py'); print('OK')"
```

期待出力: `OK`

- [ ] **Step 4: コミットする**

```bash
git add app.py
git commit -m "feat: _paginate()ヘルパーを追加しget_all_matchesをimport"
```

---

### Task 3: `show_projects()` にページャーを適用

**Files:**
- Modify: `app.py:805-808`（`show_projects()` 内のフィルタ後の caption + ループ）

- [ ] **Step 1: 既存の `st.caption` を削除し `_paginate` を呼び出す**

`show_projects()` 内の以下の2行（line 806-808 付近）：

```python
    filtered = [(p, data) for p, data in projects_with_data if _match_project(p, data)]
    st.caption(f"{len(filtered)} 件 / 全 {len(projects)} 件")

    for p, data in filtered:
```

を以下に置き換える：

```python
    filtered = [(p, data) for p, data in projects_with_data if _match_project(p, data)]
    st.caption(f"{len(filtered)} 件 / 全 {len(projects)} 件")
    paginated = _paginate(filtered, "projects")

    for p, data in paginated:
```

- [ ] **Step 2: 構文エラーがないか確認する**

```bash
python -c "import py_compile; py_compile.compile('app.py'); print('OK')"
```

期待出力: `OK`

- [ ] **Step 3: コミットする**

```bash
git add app.py
git commit -m "feat: 案件一覧にページネーションを追加"
```

---

### Task 4: `show_candidates()` にページャーを適用

**Files:**
- Modify: `app.py:882-885`（`show_candidates()` 内のフィルタ後の caption + ループ）

- [ ] **Step 1: 既存の `st.caption` の後に `_paginate` を追加する**

`show_candidates()` 内の以下の2行（line 883-885 付近）：

```python
    filtered = [(c, data) for c, data in candidates_with_data if _match_candidate(c, data)]
    st.caption(f"{len(filtered)} 件 / 全 {len(candidates)} 件")

    for c, data in filtered:
```

を以下に置き換える：

```python
    filtered = [(c, data) for c, data in candidates_with_data if _match_candidate(c, data)]
    st.caption(f"{len(filtered)} 件 / 全 {len(candidates)} 件")
    paginated = _paginate(filtered, "candidates")

    for c, data in paginated:
```

- [ ] **Step 2: 構文エラーがないか確認する**

```bash
python -c "import py_compile; py_compile.compile('app.py'); print('OK')"
```

期待出力: `OK`

- [ ] **Step 3: コミットする**

```bash
git add app.py
git commit -m "feat: 人材一覧にページネーションを追加"
```

---

### Task 5: `show_match_history()` 追加・サイドバー + ルーター更新

**Files:**
- Modify: `app.py:1006`（`def show_settings():` の直前に `show_match_history()` を挿入）
- Modify: `app.py:601-605`（サイドバー `st.radio` オプション）
- Modify: `app.py:1061-1070`（ルーター `if/elif` チェーン）

- [ ] **Step 1: `show_match_history()` を `show_settings()` の直前に挿入する**

`app.py` の `def show_settings():` の直前（line 1006 付近）に以下を挿入する：

```python
def show_match_history():
    st.header("📜 マッチング履歴")
    matches = list(get_all_matches())

    if not matches:
        st.info("マッチング履歴がありません。")
        return

    paginated = _paginate(matches, "history")

    rank_labels = ["🥇", "🥈", "🥉", "4位", "5位"]

    for m in paginated:
        project_title = m["project_title"] or f"案件ID: {m['project_id']}"
        created_at = m["created_at"][:16]

        with st.container():
            st.subheader(f"📋 {project_title}　｜　{created_at}")

            header_cols = st.columns([0.5, 2, 1, 1])
            header_cols[0].markdown("**順位**")
            header_cols[1].markdown("**人材名**")
            header_cols[2].markdown("**総合スコア**")
            header_cols[3].markdown("**スキルスコア**")

            results = json.loads(m["results"])
            for i, r in enumerate(results[:5]):
                rank = rank_labels[i] if i < len(rank_labels) else f"{i + 1}位"
                name = r.get("name", "氏名不明")
                score = r.get("score", 0)
                skill_score = r.get("skill_match_score", 0)

                row_cols = st.columns([0.5, 2, 1, 1])
                row_cols[0].write(rank)
                row_cols[1].write(name)
                row_cols[2].write(f"{score} / 100")
                row_cols[3].write(f"{skill_score} / 100")

            st.markdown("---")

```

- [ ] **Step 2: サイドバー `st.radio` に `"📜 マッチング履歴"` を追加する**

`app.py` の `st.radio(` 呼び出し（line 601-605 付近）を以下に置き換える：

```python
    page = st.radio(
        "ページ",
        ["📊 ダッシュボード", "📋 案件一覧", "👤 人材一覧", "🔍 マッチング", "📜 マッチング履歴", "⚙️ 設定"],
        label_visibility="collapsed",
    )
```

- [ ] **Step 3: ルーターに履歴ページの case を追加する**

`app.py` のルーター末尾（line 1068-1070 付近）の：

```python
elif page == "🔍 マッチング":
    show_matching()
elif page == "⚙️ 設定":
    show_settings()
```

を以下に置き換える：

```python
elif page == "🔍 マッチング":
    show_matching()
elif page == "📜 マッチング履歴":
    show_match_history()
elif page == "⚙️ 設定":
    show_settings()
```

- [ ] **Step 4: 構文エラーがないか確認する**

```bash
python -c "import py_compile; py_compile.compile('app.py'); print('OK')"
```

期待出力: `OK`

- [ ] **Step 5: Streamlit アプリを起動して動作確認する**

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501/` を開き、以下をすべて確認する：

1. サイドバーに「📜 マッチング履歴」が表示される
2. 案件一覧でページサイズ 10/20/50/100 を切り替えられ、1ページ目にリセットされる
3. 人材一覧で同様にページャーが動作する
4. 「← 前へ」「次へ →」ボタンでページが切り替わる
5. マッチング履歴ページに案件名・日時・TOP5（順位・人材名・スコア）が表示される
6. 履歴が0件の場合は「マッチング履歴がありません。」が表示される（マッチング実行前に確認）

- [ ] **Step 6: コミットする**

```bash
git add app.py
git commit -m "feat: マッチング履歴ページを追加しサイドバー・ルーターを更新"
```
