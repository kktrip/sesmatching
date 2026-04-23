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

                for err in errors:
                    st.warning(err)

                st.success(
                    f"同期完了: 新規 {new_count}件 (案件 {project_count}件 / 人材 {candidate_count}件)"
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

    for p in projects:
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
            st.write(f"**概要:** {data.get('description', '—')}")


def show_candidates():
    st.header("👤 人材一覧")
    candidates = get_all_candidates()

    if not candidates:
        st.info("人材がありません。サイドバーから「メールを取得・同期」を実行してください。")
        return

    for c in candidates:
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
            st.write(f"**概要:** {data.get('summary', '—')}")
            if c["skill_sheet_text"]:
                with st.expander("スキルシート（抜粋）"):
                    st.text(c["skill_sheet_text"][:1000])


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
        st.json(project_data)

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
