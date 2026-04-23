import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

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
from src.email_fetcher import fetch_emails
from src.attachment_parser import parse_attachment
from src.ai_processor import classify_and_extract
from src.matcher import match_candidates


def _inject_css():
    """Inject Light Command Center design system via st.markdown."""
    st.markdown("""
    <style>
    /* ═══════════════════════════════════════════════════
       Fonts
    ═══════════════════════════════════════════════════ */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

    /* ═══════════════════════════════════════════════════
       Design Tokens
    ═══════════════════════════════════════════════════ */
    :root {
        --bg-base:        #F5F7FA;
        --bg-elevated:    #EAECF0;
        --bg-card:        #FFFFFF;
        --bg-hover:       #E2E5EA;
        --border:         rgba(180,130,0,0.20);
        --border-hover:   rgba(180,130,0,0.50);
        --amber:          #D97706;
        --amber-bright:   #F59E0B;
        --amber-dim:      #B45309;
        --amber-glow:     rgba(217,119,6,0.10);
        --amber-glow-strong: rgba(217,119,6,0.25);
        --sky:            #0284C7;
        --green:          #16A34A;
        --red:            #DC2626;
        --text-primary:   #1C1E26;
        --text-secondary: #4A5568;
        --text-muted:     #8896A4;
        --font-sans:      'Noto Sans JP', -apple-system, sans-serif;
        --font-mono:      'JetBrains Mono', monospace;
        --radius:         8px;
        --radius-lg:      12px;
    }

    /* ═══════════════════════════════════════════════════
       Base
    ═══════════════════════════════════════════════════ */
    html, body, .stApp {
        background: var(--bg-base) !important;
        font-family: var(--font-sans) !important;
        color: var(--text-primary) !important;
    }

    /* ── Top bar ── */
    [data-testid="stHeader"] {
        background: rgba(245,247,250,0.90) !important;
        border-bottom: 1px solid var(--border) !important;
        backdrop-filter: blur(12px) !important;
    }

    /* ── Main content padding ── */
    .main .block-container {
        padding: 1.75rem 2.5rem !important;
        max-width: 1400px !important;
    }

    /* ═══════════════════════════════════════════════════
       Sidebar
    ═══════════════════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: var(--bg-elevated) !important;
        border-right: 1px solid var(--border) !important;
    }

    [data-testid="stSidebar"] * {
        font-family: var(--font-sans) !important;
    }

    [data-testid="stSidebar"] h1 {
        color: var(--amber) !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        border-bottom: 1px solid var(--border) !important;
        padding-bottom: 0.65rem !important;
        margin-bottom: 0.75rem !important;
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--text-muted) !important;
        font-size: 0.68rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdown"] p {
        color: var(--text-muted) !important;
        font-size: 0.8rem !important;
    }

    /* ── Sidebar radio items (VS Code style menu) ── */
    [data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
        display: none !important;
    }

    /* ラジオボタンの○とその装飾要素を非表示 */
    [data-testid="stSidebar"] .stRadio input[type="radio"] {
        position: absolute !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        pointer-events: none !important;
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
    [data-testid="stSidebar"] .stRadio label:has(input:checked) {
        border-left-color: var(--amber) !important;
        background: var(--amber-glow) !important;
        color: var(--amber) !important;
        font-weight: 500 !important;
    }

    /* ── Sidebar divider ── */
    [data-testid="stSidebar"] hr {
        border-color: var(--border) !important;
        margin: 0.75rem 0 !important;
    }

    /* ═══════════════════════════════════════════════════
       Typography
    ═══════════════════════════════════════════════════ */
    h1 {
        color: var(--text-primary) !important;
        font-size: 1.65rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em !important;
        border-bottom: 1px solid var(--border) !important;
        padding-bottom: 0.7rem !important;
        margin-bottom: 1.5rem !important;
    }

    h2 {
        color: var(--text-primary) !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        margin-top: 1.25rem !important;
    }

    h3 {
        color: var(--text-primary) !important;
        font-size: 1.05rem !important;
        font-weight: 500 !important;
    }

    p, .stMarkdown p {
        color: var(--text-secondary) !important;
        font-size: 0.9rem !important;
        line-height: 1.7 !important;
    }

    /* Prevent global p rule from overriding metric/expander internals */
    [data-testid="stMetricValue"] p,
    [data-testid="stMetricValue"] div {
        color: var(--amber) !important;
        font-family: var(--font-mono) !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        line-height: 1.1 !important;
    }

    [data-testid="stExpander"] summary p {
        color: var(--text-primary) !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        margin: 0 !important;
    }

    strong {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }

    hr {
        border-color: var(--border) !important;
        margin: 1.25rem 0 !important;
    }

    [data-testid="stCaptionContainer"],
    .stCaption {
        color: var(--text-muted) !important;
        font-size: 0.78rem !important;
    }

    /* ═══════════════════════════════════════════════════
       Metrics
    ═══════════════════════════════════════════════════ */
    [data-testid="stMetric"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-top: 2px solid var(--amber) !important;
        border-radius: var(--radius-lg) !important;
        padding: 1.25rem 1.5rem !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
        transition: transform 0.18s ease, box-shadow 0.18s ease !important;
        animation: fadeUp 0.5s ease both !important;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 32px var(--amber-glow-strong) !important;
    }

    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] label {
        color: var(--text-muted) !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        margin: 0 !important;
    }

    [data-testid="stMetricValue"] p,
    [data-testid="stMetricValue"] div {
        color: var(--amber) !important;
        font-family: var(--font-mono) !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        line-height: 1.1 !important;
        margin: 0 !important;
    }

    [data-testid="stMetricDelta"] p,
    [data-testid="stMetricDelta"] div {
        font-family: var(--font-mono) !important;
        font-size: 0.8rem !important;
    }

    /* ═══════════════════════════════════════════════════
       Expander / Cards
    ═══════════════════════════════════════════════════ */
    [data-testid="stExpander"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-left: 3px solid var(--amber) !important;
        border-radius: var(--radius) !important;
        margin-bottom: 5px !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
        transition: border-left-color 0.18s, box-shadow 0.18s, transform 0.18s !important;
        animation: fadeUp 0.35s ease both !important;
        overflow: hidden !important;
    }

    [data-testid="stExpander"]:hover {
        box-shadow: 0 5px 24px var(--amber-glow) !important;
        transform: translateX(3px) !important;
    }

    [data-testid="stExpander"] summary {
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        padding: 0.8rem 1rem !important;
        background: transparent !important;
    }

    [data-testid="stExpander"] summary:hover {
        color: var(--amber-bright) !important;
    }

    [data-testid="stExpanderDetails"] {
        background: var(--bg-hover) !important;
        border-top: 1px solid var(--border) !important;
        padding: 1rem 1.1rem !important;
    }

    /* staggered card animation */
    [data-testid="stExpander"]:nth-child(1)  { animation-delay: 0.04s !important; }
    [data-testid="stExpander"]:nth-child(2)  { animation-delay: 0.08s !important; }
    [data-testid="stExpander"]:nth-child(3)  { animation-delay: 0.12s !important; }
    [data-testid="stExpander"]:nth-child(4)  { animation-delay: 0.16s !important; }
    [data-testid="stExpander"]:nth-child(5)  { animation-delay: 0.20s !important; }

    /* ═══════════════════════════════════════════════════
       Buttons
    ═══════════════════════════════════════════════════ */
    [data-testid="stButton"] > button {
        background: transparent !important;
        color: var(--amber) !important;
        border: 1px solid var(--amber) !important;
        border-radius: var(--radius) !important;
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        letter-spacing: 0.02em !important;
        transition: background 0.18s, color 0.18s, box-shadow 0.18s !important;
    }

    [data-testid="stButton"] > button:hover {
        background: var(--amber) !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 20px var(--amber-glow-strong) !important;
    }

    /* Primary-type button (type="primary") */
    [data-testid="stBaseButton-primary"] {
        background: var(--amber) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: var(--radius) !important;
        font-weight: 700 !important;
        font-size: 0.875rem !important;
        letter-spacing: 0.02em !important;
        transition: background 0.18s, box-shadow 0.18s !important;
    }

    [data-testid="stBaseButton-primary"]:hover {
        background: var(--amber-bright) !important;
        box-shadow: 0 0 28px var(--amber-glow-strong) !important;
    }

    /* ═══════════════════════════════════════════════════
       Form Inputs
    ═══════════════════════════════════════════════════ */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        font-family: var(--font-sans) !important;
        font-size: 0.9rem !important;
        transition: border-color 0.18s, box-shadow 0.18s !important;
    }

    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {
        border-color: var(--amber) !important;
        box-shadow: 0 0 0 3px var(--amber-glow) !important;
        outline: none !important;
    }

    /* Placeholder text */
    [data-testid="stTextInput"] input::placeholder {
        color: var(--text-muted) !important;
    }

    /* ── Select / Dropdown ── */
    [data-testid="stSelectbox"] > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        color: var(--text-primary) !important;
    }

    [data-testid="stSelectbox"] > div:focus-within > div {
        border-color: var(--amber) !important;
        box-shadow: 0 0 0 3px var(--amber-glow) !important;
    }

    /* ── Form container ── */
    [data-testid="stForm"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 1.5rem !important;
    }

    /* ── Number input arrows ── */
    [data-testid="stNumberInput"] button {
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
    }

    /* ═══════════════════════════════════════════════════
       Alert / Info / Success / Warning / Error
    ═══════════════════════════════════════════════════ */
    [data-testid="stAlert"] {
        border-radius: var(--radius) !important;
        border-width: 1px !important;
        font-size: 0.875rem !important;
    }

    [data-baseweb="notification"][kind="positive"],
    .stSuccess > div {
        background: rgba(22,163,74,0.08) !important;
        border-color: var(--green) !important;
        color: var(--green) !important;
    }

    [data-baseweb="notification"][kind="warning"],
    .stWarning > div {
        background: rgba(217,119,6,0.08) !important;
        border-color: var(--amber) !important;
        color: var(--amber) !important;
    }

    [data-baseweb="notification"][kind="info"],
    .stInfo > div {
        background: rgba(2,132,199,0.08) !important;
        border-color: var(--sky) !important;
        color: var(--sky) !important;
    }

    [data-baseweb="notification"][kind="negative"],
    .stError > div {
        background: rgba(220,38,38,0.08) !important;
        border-color: var(--red) !important;
        color: var(--red) !important;
    }

    /* ═══════════════════════════════════════════════════
       Progress Bar
    ═══════════════════════════════════════════════════ */
    [data-testid="stProgressBar"] > div {
        background: var(--bg-elevated) !important;
        border-radius: 4px !important;
        overflow: hidden !important;
    }

    [data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, var(--amber-dim), var(--amber)) !important;
        box-shadow: 0 0 10px var(--amber-glow-strong) !important;
        border-radius: 4px !important;
        transition: width 0.3s ease !important;
    }

    /* ═══════════════════════════════════════════════════
       Spinner
    ═══════════════════════════════════════════════════ */
    [data-testid="stSpinner"] > div {
        border-top-color: var(--amber) !important;
    }

    /* ═══════════════════════════════════════════════════
       Scrollbar
    ═══════════════════════════════════════════════════ */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: var(--bg-base); }
    ::-webkit-scrollbar-thumb {
        background: rgba(245,158,11,0.25);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--amber-dim); }

    /* ═══════════════════════════════════════════════════
       Animations
    ═══════════════════════════════════════════════════ */
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(10px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    @keyframes glowPulse {
        0%, 100% { box-shadow: 0 0 0 0 var(--amber-glow); }
        50%       { box-shadow: 0 0 16px 4px var(--amber-glow); }
    }

    [data-testid="stMetric"]:nth-child(1) { animation-delay: 0s !important; }
    [data-testid="stMetric"]:nth-child(2) { animation-delay: 0.1s !important; }
    [data-testid="stMetric"]:nth-child(3) { animation-delay: 0.2s !important; }

    /* ── Sidebar email-sync button glows ── */
    [data-testid="stSidebar"] [data-testid="stButton"] > button {
        border-color: var(--amber) !important;
        animation: glowPulse 3s ease-in-out infinite !important;
    }

    /* ═══════════════════════════════════════════════════
       Match result containers
    ═══════════════════════════════════════════════════ */
    [data-testid="stVerticalBlock"] > div > [data-testid="stVerticalBlock"] {
        background: var(--bg-card) !important;
    }

    /* ── Code / monospace ── */
    code, pre {
        font-family: var(--font-mono) !important;
        background: var(--bg-elevated) !important;
        color: var(--amber) !important;
        border-radius: 4px !important;
        padding: 0.1em 0.35em !important;
        font-size: 0.85em !important;
    }

    /* ── Selectbox dropdown options ── */
    ul[role="listbox"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
    }

    ul[role="listbox"] li {
        color: var(--text-secondary) !important;
    }

    ul[role="listbox"] li:hover,
    ul[role="listbox"] li[aria-selected="true"] {
        background: var(--amber-glow) !important;
        color: var(--amber) !important;
    }
    </style>
    """, unsafe_allow_html=True)


def _process_one_email(em):
    """Parse attachments and classify via Claude. Returns (em, result, attachment_text)."""
    attachment_text = ""
    for att in em.get("attachments", []):
        attachment_text += parse_attachment(att["filename"], att["data"]) + "\n"
    result = classify_and_extract(em["subject"], em["body"], attachment_text)
    return em, result, attachment_text

init_db()

st.set_page_config(
    page_title="SES AIマッチング",
    page_icon="🤝",
    layout="wide",
)

_inject_css()

# ────────────────────────────────────────────
# Sidebar
# ────────────────────────────────────────────
with st.sidebar:
    st.title("🤝 SES AIマッチング")
    st.markdown("---")

    page = st.radio(
        "ページ",
        ["📊 ダッシュボード", "📋 案件一覧", "👤 人材一覧", "🔍 マッチング", "⚙️ 設定"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.subheader("メール同期")
    if st.button("📥 メールを取得・同期", use_container_width=True):
        try:
            status = st.empty()

            # Step 1: load known IDs from DB (one query, not N queries)
            status.info("DBから既知メールIDを取得中...")
            known_ids = get_all_message_ids()

            # Step 2: IMAP two-phase fetch (headers → filter → full body for new only)
            status.info(f"IMAPサーバーに接続中... (既知 {len(known_ids)} 件をスキップ)")
            emails = fetch_emails(max_count=500, skip_ids=known_ids)

            if not emails:
                status.empty()
                st.success("新しいメールはありません。")
                st.rerun()
            else:
                total = len(emails)
                status.info(f"新規 {total} 件を並列AI処理中...")
                progress = st.progress(0)

                # Step 3: parallel Claude API calls
                processed = {}
                errors = []
                completed_count = 0

                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_em = {executor.submit(_process_one_email, em): em for em in emails}
                    for future in as_completed(future_to_em):
                        completed_count += 1
                        progress.progress(completed_count / total)
                        try:
                            em, result, attachment_text = future.result()
                            processed[em["message_id"]] = (em, result, attachment_text)
                        except Exception as e:
                            em = future_to_em[future]
                            errors.append(f"AI処理エラー ({em['subject'][:30]}): {e}")

                progress.empty()
                status.empty()

                # Step 4: DB inserts (sequential, fast)
                new_count = 0
                project_count = 0
                candidate_count = 0
                dedup_skip_count = 0

                for em in emails:
                    item = processed.get(em["message_id"])
                    if item is None:
                        continue
                    _, result, attachment_text = item

                    email_type = result.get("type", "unknown")
                    data = result.get("data", {})

                    email_id = insert_email(
                        em["message_id"],
                        em["subject"],
                        em["sender"],
                        em["received_at"],
                        em["body"],
                        email_type,
                    )
                    if email_id is None:
                        continue

                    new_count += 1
                    if email_type == "project":
                        title = data.get("title", em["subject"])
                        if not project_exists(title, em["sender"]):
                            insert_project(email_id, title, json.dumps(data, ensure_ascii=False))
                            project_count += 1
                        else:
                            dedup_skip_count += 1
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
                        else:
                            dedup_skip_count += 1

                for err in errors:
                    st.warning(err)

                dedup_msg = f" / 重複スキップ {dedup_skip_count}件" if dedup_skip_count else ""
                st.success(
                    f"同期完了: 新規 {new_count}件 (案件 {project_count}件 / 人材 {candidate_count}件{dedup_msg})"
                )
                st.rerun()

        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"メール取得エラー: {e}")


# ────────────────────────────────────────────
# Pages
# ────────────────────────────────────────────

def show_dashboard():
    st.header("📊 ダッシュボード")
    stats = get_stats()

    col1, col2, col3 = st.columns(3)
    col1.metric("案件数", stats["projects"])
    col2.metric("人材数", stats["candidates"])
    col3.metric("マッチング実行数", stats["matches"])

    st.markdown("---")

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("最近の案件")
        projects = get_all_projects()[:5]
        if projects:
            for p in projects:
                data = json.loads(p["data"])
                skills = ", ".join(data.get("required_skills", [])[:3])
                with st.expander(f"📋 {p['title']}"):
                    st.write(f"**勤務地:** {data.get('location', '不明')}")
                    st.write(f"**スキル:** {skills or '—'}")
                    st.write(f"**開始時期:** {data.get('start_date', '不明')}")
                    st.write(f"**登録日:** {p['created_at'][:10]}")
        else:
            st.info("案件がまだありません。サイドバーから「メールを取得・同期」を実行してください。")

    with col_r:
        st.subheader("最近の人材")
        candidates = get_all_candidates()[:5]
        if candidates:
            for c in candidates:
                data = json.loads(c["data"])
                skills = ", ".join(data.get("skills", [])[:3])
                with st.expander(f"👤 {c['name']}"):
                    st.write(f"**経験年数:** {data.get('experience_years', '不明')}年")
                    st.write(f"**スキル:** {skills or '—'}")
                    st.write(f"**参画可能:** {data.get('available_from', '不明')}")
                    st.write(f"**登録日:** {c['created_at'][:10]}")
        else:
            st.info("人材がまだありません。")


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

    projects_with_data = [(p, json.loads(p["data"])) for p in projects]

    def _match_project(p, data):
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

    filtered = [(p, data) for p, data in projects_with_data if _match_project(p, data)]
    st.caption(f"{len(filtered)} 件 / 全 {len(projects)} 件")

    for p, data in filtered:
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


def show_candidates():
    st.header("👤 人材一覧")
    candidates = get_all_candidates()

    if not candidates:
        st.info("人材がありません。サイドバーから「メールを取得・同期」を実行してください。")
        return

    candidates_with_data = [(c, json.loads(c["data"])) for c in candidates]

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

    def _match_candidate(c, data):
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

    filtered = [(c, data) for c, data in candidates_with_data if _match_candidate(c, data)]
    st.caption(f"{len(filtered)} 件 / 全 {len(candidates)} 件")

    for c, data in filtered:
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


def show_matching():
    st.header("🔍 AIマッチング")

    projects = get_all_projects()
    candidates = get_all_candidates()

    if not projects:
        st.warning("案件がありません。まずメールを同期してください。")
        return
    if not candidates:
        st.warning("人材がありません。まずメールを同期してください。")
        return

    project_options = {f"{p['title']} ({p['created_at'][:10]})": p["id"] for p in projects}
    selected_label = st.selectbox("案件を選択してください", list(project_options.keys()))
    selected_project_id = project_options[selected_label]

    project_row = get_project_by_id(selected_project_id)
    project_data = json.loads(project_row["data"])

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

    st.markdown("---")

    # Show cached result if exists
    latest_match = get_latest_match(selected_project_id)
    if latest_match:
        st.info(f"前回のマッチング結果（{latest_match['created_at'][:16]}）を表示中")
        _render_match_results(json.loads(latest_match["results"]), candidates)

    col1, col2 = st.columns([1, 4])
    with col1:
        run_button = st.button("🚀 マッチング実行", use_container_width=True, type="primary")

    if run_button:
        with st.spinner(f"Claude が {len(candidates)} 名の人材を評価中..."):
            candidate_dicts = []
            for c in candidates:
                candidate_dicts.append({
                    "id": c["id"],
                    "name": c["name"],
                    "data": json.loads(c["data"]),
                    "skill_sheet_text": c["skill_sheet_text"] or "",
                })

            try:
                results = match_candidates(project_data, candidate_dicts)
                insert_match(selected_project_id, json.dumps(results, ensure_ascii=False))
                st.success("マッチング完了！上位5名を表示します。")
                _render_match_results(results, candidates)
            except Exception as e:
                st.error(f"マッチングエラー: {e}")


def _render_match_results(results: list, all_candidates):
    candidates_by_id = {c["id"]: c for c in all_candidates}

    st.subheader("🏆 マッチング結果 TOP 5")
    rank_labels = ["🥇", "🥈", "🥉", "4位", "5位"]

    for i, r in enumerate(results):
        rank = rank_labels[i] if i < len(rank_labels) else f"{i+1}位"
        cid = r.get("candidate_id")
        name = r.get("name", "氏名不明")
        score = r.get("score", 0)
        skill_score = r.get("skill_match_score", 0)
        reason = r.get("reason", "")
        concerns = r.get("concerns", "")

        candidate_row = candidates_by_id.get(cid)
        candidate_data = json.loads(candidate_row["data"]) if candidate_row else {}
        skills = ", ".join(candidate_data.get("skills", []))

        with st.container():
            st.markdown(f"### {rank} {name}")
            col1, col2, col3 = st.columns(3)
            col1.metric("総合スコア", f"{score} / 100")
            col2.metric("スキルマッチ", f"{skill_score} / 100")
            col3.metric("経験年数", f"{candidate_data.get('experience_years', '?')}年")

            st.write(f"**スキル:** {skills or '—'}")
            st.write(f"**参画可能時期:** {candidate_data.get('available_from', '不明')}")
            st.write(f"**希望単価:** {candidate_data.get('desired_rate', '非公開')}")
            st.write(f"**選定理由:** {reason}")
            if concerns:
                st.warning(f"**懸念点:** {concerns}")
            st.markdown("---")


def show_settings():
    st.header("⚙️ 設定")
    st.subheader("IMAPサーバー設定")
    st.info("設定は `.env` ファイルに保存します。変更後はアプリを再起動してください。")

    env_path = os.path.join(os.path.dirname(__file__), ".env")

    current_host = os.getenv("IMAP_HOST", "")
    current_port = os.getenv("IMAP_PORT", "993")
    current_user = os.getenv("IMAP_USER", "")

    with st.form("imap_settings"):
        host = st.text_input("IMAPホスト", value=current_host, placeholder="mail.example.com")
        port = st.text_input("ポート", value=current_port, placeholder="993")
        user = st.text_input("メールアドレス", value=current_user, placeholder="info@falcs.jp")
        password = st.text_input("パスワード", type="password", placeholder="メールパスワード")
        submitted = st.form_submit_button("保存", type="primary")

        if submitted:
            lines = []
            if os.path.exists(env_path):
                with open(env_path) as f:
                    lines = f.readlines()

            def _set_env_line(lines, key, value):
                for i, line in enumerate(lines):
                    if line.startswith(f"{key}="):
                        lines[i] = f"{key}={value}\n"
                        return lines
                lines.append(f"{key}={value}\n")
                return lines

            if host:
                lines = _set_env_line(lines, "IMAP_HOST", host)
            if port:
                lines = _set_env_line(lines, "IMAP_PORT", port)
            if user:
                lines = _set_env_line(lines, "IMAP_USER", user)
            if password:
                lines = _set_env_line(lines, "IMAP_PASSWORD", password)

            with open(env_path, "w") as f:
                f.writelines(lines)

            st.success("保存しました。アプリを再起動すると反映されます。")

    st.markdown("---")
    st.subheader("データベース")
    stats = get_stats()
    st.write(f"案件数: **{stats['projects']}**　人材数: **{stats['candidates']}**　マッチング数: **{stats['matches']}**")


# ────────────────────────────────────────────
# Router
# ────────────────────────────────────────────
if page == "📊 ダッシュボード":
    show_dashboard()
elif page == "📋 案件一覧":
    show_projects()
elif page == "👤 人材一覧":
    show_candidates()
elif page == "🔍 マッチング":
    show_matching()
elif page == "⚙️ 設定":
    show_settings()
