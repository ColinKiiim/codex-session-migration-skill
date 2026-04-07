#!/usr/bin/env python3
"""Promote one workspace's threads back into the recent-thread window."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from codex_migration_lib import (
    backup_file,
    create_backup_dir,
    ensure_codex_home,
    json_dump,
    load_session_index,
    load_sqlite_threads,
    parse_iso_to_epoch,
    scan_session_files,
    summarize_session_file,
    sqlite_path,
    upsert_threads_sqlite,
    write_json,
    write_session_index,
)


def epoch_to_iso(value: int) -> str:
    return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record_epoch(record: dict[str, Any]) -> int:
    index_row = record.get("index_entry") or {}
    sqlite_row = record.get("source_sqlite_row") or {}
    session_path = Path(record["session_path"]) if record.get("session_path") else None
    for candidate in [
        parse_iso_to_epoch(index_row.get("updated_at") or record.get("updated_at")),
        sqlite_row.get("updated_at"),
        parse_iso_to_epoch(record.get("last_timestamp")),
        parse_iso_to_epoch(record.get("session_meta_timestamp")),
        int(session_path.stat().st_mtime) if session_path and session_path.exists() else None,
    ]:
        if candidate is not None:
            return int(candidate)
    return int(dt.datetime.now(dt.timezone.utc).timestamp())


def build_safe_catalog(home: Path, *, include_archived: bool) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    current_index = load_session_index(home)
    sqlite_rows = load_sqlite_threads(home) if sqlite_path(home).exists() else {}
    records: dict[str, dict[str, Any]] = {
        sid: {
            "id": sid,
            "title": row.get("thread_name"),
            "updated_at": row.get("updated_at"),
            "cwd": None,
            "session_path": None,
            "archived": False,
            "index_entry": row,
            "source": None,
            "cli_version": None,
            "model_provider": None,
            "source_sqlite_row": None,
            "sandbox_policy": None,
            "approval_mode": None,
            "session_meta_timestamp": None,
            "last_timestamp": None,
        }
        for sid, row in current_index.items()
    }
    skipped_invalid: list[dict[str, str]] = []
    for session_path in scan_session_files(home, include_archived):
        try:
            summary = summarize_session_file(home, session_path)
        except json.JSONDecodeError as exc:
            skipped_invalid.append({"session_path": str(session_path), "error": str(exc)})
            continue
        sid = summary.get("id")
        if not sid:
            continue
        record = records.setdefault(
            sid,
            {
                "id": sid,
                "title": None,
                "updated_at": None,
                "cwd": None,
                "session_path": None,
                "archived": False,
                "index_entry": None,
                "source": None,
                "cli_version": None,
                "model_provider": None,
                "source_sqlite_row": None,
                "sandbox_policy": None,
                "approval_mode": None,
                "session_meta_timestamp": None,
                "last_timestamp": None,
            },
        )
        if record["session_path"] and not record["archived"] and summary["archived"]:
            continue
        record.update(summary)
    for sid, row in sqlite_rows.items():
        record = records.setdefault(
            sid,
            {
                "id": sid,
                "title": row.get("title"),
                "updated_at": None,
                "cwd": row.get("cwd"),
                "session_path": None,
                "archived": bool(row.get("archived")),
                "index_entry": None,
                "source": row.get("source"),
                "cli_version": row.get("cli_version"),
                "model_provider": row.get("model_provider"),
                "source_sqlite_row": None,
                "sandbox_policy": row.get("sandbox_policy"),
                "approval_mode": row.get("approval_mode"),
                "session_meta_timestamp": None,
                "last_timestamp": None,
            },
        )
        record["source_sqlite_row"] = row
        if not record.get("cwd"):
            record["cwd"] = row.get("cwd")
        if not record.get("title"):
            record["title"] = row.get("title")
    return records, skipped_invalid


def build_selected_records(
    home: Path,
    *,
    cwd: str,
    include_archived: bool,
    limit: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    catalog, skipped_invalid = build_safe_catalog(home, include_archived=include_archived)
    matches = [
        record
        for record in catalog.values()
        if record.get("cwd") == cwd and record.get("session_path") and Path(record["session_path"]).exists()
    ]
    matches.sort(key=lambda record: (-record_epoch(record), record["id"]))
    return (matches[:limit] if limit else matches), skipped_invalid


def build_sqlite_thread(record: dict[str, Any], *, updated_epoch: int, updated_iso: str) -> dict[str, Any]:
    source_row = dict(record.get("source_sqlite_row") or {})
    source_row["updated_at"] = updated_epoch
    source_row.setdefault("cwd", record.get("cwd"))
    source_row.setdefault("title", record.get("title") or record["id"])
    source_row.setdefault("archived", 1 if record.get("archived") else 0)
    return {
        "id": record["id"],
        "title": record.get("title"),
        "source_archived": bool(record.get("archived")),
        "target_session_path": str(record["session_path"]),
        "target_cwd": record.get("cwd"),
        "source_sqlite_row": source_row,
        "source": record.get("source"),
        "cli_version": record.get("cli_version"),
        "model_provider": record.get("model_provider"),
        "sandbox_policy": record.get("sandbox_policy"),
        "approval_mode": record.get("approval_mode"),
        "session_meta_timestamp": record.get("session_meta_timestamp"),
        "last_timestamp": updated_iso,
        "source_index_entry": {
            "id": record["id"],
            "thread_name": record.get("title") or record["id"],
            "updated_at": updated_iso,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--cwd", required=True, help="Exact workspace cwd whose threads should be promoted")
    parser.add_argument("--limit", type=int, help="Only promote the newest N matching threads")
    parser.add_argument("--include-archived", action="store_true", help="Include archived threads")
    parser.add_argument("--spacing-seconds", type=int, default=60, help="Gap between reassigned timestamps")
    parser.add_argument("--base-time", help="Optional ISO timestamp for the newest promoted thread")
    parser.add_argument("--report-path", help="Optional path to write the JSON report")
    parser.add_argument("--execute", action="store_true", help="Write the updated metadata")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    selected, skipped_invalid = build_selected_records(
        home,
        cwd=args.cwd,
        include_archived=args.include_archived,
        limit=args.limit,
    )
    if not selected:
        raise SystemExit(f"No matching threads found for cwd: {args.cwd}")

    base_epoch = parse_iso_to_epoch(args.base_time) if args.base_time else None
    if base_epoch is None:
        base_epoch = int(dt.datetime.now(dt.timezone.utc).timestamp())

    updates: list[dict[str, Any]] = []
    for idx, record in enumerate(selected):
        before_epoch = record_epoch(record)
        after_epoch = base_epoch - (idx * max(args.spacing_seconds, 1))
        updates.append(
            {
                "id": record["id"],
                "title": record.get("title"),
                "archived": bool(record.get("archived")),
                "cwd": record.get("cwd"),
                "before_updated_at": epoch_to_iso(before_epoch),
                "after_updated_at": epoch_to_iso(after_epoch),
                "record": record,
                "after_epoch": after_epoch,
            }
        )

    payload: dict[str, Any] = {
        "status": "planned",
        "home": str(home),
        "cwd": args.cwd,
        "limit": args.limit,
        "spacing_seconds": max(args.spacing_seconds, 1),
        "base_time": epoch_to_iso(base_epoch),
        "selected_count": len(updates),
        "backup_dir": None,
        "session_index_backup": None,
        "sqlite_backup_files": [],
        "skipped_invalid_session_files": skipped_invalid,
        "updates": [
            {
                "id": item["id"],
                "title": item["title"],
                "archived": item["archived"],
                "before_updated_at": item["before_updated_at"],
                "after_updated_at": item["after_updated_at"],
            }
            for item in updates
        ],
    }

    if args.execute:
        backup_dir = create_backup_dir(home, "bump-workspace-updated-at")
        index_path = home / "session_index.jsonl"
        if index_path.exists():
            payload["session_index_backup"] = str(backup_file(index_path, backup_dir).resolve())
        current_index = load_session_index(home)
        for item in updates:
            row = current_index.get(item["id"], {"id": item["id"], "thread_name": item["title"] or item["id"]})
            if not row.get("thread_name"):
                row["thread_name"] = item["title"] or item["id"]
            row["updated_at"] = item["after_updated_at"]
            current_index[item["id"]] = row
        write_session_index(home, current_index)

        if sqlite_path(home).exists():
            sqlite_threads = [
                build_sqlite_thread(item["record"], updated_epoch=item["after_epoch"], updated_iso=item["after_updated_at"])
                for item in updates
            ]
            sqlite_result = upsert_threads_sqlite(home, sqlite_threads, backup_dir / "sqlite_before")
            payload["sqlite_backup_files"] = sqlite_result.get("sqlite_backup_files", [])

        payload["status"] = "ok"
        payload["backup_dir"] = str(backup_dir)

    if args.report_path:
        write_json(Path(args.report_path).expanduser(), payload)
    print(json_dump(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
