import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import init_db, insert_email, insert_candidate, get_candidate_by_id

def test_get_candidate_by_id_includes_email_fields(tmp_path, monkeypatch):
    import src.database as db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    init_db()
    email_id = insert_email("mid1", "件名テスト", "from@example.com", "2024-01-01", "body", "candidate")
    cand_id = insert_candidate(email_id, "山田太郎", "{}", "スキルシート")
    row = get_candidate_by_id(cand_id)
    assert row["email_subject"] == "件名テスト"
    assert row["sender"] == "from@example.com"
    assert row["lark_message_id"] is None
    assert row["name"] == "山田太郎"
