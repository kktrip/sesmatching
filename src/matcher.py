import json
import re
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


def _parse_json_response(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner)
    return json.loads(text)


def _extract_relevant_excerpt(text: str, required_skills: list, max_chars: int = 300) -> str:
    """Return skill-sheet excerpt containing only sentences relevant to required_skills."""
    if not text:
        return ""
    if not required_skills:
        return text[:150]
    keywords = [s.lower() for s in required_skills]
    sentences = re.split(r'[。\r\n]+', text)
    relevant = [s.strip() for s in sentences
                if any(kw in s.lower() for kw in keywords) and s.strip()]
    excerpt = "　".join(relevant)[:max_chars]
    return excerpt or text[:150]


def _keyword_score(project_data: dict, candidate: dict) -> int:
    """Return keyword overlap count between project required_skills and candidate skills/sheet."""
    required = [s.lower() for s in project_data.get("required_skills", [])]
    cand_skills = [s.lower() for s in (candidate.get("data") or {}).get("skills", [])]
    sheet = (candidate.get("skill_sheet_text") or "").lower()
    score = 0
    for req in required:
        if any(req in cs for cs in cand_skills):
            score += 2
        elif req in sheet:
            score += 1
    return score


def _haiku_prescreening(project_data: dict, candidates: list[dict]) -> list[dict]:
    """Pre-screen candidates with Haiku; return top-10 by skill score."""
    required_skills = project_data.get("required_skills", [])

    candidate_summaries = [
        {
            "id": c["id"],
            "name": c["name"],
            "skills": (c.get("data") or {}).get("skills", []),
            "skill_excerpt": c.get("_compressed_excerpt", ""),
        }
        for c in candidates
    ]

    prompt = f"""あなたはSES案件マッチングの専門家です。
以下の案件必須スキルに対して、各人材のスキル適合度を0-100で評価してください。

【案件の必須スキル】
{json.dumps(required_skills, ensure_ascii=False)}

【人材リスト】
{json.dumps(candidate_summaries, ensure_ascii=False)}

以下のJSON配列のみで回答してください（説明文不要）:
[{{"id": 人材ID, "score": スキル適合度(0-100)}}]"""

    try:
        response = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        scores = _parse_json_response(response.content[0].text)
        score_map = {s["id"]: s["score"] for s in scores}
        ranked = sorted(candidates, key=lambda c: score_map.get(c["id"], 0), reverse=True)
        return ranked[:10]
    except Exception:
        return candidates


def match_candidates(project_data: dict, candidates: list[dict]) -> list[dict]:
    """
    Match a project against candidates and return top 5 ranked results.

    candidates: list of {"id": int, "name": str, "data": dict, "skill_sheet_text": str}
    Returns: list of match dicts sorted by score descending (up to 5)
    """
    if not candidates:
        return []

    # Stage 1: keyword pre-filter — limit to top 20 before Claude call
    if len(candidates) > 20:
        scored = sorted(candidates, key=lambda c: _keyword_score(project_data, c), reverse=True)
        candidates = scored[:20]

    candidate_summaries = []
    for c in candidates:
        summary = {
            "id": c["id"],
            "name": c["name"],
            **c["data"],
        }
        if c.get("skill_sheet_text"):
            summary["skill_sheet_excerpt"] = c["skill_sheet_text"][:500]
        candidate_summaries.append(summary)

    prompt = f"""あなたはSES（システムエンジニアリングサービス）の経験豊富なコーディネーターです。
以下の案件に最もマッチする人材を上位5名選定してください。

【案件情報】
{json.dumps(project_data, ensure_ascii=False, indent=2)}

【人材リスト（{len(candidate_summaries)}名）】
{json.dumps(candidate_summaries, ensure_ascii=False, indent=2)}

各人材を以下の観点で評価し、上位5名を選んでください:
- スキルマッチ度 (40%): 必要スキルとの合致
- 経験年数 (20%): 求められる経験との適合
- 参画可能時期 (20%): 案件開始時期との一致
- 勤務形態 (20%): 勤務地・リモート希望との適合

以下のJSON配列形式のみで回答してください（説明文不要）:
[
  {{
    "candidate_id": 人材のid(数値),
    "name": "氏名",
    "score": 総合スコア(0〜100の整数),
    "skill_match_score": スキルマッチスコア(0〜100の整数),
    "reason": "選定理由（具体的に、なぜこの人材が適しているか200字程度）",
    "concerns": "懸念点（特になければ空文字）"
  }}
]

必ず候補者数が5名未満の場合はその全員を、5名以上なら上位5名のみ返してください。"""

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    results = _parse_json_response(response.content[0].text)
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:5]
