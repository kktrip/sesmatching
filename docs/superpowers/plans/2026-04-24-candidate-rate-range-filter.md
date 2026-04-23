# 人材一覧 単価範囲フィルター Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 人材一覧の検索フィルタに単価の下限・上限（万円）を追加し、AIが抽出した自由テキスト形式の単価文字列と数値比較できるようにする。

**Architecture:** `src/utils.py` に純粋関数 `_parse_rate_yen()` を追加してテスト可能にし、`app.py` の `show_candidates()` からインポートして使用する。UIは既存の3カラム構成を維持しつつ単価テキスト入力を数値入力2つに置き換える。

**Tech Stack:** Python 3.10+, Streamlit, re (標準ライブラリ), pytest

---

## ファイル構成

| 役割 | ファイル | 変更種別 |
|---|---|---|
| 単価パース純粋関数 | `src/utils.py` | 新規作成 |
| パース関数の単体テスト | `tests/test_rate_parser.py` | 新規作成 |
| UI・フィルタロジック | `app.py:943-985` | 修正 |

---

### Task 1: `_parse_rate_yen` のテスト作成と実装

**Files:**
- Create: `src/utils.py`
- Create: `tests/test_rate_parser.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_rate_parser.py` を作成する：

```python
import pytest
from src.utils import _parse_rate_yen


def test_single_man_yen():
    assert _parse_rate_yen("60万円/月") == (600000, 600000)


def test_range_man_yen():
    assert _parse_rate_yen("60〜70万円") == (600000, 700000)


def test_single_yen_with_comma():
    assert _parse_rate_yen("650,000円") == (650000, 650000)


def test_range_yen_with_comma():
    assert _parse_rate_yen("650,000〜700,000円") == (650000, 700000)


def test_upper_only():
    assert _parse_rate_yen("〜60万円") == (0, 600000)


def test_lower_only():
    assert _parse_rate_yen("60万〜") == (600000, None)


def test_empty_string():
    assert _parse_rate_yen("") == (None, None)


def test_none_input():
    assert _parse_rate_yen(None) == (None, None)


def test_unparseable():
    assert _parse_rate_yen("応相談") == (None, None)


def test_sen_unit():
    assert _parse_rate_yen("800千円") == (800000, 800000)
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_rate_parser.py -v
```

期待結果: `ImportError: cannot import name '_parse_rate_yen' from 'src.utils'`（ファイル未存在）

- [ ] **Step 3: `src/utils.py` を作成して `_parse_rate_yen` を実装**

```python
import re


def _parse_rate_yen(rate_str) -> tuple:
    """単価文字列から (min_yen, max_yen) を返す。パース失敗時は (None, None)。"""
    if not rate_str:
        return (None, None)

    s = rate_str.replace(",", "").replace("，", "")

    if "万" in s:
        unit = 10000
    elif "千" in s:
        unit = 1000
    else:
        unit = 1

    sep_match = re.search(r"[〜~～]", s)

    if not sep_match:
        numbers = re.findall(r"\d+(?:\.\d+)?", s)
        if not numbers:
            return (None, None)
        val = int(float(numbers[0]) * unit)
        return (val, val)

    sep_pos = sep_match.start()
    left_part = s[:sep_pos]
    right_part = s[sep_pos + 1:]

    left_nums = re.findall(r"\d+(?:\.\d+)?", left_part)
    right_nums = re.findall(r"\d+(?:\.\d+)?", right_part)

    min_val = int(float(left_nums[0]) * unit) if left_nums else 0
    max_val = int(float(right_nums[0]) * unit) if right_nums else None

    return (min_val, max_val)
```

- [ ] **Step 4: テストが全て通ることを確認**

```bash
pytest tests/test_rate_parser.py -v
```

期待結果: 10件全て `PASSED`

- [ ] **Step 5: コミット**

```bash
git add src/utils.py tests/test_rate_parser.py
git commit -m "feat: add _parse_rate_yen utility for candidate rate range filtering"
```

---

### Task 2: `app.py` のUIとフィルタロジック更新

**Files:**
- Modify: `app.py:943-985`（`show_candidates()` 内の検索フィルタ部分）

- [ ] **Step 1: インポートを追加**

`app.py` の先頭のインポートブロック（`from src.database import ...` の後）に追記する：

```python
from src.utils import _parse_rate_yen
```

- [ ] **Step 2: 検索フィルタのUIを差し替える**

`show_candidates()` 内の `with st.expander("🔍 検索・絞り込み", ...)` ブロック（app.py:943-958）を以下に置き換える：

```python
    with st.expander("🔍 検索・絞り込み", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            q_skill = st.text_input("スキル", key="cand_q_skill")
        with col2:
            q_age_min = st.number_input("年齢（下限）", min_value=0, max_value=99, value=0, step=1, key="cand_q_age_min")
            q_age_max = st.number_input("年齢（上限）", min_value=0, max_value=99, value=99, step=1, key="cand_q_age_max")
        with col3:
            q_rate_min = st.number_input("単価（下限）万円", min_value=0, value=0, step=1, key="cand_q_rate_min")
            q_rate_max = st.number_input("単価（上限）万円", min_value=0, value=0, step=1, key="cand_q_rate_max")
        col_ws, col_avail = st.columns(2)
        with col_ws:
            q_work_style = st.selectbox(
                "希望勤務形態",
                ["指定なし", "リモート", "常駐", "ハイブリッド"],
                key="cand_q_ws",
            )
        with col_avail:
            q_available = st.text_input("参画可能時期", key="cand_q_avail")
        q_free = st.text_input("フリーテキスト（全項目検索）", key="cand_q_free")
```

- [ ] **Step 3: `_match_candidate()` のフィルタロジックを更新**

`_match_candidate()` 内（app.py:960-985）を以下に置き換える：

```python
    def _match_candidate(c, data):
        skills_str = " ".join(data.get("skills", [])).lower()
        ws_str = (data.get("work_style_preference") or "").lower()
        avail_str = (data.get("available_from") or "").lower()
        all_text = (json.dumps(data, ensure_ascii=False) + " " + c["name"]).lower()
        age = data.get("age")

        if q_skill and q_skill.lower() not in skills_str:
            return False

        if q_rate_min > 0 or q_rate_max > 0:
            cand_min, cand_max = _parse_rate_yen(data.get("desired_rate") or "")
            if cand_min is not None or cand_max is not None:
                filter_min = q_rate_min * 10000
                filter_max = q_rate_max * 10000
                if filter_min > 0 and cand_max is not None and cand_max < filter_min:
                    return False
                if filter_max > 0 and cand_min is not None and cand_min > filter_max:
                    return False

        if age is not None:
            try:
                age_int = int(age)
                if age_int < q_age_min or age_int > q_age_max:
                    return False
            except (ValueError, TypeError):
                pass
        if q_work_style != "指定なし" and q_work_style.lower() not in ws_str:
            return False
        if q_available and q_available.lower() not in avail_str:
            return False
        if q_free and q_free.lower() not in all_text:
            return False
        return True
```

- [ ] **Step 4: 既存テストが全て通ることを確認**

```bash
pytest tests/ -v
```

期待結果: 全テスト `PASSED`（新規 10件 + 既存テスト）

- [ ] **Step 5: コミット**

```bash
git add app.py
git commit -m "feat: replace rate text filter with min/max number inputs in candidate search"
```
