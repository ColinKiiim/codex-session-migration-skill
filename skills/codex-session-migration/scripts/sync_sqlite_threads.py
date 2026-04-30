#!/usr/bin/env python3
"""Synchronize thread metadata into state_5.sqlite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from codex_migration_lib import (
    MigrationError,
    create_backup_dir,
    ensure_codex_home,
    find_session_path_by_thread_id,
    invalid_session_warning,
    json_dump,
    load_session_index,
    load_sqlite_threads,
    parse_spec,
    plan_from_spec,
    read_json,
    summarize_session_file,
    upsert_threads_sqlite,
)


def gather_threads(home: Path, plan: dict | None, thread_ids: list[str], cwd: str | None) -> tuple[list[dict], list[dict[str, str]]]:
    if plan is not None:
        rows = plan["threads"]
        if thread_ids:
            wanted = set(thread_ids)
            rows = [row for row in rows if row["id"] in wanted]
        return rows, []
    if not thread_ids:
        raise MigrationError("Direct mode requires at least one --thread-id")
    sqlite_rows = load_sqlite_threads(home, thread_ids)
    index_rows = load_session_index(home)
    rows = []
    warnings: list[dict[str, str]] = []
    for thread_id in thread_ids:
        source_row = dict(sqlite_rows.get(thread_id) or {})
        index_entry = index_rows.get(thread_id)
        session_path = find_session_path_by_thread_id(home, thread_id, sqlite_row=source_row, include_archived=True)
        if not session_path:
            raise MigrationError(f"Thread is missing a session file: {thread_id}")
        summary: dict = {}
        try:
            summary = summarize_session_file(home, session_path)
        except json.JSONDecodeError as exc:
            if not source_row:
                raise MigrationError(f"Thread has no sqlite row and its session file is invalid: {thread_id}") from exc
            warnings.append(invalid_session_warning(session_path, exc))
        rows.append(
            {
                "id": thread_id,
                "title": source_row.get("title") or (index_entry or {}).get("thread_name") or summary.get("title"),
                "source_archived": bool(source_row.get("archived")) or bool(summary.get("archived")),
                "target_session_path": str(session_path),
                "target_cwd": cwd or source_row.get("cwd") or summary.get("cwd"),
                "source_sqlite_row": source_row,
                "source": source_row.get("source") or summary.get("source"),
                "cli_version": source_row.get("cli_version") or summary.get("cli_version"),
                "model_provider": source_row.get("model_provider") or summary.get("model_provider"),
                "sandbox_policy": source_row.get("sandbox_policy") or summary.get("sandbox_policy"),
                "approval_mode": source_row.get("approval_mode") or summary.get("approval_mode"),
                "session_meta_timestamp": summary.get("session_meta_timestamp"),
                "last_timestamp": summary.get("last_timestamp"),
                "source_index_entry": index_entry,
            }
        )
    return rows, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", help="Target CODEX_HOME directory")
    parser.add_argument("--plan", help="Migration plan JSON")
    parser.add_argument("--spec", help="Migration spec JSON")
    parser.add_argument("--thread-id", action="append", default=[])
    parser.add_argument("--cwd", help="Direct target cwd override")
    parser.add_argument("--execute", action="store_true", help="Required to perform writes")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Refusing to mutate without --execute")

    plan = None
    if args.plan:
        plan = read_json(Path(args.plan))
        home = ensure_codex_home(plan["target_home"])
    elif args.spec:
        spec = parse_spec(Path(args.spec))
        plan = plan_from_spec(spec)
        if plan.get("errors"):
            raise SystemExit(f"Plan contains errors: {plan['errors']}")
        home = ensure_codex_home(plan["target_home"])
    elif args.home:
        home = ensure_codex_home(args.home)
    else:
        raise SystemExit("Provide --plan, --spec, or --home")

    threads, warnings = gather_threads(home, plan, args.thread_id, args.cwd)
    backup_dir = create_backup_dir(home, "sqlite-sync")
    result = upsert_threads_sqlite(home, threads, backup_dir / "sqlite_before")
    print(json_dump({"status": "ok", "backup_dir": str(backup_dir), "rows": result["rows"], "warnings": warnings}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
