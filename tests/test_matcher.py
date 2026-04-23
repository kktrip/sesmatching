import pytest
from src.matcher import _extract_relevant_excerpt


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
