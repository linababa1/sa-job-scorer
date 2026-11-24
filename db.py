import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("data") / "jobs.db"
STATUSES = ["Not applied", "Applied", "Interview", "Offer", "Rejected", "Skipped"]

def _conn():
    Path("data").mkdir(exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                job_title TEXT,
                company TEXT,
                jd_text TEXT NOT NULL,
                overall_score INTEGER,
                verdict TEXT,
                dimensions_json TEXT,
                strengths_json TEXT,
                gaps_json TEXT,
                requirements_met_json TEXT,
                requirements_missing_json TEXT,
                summary TEXT,
                seniority_note TEXT,
                years_required TEXT,
                entry_level_friendly INTEGER,
                status TEXT DEFAULT 'Not applied',
                notes TEXT
            )
        """)

def add_job(jd_text: str, result: dict) -> int:
    with _conn() as c:
        cur = c.execute("""
            INSERT INTO jobs (created_at, job_title, company, jd_text, overall_score, verdict,
                              dimensions_json, strengths_json, gaps_json,
                              requirements_met_json, requirements_missing_json,
                              summary, seniority_note, years_required, entry_level_friendly, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            result.get("job_title"), result.get("company"), jd_text,
            result.get("overall_score"), result.get("verdict"),
            json.dumps(result.get("dimensions", {})),
            json.dumps(result.get("top_strengths", [])),
            json.dumps(result.get("top_gaps", [])),
            json.dumps(result.get("requirements_met", [])),
            json.dumps(result.get("requirements_missing", [])),
            result.get("one_line_summary"), result.get("seniority_note"),
            result.get("years_required"),
            1 if result.get("entry_level_friendly") else 0,
            "Not applied",
        ))
        return cur.lastrowid

def list_jobs():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM jobs ORDER BY created_at DESC")]

def update_status(job_id: int, status: str, notes: str | None = None):
    with _conn() as c:
        if notes is not None:
            c.execute("UPDATE jobs SET status=?, notes=? WHERE id=?", (status, notes, job_id))
        else:
            c.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))

def delete_job(job_id: int):
    with _conn() as c:
        c.execute("DELETE FROM jobs WHERE id=?", (job_id,))

def wipe_all():
    with _conn() as c:
        c.execute("DELETE FROM jobs")