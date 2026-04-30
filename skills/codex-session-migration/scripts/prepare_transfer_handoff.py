#!/usr/bin/env python3
"""Resolve one thread and build a source-side handoff package in one command."""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from build_transfer_package import SKILL_ROOT, copy_tree_clean, zip_tree_posix
from codex_bundle_lib import (
    MigrationError,
    ensure_codex_home,
    json_dump,
    render_target_import_prompt,
    write_bundle,
    write_prompt_file,
)
from codex_migration_lib import build_catalog_safe
from search_threads import score_row


def now_utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def default_target_package_path(target_platform: str, zip_name: str) -> str:
    if target_platform == "windows":
        return rf"C:\REPLACE_WITH_ACTUAL_FOLDER\{zip_name}"
    return f"<replace with actual path to {zip_name} on the target machine>"


def default_target_cwd_placeholder(target_platform: str) -> str:
    if target_platform == "windows":
        return r"C:\REPLACE_WITH_TARGET_WORKSPACE"
    if target_platform == "macos":
        return "/Users/REPLACE_WITH_TARGET_WORKSPACE"
    return "/home/REPLACE_WITH_TARGET_WORKSPACE"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_thread(home: Path, query: str, include_archived: bool = False) -> dict:
    catalog, _skipped_invalid = build_catalog_safe(home, include_archived=include_archived, include_sqlite=True)
    rows = []
    for item in catalog.values():
        if not include_archived and item.get("archived"):
            continue
        row = {
            "id": item["id"],
            "title": item.get("title"),
            "updated_at": item.get("updated_at"),
            "cwd": item.get("cwd"),
            "archived": bool(item.get("archived")),
            "session_path": item.get("session_path"),
        }
        row["score"] = score_row(query, row)
        if row["score"] > 0:
            rows.append(row)

    rows.sort(key=lambda row: (-row["score"], row.get("updated_at") or "", row["id"]))
    if not rows:
        raise MigrationError(f"No thread matched query: {query}")

    best = rows[0]
    tied = [row for row in rows if row["score"] == best["score"]]
    if len(tied) > 1:
        raise MigrationError(
            "Thread query is ambiguous. Top matches:\n"
            + json_dump(
                [
                    {
                        "id": row["id"],
                        "title": row.get("title"),
                        "cwd": row.get("cwd"),
                        "updated_at": row.get("updated_at"),
                        "score": row["score"],
                    }
                    for row in tied[:5]
                ]
            )
        )
    return best


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-home", required=True, help="Source CODEX_HOME")
    parser.add_argument("--query", help="Thread title/id/cwd fragment to resolve")
    parser.add_argument("--thread-id", help="Exact thread id to export")
    parser.add_argument("--target-platform", required=True, choices=["windows", "macos", "linux"])
    parser.add_argument("--output-root", help="Optional output root directory")
    parser.add_argument("--target-package-path", help="Actual or placeholder target-machine path for the zip")
    parser.add_argument("--target-cwd", help="Actual or placeholder target workspace path")
    parser.add_argument("--prompt-output", help="Optional file path to write Prompt 1 to")
    parser.add_argument("--include-archived", action="store_true", help="Allow resolving archived threads")
    args = parser.parse_args()

    if not args.thread_id and not args.query:
        raise SystemExit("Provide --thread-id or --query")

    source_home = ensure_codex_home(args.source_home)
    if args.thread_id:
        match = {"id": args.thread_id, "title": None, "cwd": None}
    else:
        match = resolve_thread(source_home, args.query, include_archived=args.include_archived)

    thread_id = match["id"]
    output_root = Path(args.output_root) if args.output_root else (source_home / "migration_backups")
    output_root.mkdir(parents=True, exist_ok=True)
    handoff_dir = output_root / f"{now_utc_compact()}-transfer-thread-{thread_id}"
    package_dir = handoff_dir / "package"
    zip_name = "thread-transfer.zip"
    package_zip = handoff_dir / zip_name

    (package_dir / "bundle").mkdir(parents=True, exist_ok=True)
    (package_dir / "tooling").mkdir(parents=True, exist_ok=True)
    copy_tree_clean(SKILL_ROOT, package_dir / "tooling" / "codex-session-migration")

    bundle_path = package_dir / "bundle" / f"{thread_id}.zip"
    export_result = write_bundle(source_home, thread_id, bundle_path)

    target_package_path = args.target_package_path or default_target_package_path(args.target_platform, package_zip.name)
    target_cwd = args.target_cwd or default_target_cwd_placeholder(args.target_platform)
    prompt_text = render_target_import_prompt(
        thread_id=thread_id,
        package_zip_path=target_package_path,
        target_cwd=target_cwd,
        target_platform=args.target_platform,
        package_contents=[
            f"bundle/{thread_id}.zip",
            "tooling/codex-session-migration/",
        ],
    )
    prompt_output = Path(args.prompt_output) if args.prompt_output else handoff_dir / "target-import-prompt.md"
    write_prompt_file(prompt_text, prompt_output)
    zip_tree_posix(package_dir, package_zip)

    result = {
        "status": "ok",
        "thread_id": thread_id,
        "thread_title": match.get("title"),
        "thread_cwd": match.get("cwd"),
        "package_dir": str(package_dir),
        "package_zip": str(package_zip),
        "package_sha256": sha256_file(package_zip),
        "prompt_output": str(prompt_output),
        "prompt_text": prompt_text,
        "export": export_result,
    }
    print(json_dump(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
