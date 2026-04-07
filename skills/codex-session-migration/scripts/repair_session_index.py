#!/usr/bin/env python3
"""Repair session_index.jsonl from on-disk sessions while preserving sidebar names."""

from __future__ import annotations

import argparse
import collections
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
    now_utc_iso,
    parse_iso_to_epoch,
    read_jsonl,
    scan_session_files,
    summarize_session_file,
    sqlite_path,
    write_json,
    write_session_index,
)


def iso_from_epoch(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    try:
        stamp = int(value)
    except (TypeError, ValueError):
        return None
    return dt.datetime.fromtimestamp(stamp, tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_from_mtime(path: Path | None) -> str | None:
    if not path or not path.exists():
        return None
    return iso_from_epoch(int(path.stat().st_mtime))


def load_raw_index_rows(path: Path) -> list[dict[str, Any]]:
    return read_jsonl(path) if path.exists() else []


def last_row_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        sid = row.get("id")
        if sid:
            latest[sid] = row
    return latest


def duplicate_ids(rows: list[dict[str, Any]]) -> list[str]:
    counts = collections.Counter(row.get("id") for row in rows if row.get("id"))
    return sorted(sid for sid, count in counts.items() if count > 1)


def choose_thread_name(
    *,
    thread_id: str,
    record: dict[str, Any],
    current_row: dict[str, Any] | None,
    name_source_row: dict[str, Any] | None,
    sqlite_row: dict[str, Any] | None,
) -> str:
    for candidate in [
        (name_source_row or {}).get("thread_name"),
        (current_row or {}).get("thread_name"),
        record.get("title"),
        (sqlite_row or {}).get("title"),
        (sqlite_row or {}).get("first_user_message"),
        thread_id,
    ]:
        if candidate:
            return str(candidate)
    return thread_id


def choose_updated_at(
    *,
    record: dict[str, Any],
    current_row: dict[str, Any] | None,
    sqlite_row: dict[str, Any] | None,
) -> str:
    session_path = Path(record["session_path"]) if record.get("session_path") else None
    for candidate in [
        (current_row or {}).get("updated_at"),
        iso_from_epoch((sqlite_row or {}).get("updated_at")),
        record.get("last_timestamp"),
        record.get("session_meta_timestamp"),
        iso_from_mtime(session_path),
        now_utc_iso(),
    ]:
        if candidate:
            return str(candidate)
    return now_utc_iso()


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


def build_repaired_rows(
    home: Path,
    *,
    include_archived: bool,
    name_source_rows: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    index_path = home / "session_index.jsonl"
    raw_index_rows = load_raw_index_rows(index_path)
    current_index = load_session_index(home)
    sqlite_rows = load_sqlite_threads(home) if sqlite_path(home).exists() else {}
    catalog, skipped_invalid = build_safe_catalog(home, include_archived=include_archived)

    actual_records = {
        sid: record
        for sid, record in catalog.items()
        if record.get("session_path") and Path(record["session_path"]).exists()
    }
    rebuilt_rows: dict[str, dict[str, Any]] = {}
    missing_from_index: list[str] = []
    name_restored_from_source: list[str] = []

    for sid, record in sorted(actual_records.items()):
        current_row = current_index.get(sid)
        name_source_row = name_source_rows.get(sid)
        sqlite_row = sqlite_rows.get(sid) or record.get("source_sqlite_row")
        thread_name = choose_thread_name(
            thread_id=sid,
            record=record,
            current_row=current_row,
            name_source_row=name_source_row,
            sqlite_row=sqlite_row,
        )
        updated_at = choose_updated_at(record=record, current_row=current_row, sqlite_row=sqlite_row)
        rebuilt_rows[sid] = {
            "id": sid,
            "thread_name": thread_name,
            "updated_at": updated_at,
        }
        if current_row is None:
            missing_from_index.append(sid)
        if name_source_row and thread_name == name_source_row.get("thread_name") and thread_name != (current_row or {}).get(
            "thread_name"
        ):
            name_restored_from_source.append(sid)

    current_index_ids = set(current_index)
    rebuilt_ids = set(rebuilt_rows)
    stats = {
        "session_file_threads": len(actual_records),
        "sqlite_threads": len(sqlite_rows),
        "index_line_count_before": len(raw_index_rows),
        "index_unique_count_before": len(current_index),
        "index_duplicate_ids_before": duplicate_ids(raw_index_rows),
        "missing_from_index": missing_from_index,
        "orphan_index_ids": sorted(current_index_ids - rebuilt_ids),
        "rebuilt_index_count": len(rebuilt_rows),
        "name_restored_from_source": name_restored_from_source,
        "skipped_invalid_session_files": skipped_invalid,
    }
    return rebuilt_rows, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument(
        "--name-source-index",
        help="Optional older session_index.jsonl used only as a source of thread_name values",
    )
    parser.add_argument("--include-archived", action="store_true", help="Include archived session files")
    parser.add_argument("--report-path", help="Optional path to write the JSON report")
    parser.add_argument("--execute", action="store_true", help="Write the repaired session_index.jsonl")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    name_source_rows: dict[str, dict[str, Any]] = {}
    if args.name_source_index:
        source_path = Path(args.name_source_index).expanduser()
        name_source_rows = last_row_by_id(load_raw_index_rows(source_path))

    rebuilt_rows, stats = build_repaired_rows(
        home,
        include_archived=args.include_archived,
        name_source_rows=name_source_rows,
    )
    payload: dict[str, Any] = {
        "status": "planned",
        "home": str(home),
        "include_archived": bool(args.include_archived),
        "name_source_index": str(Path(args.name_source_index).expanduser()) if args.name_source_index else None,
        "stats": stats,
        "backup_dir": None,
        "session_index_backup": None,
    }

    if args.execute:
        backup_dir = create_backup_dir(home, "repair-session-index")
        index_path = home / "session_index.jsonl"
        if index_path.exists():
            payload["session_index_backup"] = str(backup_file(index_path, backup_dir).resolve())
        write_session_index(home, rebuilt_rows)
        payload["status"] = "ok"
        payload["backup_dir"] = str(backup_dir)

    if args.report_path:
        write_json(Path(args.report_path).expanduser(), payload)
    print(json_dump(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
