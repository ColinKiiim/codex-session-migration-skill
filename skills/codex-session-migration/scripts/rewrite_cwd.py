#!/usr/bin/env python3
"""Rewrite session cwd values in target JSONL files."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_migration_lib import (
    MigrationError,
    backup_file,
    build_catalog,
    create_backup_dir,
    ensure_codex_home,
    json_dump,
    parse_spec,
    plan_from_spec,
    read_json,
    rewrite_session_cwd,
)


def selected_threads_from_inputs(home: Path, plan: dict | None, thread_ids: list[str], cwd: str | None) -> list[dict]:
    if plan is not None:
        items = plan["threads"]
        if thread_ids:
            wanted = set(thread_ids)
            items = [item for item in items if item["id"] in wanted]
        return items
    if not thread_ids or cwd is None:
        raise MigrationError("Direct mode requires --thread-id and --cwd")
    catalog = build_catalog(home, include_archived=True, include_sqlite=False)
    rows = []
    for thread_id in thread_ids:
        record = catalog.get(thread_id)
        if not record or not record.get("session_path"):
            raise MigrationError(f"Thread is missing a target session file: {thread_id}")
        rows.append(
            {
                "id": thread_id,
                "target_session_path": record["session_path"],
                "target_cwd": cwd,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", help="Target CODEX_HOME directory")
    parser.add_argument("--plan", help="Migration plan JSON")
    parser.add_argument("--spec", help="Migration spec JSON")
    parser.add_argument("--thread-id", action="append", default=[])
    parser.add_argument("--cwd", help="Direct rewrite target cwd")
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

    threads = selected_threads_from_inputs(home, plan, args.thread_id, args.cwd)
    backup_dir = create_backup_dir(home, "rewrite-cwd")
    rewritten = []
    for thread in threads:
        session_path = Path(thread["target_session_path"])
        if not session_path.exists():
            raise MigrationError(f"Target session file does not exist: {session_path}")
        backup_file(session_path, backup_dir / "session_backups", home)
        counts = rewrite_session_cwd(session_path, thread["target_cwd"])
        rewritten.append({"id": thread["id"], "path": str(session_path), "counts": counts})
    print(json_dump({"status": "ok", "backup_dir": str(backup_dir), "rewritten": rewritten}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
