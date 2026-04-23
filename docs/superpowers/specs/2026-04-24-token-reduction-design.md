# マッチングトークン削減 設計

**日付:** 2026-04-24  
**対象ファイル:** `src/matcher.py`

---

## 概要

マッチング実行時のトークン消費を削減する。精度（最終TOP5の質）は維持しつつ、以下の2施策を組み合わせる。

- **A: 二段階マッチング** — Haiku でプレスクリーニング → 上位10名のみ Sonnet で詳細評価
- **B: プロンプト圧縮** — スキルシートを案件必須スキルの関連部分のみに絞り込む

---

## アーキテクチャ

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| `src/matcher.py` | `_extract_relevant_excerpt()` 追加、`_haiku_prescreening()` 追加、`match_candidates()` を二段階フローに修正 |

外部インターフェース（`match_candidates` の引数・戻り値の型）は変更しない。

### 処理フロー

```
candidates（最大20名、キーワード絞り込み済み）
  ↓
[B] _extract_relevant_excerpt() でスキルシートを圧縮
  ↓
[A-1] _haiku_prescreening() → Haiku がスコアのみ付与 → 上位10名を選別
  ↓
[A-2] Sonnet で詳細評価（既存ロジック、候補者は10名に削減）
  ↓
TOP5 を返す
```

---

## 詳細設計

### 1. `_extract_relevant_excerpt(text, required_skills, max_chars=300)` — `src/matcher.py`

**責務:** スキルシートテキストから案件必須スキルに関連する文だけを抽出する。

```python
import re

def _extract_relevant_excerpt(text: str, required_skills: list, max_chars: int = 300) -> str:
    if not text:
        return ""
    keywords = [s.lower() for s in required_skills]
    sentences = re.split(r'[。\n]+', text)
    relevant = [s.strip() for s in sentences
                if any(kw in s.lower() for kw in keywords) and s.strip()]
    excerpt = "　".join(relevant)[:max_chars]
    return excerpt or text[:150]
```

- `required_skills` に含まれるキーワードを含む文だけ結合
- 上限 300 文字（変更前は 500 文字）
- 関連文が1件もない場合は先頭 150 文字にフォールバック

---

### 2. `_haiku_prescreening(project_data, candidates)` — `src/matcher.py`

**責務:** Haiku で候補者全員を軽量スコアリングし、上位10名のリストを返す。

**モデル:** `claude-haiku-4-5-20251001`  
**max_tokens:** `400`

**プロンプト設計:**

```
あなたはSES案件マッチングの専門家です。
以下の案件必須スキルに対して、各人材のスキル適合度を0-100で評価してください。

【案件の必須スキル】
{required_skills_json}

【人材リスト】
{compressed_candidates_json}
（各エントリ: {"id": N, "name": "...", "skills": [...], "skill_excerpt": "..."}）

以下のJSON配列のみで回答してください（説明文不要）:
[{"id": 人材ID, "score": スキル適合度(0-100)}, ...]
```

**戻り値:** スコア順で上位10名の候補者 `list[dict]`（元の candidates エントリをそのまま返す）

**エラー処理:** Haiku のレスポンスが parse 失敗した場合、元の candidates をそのまま返す（Sonnet にすべて渡す）

---

### 3. `match_candidates()` の修正 — `src/matcher.py`

変更前：
```python
# スキルシート 500 文字をそのまま summary に追加
# 20名全員を Sonnet に送信
```

変更後：
```python
# 1. 各候補者のスキルシートを圧縮
for c in candidates:
    c["_compressed_excerpt"] = _extract_relevant_excerpt(
        c.get("skill_sheet_text", ""),
        project_data.get("required_skills", [])
    )

# 2. Haiku でプレスクリーニング → 上位10名
candidates = _haiku_prescreening(project_data, candidates)

# 3. 圧縮済みスキルシートで Sonnet 用 summary を構築（500→300文字）
for c in candidates:
    summary["skill_sheet_excerpt"] = c["_compressed_excerpt"]  # 300文字上限

# 4. Sonnet 詳細評価（既存ロジック）
# max_tokens: 3000 → 2000
```

---

## コスト試算（20名マッチング時）

| | 変更前 | 変更後 |
|---|---|---|
| Haiku 入力 | 0 | ~1,800 tokens |
| Haiku 出力 | 0 | ~200 tokens |
| Sonnet 入力 | ~6,500 tokens | ~2,800 tokens |
| Sonnet 出力 | ~2,500 tokens | ~1,500 tokens |
| **Sonnet換算コスト** | **9,000** | **~3,500**（約61%削減） |

※ Haiku は Sonnet の約1/15のコスト

---

## 完了基準

- [ ] `_extract_relevant_excerpt()` が必須スキルを含む文を抽出できる
- [ ] 関連文がない場合に先頭150文字にフォールバックする
- [ ] `_haiku_prescreening()` が上位10名を返す
- [ ] Haiku のパース失敗時に候補者をそのまま返す（フォールバック）
- [ ] `match_candidates()` が変更後のフローで動作する
- [ ] 戻り値の型・フォーマットが変更前と同一
- [ ] マッチング結果（TOP5）の質が変更前と同等
