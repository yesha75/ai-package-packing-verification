"""Lightweight SQLite inspection history; local-development use only."""
import json
import sqlite3
from backend import config


def connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(config.DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS inspections (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
            checklist_id TEXT NOT NULL, filename TEXT NOT NULL,
            status TEXT NOT NULL, annotated_path TEXT NOT NULL,
            result_json TEXT NOT NULL
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_status ON inspections(status)")


def save_inspection(record: dict, annotated_path: str) -> None:
    with connect() as db:
        db.execute("""INSERT INTO inspections
            (id,created_at,checklist_id,filename,status,annotated_path,result_json)
            VALUES (?,?,?,?,?,?,?)""", (
            record["id"], record["created_at"], record["checklist_id"],
            record["filename"], record["status"], annotated_path,
            json.dumps(record),
        ))


def list_inspections(limit: int = 50) -> list[dict]:
    with connect() as db:
        rows = db.execute("SELECT result_json FROM inspections ORDER BY created_at DESC LIMIT ?",
                          (limit,)).fetchall()
    return [json.loads(r["result_json"]) for r in rows]


def get_inspection(inspection_id: str) -> tuple[dict, str] | None:
    with connect() as db:
        row = db.execute("SELECT result_json,annotated_path FROM inspections WHERE id=?",
                         (inspection_id,)).fetchone()
    return (json.loads(row["result_json"]), row["annotated_path"]) if row else None


def get_summary() -> dict:
    with connect() as db:
        rows = db.execute("SELECT status,COUNT(*) AS total FROM inspections GROUP BY status").fetchall()
    counts = {row["status"]: row["total"] for row in rows}
    return {"inspected": sum(counts.values()), "passed": counts.get("Pass", 0),
            "needs_review": counts.get("Needs Review", 0)}
