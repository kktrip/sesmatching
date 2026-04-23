# SES AIマッチング 改善設計書

**日付:** 2026-04-23  
**対象ブランチ:** claude/ai-talent-project-matching-lozLt

---

## 概要

以下7つの改善を一括実装する。

1. 案件・人材の重複排除
2. 案件一覧の検索機能
3. 人材一覧の検索機能
4. 人材メール全文表示
5. AI加工の最小化
6. マッチング画面の案件詳細を見やすく表示
7. マッチング速度改善

---

## 1. 重複排除

### 判断基準
- **案件**: `title`（AI抽出） ＋ `sender` の組み合わせが既存レコードと一致する場合はスキップ
- **人材**: `name`（AI抽出） ＋ `sender` の組み合わせが既存レコードと一致する場合はスキップ

### 実装
`src/database.py` に以下を追加:

```python
def project_exists(title: str, sender: str) -> bool:
    """同タイトル・同送信者の案件が既存かチェック"""

def candidate_exists(name: str, sender: str) -> bool:
    """同氏名・同送信者の人材が既存かチェック"""
```

`app.py` のメール同期処理で `insert_project` / `insert_candidate` の直前にこれらを呼び出し、重複なら登録スキップ。

---

## 2. 案件一覧の検索機能

### UI
`show_projects()` の先頭に検索フォームを追加（`st.form` or 即時フィルタ）。

### 検索項目
| 項目 | UI部品 | 対象フィールド |
|---|---|---|
| 案件名 | テキストボックス | `title`（部分一致） |
| 必要スキル | テキストボックス | `required_skills`（部分一致） |
| 勤務形態 | セレクトボックス | `work_style`（完全一致/指定なし） |
| 単価 | テキストボックス | `budget`（部分一致） |
| フリーテキスト | テキストボックス | 全フィールド結合文字列（部分一致） |

### 実装方法
DB全件取得後、Pythonリスト内包表記でフィルタリング（DBクエリ変更なし）。

---

## 3. 人材一覧の検索機能

### UI
`show_candidates()` の先頭に検索フォームを追加。

### 検索項目
| 項目 | UI部品 | 対象フィールド |
|---|---|---|
| スキル | テキストボックス | `skills`（部分一致） |
| 年齢（下限〜上限） | 数値入力×2 | `age`（範囲） |
| 希望勤務形態 | セレクトボックス | `work_style_preference` |
| 単価 | テキストボックス | `desired_rate`（部分一致） |
| 参画可能時期 | テキストボックス | `available_from`（部分一致） |
| フリーテキスト | テキストボックス | 全フィールド結合文字列（部分一致） |

---

## 4. 人材メール全文表示

### DB変更
`get_all_candidates()` のSQLを変更し、`emails.body` を JOIN で取得する。

```sql
SELECT c.*, e.sender, e.received_at, e.body as email_body
FROM candidates c
LEFT JOIN emails e ON c.email_id = e.id
ORDER BY c.created_at DESC
```

### UI
各人材エクスパンダー内の末尾に折りたたみ表示を追加:

```
▼ メール全文を見る
  （emails.body をそのまま表示）
```

---

## 5. AI加工の最小化

### 変更内容
`src/ai_processor.py` の `classify_and_extract` プロンプトから以下を削除:

- 案件: `"description": "案件概要（300字以内）"`
- 人材: `"summary": "人材概要（300字以内）"`

### 表示変更
- 案件一覧・人材一覧において、削除したdescription/summaryの代わりに**メール本文冒頭800字**を表示する
- ラベルは「元のメール（抜粋）」として `st.text()` で表示

### 注意
スキル・単価・勤務形態・参画可能時期などの構造化フィールド抽出はAIで継続する。

---

## 6. マッチング画面の案件詳細表示

### 変更前
```python
st.json(project_data)
```

### 変更後
各フィールドをラベル付きで `st.write()` 表示:

```
案件名: ○○○
必要スキル: Java, Spring Boot, Docker
勤務形態: リモート
単価/予算: 70〜80万円
開始時期: 2026年5月
勤務地: 東京都
期間: 6ヶ月〜
必要経験年数: 3年以上
```

---

## 7. マッチング速度改善

### 現状の問題
全候補者（例: 50名）をまとめて1つのClaudeプロンプトに送信 → 入力トークン大 → 遅い

### 改善: 2段階フィルタリング

**Stage 1 (Python):** スキルキーワードマッチングで事前スコアリング
- 案件の `required_skills` と候補者の `skills` のキーワード一致数を数える
- 上位20名に絞り込む（候補者数が20名以下の場合は全員）

**Stage 2 (Claude):** 絞り込んだ20名のみをClaudeに送信して精密評価

### 期待効果
候補者50名 → 20名に絞り込みでプロンプト量が最大60%削減、速度2〜3倍改善を見込む。

---

## ファイル変更一覧

| ファイル | 変更内容 |
|---|---|
| `src/database.py` | `project_exists()`, `candidate_exists()` 追加、`get_all_candidates()` のSQL変更 |
| `src/ai_processor.py` | `description`/`summary` フィールドをプロンプトから削除 |
| `src/matcher.py` | Stage 1 スキルキーワードフィルタリング追加 |
| `app.py` | 重複チェック追加、検索UI追加、メール全文表示追加、案件詳細表示改善 |
