#!/usr/bin/env python3
"""Verify thread cwd bindings across sqlite, session_index, and session JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from codex_migration_lib import (
    ensure_codex_home,
    find_session_path_by_thread_id,
    invalid_session_warning,
    json_dump,
    load_session_index,
    load_sqlite_threads,
    read_jsonl,
)


def count_session_cwd(session_path: Path, target_cwd: str, old_cwd: str | None) -> dict:
    counts = {
        "session_meta_target": 0,
        "turn_context_target": 0,
        "old_cwd_count": 0,
        "other_cwd_count": 0,
    }
    items = read_jsonl(session_path)
    for item in items:
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        cwd = payload.get("cwd")
        if cwd is None:
            continue
        if cwd == old_cwd and old_cwd != target_cwd:
            counts["old_cwd_count"] += 1
        elif cwd != target_cwd:
            counts["other_cwd_count"] += 1
        if item.get("type") == "session_meta" and cwd == target_cwd:
            counts["session_meta_target"] += 1
        elif item.get("type") == "turn_context" and cwd == target_cwd:
            counts["turn_context_target"] += 1
    return counts


def verify_thread(home: Path, thread_id: str, target_cwd: str) -> dict:
    sqlite_row = load_sqlite_threads(home, [thread_id]).get(thread_id)
    index_row = load_session_index(home).get(thread_id)
    session_path = find_session_path_by_thread_id(home, thread_id, sqlite_row=sqlite_row, include_archived=True)
    old_cwd = sqlite_row.get("cwd") if sqlite_row else None
    session = {
        "exists": bool(session_path and session_path.exists()),
        "path": str(session_path) if session_path else None,
        "invalid_json": False,
        "warning": None,
        "counts": None,
    }
    if session_path and session_path.exists():
        try:
            session["counts"] = count_session_cwd(session_path, target_cwd, old_cwd)
        except json.JSONDecodeError as exc:
            session["invalid_json"] = True
            session["warning"] = invalid_session_warning(session_path, exc)

    sqlite_ok = bool(sqlite_row and sqlite_row.get("cwd") == target_cwd)
    counts = session.get("counts") or {}
    session_ok = bool(
        session["exists"]
        and not session["invalid_json"]
        and counts.get("session_meta_target", 0) >= 1
        and counts.get("old_cwd_count", 0) == 0
        and counts.get("other_cwd_count", 0) == 0
    )
    return {
        "id": thread_id,
        "ok": bool(sqlite_ok and index_row and session_ok),
        "sqlite": {
            "exists": bool(sqlite_row),
            "cwd": sqlite_row.get("cwd") if sqlite_row else None,
            "archived": bool(sqlite_row.get("archived")) if sqlite_row else None,
            "updated_at": sqlite_row.get("updated_at") if sqlite_row else None,
        },
        "session_index": {
            "exists": bool(index_row),
            "thread_name": index_row.get("thread_name") if index_row else None,
            "updated_at": index_row.get("updated_at") if index_row else None,
        },
        "session_file": session,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--cwd", required=True, help="Expected cwd")
    parser.add_argument("--thread-id", action="append", required=True)
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    results = [verify_thread(home, thread_id, args.cwd) for thread_id in args.thread_id]
    payload = {"status": "ok" if all(item["ok"] for item in results) else "warning", "cwd": args.cwd, "threads": results}
    if args.format == "json":
        print(json_dump(payload))
        return 0
    for item in results:
        print(f"{'ok' if item['ok'] else 'warning'}\t{item['id']}\t{item['session_index'].get('thread_name') or ''}")
    return 0 if all(item["ok"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
