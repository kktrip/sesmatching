import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "sesmatching.db"


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                subject TEXT,
                sender TEXT,
                received_at TEXT,
                body TEXT,
                email_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER REFERENCES emails(id),
                title TEXT,
                data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER REFERENCES emails(id),
                name TEXT,
                data TEXT,
                skill_sheet_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id),
                results TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)


def insert_email(message_id, subject, sender, received_at, body, email_type):
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO emails (message_id, subject, sender, received_at, body, email_type) VALUES (?,?,?,?,?,?)",
                (message_id, subject, sender, received_at, body, email_type),
            )
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            return None


def insert_project(email_id, title, data_json):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO projects (email_id, title, data) VALUES (?,?,?)",
            (email_id, title, data_json),
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def insert_candidate(email_id, name, data_json, skill_sheet_text):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO candidates (email_id, name, data, skill_sheet_text) VALUES (?,?,?,?)",
            (email_id, name, data_json, skill_sheet_text),
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def insert_match(project_id, results_json):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO matches (project_id, results) VALUES (?,?)",
            (project_id, results_json),
        )


def get_all_projects():
    with get_connection() as conn:
        return conn.execute(
            "SELECT p.*, e.sender, e.received_at FROM projects p LEFT JOIN emails e ON p.email_id = e.id ORDER BY p.created_at DESC"
        ).fetchall()


def get_all_candidates():
    with get_connection() as conn:
        return conn.execute(
            "SELECT c.*, e.sender, e.received_at FROM candidates c LEFT JOIN emails e ON c.email_id = e.id ORDER BY c.created_at DESC"
        ).fetchall()


def get_project_by_id(project_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()


def get_candidate_by_id(candidate_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()


def get_latest_match(project_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM matches WHERE project_id=? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()


def get_stats():
    with get_connection() as conn:
        projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        candidates = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        matches = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        return {"projects": projects, "candidates": candidates, "matches": matches}


def email_exists(message_id):
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM emails WHERE message_id=?", (message_id,)).fetchone()
        return row is not None


def get_all_message_ids():
    """Return set of all message_id strings already stored in DB."""
    with get_connection() as conn:
        rows = conn.execute("SELECT message_id FROM emails").fetchall()
        return {row[0] for row in rows}


def project_exists(title: str, sender: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT p.id FROM projects p JOIN emails e ON p.email_id = e.id WHERE p.title=? AND e.sender=?",
            (title, sender),
        ).fetchone()
        return row is not None


def candidate_exists(name: str, sender: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT c.id FROM candidates c JOIN emails e ON c.email_id = e.id WHERE c.name=? AND e.sender=?",
            (name, sender),
        ).fetchone()
        return row is not None
