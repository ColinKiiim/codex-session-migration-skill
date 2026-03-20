#!/usr/bin/env python3
"""List threads from a Codex home."""

from __future__ import annotations

import argparse

from codex_migration_lib import build_catalog, ensure_codex_home, json_dump


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--include-archived", action="store_true", help="Include archived sessions")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    catalog = build_catalog(home, include_archived=args.include_archived, include_sqlite=True)
    rows = sorted(
        [
            {
                "id": item["id"],
                "title": item.get("title"),
                "updated_at": item.get("updated_at"),
                "cwd": item.get("cwd"),
                "archived": bool(item.get("archived")),
                "session_path": item.get("session_path"),
            }
            for item in catalog.values()
            if args.include_archived or not item.get("archived")
        ],
        key=lambda row: (row.get("updated_at") or "", row["id"]),
    )
    if args.format == "json":
        print(json_dump(rows))
        return 0

    for row in rows:
        status = "archived" if row["archived"] else "active"
        print(f"{row['id']}\t{status}\t{row.get('title') or ''}\t{row.get('cwd') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
