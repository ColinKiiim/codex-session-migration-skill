#!/usr/bin/env python3
"""Verify one imported Codex thread bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_bundle_lib import json_bytes, verify_bundle_import
from codex_migration_lib import ensure_codex_home


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, help="Bundle zip path")
    parser.add_argument("--target-home", required=True, help="Target CODEX_HOME")
    parser.add_argument("--target-cwd", required=True, help="Expected target cwd")
    args = parser.parse_args()

    result = verify_bundle_import(Path(args.bundle), ensure_codex_home(args.target_home), args.target_cwd)
    print(json_bytes(result).decode("utf-8"), end="")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
