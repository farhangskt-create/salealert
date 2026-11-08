"""Run the CENTRAL Sale Alert collector at most once per 36 hours.

Invoke hourly via a reliable SERVER scheduler (cron / Windows Task Scheduler).
This command is never invoked on customer Android devices.
The embedded SQLite lock prevents two simultaneous runs on the same host.
A failed scrape keeps the previously published feed unchanged.
"""
import argparse
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

INTERVAL_SECONDS = 36 * 60 * 60

def run_due(root: Path, now: int | None = None) -> int:
    now = int(time.time()) if now is None else now
    db_path = root / "storage" / "collector_schedule.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=1)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS collector_runs (id INTEGER PRIMARY KEY CHECK(id=1), last_attempt INTEGER NOT NULL, last_success INTEGER, last_exit INTEGER)")
        # Hold the write lock during the collector run; a second runner cannot duplicate it.
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT last_attempt FROM collector_runs WHERE id=1").fetchone()
        if row and now - row[0] < INTERVAL_SECONDS and now >= row[0]:
            print(f"SKIPPED: central collector checked {now-row[0]} seconds ago; interval is 36 hours.")
            conn.rollback()
            return 0
        print("RUNNING: central collector; all devices reuse its published output.", flush=True)
        result = subprocess.run([sys.executable, "main.py"], cwd=root, check=False)
        conn.execute("INSERT INTO collector_runs(id,last_attempt,last_success,last_exit) VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET last_attempt=excluded.last_attempt, last_success=CASE WHEN excluded.last_exit=0 THEN excluded.last_success ELSE collector_runs.last_success END, last_exit=excluded.last_exit", (now, now if result.returncode == 0 else None, result.returncode))
        conn.commit()
        return result.returncode
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run centrally scheduled Sale Alert collection only if 36 hours have passed")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        db = Path(__file__).resolve().parent / "storage" / "collector_schedule.sqlite"
        if db.exists():
            with sqlite3.connect(db) as c:
                try:
                    print(c.execute("SELECT last_attempt,last_success,last_exit FROM collector_runs WHERE id=1").fetchone())
                except sqlite3.OperationalError:
                    print("No previous runs")
        else:
            print("Collector has not run yet")
    else:
        raise SystemExit(run_due(Path(__file__).resolve().parent))
