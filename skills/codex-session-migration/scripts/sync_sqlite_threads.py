#!/usr/bin/env python3
"""Synchronize thread metadata into state_5.sqlite."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_migration_lib import (
    MigrationError,
    build_catalog,
    create_backup_dir,
    ensure_codex_home,
    json_dump,
    parse_spec,
    plan_from_spec,
    read_json,
    upsert_threads_sqlite,
)


def gather_threads(home: Path, plan: dict | None, thread_ids: list[str], cwd: str | None) -> list[dict]:
    if plan is not None:
        rows = plan["threads"]
        if thread_ids:
            wanted = set(thread_ids)
            rows = [row for row in rows if row["id"] in wanted]
        return rows
    if not thread_ids:
        raise MigrationError("Direct mode requires at least one --thread-id")
    catalog = build_catalog(home, include_archived=True, include_sqlite=True)
    rows = []
    for thread_id in thread_ids:
        record = catalog.get(thread_id)
        if not record or not record.get("session_path"):
            raise MigrationError(f"Thread is missing a session file: {thread_id}")
        rows.append(
            {
                "id": thread_id,
                "title": record.get("title"),
                "source_archived": bool(record.get("archived")),
                "target_session_path": record["session_path"],
                "target_cwd": cwd or record.get("cwd"),
                "source_sqlite_row": record.get("source_sqlite_row"),
                "source": record.get("source"),
                "cli_version": record.get("cli_version"),
                "model_provider": record.get("model_provider"),
                "sandbox_policy": record.get("sandbox_policy"),
                "approval_mode": record.get("approval_mode"),
                "session_meta_timestamp": record.get("session_meta_timestamp"),
                "last_timestamp": record.get("last_timestamp"),
                "source_index_entry": record.get("index_entry"),
            }
        )
    return rows


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

    threads = gather_threads(home, plan, args.thread_id, args.cwd)
    backup_dir = create_backup_dir(home, "sqlite-sync")
    result = upsert_threads_sqlite(home, threads, backup_dir / "sqlite_before")
    print(json_dump({"status": "ok", "backup_dir": str(backup_dir), "rows": result["rows"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
