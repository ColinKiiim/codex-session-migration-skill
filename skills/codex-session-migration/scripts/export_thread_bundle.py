#!/usr/bin/env python3
"""Export one Codex thread into a portable bundle zip."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_bundle_lib import ensure_codex_home, json_bytes, write_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Source CODEX_HOME")
    parser.add_argument("--thread-id", required=True, help="Thread id to export")
    parser.add_argument("--output", required=True, help="Output zip file path")
    args = parser.parse_args()

    result = write_bundle(ensure_codex_home(args.home), args.thread_id, Path(args.output))
    print(json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
