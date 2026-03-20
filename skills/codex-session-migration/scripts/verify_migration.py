#!/usr/bin/env python3
"""Verify that a migration plan matches target on-disk state."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_migration_lib import ensure_codex_home, json_dump, load_session_index, load_sqlite_threads, read_json, read_jsonl, sqlite_path


def collect_cwds(session_path: Path) -> list[str]:
    values = []
    for item in read_jsonl(session_path):
        payload = item.get("payload")
        if item.get("type") in {"session_meta", "turn_context"} and isinstance(payload, dict) and payload.get("cwd"):
            values.append(payload["cwd"])
    return sorted(set(values))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    args = parser.parse_args()

    plan = read_json(Path(args.plan))
    target_home = ensure_codex_home(plan["target_home"])
    target_index = load_session_index(target_home)
    sqlite_rows = load_sqlite_threads(target_home) if sqlite_path(target_home).exists() else {}
    checks = []
    failures = []
    for thread in plan["threads"]:
        target_session_path = Path(thread["target_session_path"]) if thread.get("target_session_path") else None
        file_exists = bool(target_session_path and target_session_path.exists())
        index_exists = thread["id"] in target_index
        session_cwds = collect_cwds(target_session_path) if file_exists else []
        sqlite_row = sqlite_rows.get(thread["id"])
        sqlite_cwd = sqlite_row.get("cwd") if sqlite_row else None
        check = {
            "id": thread["id"],
            "file_exists": file_exists,
            "index_exists": index_exists,
            "session_cwds": session_cwds,
            "sqlite_row_exists": sqlite_row is not None,
            "sqlite_cwd": sqlite_cwd,
            "expected_cwd": thread.get("target_cwd"),
        }
        checks.append(check)
        if not file_exists:
            failures.append(f"Missing target session file for {thread['id']}")
        if thread["index_action"] in {"add", "replace"} and not index_exists:
            failures.append(f"Missing session index entry for {thread['id']}")
        if thread.get("target_cwd") and session_cwds and session_cwds != [thread["target_cwd"]]:
            failures.append(f"Session cwd mismatch for {thread['id']}")
        if thread["sqlite_action"] == "upsert":
            if sqlite_row is None:
                failures.append(f"Missing sqlite row for {thread['id']}")
            elif thread.get("target_cwd") and sqlite_cwd != thread["target_cwd"]:
                failures.append(f"SQLite cwd mismatch for {thread['id']}")
    payload = {"status": "ok" if not failures else "failed", "failures": failures, "checks": checks}
    print(json_dump(payload))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
