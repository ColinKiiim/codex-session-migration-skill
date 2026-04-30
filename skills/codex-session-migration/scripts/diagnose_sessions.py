#!/usr/bin/env python3
"""Diagnose malformed Codex session JSONL files without modifying them."""

from __future__ import annotations

import argparse
import json

from codex_migration_lib import (
    ensure_codex_home,
    extract_thread_id,
    invalid_session_warning,
    json_dump,
    load_session_index,
    load_sqlite_threads,
    read_jsonl,
    scan_session_files,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    index_rows = load_session_index(home)
    sqlite_rows = load_sqlite_threads(home)
    invalid = []
    valid = 0
    files = scan_session_files(home, include_archived=args.include_archived)
    for path in files:
        thread_id = extract_thread_id(path)
        try:
            read_jsonl(path)
            valid += 1
        except json.JSONDecodeError as exc:
            sqlite_row = sqlite_rows.get(thread_id or "") or {}
            index_row = index_rows.get(thread_id or "") or {}
            item = invalid_session_warning(path, exc)
            item.update(
                {
                    "indexed_title": index_row.get("thread_name"),
                    "sqlite_title": sqlite_row.get("title"),
                    "sqlite_cwd": sqlite_row.get("cwd"),
                    "sqlite_archived": bool(sqlite_row.get("archived")) if sqlite_row else None,
                }
            )
            invalid.append(item)

    payload = {
        "status": "warning" if invalid else "ok",
        "home": str(home),
        "total_session_files": len(files),
        "valid_session_files": valid,
        "invalid_session_files": len(invalid),
        "invalid": invalid,
        "repair_note": "This command only diagnoses malformed JSONL files. Do not rewrite originals without a separate backup and recovery plan.",
    }
    if args.format == "json":
        print(json_dump(payload))
        return 0
    print(f"total\t{payload['total_session_files']}")
    print(f"valid\t{payload['valid_session_files']}")
    print(f"invalid\t{payload['invalid_session_files']}")
    for item in invalid:
        print(f"{item.get('thread_id')}\t{item.get('session_path')}\t{item.get('error')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
