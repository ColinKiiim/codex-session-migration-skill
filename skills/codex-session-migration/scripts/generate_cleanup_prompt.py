#!/usr/bin/env python3
"""Generate a post-success cleanup prompt using actual target-machine paths."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_bundle_lib import json_bytes, render_cleanup_prompt, write_prompt_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", required=True, help="Thread id that was imported")
    parser.add_argument("--target-cwd", required=True, help="Confirmed target workspace path")
    parser.add_argument("--extract-dir", required=True, help="Temporary extraction directory used during import")
    parser.add_argument("--isolated-home", required=True, help="Disposable target CODEX_HOME used during isolated testing")
    parser.add_argument("--real-home", required=True, help="Real target CODEX_HOME that was imported into")
    parser.add_argument(
        "--real-import-backup-dir",
        required=True,
        help="The migration_backups directory created by the real import inside the real target CODEX_HOME",
    )
    parser.add_argument("--external-backup-dir", help="Optional full external backup created before the real import")
    parser.add_argument("--bundle-zip-path", help="Optional transfer-package zip path to preserve for rollback")
    parser.add_argument("--output", help="Optional file path to write the cleanup prompt to")
    args = parser.parse_args()

    prompt_text = render_cleanup_prompt(
        thread_id=args.thread_id,
        target_cwd=args.target_cwd,
        extract_dir=args.extract_dir,
        isolated_home=args.isolated_home,
        real_home=args.real_home,
        real_import_backup_dir=args.real_import_backup_dir,
        external_backup_dir=args.external_backup_dir,
        bundle_zip_path=args.bundle_zip_path,
    )

    if args.output:
        output_path = write_prompt_file(prompt_text, Path(args.output))
        print(json_bytes({"status": "ok", "output_path": str(output_path), "thread_id": args.thread_id}).decode("utf-8"), end="")
    else:
        print(prompt_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
