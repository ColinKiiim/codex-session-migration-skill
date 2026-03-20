#!/usr/bin/env python3
"""Archive a single thread inside one CODEX_HOME."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sqlite3
from pathlib import Path

from codex_migration_lib import (
    MigrationError,
    build_catalog,
    copy_sqlite_bundle,
    create_backup_dir,
    ensure_codex_home,
    json_dump,
    sqlite_path,
)


def now_epoch() -> int:
    return int(dt.datetime.now(dt.timezone.utc).timestamp())


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def archive_thread(home: Path, thread_id: str, execute: bool) -> dict[str, object]:
    catalog = build_catalog(home, include_archived=True, include_sqlite=True)
    record = catalog.get(thread_id)
    if not record:
        raise MigrationError(f"Thread not found: {thread_id}")
    if record.get("archived"):
        raise MigrationError(f"Thread is already archived: {thread_id}")
    if not record.get("session_path"):
        raise MigrationError(f"Thread has no session file: {thread_id}")

    source_session = Path(record["session_path"])
    archived_dir = home / "archived_sessions"
    archived_session = archived_dir / source_session.name
    if archived_session.exists():
        raise MigrationError(f"Archived session target already exists: {archived_session}")

    backup_dir = home / "migration_backups" / f"{now_stamp()}-archive-thread-{thread_id}"
    index_path = home / "session_index.jsonl"
    sqlite_backups: list[dict[str, str]] = []
    db_path = sqlite_path(home)

    plan = {
        "thread_id": thread_id,
        "title": record.get("title"),
        "source_session_path": str(source_session),
        "archived_session_path": str(archived_session),
        "backup_dir": str(backup_dir),
        "sqlite_present": db_path.exists(),
        "index_present": index_path.exists(),
        "sqlite_backups": sqlite_backups,
        "execute": execute,
    }
    if not execute:
        return {"status": "dry-run", **plan}

    backup_dir = create_backup_dir(home, f"archive-thread-{thread_id}")
    preflight = backup_dir / "preflight"
    preflight.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_session, preflight / source_session.name)

    if index_path.exists():
        shutil.copy2(index_path, preflight / "session_index.before.jsonl")

    if db_path.exists():
        sqlite_backups = copy_sqlite_bundle(db_path, preflight / "sqlite")

    archived_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_session), str(archived_session))

    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE threads
            SET archived = 1,
                archived_at = ?,
                rollout_path = ?
            WHERE id = ?
            """,
            (now_epoch(), str(archived_session), thread_id),
        )
        conn.commit()
        conn.close()

    plan["sqlite_backups"] = sqlite_backups
    manifest = {"status": "ok", **plan}
    (backup_dir / "archive_manifest.json").write_text(json_dump(manifest) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="CODEX_HOME path")
    parser.add_argument("--thread-id", required=True, help="Thread id to archive")
    parser.add_argument("--execute", action="store_true", help="Perform the archive instead of dry-run")
    args = parser.parse_args()

    result = archive_thread(ensure_codex_home(args.home), args.thread_id, args.execute)
    print(json_dump(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
