#!/usr/bin/env python3
"""Inspect a Codex home and print a compact summary."""

from __future__ import annotations

import argparse

from codex_migration_lib import build_catalog, ensure_codex_home, json_dump, sqlite_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--include-archived", action="store_true", help="Count archived sessions too")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    catalog = build_catalog(home, include_archived=args.include_archived, include_sqlite=True)
    active = sum(1 for item in catalog.values() if item.get("session_path") and not item.get("archived"))
    archived = sum(1 for item in catalog.values() if item.get("archived"))
    summary = {
        "home": str(home),
        "has_session_index": (home / "session_index.jsonl").exists(),
        "has_sessions_dir": (home / "sessions").exists(),
        "has_archived_sessions_dir": (home / "archived_sessions").exists(),
        "has_sqlite": sqlite_path(home).exists(),
        "thread_count_total": len(catalog),
        "thread_count_active": active,
        "thread_count_archived": archived,
    }
    print(json_dump(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
