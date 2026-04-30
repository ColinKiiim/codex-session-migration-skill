#!/usr/bin/env python3
"""Search thread metadata without parsing session JSONL bodies."""

from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path
from typing import Any

from codex_migration_lib import (
    ensure_codex_home,
    find_session_path_by_thread_id,
    json_dump,
    load_session_index,
    load_sqlite_threads,
)


def normalize(value: str | None) -> str:
    chars: list[str] = []
    for ch in (value or "").casefold():
        category = unicodedata.category(ch)
        if category.startswith("Z") or category.startswith("P"):
            continue
        chars.append(ch)
    return "".join(chars)


def add_match(reasons: list[str], score: int, field: str, value: str | None, query: str) -> int:
    if not value:
        return score
    q = query.casefold()
    q_norm = normalize(query)
    value_folded = value.casefold()
    value_norm = normalize(value)
    if value_folded == q:
        reasons.append(f"{field} equals query")
        return score + 100
    if q in value_folded:
        reasons.append(f"{field} contains query")
        return score + 60
    if q_norm and q_norm in value_norm:
        reasons.append(f"{field} contains normalized query")
        return score + 50
    return score


def build_rows(home: Path, query: str, include_archived: bool) -> list[dict[str, Any]]:
    sqlite_rows = load_sqlite_threads(home)
    index_rows = load_session_index(home)
    ids = set(sqlite_rows) | set(index_rows)
    rows: list[dict[str, Any]] = []
    for thread_id in sorted(ids):
        sqlite_row = sqlite_rows.get(thread_id) or {}
        index_row = index_rows.get(thread_id) or {}
        archived = bool(sqlite_row.get("archived"))
        if archived and not include_archived:
            continue

        reasons: list[str] = []
        score = 0
        score = add_match(reasons, score, "id", thread_id, query)
        score = add_match(reasons, score, "sqlite.title", sqlite_row.get("title"), query)
        score = add_match(reasons, score, "sqlite.cwd", sqlite_row.get("cwd"), query)
        score = add_match(reasons, score, "sqlite.first_user_message", sqlite_row.get("first_user_message"), query)
        score = add_match(reasons, score, "session_index.thread_name", index_row.get("thread_name"), query)
        if score <= 0:
            continue

        session_path = find_session_path_by_thread_id(home, thread_id, sqlite_row=sqlite_row, include_archived=True)
        matched_sources = sorted({reason.split(" ", 1)[0] for reason in reasons})
        rows.append(
            {
                "id": thread_id,
                "score": score,
                "reasons": reasons,
                "matched_sources": matched_sources,
                "title_sqlite": sqlite_row.get("title"),
                "thread_name_index": index_row.get("thread_name"),
                "cwd_sqlite": sqlite_row.get("cwd"),
                "archived_sqlite": archived,
                "updated_at_sqlite": sqlite_row.get("updated_at"),
                "updated_at_index": index_row.get("updated_at"),
                "session_path_sqlite": sqlite_row.get("rollout_path"),
                "resolved_session_path": str(session_path) if session_path else None,
                "session_file_exists": bool(session_path and session_path.exists()),
            }
        )
    rows.sort(key=lambda row: (-row["score"], -(row.get("updated_at_sqlite") or 0), row["id"]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--query", required=True, help="Thread id, title, index name, cwd, or first-message fragment")
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    rows = build_rows(home, args.query, args.include_archived)[: max(1, args.limit)]
    if args.format == "json":
        print(json_dump({"query": args.query, "matches": rows}))
        return 0

    for row in rows:
        status = "archived" if row["archived_sqlite"] else "active"
        reasons = "; ".join(row["reasons"])
        print(f"{row['score']}\t{row['id']}\t{status}\t{row.get('thread_name_index') or row.get('title_sqlite') or ''}\t{reasons}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
