# SES AIマッチング UI改善（黄色テーマ）設計書

**日付:** 2026-04-23

---

## 概要

現在の白/グレーベースのStreamlitデフォルトデザインを、レモン黄色（#EAB308）を基調としたモダンなライトテーマに変更する。

---

## アプローチ

**config.toml + CSS注入**（推奨）を採用。

- `.streamlit/config.toml` でStreamlitネイティブのベースカラーを設定
- `app.py` に `_inject_css()` ヘルパー関数を追加し、カード・ボタン・メトリクスなど細部をスタイリング

---

## カラーパレット

| 役割 | コード | 用途 |
|---|---|---|
| プライマリ | `#EAB308` | ボタン・アクティブ要素・アクセント |
| ホバー | `#CA8A04` | ボタンホバー・インタラクション |
| 薄黄背景 | `#FEFCE8` | サイドバー・フォーム背景 |
| メイン背景 | `#FFFFFF` | メインコンテンツ背景 |
| テキスト | `#1C1917` | 本文・見出し |
| サブテキスト | `#78716C` | 補足情報・ラベル |
| ボーダー | `#E7E5E4` | 区切り線・枠線 |

---

## スタイリング仕様

### サイドバー
- 背景: `#FEFCE8`（薄黄）
- アクティブページのラジオボタン: 黄色ハイライト

### エクスパンダー（案件・人材カード）
- 左側に `4px` の黄色アクセントライン（`border-left: 4px solid #EAB308`）
- 軽いボックスシャドウ: `0 1px 3px rgba(0,0,0,0.08)`
- ホバー時にシャドウを強調

### メトリクス（ダッシュボードの件数）
- 黄色の上ボーダー（`border-top: 3px solid #EAB308`）付きカード風表示
- 背景: 白、軽いシャドウ

### ボタン（「メールを取得・同期」「マッチング実行」）
- 背景: `#EAB308`
- テキスト: `#1C1917`（ダーク）
- ホバー: `#CA8A04`
- 角丸: `8px`

### 検索フォーム（テキストインプット・セレクトボックス）
- フォーカス時のボーダー: `#EAB308`
- 背景: `#FFFBEB`（ごく薄い黄）

### ページヘッダー
- 黄色の下線アクセント（`border-bottom: 2px solid #EAB308`）

---

## ファイル変更一覧

| ファイル | 変更内容 |
|---|---|
| `.streamlit/config.toml` | 新規作成。primaryColor, backgroundColor, secondaryBackgroundColor, textColor を設定 |
| `app.py` | `_inject_css()` 関数を追加。`init_db()` の直後に呼び出す |

---

## 実装詳細

### `.streamlit/config.toml`

```toml
[theme]
primaryColor = "#EAB308"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#FEFCE8"
textColor = "#1C1917"
font = "sans serif"
```

### `app.py` — `_inject_css()` 関数

```python
def _inject_css():
    st.markdown("""
    <style>
    /* ── エクスパンダー（カード）── */
    [data-testid="stExpander"] {
        border-left: 4px solid #EAB308;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        margin-bottom: 8px;
        background: #FFFFFF;
    }
    [data-testid="stExpander"]:hover {
        box-shadow: 0 3px 8px rgba(234,179,8,0.2);
    }

    /* ── メトリクス ── */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border-top: 3px solid #EAB308;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    /* ── ボタン ── */
    [data-testid="stButton"] > button {
        background-color: #EAB308;
        color: #1C1917;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    [data-testid="stButton"] > button:hover {
        background-color: #CA8A04;
        color: #FFFFFF;
    }

    /* ── ページヘッダー ── */
    h1 {
        border-bottom: 2px solid #EAB308;
        padding-bottom: 8px;
    }

    /* ── テキストインプット フォーカス ── */
    [data-testid="stTextInput"] input:focus {
        border-color: #EAB308 !important;
        box-shadow: 0 0 0 2px rgba(234,179,8,0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)
```

### 呼び出し位置

`st.set_page_config(...)` の直後、サイドバーコードの前に `_inject_css()` を呼び出す。

---

## 注意事項

- StreamlitのCSSクラス名（`data-testid`等）はバージョンアップで変わる可能性がある。Streamlitのバージョンを固定して運用することを推奨。
- CSS注入は `unsafe_allow_html=True` が必要。既存コードでも同様の手法を使用可能。
