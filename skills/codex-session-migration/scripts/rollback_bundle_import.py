#!/usr/bin/env python3
"""Rollback one imported Codex thread bundle using its manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_bundle_lib import json_bytes, rollback_bundle_import


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="Path to import_manifest.json produced during bundle import")
    args = parser.parse_args()

    result = rollback_bundle_import(Path(args.manifest))
    print(json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
