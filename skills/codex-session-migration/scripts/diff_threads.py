#!/usr/bin/env python3
"""Compare source and target Codex homes by thread id."""

from __future__ import annotations

import argparse

from codex_migration_lib import build_catalog_safe, ensure_codex_home, json_dump


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-home", required=True)
    parser.add_argument("--target-home", required=True)
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument("--format", choices=["text", "json"], default="json")
    args = parser.parse_args()

    source_home = ensure_codex_home(args.source_home)
    target_home = ensure_codex_home(args.target_home)
    source_catalog, source_skipped = build_catalog_safe(source_home, include_archived=args.include_archived, include_sqlite=True)
    target_catalog, target_skipped = build_catalog_safe(target_home, include_archived=True, include_sqlite=True)

    source_ids = set(source_catalog)
    target_ids = set(target_catalog)
    shared = sorted(source_ids & target_ids)
    only_source = sorted(source_ids - target_ids)
    only_target = sorted(target_ids - source_ids)
    cwd_mismatches = []
    for sid in shared:
        source_cwd = source_catalog[sid].get("cwd")
        target_cwd = target_catalog[sid].get("cwd")
        if source_cwd != target_cwd:
            cwd_mismatches.append(
                {
                    "id": sid,
                    "title": source_catalog[sid].get("title") or target_catalog[sid].get("title"),
                    "source_cwd": source_cwd,
                    "target_cwd": target_cwd,
                }
            )

    payload = {
        "source_home": str(source_home),
        "target_home": str(target_home),
        "only_source": only_source,
        "only_target": only_target,
        "shared": shared,
        "cwd_mismatches": cwd_mismatches,
        "skipped_invalid_session_files": {
            "source": source_skipped,
            "target": target_skipped,
        },
    }
    if args.format == "json":
        print(json_dump(payload))
        return 0

    print(f"only_source\t{len(only_source)}")
    for sid in only_source:
        print(f"+\t{sid}\t{source_catalog[sid].get('title') or ''}")
    print(f"only_target\t{len(only_target)}")
    for sid in only_target:
        print(f"-\t{sid}\t{target_catalog[sid].get('title') or ''}")
    print(f"cwd_mismatches\t{len(cwd_mismatches)}")
    for item in cwd_mismatches:
        print(f"~\t{item['id']}\t{item['source_cwd'] or ''}\t=>\t{item['target_cwd'] or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
