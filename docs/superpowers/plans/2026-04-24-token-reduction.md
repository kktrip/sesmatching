# マッチングトークン削減 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `src/matcher.py` にプロンプト圧縮と二段階マッチング（Haiku→Sonnet）を追加し、トークン消費を約60%削減する。

**Architecture:** `_extract_relevant_excerpt()` でスキルシートを圧縮し、`_haiku_prescreening()` で Haiku が20名をスコアリングして上位10名に絞る。その後、既存の Sonnet 評価ロジックを上位10名のみに適用する。`match_candidates()` の外部インターフェースは変更しない。

**Tech Stack:** Python / Anthropic SDK (`anthropic`) / `unittest.mock` (テスト用) / `pytest`

---

### 変更ファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `src/matcher.py` | `import re` 追加、`_extract_relevant_excerpt()` 追加、`_haiku_prescreening()` 追加、`match_candidates()` を二段階フローに修正、`max_tokens` を 3000→2000 に変更 |
| `tests/test_matcher.py` | 新規作成（上記3関数のユニットテスト） |

---

### Task 1: `_extract_relevant_excerpt()` を追加

**Files:**
- Modify: `src/matcher.py`（`_keyword_score()` の直前に挿入）
- Create: `tests/test_matcher.py`

- [ ] **Step 1: `tests/test_matcher.py` を作成し、失敗するテストを書く**

```python
# tests/test_matcher.py
import pytest
from src.matcher import _extract_relevant_excerpt


def test_extract_finds_matching_sentences():
    text = "Pythonでの開発経験があります。\nJavaScriptも対応可能です。\nExcelの操作ができます。"
    result = _extract_relevant_excerpt(text, ["Python", "JavaScript"], max_chars=300)
    assert "Python" in result
    assert "JavaScript" in result
    assert "Excel" not in result


def test_extract_excludes_unrelated_sentences():
    text = "一般的なPC操作ができます。\nPythonで5年の経験があります。\n英語は日常会話レベルです。"
    result = _extract_relevant_excerpt(text, ["Python"], max_chars=300)
    assert "Python" in result
    assert "PC操作" not in result
    assert "英語" not in result


def test_extract_respects_max_chars():
    text = "Python " * 100
    result = _extract_relevant_excerpt(text, ["Python"], max_chars=50)
    assert len(result) <= 50


def test_extract_fallback_when_no_match():
    text = "特にスキルの記載はありません。一般的な業務経験があります。"
    result = _extract_relevant_excerpt(text, ["AWS", "Kubernetes"], max_chars=300)
    # フォールバック: 先頭150文字を返す
    assert result == text[:150]


def test_extract_empty_text():
    result = _extract_relevant_excerpt("", ["Python"], max_chars=300)
    assert result == ""


def test_extract_case_insensitive():
    text = "python開発の経験があります。"
    result = _extract_relevant_excerpt(text, ["Python"], max_chars=300)
    assert "python" in result
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
cd C:\Users\kazua\app\sesmatching
python -m pytest tests/test_matcher.py -v
```

期待出力: `ImportError` または `FAILED`（`_extract_relevant_excerpt` 未定義）

- [ ] **Step 3: `src/matcher.py` に `import re` と `_extract_relevant_excerpt()` を追加する**

`src/matcher.py` の先頭 `import json` の直後に `import re` を追加する：

```python
import json
import re
import os
import anthropic
```

次に `_keyword_score()` 関数の直前（line 27 付近）に以下を挿入する：

```python
def _extract_relevant_excerpt(text: str, required_skills: list, max_chars: int = 300) -> str:
    """Return skill-sheet excerpt containing only sentences relevant to required_skills."""
    if not text:
        return ""
    keywords = [s.lower() for s in required_skills]
    sentences = re.split(r'[。\n]+', text)
    relevant = [s.strip() for s in sentences
                if any(kw in s.lower() for kw in keywords) and s.strip()]
    excerpt = "　".join(relevant)[:max_chars]
    return excerpt or text[:150]
```

- [ ] **Step 4: テストがすべて通ることを確認する**

```bash
python -m pytest tests/test_matcher.py -v
```

期待出力: `6 passed`

- [ ] **Step 5: コミットする**

```bash
git add src/matcher.py tests/test_matcher.py
git commit -m "feat: _extract_relevant_excerpt()を追加"
```

---

### Task 2: `_haiku_prescreening()` を追加

**Files:**
- Modify: `src/matcher.py`（`match_candidates()` の直前に挿入）
- Modify: `tests/test_matcher.py`（テストを追記）

- [ ] **Step 1: `tests/test_matcher.py` に失敗するテストを追記する**

```python
import json
from unittest.mock import MagicMock, patch
from src.matcher import _extract_relevant_excerpt, _haiku_prescreening


def test_haiku_prescreening_returns_top_10():
    candidates = [
        {
            "id": i,
            "name": f"候補者{i}",
            "data": {"skills": []},
            "skill_sheet_text": "",
            "_compressed_excerpt": "",
        }
        for i in range(20)
    ]
    project_data = {"required_skills": ["Python"]}
    # id=0 が最高スコア(20)、id=19 が最低スコア(1)
    mock_scores = json.dumps([{"id": i, "score": 20 - i} for i in range(20)])

    with patch("src.matcher._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create.return_value.content = [
            MagicMock(text=mock_scores)
        ]
        result = _haiku_prescreening(project_data, candidates)

    assert len(result) == 10
    result_ids = [c["id"] for c in result]
    # 上位10名（id=0〜9）が選ばれる
    for i in range(10):
        assert i in result_ids


def test_haiku_prescreening_fallback_on_parse_error():
    candidates = [
        {
            "id": i,
            "name": f"候補者{i}",
            "data": {"skills": []},
            "skill_sheet_text": "",
            "_compressed_excerpt": "",
        }
        for i in range(5)
    ]
    project_data = {"required_skills": ["Python"]}

    with patch("src.matcher._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create.return_value.content = [
            MagicMock(text="invalid json {{")
        ]
        result = _haiku_prescreening(project_data, candidates)

    # フォールバック: 元の candidates をそのまま返す
    assert result == candidates


def test_haiku_prescreening_fewer_than_10_candidates():
    candidates = [
        {
            "id": i,
            "name": f"候補者{i}",
            "data": {"skills": []},
            "skill_sheet_text": "",
            "_compressed_excerpt": "",
        }
        for i in range(7)
    ]
    project_data = {"required_skills": ["Python"]}
    mock_scores = json.dumps([{"id": i, "score": 7 - i} for i in range(7)])

    with patch("src.matcher._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create.return_value.content = [
            MagicMock(text=mock_scores)
        ]
        result = _haiku_prescreening(project_data, candidates)

    # 7名しかいない場合は全員返す（10名に満たない）
    assert len(result) == 7
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m pytest tests/test_matcher.py::test_haiku_prescreening_returns_top_10 -v
```

期待出力: `FAILED`（`_haiku_prescreening` 未定義）

- [ ] **Step 3: `_haiku_prescreening()` を `match_candidates()` の直前に追加する**

`src/matcher.py` の `match_candidates()` 定義（`def match_candidates(` の行）の直前に以下を挿入する：

```python
def _haiku_prescreening(project_data: dict, candidates: list[dict]) -> list[dict]:
    """Pre-screen candidates with Haiku; return top-10 by skill score."""
    required_skills = project_data.get("required_skills", [])

    candidate_summaries = [
        {
            "id": c["id"],
            "name": c["name"],
            "skills": (c.get("data") or {}).get("skills", []),
            "skill_excerpt": c.get("_compressed_excerpt", ""),
        }
        for c in candidates
    ]

    prompt = f"""あなたはSES案件マッチングの専門家です。
以下の案件必須スキルに対して、各人材のスキル適合度を0-100で評価してください。

【案件の必須スキル】
{json.dumps(required_skills, ensure_ascii=False)}

【人材リスト】
{json.dumps(candidate_summaries, ensure_ascii=False)}

以下のJSON配列のみで回答してください（説明文不要）:
[{{"id": 人材ID, "score": スキル適合度(0-100)}}]"""

    try:
        response = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        scores = _parse_json_response(response.content[0].text)
        score_map = {s["id"]: s["score"] for s in scores}
        ranked = sorted(candidates, key=lambda c: score_map.get(c["id"], 0), reverse=True)
        return ranked[:10]
    except Exception:
        return candidates
```

- [ ] **Step 4: テストがすべて通ることを確認する**

```bash
python -m pytest tests/test_matcher.py -v
```

期待出力: `9 passed`

- [ ] **Step 5: コミットする**

```bash
git add src/matcher.py tests/test_matcher.py
git commit -m "feat: _haiku_prescreening()を追加"
```

---

### Task 3: `match_candidates()` を二段階フローに更新

**Files:**
- Modify: `src/matcher.py`（`match_candidates()` の本体を修正）
- Modify: `tests/test_matcher.py`（統合テストを追記）

- [ ] **Step 1: `tests/test_matcher.py` に失敗するテストを追記する**

```python
from src.matcher import _extract_relevant_excerpt, _haiku_prescreening, match_candidates


def test_match_candidates_calls_haiku_then_sonnet():
    """20名のとき Haiku と Sonnet の2回 API が呼ばれることを確認する。"""
    candidates = [
        {
            "id": i,
            "name": f"候補者{i}",
            "data": {"skills": ["Python"], "experience_years": 3, "available_from": "即日", "work_style_preference": "リモート"},
            "skill_sheet_text": "Pythonでの開発経験があります。",
        }
        for i in range(20)
    ]
    project_data = {
        "title": "Pythonエンジニア募集",
        "required_skills": ["Python"],
        "experience_years": 2,
        "work_style": "リモート",
        "location": "東京",
        "start_date": "即日",
        "period": "6ヶ月",
        "budget": "60万",
    }

    haiku_scores = json.dumps([{"id": i, "score": 20 - i} for i in range(20)])
    sonnet_results = json.dumps([
        {
            "candidate_id": i,
            "name": f"候補者{i}",
            "score": 90 - i * 3,
            "skill_match_score": 85,
            "reason": "Pythonスキルが合致しています。",
            "concerns": "",
        }
        for i in range(5)
    ])

    call_count = 0

    def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            mock.content = [MagicMock(text=haiku_scores)]
        else:
            mock.content = [MagicMock(text=sonnet_results)]
        return mock

    with patch("src.matcher._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create.side_effect = mock_create
        result = match_candidates(project_data, candidates)

    assert call_count == 2
    assert len(result) <= 5
    assert all("score" in r for r in result)


def test_match_candidates_returns_empty_for_no_candidates():
    result = match_candidates({"required_skills": ["Python"]}, [])
    assert result == []


def test_match_candidates_sonnet_uses_max_tokens_2000():
    """Sonnet 呼び出し時の max_tokens が 2000 であることを確認する。"""
    candidates = [
        {
            "id": i,
            "name": f"候補者{i}",
            "data": {"skills": ["Python"]},
            "skill_sheet_text": "Python開発",
        }
        for i in range(3)
    ]
    project_data = {"required_skills": ["Python"], "title": "テスト案件"}

    sonnet_results = json.dumps([
        {"candidate_id": 0, "name": "候補者0", "score": 90, "skill_match_score": 85, "reason": "理由", "concerns": ""}
    ])

    call_args_list = []

    def mock_create(**kwargs):
        call_args_list.append(kwargs)
        mock = MagicMock()
        if len(call_args_list) == 1:
            mock.content = [MagicMock(text=json.dumps([{"id": i, "score": 3 - i} for i in range(3)]))]
        else:
            mock.content = [MagicMock(text=sonnet_results)]
        return mock

    with patch("src.matcher._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create.side_effect = mock_create
        match_candidates(project_data, candidates)

    sonnet_call = call_args_list[1]
    assert sonnet_call["max_tokens"] == 2000
    assert sonnet_call["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m pytest tests/test_matcher.py::test_match_candidates_calls_haiku_then_sonnet -v
```

期待出力: `FAILED`（`call_count == 1` で assertion error）

- [ ] **Step 3: `match_candidates()` を二段階フローに書き換える**

`src/matcher.py` の `match_candidates()` 全体を以下に置き換える：

```python
def match_candidates(project_data: dict, candidates: list[dict]) -> list[dict]:
    """
    Match a project against candidates and return top 5 ranked results.

    candidates: list of {"id": int, "name": str, "data": dict, "skill_sheet_text": str}
    Returns: list of match dicts sorted by score descending (up to 5)
    """
    if not candidates:
        return []

    # Stage 0: keyword pre-filter — limit to top 20 before Claude calls
    if len(candidates) > 20:
        scored = sorted(candidates, key=lambda c: _keyword_score(project_data, c), reverse=True)
        candidates = scored[:20]

    # Stage B: compress skill sheets to relevant excerpts
    required_skills = project_data.get("required_skills", [])
    for c in candidates:
        c["_compressed_excerpt"] = _extract_relevant_excerpt(
            c.get("skill_sheet_text") or "", required_skills
        )

    # Stage A-1: Haiku pre-screening → top 10
    candidates = _haiku_prescreening(project_data, candidates)

    # Stage A-2: Sonnet detailed evaluation
    candidate_summaries = []
    for c in candidates:
        summary = {
            "id": c["id"],
            "name": c["name"],
            **c["data"],
        }
        if c.get("_compressed_excerpt"):
            summary["skill_sheet_excerpt"] = c["_compressed_excerpt"]
        candidate_summaries.append(summary)

    prompt = f"""あなたはSES（システムエンジニアリングサービス）の経験豊富なコーディネーターです。
以下の案件に最もマッチする人材を上位5名選定してください。

【案件情報】
{json.dumps(project_data, ensure_ascii=False, indent=2)}

【人材リスト（{len(candidate_summaries)}名）】
{json.dumps(candidate_summaries, ensure_ascii=False, indent=2)}

各人材を以下の観点で評価し、上位5名を選んでください:
- スキルマッチ度 (40%): 必要スキルとの合致
- 経験年数 (20%): 求められる経験との適合
- 参画可能時期 (20%): 案件開始時期との一致
- 勤務形態 (20%): 勤務地・リモート希望との適合

以下のJSON配列形式のみで回答してください（説明文不要）:
[
  {{
    "candidate_id": 人材のid(数値),
    "name": "氏名",
    "score": 総合スコア(0〜100の整数),
    "skill_match_score": スキルマッチスコア(0〜100の整数),
    "reason": "選定理由（具体的に、なぜこの人材が適しているか200字程度）",
    "concerns": "懸念点（特になければ空文字）"
  }}
]

必ず候補者数が5名未満の場合はその全員を、5名以上なら上位5名のみ返してください。"""

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    results = _parse_json_response(response.content[0].text)
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:5]
```

- [ ] **Step 4: テストがすべて通ることを確認する**

```bash
python -m pytest tests/test_matcher.py -v
```

期待出力: `12 passed`

- [ ] **Step 5: 構文エラーがないか確認する**

```bash
python -c "import py_compile; py_compile.compile('src/matcher.py'); print('OK')"
```

期待出力: `OK`

- [ ] **Step 6: コミットする**

```bash
git add src/matcher.py tests/test_matcher.py
git commit -m "feat: match_candidates()を二段階マッチング(Haiku→Sonnet)に変更"
```
