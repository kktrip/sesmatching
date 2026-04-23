# SES AIマッチング 改善 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 案件・人材の重複排除、一覧検索機能、人材メール全文表示、AI加工最小化、マッチング画面改善、マッチング速度改善を実装する。

**Architecture:** `database.py` に重複チェック関数とクエリ改善を加え、`ai_processor.py` のプロンプトから要約生成を削除し、`matcher.py` にキーワード事前フィルタを追加する。UIは `app.py` のみに集約し、検索・表示改善はすべて `app.py` 内で完結させる。

**Tech Stack:** Python 3.9+, Streamlit, SQLite (sqlite3), Anthropic Claude API

---

## ファイル変更一覧

| ファイル | 変更内容 |
|---|---|
| `src/database.py` | `project_exists()`, `candidate_exists()` 追加; `get_all_candidates()` のSQL変更（`email_body`をJOINで取得） |
| `src/ai_processor.py` | `description`/`summary` フィールドをプロンプトから削除 |
| `src/matcher.py` | `_keyword_score()` 追加; `match_candidates()` に20名上限フィルタ追加 |
| `app.py` | 重複チェック追加; 案件/人材検索UI追加; メール全文表示追加; 案件詳細表示改善; importに `project_exists`, `candidate_exists` 追加 |

---

## Task 1: database.py — 重複チェック関数を追加

**Files:**
- Modify: `src/database.py`

- [ ] **Step 1: `project_exists()` 関数を追加する**

`src/database.py` の末尾（`get_all_message_ids` の後）に追加:

```python
def project_exists(title: str, sender: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT p.id FROM projects p JOIN emails e ON p.email_id = e.id WHERE p.title=? AND e.sender=?",
            (title, sender),
        ).fetchone()
        return row is not None


def candidate_exists(name: str, sender: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT c.id FROM candidates c JOIN emails e ON c.email_id = e.id WHERE c.name=? AND e.sender=?",
            (name, sender),
        ).fetchone()
        return row is not None
```

- [ ] **Step 2: 動作確認（手動）**

Pythonシェルで実行して構文エラーがないか確認:
```bash
cd C:\Users\kazua\app\sesmatching
python -c "from src.database import project_exists, candidate_exists; print('OK')"
```
期待出力: `OK`

- [ ] **Step 3: コミット**

```bash
git add src/database.py
git commit -m "feat: 案件・人材の重複チェック関数を追加"
```

---

## Task 2: database.py — get_all_candidates にメール本文を含める

**Files:**
- Modify: `src/database.py:99-103`

- [ ] **Step 1: `get_all_candidates()` のSQLを変更する**

`src/database.py` の `get_all_candidates` 関数を以下に置き換える:

```python
def get_all_candidates():
    with get_connection() as conn:
        return conn.execute(
            "SELECT c.*, e.sender, e.received_at, e.body as email_body "
            "FROM candidates c LEFT JOIN emails e ON c.email_id = e.id "
            "ORDER BY c.created_at DESC"
        ).fetchall()
```

- [ ] **Step 2: 動作確認（手動）**

```bash
python -c "from src.database import get_all_candidates; rows = get_all_candidates(); print(len(rows), 'candidates'); print(list(rows[0].keys()) if rows else 'no rows')"
```
期待: キー一覧に `email_body` が含まれている

- [ ] **Step 3: コミット**

```bash
git add src/database.py
git commit -m "feat: get_all_candidates にメール本文(email_body)を追加"
```

---

## Task 3: ai_processor.py — 要約フィールドをプロンプトから削除

**Files:**
- Modify: `src/ai_processor.py`

- [ ] **Step 1: 案件プロンプトから `description` フィールドを削除する**

`src/ai_processor.py` の `classify_and_extract` 内のプロンプト文字列で、案件JSONの `description` 行を削除する。

変更前（62〜68行あたり）:
```python
    "budget": "単価・予算（記載がない場合は空文字）",
    "start_date": "開始時期",
    "description": "案件概要（300字以内）"
  }}
}}
```

変更後:
```python
    "budget": "単価・予算（記載がない場合は空文字）",
    "start_date": "開始時期"
  }}
}}
```

- [ ] **Step 2: 人材プロンプトから `summary` フィールドを削除する**

同じプロンプト文字列内の人材JSONの `summary` 行を削除する。

変更前（79〜84行あたり）:
```python
    "desired_rate": "希望単価（記載がない場合は空文字）",
    "summary": "人材概要（300字以内）"
  }}
}}
```

変更後:
```python
    "desired_rate": "希望単価（記載がない場合は空文字）"
  }}
}}
```

- [ ] **Step 3: 動作確認（手動）**

```bash
python -c "from src.ai_processor import classify_and_extract; print('import OK')"
```
期待出力: `import OK`

- [ ] **Step 4: コミット**

```bash
git add src/ai_processor.py
git commit -m "feat: AIプロンプトからdescription/summaryの要約生成を削除"
```

---

## Task 4: matcher.py — キーワード事前フィルタで速度改善

**Files:**
- Modify: `src/matcher.py`

- [ ] **Step 1: `_keyword_score()` 関数を追加する**

`src/matcher.py` の `_parse_json_response` の後、`match_candidates` の前に追加:

```python
def _keyword_score(project_data: dict, candidate: dict) -> int:
    """Return keyword overlap count between project required_skills and candidate skills/sheet."""
    required = [s.lower() for s in project_data.get("required_skills", [])]
    cand_skills = [s.lower() for s in candidate["data"].get("skills", [])]
    sheet = (candidate.get("skill_sheet_text") or "").lower()
    score = 0
    for req in required:
        if any(req in cs for cs in cand_skills):
            score += 2
        elif req in sheet:
            score += 1
    return score
```

- [ ] **Step 2: `match_candidates()` の先頭に20名フィルタを追加する**

`match_candidates` の `if not candidates: return []` の直後に追加:

```python
    # Stage 1: keyword pre-filter — limit to top 20 before Claude call
    if len(candidates) > 20:
        scored = sorted(candidates, key=lambda c: _keyword_score(project_data, c), reverse=True)
        candidates = scored[:20]
```

- [ ] **Step 3: 動作確認（手動）**

```bash
python -c "from src.matcher import match_candidates, _keyword_score; print('import OK')"
```
期待出力: `import OK`

- [ ] **Step 4: コミット**

```bash
git add src/matcher.py
git commit -m "feat: マッチング速度改善 — キーワード事前スコアで上位20名に絞り込み"
```

---

## Task 5: app.py — 重複チェックをメール同期に組み込む

**Files:**
- Modify: `app.py`

- [ ] **Step 1: import に `project_exists`, `candidate_exists` を追加する**

`app.py` の先頭の `from src.database import (` ブロックに追加:

```python
from src.database import (
    init_db,
    get_stats,
    get_all_projects,
    get_all_candidates,
    get_project_by_id,
    get_candidate_by_id,
    get_latest_match,
    insert_email,
    insert_project,
    insert_candidate,
    insert_match,
    get_all_message_ids,
    project_exists,
    candidate_exists,
)
```

- [ ] **Step 2: メール同期処理の insert_project / insert_candidate を重複チェック付きに変更する**

`app.py` の以下のブロック（130〜141行あたり）を置き換える。

変更前:
```python
                    new_count += 1
                    if email_type == "project":
                        insert_project(email_id, data.get("title", em["subject"]), json.dumps(data, ensure_ascii=False))
                        project_count += 1
                    elif email_type == "candidate":
                        insert_candidate(
                            email_id,
                            data.get("name", "氏名不明"),
                            json.dumps(data, ensure_ascii=False),
                            attachment_text[:5000],
                        )
                        candidate_count += 1
```

変更後:
```python
                    new_count += 1
                    if email_type == "project":
                        title = data.get("title", em["subject"])
                        if not project_exists(title, em["sender"]):
                            insert_project(email_id, title, json.dumps(data, ensure_ascii=False))
                            project_count += 1
                    elif email_type == "candidate":
                        name = data.get("name", "氏名不明")
                        if not candidate_exists(name, em["sender"]):
                            insert_candidate(
                                email_id,
                                name,
                                json.dumps(data, ensure_ascii=False),
                                attachment_text[:5000],
                            )
                            candidate_count += 1
```

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: メール同期に重複チェック(タイトル+送信者)を追加"
```

---

## Task 6: app.py — 案件一覧に検索UIを追加

**Files:**
- Modify: `app.py`

- [ ] **Step 1: `show_projects()` 全体を以下に置き換える**

```python
def show_projects():
    st.header("📋 案件一覧")
    projects = get_all_projects()

    if not projects:
        st.info("案件がありません。サイドバーから「メールを取得・同期」を実行してください。")
        return

    # ── 検索フィルタ ──
    with st.expander("🔍 検索・絞り込み", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            q_title = st.text_input("案件名", key="proj_q_title")
            q_skill = st.text_input("必要スキル", key="proj_q_skill")
        with col2:
            q_work_style = st.selectbox(
                "勤務形態",
                ["指定なし", "リモート", "常駐", "ハイブリッド"],
                key="proj_q_ws",
            )
            q_budget = st.text_input("単価", key="proj_q_budget")
        with col3:
            q_free = st.text_input("フリーテキスト（全項目検索）", key="proj_q_free")

    def _match_project(p):
        data = json.loads(p["data"])
        title_str = p["title"].lower()
        skills_str = " ".join(data.get("required_skills", [])).lower()
        work_style_str = (data.get("work_style") or "").lower()
        budget_str = (data.get("budget") or "").lower()
        all_text = (json.dumps(data, ensure_ascii=False) + " " + p["title"]).lower()

        if q_title and q_title.lower() not in title_str:
            return False
        if q_skill and q_skill.lower() not in skills_str:
            return False
        if q_work_style != "指定なし" and q_work_style.lower() not in work_style_str:
            return False
        if q_budget and q_budget.lower() not in budget_str:
            return False
        if q_free and q_free.lower() not in all_text:
            return False
        return True

    filtered = [p for p in projects if _match_project(p)]
    st.caption(f"{len(filtered)} 件 / 全 {len(projects)} 件")

    for p in filtered:
        data = json.loads(p["data"])
        skills = ", ".join(data.get("required_skills", []))
        with st.expander(f"📋 {p['title']}　｜　{data.get('location', '勤務地不明')}　｜　{p['created_at'][:10]}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**必要スキル:** {skills or '—'}")
                st.write(f"**必要経験年数:** {data.get('experience_years', '不明')}年以上")
                st.write(f"**期間:** {data.get('period', '不明')}")
                st.write(f"**開始時期:** {data.get('start_date', '不明')}")
            with col2:
                st.write(f"**勤務形態:** {data.get('work_style', '不明')}")
                st.write(f"**単価/予算:** {data.get('budget', '非公開')}")
                st.write(f"**送信者:** {p['sender']}")
```

- [ ] **Step 2: Streamlit を起動して案件一覧を目視確認する**

```bash
streamlit run app.py
```

ブラウザで「📋 案件一覧」を開き、検索フォームが表示され絞り込みが動作することを確認する。

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: 案件一覧に検索フィルタUIを追加"
```

---

## Task 7: app.py — 人材一覧に検索UIとメール全文表示を追加

**Files:**
- Modify: `app.py`

- [ ] **Step 1: `show_candidates()` 全体を以下に置き換える**

```python
def show_candidates():
    st.header("👤 人材一覧")
    candidates = get_all_candidates()

    if not candidates:
        st.info("人材がありません。サイドバーから「メールを取得・同期」を実行してください。")
        return

    # ── 検索フィルタ ──
    with st.expander("🔍 検索・絞り込み", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            q_skill = st.text_input("スキル", key="cand_q_skill")
            q_rate = st.text_input("単価", key="cand_q_rate")
        with col2:
            q_age_min = st.number_input("年齢（下限）", min_value=0, max_value=99, value=0, step=1, key="cand_q_age_min")
            q_age_max = st.number_input("年齢（上限）", min_value=0, max_value=99, value=99, step=1, key="cand_q_age_max")
        with col3:
            q_work_style = st.selectbox(
                "希望勤務形態",
                ["指定なし", "リモート", "常駐", "ハイブリッド"],
                key="cand_q_ws",
            )
            q_available = st.text_input("参画可能時期", key="cand_q_avail")
        q_free = st.text_input("フリーテキスト（全項目検索）", key="cand_q_free")

    def _match_candidate(c):
        data = json.loads(c["data"])
        skills_str = " ".join(data.get("skills", [])).lower()
        rate_str = (data.get("desired_rate") or "").lower()
        ws_str = (data.get("work_style_preference") or "").lower()
        avail_str = (data.get("available_from") or "").lower()
        all_text = (json.dumps(data, ensure_ascii=False) + " " + c["name"]).lower()
        age = data.get("age")

        if q_skill and q_skill.lower() not in skills_str:
            return False
        if q_rate and q_rate.lower() not in rate_str:
            return False
        if age is not None:
            if int(age) < q_age_min or int(age) > q_age_max:
                return False
        if q_work_style != "指定なし" and q_work_style.lower() not in ws_str:
            return False
        if q_available and q_available.lower() not in avail_str:
            return False
        if q_free and q_free.lower() not in all_text:
            return False
        return True

    filtered = [c for c in candidates if _match_candidate(c)]
    st.caption(f"{len(filtered)} 件 / 全 {len(candidates)} 件")

    for c in filtered:
        data = json.loads(c["data"])
        skills = ", ".join(data.get("skills", []))
        with st.expander(f"👤 {c['name']}　｜　経験 {data.get('experience_years', '?')}年　｜　{c['created_at'][:10]}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**スキル:** {skills or '—'}")
                st.write(f"**経験年数:** {data.get('experience_years', '不明')}年")
                st.write(f"**年齢:** {data.get('age', '非公開')}")
            with col2:
                st.write(f"**参画可能時期:** {data.get('available_from', '不明')}")
                st.write(f"**希望勤務形態:** {data.get('work_style_preference', '不明')}")
                st.write(f"**希望単価:** {data.get('desired_rate', '非公開')}")
            if c["skill_sheet_text"]:
                with st.expander("スキルシート（抜粋）"):
                    st.text(c["skill_sheet_text"][:1000])
            email_body = c["email_body"] if "email_body" in c.keys() else None
            if email_body:
                with st.expander("📧 メール全文を見る"):
                    st.text(email_body)
```

- [ ] **Step 2: Streamlit で人材一覧を目視確認する**

```bash
streamlit run app.py
```

「👤 人材一覧」を開き、検索フォームとメール全文表示が正しく動作することを確認する。

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: 人材一覧に検索フィルタとメール全文表示を追加"
```

---

## Task 8: app.py — マッチング画面の案件詳細表示を改善

**Files:**
- Modify: `app.py`

- [ ] **Step 1: `show_matching()` 内の `st.json(project_data)` を置き換える**

`show_matching()` の以下の部分:

```python
    with st.expander("案件詳細を確認"):
        st.json(project_data)
```

を以下に置き換える:

```python
    with st.expander("案件詳細を確認"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**案件名:** {project_row['title']}")
            st.write(f"**必要スキル:** {', '.join(project_data.get('required_skills', [])) or '—'}")
            st.write(f"**必要経験年数:** {project_data.get('experience_years', '不明')}年以上")
            st.write(f"**開始時期:** {project_data.get('start_date', '不明')}")
        with col_b:
            st.write(f"**勤務形態:** {project_data.get('work_style', '不明')}")
            st.write(f"**単価/予算:** {project_data.get('budget', '非公開')}")
            st.write(f"**勤務地:** {project_data.get('location', '不明')}")
            st.write(f"**期間:** {project_data.get('period', '不明')}")
```

- [ ] **Step 2: Streamlit でマッチング画面を目視確認する**

「🔍 マッチング」を開き、案件詳細がラベル付きフィールドで表示されることを確認する（JSONでなく）。

- [ ] **Step 3: コミット**

```bash
git add app.py
git commit -m "feat: マッチング画面の案件詳細をJSONから見やすい表示に変更"
```

---

## 最終確認チェックリスト

- [ ] `python -c "from src.database import project_exists, candidate_exists; print('OK')"` が通る
- [ ] `python -c "from src.matcher import _keyword_score; print('OK')"` が通る
- [ ] Streamlit で案件一覧の検索が動作する
- [ ] Streamlit で人材一覧の検索が動作する
- [ ] 人材一覧でメール全文が展開表示される
- [ ] マッチング画面の案件詳細がJSON形式でなく表示される
- [ ] 同じタイトル+送信者の案件を再同期しても重複登録されない

---

## 注意事項

- `email_body` カラムは `get_all_candidates()` の JOINで取得する。既存DBには `emails.body` が保存されているので追加マイグレーション不要。
- `get_all_projects()` は現在 `email_body` を返さないが、案件一覧ではメール全文表示は要件外のため変更不要。
- `q_age_min`/`q_age_max` フィルタは `age` が `null` の人材はフィルタせず通過させる（age不明者を除外しない）。
