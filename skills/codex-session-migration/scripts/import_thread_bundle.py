#!/usr/bin/env python3
"""Import one Codex thread bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_bundle_lib import import_bundle, json_bytes
from codex_migration_lib import ensure_codex_home


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, help="Bundle zip path")
    parser.add_argument("--target-home", required=True, help="Target CODEX_HOME")
    parser.add_argument("--target-cwd", required=True, help="Target cwd to bind the thread to")
    parser.add_argument("--allow-replace", action="store_true", help="Allow overwriting an existing session path")
    parser.add_argument("--execute", action="store_true", help="Required to perform writes")
    args = parser.parse_args()

    if not args.execute:
        raise SystemExit("Refusing to mutate without --execute")

    result = import_bundle(
        Path(args.bundle),
        ensure_codex_home(args.target_home),
        args.target_cwd,
        allow_replace=args.allow_replace,
    )
    print(json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
