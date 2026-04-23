# Yellow UI Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** StreamlitアプリにレモンイエローベースのモダンUIテーマを適用する。

**Architecture:** `.streamlit/config.toml` でStreamlitのネイティブテーマカラーを設定し、`app.py` に `_inject_css()` 関数を追加してカード・ボタン・メトリクスなどの細部スタイルを注入する。2ファイルの変更のみ。

**Tech Stack:** Python 3.9+, Streamlit, CSS (st.markdown injection)

---

## ファイル変更一覧

| ファイル | 変更内容 |
|---|---|
| `.streamlit/config.toml` | 新規作成。Streamlitネイティブテーマカラーを設定 |
| `app.py` | `_inject_css()` 関数を追加し `st.set_page_config()` の直後に呼び出す |

---

## Task 1: .streamlit/config.toml を作成する

**Files:**
- Create: `.streamlit/config.toml`

- [ ] **Step 1: `.streamlit` ディレクトリと `config.toml` を作成する**

`C:\Users\kazua\app\sesmatching\.streamlit\config.toml` を以下の内容で作成する:

```toml
[theme]
primaryColor = "#EAB308"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#FEFCE8"
textColor = "#1C1917"
font = "sans serif"
```

- [ ] **Step 2: Streamlit が config を認識することを確認する**

```bash
python -c "import streamlit; print(streamlit.__version__)"
```

期待出力: バージョン番号が表示される（エラーなし）

- [ ] **Step 3: コミット**

```bash
git add .streamlit/config.toml
git commit -m "feat: Streamlitテーマカラーをレモンイエローに設定"
```

---

## Task 2: app.py に _inject_css() を追加する

**Files:**
- Modify: `app.py`

- [ ] **Step 1: `_inject_css()` 関数を `app.py` の先頭付近（`init_db()` の前）に追加する**

`app.py` の `from src.matcher import match_candidates` の後ろ、`init_db()` の前に以下の関数を追加する:

```python
def _inject_css():
    st.markdown("""
    <style>
    /* ── エクスパンダー（カード） ── */
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
        background-color: #EAB308 !important;
        color: #1C1917 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    [data-testid="stButton"] > button:hover {
        background-color: #CA8A04 !important;
        color: #FFFFFF !important;
    }

    /* ── プライマリボタン（マッチング実行など） ── */
    [data-testid="stButton"] > button[kind="primary"] {
        background-color: #EAB308 !important;
        color: #1C1917 !important;
    }
    [data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #CA8A04 !important;
        color: #FFFFFF !important;
    }

    /* ── ページヘッダー ── */
    h1 {
        border-bottom: 2px solid #EAB308;
        padding-bottom: 8px;
        margin-bottom: 20px;
    }

    /* ── テキストインプット フォーカス ── */
    [data-testid="stTextInput"] input:focus {
        border-color: #EAB308 !important;
        box-shadow: 0 0 0 2px rgba(234,179,8,0.25) !important;
    }

    /* ── セレクトボックス フォーカス ── */
    [data-testid="stSelectbox"] > div:focus-within {
        border-color: #EAB308 !important;
    }

    /* ── サイドバータイトル ── */
    [data-testid="stSidebar"] h1 {
        border-bottom: 2px solid #EAB308;
    }

    /* ── プログレスバー ── */
    [data-testid="stProgressBar"] > div > div {
        background-color: #EAB308 !important;
    }
    </style>
    """, unsafe_allow_html=True)
```

- [ ] **Step 2: `st.set_page_config(...)` の直後に `_inject_css()` の呼び出しを追加する**

`app.py` の以下の部分を探す:

```python
st.set_page_config(
    page_title="SES AIマッチング",
    page_icon="🤝",
    layout="wide",
)
```

この直後（`# ────── Sidebar` のコメントの前）に追加:

```python
_inject_css()
```

- [ ] **Step 3: 構文チェック**

```bash
python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('syntax OK')"
```

期待出力: `syntax OK`

- [ ] **Step 4: コミット**

```bash
git add app.py
git commit -m "feat: 黄色テーマのCSSスタイルを注入する_inject_css()を追加"
```

---

## 最終確認チェックリスト

- [ ] `streamlit run app.py` でアプリが起動する
- [ ] ダッシュボードのメトリクスに黄色の上ボーダーが表示される
- [ ] エクスパンダー（案件・人材カード）の左側に黄色のラインが表示される
- [ ] 「メールを取得・同期」ボタンが黄色になっている
- [ ] ページヘッダー（「ダッシュボード」「案件一覧」等）の下に黄色の下線がある
- [ ] サイドバーの背景が薄黄色（#FEFCE8）になっている
- [ ] テキスト入力フォーカス時に黄色のリングが表示される
