import json
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _parse_json_response(text: str) -> dict | list:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner)
    return json.loads(text)


def classify_and_extract(subject: str, body: str, attachment_text: str = "") -> dict:
    """
    Classify email as project/candidate and extract structured data.
    Returns dict with keys: type, data
    """
    attachment_section = ""
    if attachment_text.strip():
        attachment_section = f"\n\n【添付ファイル内容】\n{attachment_text[:4000]}"

    prompt = f"""以下のメールを分析し、案件紹介メールか人材紹介メールかを判断して構造化データを抽出してください。

【件名】{subject}

【本文】
{body[:4000]}{attachment_section}

以下のJSON形式のみで回答してください（説明文不要）:

案件メールの場合:
{{
  "type": "project",
  "data": {{
    "title": "案件名",
    "required_skills": ["スキル1", "スキル2"],
    "experience_years": 必要経験年数(数値、不明な場合はnull),
    "period": "期間・契約形態",
    "location": "勤務地",
    "work_style": "リモート/常駐/ハイブリッド/不明",
    "budget": "単価・予算（記載がない場合は空文字）",
    "start_date": "開始時期",
    "description": "案件概要（300字以内）"
  }}
}}

人材メールの場合:
{{
  "type": "candidate",
  "data": {{
    "name": "氏名（不明な場合は「氏名不明」）",
    "age": 年齢(数値、不明な場合はnull),
    "skills": ["スキル1", "スキル2"],
    "experience_years": 経験年数(数値、不明な場合はnull),
    "available_from": "参画可能時期",
    "work_style_preference": "希望勤務形態",
    "desired_rate": "希望単価（記載がない場合は空文字）",
    "summary": "人材概要（300字以内）"
  }}
}}

どちらでもない場合:
{{
  "type": "unknown",
  "data": {{}}
}}"""

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    return _parse_json_response(response.content[0].text)
