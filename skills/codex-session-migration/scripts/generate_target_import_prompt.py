#!/usr/bin/env python3
"""Generate a target-machine import prompt for a bundle transfer."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_bundle_lib import json_bytes, render_target_import_prompt, write_prompt_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", required=True, help="Thread id contained in the bundle")
    parser.add_argument("--target-platform", required=True, choices=["windows", "macos", "linux"])
    parser.add_argument("--package-path", required=True, help="Actual or placeholder package zip path on the target machine")
    parser.add_argument("--target-cwd", required=True, help="Actual or placeholder target workspace path")
    parser.add_argument("--output", help="Optional file path to write the prompt to")
    parser.add_argument(
        "--extra-item",
        action="append",
        default=[],
        help="Optional additional package-root item to mention in the prompt",
    )
    args = parser.parse_args()

    prompt_text = render_target_import_prompt(
        thread_id=args.thread_id,
        package_zip_path=args.package_path,
        target_cwd=args.target_cwd,
        target_platform=args.target_platform,
        package_contents=[
            f"bundle/{args.thread_id}.zip",
            "tooling/codex-session-migration/",
            *args.extra_item,
        ],
    )

    if args.output:
        output_path = write_prompt_file(prompt_text, Path(args.output))
        print(
            json_bytes(
                {
                    "status": "ok",
                    "output_path": str(output_path),
                    "thread_id": args.thread_id,
                    "target_platform": args.target_platform,
                }
            ).decode("utf-8"),
            end="",
        )
    else:
        print(prompt_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
