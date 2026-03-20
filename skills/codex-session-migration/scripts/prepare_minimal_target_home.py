#!/usr/bin/env python3
"""Create a disposable target CODEX_HOME for bundle import testing."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_bundle_lib import create_minimal_target_home, json_bytes
from codex_migration_lib import ensure_codex_home


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-home", required=True, help="Existing CODEX_HOME used as schema source")
    parser.add_argument("--target-home", required=True, help="Disposable target CODEX_HOME to create")
    args = parser.parse_args()

    result = create_minimal_target_home(
        ensure_codex_home(args.source_home),
        Path(args.target_home),
    )
    print(json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
