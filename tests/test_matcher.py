import json
import pytest
from unittest.mock import MagicMock, patch
from src.matcher import _extract_relevant_excerpt, _haiku_prescreening


def test_extract_finds_matching_sentences():
    text = "Pythonでの開発経験があります。\nJavaScriptも対応可能です。\nExcelの操作ができます。"
    result = _extract_relevant_excerpt(text, ["Python", "JavaScript"], max_chars=300)
    assert "Python" in result
    assert "JavaScript" in result
    assert "Excel" not in result


def test_extract_excludes_unrelated_sentences():
    text = "一般的なPC操作ができます。\nPythonで5年の経験があります。\n英語は日常会話レベルです。"
    result = _extract_relevant_excerpt(text, ["Python"], max_chars=300)
    assert "Python" in result
    assert "PC操作" not in result
    assert "英語" not in result


def test_extract_respects_max_chars():
    text = "Python " * 100
    result = _extract_relevant_excerpt(text, ["Python"], max_chars=50)
    assert len(result) <= 50


def test_extract_fallback_when_no_match():
    text = "特にスキルの記載はありません。一般的な業務経験があります。"
    result = _extract_relevant_excerpt(text, ["AWS", "Kubernetes"], max_chars=300)
    # フォールバック: 先頭150文字を返す
    assert result == text[:150]


def test_extract_empty_text():
    result = _extract_relevant_excerpt("", ["Python"], max_chars=300)
    assert result == ""


def test_extract_case_insensitive():
    text = "python開発の経験があります。"
    result = _extract_relevant_excerpt(text, ["Python"], max_chars=300)
    assert "python" in result


def test_haiku_prescreening_returns_top_10():
    candidates = [
        {
            "id": i,
            "name": f"候補者{i}",
            "data": {"skills": []},
            "skill_sheet_text": "",
            "_compressed_excerpt": "",
        }
        for i in range(20)
    ]
    project_data = {"required_skills": ["Python"]}
    # id=0 が最高スコア(20)、id=19 が最低スコア(1)
    mock_scores = json.dumps([{"id": i, "score": 20 - i} for i in range(20)])

    with patch("src.matcher._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create.return_value.content = [
            MagicMock(text=mock_scores)
        ]
        result = _haiku_prescreening(project_data, candidates)

    assert len(result) == 10
    result_ids = [c["id"] for c in result]
    # 上位10名（id=0〜9）が選ばれる
    for i in range(10):
        assert i in result_ids


def test_haiku_prescreening_fallback_on_parse_error():
    candidates = [
        {
            "id": i,
            "name": f"候補者{i}",
            "data": {"skills": []},
            "skill_sheet_text": "",
            "_compressed_excerpt": "",
        }
        for i in range(5)
    ]
    project_data = {"required_skills": ["Python"]}

    with patch("src.matcher._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create.return_value.content = [
            MagicMock(text="invalid json {{")
        ]
        result = _haiku_prescreening(project_data, candidates)

    # フォールバック: 元の candidates をそのまま返す
    assert result == candidates


def test_haiku_prescreening_fewer_than_10_candidates():
    candidates = [
        {
            "id": i,
            "name": f"候補者{i}",
            "data": {"skills": []},
            "skill_sheet_text": "",
            "_compressed_excerpt": "",
        }
        for i in range(7)
    ]
    project_data = {"required_skills": ["Python"]}
    mock_scores = json.dumps([{"id": i, "score": 7 - i} for i in range(7)])

    with patch("src.matcher._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create.return_value.content = [
            MagicMock(text=mock_scores)
        ]
        result = _haiku_prescreening(project_data, candidates)

    # 7名しかいない場合は全員返す（10名に満たない）
    assert len(result) == 7
