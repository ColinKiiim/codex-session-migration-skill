#!/usr/bin/env python3
"""Execute a migration plan."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from codex_migration_lib import (
    MigrationError,
    backup_file,
    copy_sqlite_bundle,
    create_backup_dir,
    ensure_codex_home,
    json_dump,
    read_json,
    rewrite_session_cwd,
    sqlite_path,
    upsert_threads_sqlite,
    write_json,
    write_session_index,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, help="Path to a migration plan JSON file")
    parser.add_argument("--execute", action="store_true", help="Required to perform writes")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Refusing to mutate without --execute")

    plan = read_json(Path(args.plan))
    if plan.get("errors"):
        raise SystemExit(f"Plan contains errors: {plan['errors']}")

    target_home = ensure_codex_home(plan["target_home"])
    backup_dir = create_backup_dir(target_home, plan.get("backup_label") or plan.get("mode"))
    manifest = {
        "schema_version": 1,
        "plan_path": str(Path(args.plan).resolve()),
        "target_home": str(target_home),
        "backup_dir": str(backup_dir),
        "created_session_files": [],
        "overwritten_session_backups": [],
        "rewritten_sessions": [],
        "session_index_backup": None,
        "sqlite_backup_files": [],
    }

    session_index_path = target_home / "session_index.jsonl"
    if session_index_path.exists():
        manifest["session_index_backup"] = str(backup_file(session_index_path, backup_dir).resolve())
    if sqlite_path(target_home).exists() and any(item["sqlite_action"] == "upsert" for item in plan["threads"]):
        sqlite_backup_dir = backup_dir / "sqlite_before"
        sqlite_backup_dir.mkdir(parents=True, exist_ok=True)
        manifest["sqlite_backup_files"] = copy_sqlite_bundle(sqlite_path(target_home), sqlite_backup_dir)

    target_index = {}
    if session_index_path.exists():
        from codex_migration_lib import load_session_index  # local import to keep startup simple

        target_index = load_session_index(target_home)

    sqlite_threads = []
    for thread in plan["threads"]:
        target_session_path = Path(thread["target_session_path"]) if thread.get("target_session_path") else None
        if not target_session_path:
            continue
        copy_action = thread["copy_action"]
        if copy_action in {"copy", "replace"}:
            source_session_path = Path(thread["source_session_path"])
            if not source_session_path.exists():
                raise MigrationError(f"Source session file does not exist: {source_session_path}")
            target_session_path.parent.mkdir(parents=True, exist_ok=True)
            if copy_action == "replace" and target_session_path.exists():
                backup_path = backup_file(target_session_path, backup_dir / "overwritten_sessions", target_home)
                manifest["overwritten_session_backups"].append(
                    {"original": str(target_session_path), "backup": str(backup_path)}
                )
            if copy_action == "copy" and not target_session_path.exists():
                manifest["created_session_files"].append(str(target_session_path))
            shutil.copy2(source_session_path, target_session_path)
        if thread.get("target_cwd") and target_session_path.exists():
            counts = rewrite_session_cwd(target_session_path, thread["target_cwd"])
            manifest["rewritten_sessions"].append(
                {"path": str(target_session_path), "counts": counts, "cwd": thread["target_cwd"]}
            )
        if thread["index_action"] in {"add", "replace"} and thread.get("source_index_entry"):
            target_index[thread["id"]] = thread["source_index_entry"]
        if thread["sqlite_action"] == "upsert" and target_session_path.exists():
            sqlite_threads.append(thread)

    write_session_index(target_home, target_index)
    if sqlite_threads:
        result = upsert_threads_sqlite(target_home, sqlite_threads)
        manifest["sqlite_rows"] = result["rows"]

    manifest_path = backup_dir / "migration_manifest.json"
    write_json(manifest_path, manifest)
    print(json_dump({"status": "ok", "manifest": str(manifest_path), "backup_dir": str(backup_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
