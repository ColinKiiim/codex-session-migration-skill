#!/usr/bin/env python3
"""Search threads in a Codex home by id, title, or cwd fragment."""

from __future__ import annotations

import argparse
import unicodedata

from codex_migration_lib import build_catalog, ensure_codex_home, json_dump


def normalize_search_text(value: str) -> str:
    chars: list[str] = []
    for ch in value.casefold():
        category = unicodedata.category(ch)
        if category.startswith("Z") or category.startswith("P"):
            continue
        chars.append(ch)
    return "".join(chars)


def score_row(query: str, row: dict) -> int:
    q = query.casefold()
    q_norm = normalize_search_text(query)
    thread_id = (row.get("id") or "").casefold()
    title = (row.get("title") or "").casefold()
    cwd = (row.get("cwd") or "").casefold()
    thread_id_norm = normalize_search_text(row.get("id") or "")
    title_norm = normalize_search_text(row.get("title") or "")
    cwd_norm = normalize_search_text(row.get("cwd") or "")

    score = 0
    if thread_id == q:
        score += 1000
    elif q in thread_id:
        score += 500
    elif q_norm and q_norm in thread_id_norm:
        score += 450

    if title == q:
        score += 300
    elif q in title:
        score += 200
    elif q_norm and q_norm in title_norm:
        score += 260

    if cwd == q:
        score += 80
    elif q in cwd:
        score += 40
    elif q_norm and q_norm in cwd_norm:
        score += 30
    return score


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--query", required=True, help="Thread id, title fragment, or cwd fragment")
    parser.add_argument("--include-archived", action="store_true", help="Include archived sessions")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of matches to return")
    parser.add_argument("--format", choices=["text", "json"], default="json")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    catalog = build_catalog(home, include_archived=args.include_archived, include_sqlite=True)
    rows = []
    for item in catalog.values():
        if not args.include_archived and item.get("archived"):
            continue
        row = {
            "id": item["id"],
            "title": item.get("title"),
            "updated_at": item.get("updated_at"),
            "cwd": item.get("cwd"),
            "archived": bool(item.get("archived")),
            "session_path": item.get("session_path"),
        }
        row["score"] = score_row(args.query, row)
        if row["score"] > 0:
            rows.append(row)

    rows.sort(key=lambda row: (-row["score"], -(1 if row["updated_at"] else 0), row.get("updated_at") or "", row["id"]))
    rows = rows[: max(1, args.limit)]

    if args.format == "json":
        print(json_dump(rows))
        return 0

    for row in rows:
        status = "archived" if row["archived"] else "active"
        print(f"{row['score']}\t{row['id']}\t{status}\t{row.get('title') or ''}\t{row.get('cwd') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
