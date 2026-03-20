#!/usr/bin/env python3
"""Create a dry-run migration plan from a spec JSON file."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_migration_lib import MigrationError, json_dump, parse_spec, plan_from_spec, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, help="Path to a migration spec JSON file")
    parser.add_argument("--output", help="Optional output path for the generated plan JSON")
    args = parser.parse_args()

    try:
        spec = parse_spec(Path(args.spec))
        plan = plan_from_spec(spec)
    except MigrationError as exc:
        raise SystemExit(f"Error: {exc}") from exc

    if args.output:
        write_json(Path(args.output), plan)
    print(json_dump(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
