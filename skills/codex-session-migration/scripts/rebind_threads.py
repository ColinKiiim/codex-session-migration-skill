#!/usr/bin/env python3
"""Rebind one or more existing threads to a new workspace cwd inside one CODEX_HOME."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from codex_migration_lib import (
    MigrationError,
    backup_file,
    create_backup_dir,
    ensure_codex_home,
    find_session_path_by_thread_id,
    invalid_session_warning,
    json_dump,
    load_session_index,
    load_sqlite_threads,
    parse_iso_to_epoch,
    rewrite_session_cwd,
    summarize_session_file,
    upsert_threads_sqlite,
    write_json,
    write_session_index,
)


UI_REFRESH_HINT = (
    "Check the Codex Desktop sidebar first. Recent Desktop builds may refresh visible threads "
    "without a full restart. If the threads do not appear, fully restart Codex Desktop to force a reload."
)


def epoch_to_iso(value: int) -> str:
    return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def plan_threads(
    home: Path,
    thread_ids: list[str],
    target_cwd: str,
    *,
    include_archived: bool,
    promote_to_sidebar: bool,
    base_epoch: int,
    spacing_seconds: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    sqlite_rows = load_sqlite_threads(home, thread_ids)
    index_rows = load_session_index(home)
    planned: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    for idx, thread_id in enumerate(thread_ids):
        sqlite_row = dict(sqlite_rows.get(thread_id) or {})
        if sqlite_row.get("archived") and not include_archived:
            raise MigrationError(f"Thread is archived; pass --include-archived to rebind it: {thread_id}")
        index_row = dict(index_rows.get(thread_id) or {})
        session_path = find_session_path_by_thread_id(home, thread_id, sqlite_row=sqlite_row, include_archived=True)
        if not session_path:
            raise MigrationError(f"Thread is missing a session file: {thread_id}")
        summary: dict[str, Any] = {}
        try:
            summary = summarize_session_file(home, session_path)
        except json.JSONDecodeError as exc:
            warnings.append(invalid_session_warning(session_path, exc))
            raise MigrationError(f"Cannot rebind invalid target session JSONL: {session_path}") from exc

        before_updated_epoch = int(sqlite_row.get("updated_at") or parse_iso_to_epoch(index_row.get("updated_at")) or 0)
        after_updated_epoch = base_epoch - (idx * max(spacing_seconds, 1)) if promote_to_sidebar else before_updated_epoch
        planned.append(
            {
                "id": thread_id,
                "target_cwd": target_cwd,
                "target_session_path": str(session_path),
                "before_cwd": sqlite_row.get("cwd") or summary.get("cwd"),
                "after_cwd": target_cwd,
                "sqlite_title": sqlite_row.get("title"),
                "session_index_thread_name": index_row.get("thread_name"),
                "thread_name_preserved": bool(index_row.get("thread_name")),
                "archived": bool(sqlite_row.get("archived") or summary.get("archived")),
                "before_updated_at": epoch_to_iso(before_updated_epoch) if before_updated_epoch else None,
                "after_updated_at": epoch_to_iso(after_updated_epoch) if after_updated_epoch else None,
                "source_sqlite_row": sqlite_row,
                "source_index_entry": index_row,
                "summary": summary,
                "after_updated_epoch": after_updated_epoch,
            }
        )
    return planned, warnings


def build_sqlite_payload(item: dict[str, Any], *, promote_to_sidebar: bool) -> dict[str, Any]:
    source_row = dict(item.get("source_sqlite_row") or {})
    source_row["cwd"] = item["target_cwd"]
    if promote_to_sidebar and item.get("after_updated_epoch"):
        source_row["updated_at"] = item["after_updated_epoch"]
    summary = item.get("summary") or {}
    return {
        "id": item["id"],
        "title": source_row.get("title") or item.get("session_index_thread_name") or item["id"],
        "source_archived": bool(item.get("archived")),
        "target_session_path": item["target_session_path"],
        "target_cwd": item["target_cwd"],
        "source_sqlite_row": source_row,
        "source": source_row.get("source") or summary.get("source"),
        "cli_version": source_row.get("cli_version") or summary.get("cli_version"),
        "model_provider": source_row.get("model_provider") or summary.get("model_provider"),
        "sandbox_policy": source_row.get("sandbox_policy") or summary.get("sandbox_policy"),
        "approval_mode": source_row.get("approval_mode") or summary.get("approval_mode"),
        "session_meta_timestamp": summary.get("session_meta_timestamp"),
        "last_timestamp": item.get("after_updated_at") or summary.get("last_timestamp"),
        "source_index_entry": {
            "id": item["id"],
            "thread_name": item.get("session_index_thread_name") or source_row.get("title") or item["id"],
            "updated_at": item.get("after_updated_at") or (item.get("source_index_entry") or {}).get("updated_at"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--thread-id", action="append", required=True)
    parser.add_argument("--target-cwd", required=True)
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument("--promote-to-sidebar", action="store_true", help="Bump updated_at metadata so Desktop is more likely to surface the threads")
    parser.add_argument("--spacing-seconds", type=int, default=60)
    parser.add_argument("--base-time", help="Optional ISO timestamp for the newest promoted thread")
    parser.add_argument("--report-path")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    base_epoch = parse_iso_to_epoch(args.base_time) if args.base_time else None
    if base_epoch is None:
        base_epoch = int(dt.datetime.now(dt.timezone.utc).timestamp())
    planned, warnings = plan_threads(
        home,
        args.thread_id,
        args.target_cwd,
        include_archived=args.include_archived,
        promote_to_sidebar=args.promote_to_sidebar,
        base_epoch=base_epoch,
        spacing_seconds=args.spacing_seconds,
    )
    report = {
        "status": "planned",
        "home": str(home),
        "target_cwd": args.target_cwd,
        "promote_to_sidebar": args.promote_to_sidebar,
        "ui_refresh_hint": UI_REFRESH_HINT,
        "backup_dir": None,
        "warnings": warnings,
        "threads": [
            {
                key: item.get(key)
                for key in [
                    "id",
                    "target_session_path",
                    "before_cwd",
                    "after_cwd",
                    "sqlite_title",
                    "session_index_thread_name",
                    "thread_name_preserved",
                    "archived",
                    "before_updated_at",
                    "after_updated_at",
                ]
            }
            for item in planned
        ],
    }

    if args.execute:
        backup_dir = create_backup_dir(home, "rebind-threads")
        report["backup_dir"] = str(backup_dir)
        index_path = home / "session_index.jsonl"
        if index_path.exists():
            report["session_index_backup"] = str(backup_file(index_path, backup_dir).resolve())

        current_index = load_session_index(home)
        rewritten = []
        for item in planned:
            session_path = Path(item["target_session_path"])
            backup_file(session_path, backup_dir / "session_backups", home)
            counts = rewrite_session_cwd(session_path, item["target_cwd"])
            rewritten.append({"id": item["id"], "path": str(session_path), "counts": counts})
            row = current_index.get(
                item["id"],
                {"id": item["id"], "thread_name": item.get("session_index_thread_name") or item.get("sqlite_title") or item["id"]},
            )
            if not row.get("thread_name"):
                row["thread_name"] = item.get("session_index_thread_name") or item.get("sqlite_title") or item["id"]
            if args.promote_to_sidebar and item.get("after_updated_at"):
                row["updated_at"] = item["after_updated_at"]
            current_index[item["id"]] = row
        write_session_index(home, current_index)

        sqlite_result = upsert_threads_sqlite(
            home,
            [build_sqlite_payload(item, promote_to_sidebar=args.promote_to_sidebar) for item in planned],
            backup_dir / "sqlite_before",
        )
        report["status"] = "ok"
        report["rewritten"] = rewritten
        report["sqlite_rows"] = sqlite_result.get("rows", [])
        report["sqlite_backup_files"] = sqlite_result.get("sqlite_backup_files", [])
        write_json(backup_dir / "rebind_report.json", report)

    if args.report_path:
        write_json(Path(args.report_path).expanduser(), report)
    print(json_dump(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
