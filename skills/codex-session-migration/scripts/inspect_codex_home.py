#!/usr/bin/env python3
"""Inspect a Codex home and print a compact summary."""

from __future__ import annotations

import argparse

from codex_migration_lib import build_catalog_safe, ensure_codex_home, json_dump, load_session_index, load_sqlite_threads, scan_session_files, sqlite_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--include-archived", action="store_true", help="Count archived sessions too")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    session_index = load_session_index(home)
    sqlite_rows = load_sqlite_threads(home)
    session_files = scan_session_files(home, include_archived=args.include_archived)
    catalog, skipped_invalid = build_catalog_safe(home, include_archived=args.include_archived, include_sqlite=True)
    active = sum(1 for item in catalog.values() if item.get("session_path") and not item.get("archived"))
    archived = sum(1 for item in catalog.values() if item.get("archived"))
    summary = {
        "status": "warning" if skipped_invalid else "ok",
        "home": str(home),
        "has_session_index": (home / "session_index.jsonl").exists(),
        "has_sessions_dir": (home / "sessions").exists(),
        "has_archived_sessions_dir": (home / "archived_sessions").exists(),
        "has_sqlite": sqlite_path(home).exists(),
        "session_index_rows": len(session_index),
        "sqlite_threads": len(sqlite_rows),
        "session_files": len(session_files),
        "valid_session_file_threads": sum(1 for item in catalog.values() if item.get("session_path")),
        "invalid_session_files": len(skipped_invalid),
        "skipped_invalid_session_files": skipped_invalid,
        "thread_count_total": len(catalog),
        "thread_count_active": active,
        "thread_count_archived": archived,
    }
    print(json_dump(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
