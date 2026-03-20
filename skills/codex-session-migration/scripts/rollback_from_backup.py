#!/usr/bin/env python3
"""Rollback a migration using a manifest file."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from codex_migration_lib import json_dump, read_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--execute", action="store_true", help="Required to perform writes")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Refusing to mutate without --execute")

    manifest = read_json(Path(args.manifest))
    restored = {"session_index": None, "sqlite": [], "sessions_restored": [], "sessions_removed": []}

    if manifest.get("session_index_backup"):
        backup = Path(manifest["session_index_backup"])
        target = Path(manifest["target_home"]) / "session_index.jsonl"
        shutil.copy2(backup, target)
        restored["session_index"] = str(target)

    for row in manifest.get("sqlite_backup_files", []):
        shutil.copy2(Path(row["backup"]), Path(row["source"]))
        restored["sqlite"].append(row["source"])

    for row in manifest.get("overwritten_session_backups", []):
        shutil.copy2(Path(row["backup"]), Path(row["original"]))
        restored["sessions_restored"].append(row["original"])

    for path_str in manifest.get("created_session_files", []):
        path = Path(path_str)
        if path.exists():
            path.unlink()
            restored["sessions_removed"].append(str(path))

    print(json_dump({"status": "ok", "restored": restored}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
