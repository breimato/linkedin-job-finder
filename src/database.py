import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from .scraper import JobPosting

DB_PATH = Path("data/jobs.db")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            job_id      TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            company     TEXT NOT NULL,
            location    TEXT,
            job_url     TEXT NOT NULL,
            site        TEXT NOT NULL,
            date_posted TEXT,
            date_seen   TEXT NOT NULL,
            notified    INTEGER DEFAULT 0,
            easy_apply  INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS apply_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id        TEXT NOT NULL REFERENCES seen_jobs(job_id),
            status        TEXT NOT NULL,
            requested_at  TEXT NOT NULL,
            actioned_at   TEXT,
            applied_at    TEXT,
            error_message TEXT
        );
    """)
    conn.commit()
    conn.close()


def filter_new(jobs: list[JobPosting]) -> list[JobPosting]:
    if not jobs:
        return []
    conn = _connect()
    ids = [j["job_id"] for j in jobs]
    placeholders = ",".join("?" * len(ids))
    seen = {row[0] for row in conn.execute(
        f"SELECT job_id FROM seen_jobs WHERE job_id IN ({placeholders})", ids
    )}
    conn.close()
    return [j for j in jobs if j["job_id"] not in seen]


def mark_seen(jobs: list[JobPosting]) -> None:
    if not jobs:
        return
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    conn.executemany(
        "INSERT OR IGNORE INTO seen_jobs "
        "(job_id, title, company, location, job_url, site, date_posted, date_seen, easy_apply) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (j["job_id"], j["title"], j["company"], j["location"],
             j["job_url"], j["site"], j["date_posted"], now, int(j["easy_apply"]))
            for j in jobs
        ],
    )
    conn.commit()
    conn.close()


def mark_notified(job_ids: list[str]) -> None:
    if not job_ids:
        return
    conn = _connect()
    placeholders = ",".join("?" * len(job_ids))
    conn.execute(f"UPDATE seen_jobs SET notified=1 WHERE job_id IN ({placeholders})", job_ids)
    conn.commit()
    conn.close()


def queue_for_review(job_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO apply_log (job_id, status, requested_at) VALUES (?,?,?)",
        (job_id, "pending_review", now),
    )
    conn.commit()
    conn.close()


def update_apply_status(job_id: str, status: str, error: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    if status == "applied":
        conn.execute(
            "UPDATE apply_log SET status=?, applied_at=? "
            "WHERE job_id=? AND status NOT IN ('applied','rejected')",
            (status, now, job_id),
        )
    else:
        conn.execute(
            "UPDATE apply_log SET status=?, actioned_at=?, error_message=? "
            "WHERE job_id=? AND status NOT IN ('applied','rejected')",
            (status, now, error, job_id),
        )
    conn.commit()
    conn.close()


def get_pending_reviews() -> list[dict]:
    conn = _connect()
    rows = conn.execute("""
        SELECT al.job_id, sj.title, sj.company, sj.location, sj.job_url, al.requested_at
        FROM apply_log al
        JOIN seen_jobs sj ON al.job_id = sj.job_id
        WHERE al.status = 'pending_review'
        ORDER BY al.requested_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_applied_today() -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    conn = _connect()
    count = conn.execute(
        "SELECT COUNT(*) FROM apply_log WHERE status='applied' AND date(applied_at)=?",
        (today,),
    ).fetchone()[0]
    conn.close()
    return count


def get_job_by_id(job_id: str) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM seen_jobs WHERE job_id=?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats() -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    conn = _connect()
    total = conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
    today_seen = conn.execute(
        "SELECT COUNT(*) FROM seen_jobs WHERE date(date_seen)=?", (today,)
    ).fetchone()[0]
    applied = conn.execute(
        "SELECT COUNT(*) FROM apply_log WHERE status='applied'"
    ).fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM apply_log WHERE status='pending_review'"
    ).fetchone()[0]
    conn.close()
    return {
        "total_seen": total,
        "seen_today": today_seen,
        "applied_total": applied,
        "pending_review": pending,
    }
