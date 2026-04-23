# サイドバーナビゲーション: VS Code 風メニュー

**日付:** 2026-04-24  
**対象ファイル:** `app.py` — `_inject_css()` 関数内のサイドバー・ラジオCSS

---

## 概要

現在 `st.radio` で実装されているサイドバーナビゲーションを、ラジオボタンの○を非表示にし CSS だけで VS Code 風のメニュー項目として再スタイリングする。ロジックの変更は一切行わない。

---

## ビジュアル仕様

```
┌─────────────────────┐
│ 🤝 SES AIマッチング  │
├─────────────────────┤
│▌📊 ダッシュボード    │  ← アクティブ項目
│  📋 案件一覧         │
│  👤 人材一覧         │
│  🔍 マッチング       │
│  ⚙️  設定            │
├─────────────────────┤
│ メール同期           │
│ [📥 メールを取得]    │
└─────────────────────┘
```

### アクティブ状態
- 左端に `3px solid var(--amber)` の縦バー
- 背景: `var(--amber-glow)` (rgba(217,119,6,0.10))
- テキスト・絵文字: `var(--amber)` 色、`font-weight: 500`

### 非アクティブ状態
- 背景: なし
- テキスト: `var(--text-secondary)`

### ホバー状態
- 背景: `var(--amber-glow)`
- テキスト: `var(--amber-bright)`
- 縦バーなし

---

## 実装方針

### アプローチ
`st.radio` を維持したまま CSS のみで再スタイリング（アプローチ A）。ページ遷移ロジック・`st.radio` の呼び出しコードは変更しない。

### 変更箇所
`app.py` の `_inject_css()` 内、`/* ── Sidebar radio items ── */` セクション（約25行）を置き換える。

### CSS 変更詳細

1. **ラジオ○の非表示**
   - `input[type="radio"]` を `display: none`
   - Streamlit が挿入する装飾用 `div`（○の視覚要素）も `display: none`

2. **label をブロック要素に**
   - `display: block`、`padding: 0.6rem 1rem`
   - `border-left: 3px solid transparent`（非アクティブ時は透明バーを確保してレイアウトずれ防止）

3. **アクティブ項目**
   - セレクタ: `[data-testid="stSidebar"] .stRadio label:has(input[aria-checked="true"])`  
     またはフォールバック: `[aria-checked="true"]` の最近接 `label`
   - `border-left-color: var(--amber)`
   - `background: var(--amber-glow)`
   - `color: var(--amber)` + `font-weight: 500`

4. **ホバー**
   - `background: var(--amber-glow)`
   - `color: var(--amber-bright)`

5. **`stRadio > div` の gap を `0`**
   - 行間をなくし、リスト状に詰める

---

## 制約・注意事項

- Streamlit の内部 HTML 構造（`aria-checked` 属性の付き方）は Streamlit バージョンアップで変わりうる。アクティブセレクタが効かなくなった場合は DevTools で再確認する。
- CSS の変更は `_inject_css()` 関数の該当セクションのみ。他のスタイルには触れない。
- `st.radio` の値・ページルーター（`if page == ...`）は変更しない。

---

## 完了基準

- [ ] サイドバーにラジオボタンの○が表示されない
- [ ] 各メニュー項目が行全体クリック可能
- [ ] アクティブ項目に左アンバーバーと薄アンバー背景が表示される
- [ ] ホバー時に薄アンバー背景が表示される
- [ ] 5ページすべての遷移が正常に動作する
