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


def _parse_json_response(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner)
    return json.loads(text)


def match_candidates(project_data: dict, candidates: list[dict]) -> list[dict]:
    """
    Match a project against candidates and return top 5 ranked results.

    candidates: list of {"id": int, "name": str, "data": dict, "skill_sheet_text": str}
    Returns: list of match dicts sorted by score descending (up to 5)
    """
    if not candidates:
        return []

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
