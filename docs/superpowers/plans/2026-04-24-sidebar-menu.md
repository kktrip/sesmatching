# サイドバー VS Code 風メニュー 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `app.py` の `_inject_css()` 内サイドバーラジオCSSを置き換え、ラジオボタンの○を非表示にして VS Code 風の左アンバーバー付きナビメニューを実現する。

**Architecture:** `st.radio` のロジックは一切変更しない。`_inject_css()` 内の `/* ── Sidebar radio items ── */` セクション（約25行）だけを新しいCSSブロックに差し替える。アクティブ項目の検出は `:has(input[aria-checked="true"])` セレクタで行う。

**Tech Stack:** Python / Streamlit / CSS (`:has()` セレクタ — Chrome 105+, Firefox 121+, Safari 15.4+ 対応)

---

### Task 1: サイドバーラジオCSSを VS Code 風メニューCSSに差し替える

**Files:**
- Modify: `app.py:130-158`（`_inject_css()` 内の `/* ── Sidebar radio items ── */` セクション）

- [ ] **Step 1: 現在の該当セクションを確認する**

`app.py` の 130〜158行目付近にある以下のブロックを確認する：

```css
/* ── Sidebar radio items ── */
[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
    display: none;
}

[data-testid="stSidebar"] .stRadio > div {
    gap: 2px !important;
}

[data-testid="stSidebar"] .stRadio label {
    color: var(--text-secondary) !important;
    font-size: 0.875rem !important;
    font-weight: 400 !important;
    padding: 0.45rem 0.8rem !important;
    border-radius: 6px !important;
    transition: background 0.15s, color 0.15s !important;
    cursor: pointer !important;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background: var(--amber-glow) !important;
    color: var(--amber-bright) !important;
}

[data-testid="stSidebar"] .stRadio [aria-checked="true"] ~ div,
[data-testid="stSidebar"] .stRadio input:checked + label {
    color: var(--amber) !important;
    font-weight: 500 !important;
}
```

- [ ] **Step 2: 上記ブロックを以下の新しいCSSに差し替える**

`app.py` の該当セクション全体を次のCSSブロックで置き換える：

```css
/* ── Sidebar radio items (VS Code style menu) ── */
[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
    display: none;
}

/* ラジオボタンの○とその装飾要素を非表示 */
[data-testid="stSidebar"] .stRadio input[type="radio"] {
    display: none !important;
}

[data-testid="stSidebar"] .stRadio label > div:first-child {
    display: none !important;
}

/* メニュー項目の行全体をクリック可能に */
[data-testid="stSidebar"] .stRadio > div {
    gap: 0 !important;
}

[data-testid="stSidebar"] .stRadio label {
    display: flex !important;
    align-items: center !important;
    color: var(--text-secondary) !important;
    font-size: 0.875rem !important;
    font-weight: 400 !important;
    padding: 0.55rem 1rem !important;
    border-left: 3px solid transparent !important;
    border-radius: 0 !important;
    transition: background 0.15s, color 0.15s, border-left-color 0.15s !important;
    cursor: pointer !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

/* ホバー */
[data-testid="stSidebar"] .stRadio label:hover {
    background: var(--amber-glow) !important;
    color: var(--amber-bright) !important;
}

/* アクティブ項目: 左アンバーバー + 薄アンバー背景 */
[data-testid="stSidebar"] .stRadio label:has(input[aria-checked="true"]) {
    border-left-color: var(--amber) !important;
    background: var(--amber-glow) !important;
    color: var(--amber) !important;
    font-weight: 500 !important;
}
```

- [ ] **Step 3: ブラウザで視覚確認する**

`http://localhost:8501/` を開き、以下をすべて確認する：

1. サイドバーにラジオボタンの○が表示されていない
2. 「📊 ダッシュボード」がアクティブ時に左端アンバーバー + 薄アンバー背景になっている
3. 他の項目にマウスをホバーすると薄アンバー背景になる
4. 各メニュー項目をクリックするとページが切り替わる（📊📋👤🔍⚙️ すべて）
5. 項目間に余分な隙間がなくリスト状に並んでいる

- [ ] **Step 4: `:has()` が効かない場合のフォールバックを確認する**

Step 3 でアクティブスタイルが表示されない場合のみ実施。ブラウザの DevTools でサイドバーのラジオ input 要素を検査し、`aria-checked` 属性の有無を確認する。

`aria-checked` が input ではなく親要素に付いている場合は、以下のセレクタに変更する：

```css
/* aria-checked が input の親 div についている場合 */
[data-testid="stSidebar"] .stRadio label:has([aria-checked="true"]) {
    border-left-color: var(--amber) !important;
    background: var(--amber-glow) !important;
    color: var(--amber) !important;
    font-weight: 500 !important;
}
```

- [ ] **Step 5: コミットする**

```bash
git add app.py
git commit -m "feat: サイドバーナビをVS Code風メニューにリスタイル"
```
