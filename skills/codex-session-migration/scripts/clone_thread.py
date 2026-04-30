#!/usr/bin/env python3
"""Clone a thread within one CODEX_HOME under a new thread id and cwd."""

from __future__ import annotations

import argparse
import datetime as dt
import secrets
from pathlib import Path

from codex_migration_lib import (
    MigrationError,
    backup_file,
    build_catalog,
    create_backup_dir,
    ensure_codex_home,
    json_dump,
    load_session_index,
    load_sqlite_threads,
    now_utc_iso,
    read_jsonl,
    upsert_threads_sqlite,
    write_json,
    write_jsonl,
    write_session_index,
)


def uuid7_like() -> str:
    ts_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    value = ((ts_ms & ((1 << 48) - 1)) << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    hex_value = f"{value:032x}"
    return f"{hex_value[:8]}-{hex_value[8:12]}-{hex_value[12:16]}-{hex_value[16:20]}-{hex_value[20:]}"


def default_target_session_path(home: Path, thread_id: str) -> Path:
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H-%M-%S")
    return home / "sessions" / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d") / f"rollout-{stamp}-{thread_id}.jsonl"


def clone_session_file(source_path: Path, target_path: Path, source_thread_id: str, target_thread_id: str, target_cwd: str) -> dict[str, int]:
    items = read_jsonl(source_path)
    counts = {"session_meta_id": 0, "session_meta_cwd": 0, "turn_context_cwd": 0}
    for item in items:
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        if item.get("type") == "session_meta":
            if payload.get("id") in {None, source_thread_id}:
                payload["id"] = target_thread_id
                counts["session_meta_id"] += 1
            if payload.get("cwd") != target_cwd:
                payload["cwd"] = target_cwd
                counts["session_meta_cwd"] += 1
            item["payload"] = payload
        elif item.get("type") == "turn_context" and payload.get("cwd") != target_cwd:
            payload["cwd"] = target_cwd
            item["payload"] = payload
            counts["turn_context_cwd"] += 1
    if counts["session_meta_id"] == 0:
        raise MigrationError(f"Session meta id not found in source file: {source_path}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(target_path, items)
    return counts


def resolve_source(home: Path, thread_id: str) -> dict:
    sqlite_row = load_sqlite_threads(home, [thread_id]).get(thread_id)
    index_row = load_session_index(home).get(thread_id)
    session_path = Path(sqlite_row["rollout_path"]) if sqlite_row and sqlite_row.get("rollout_path") else None
    if session_path and session_path.exists():
        return {
            "sqlite_row": sqlite_row,
            "index_row": index_row,
            "session_path": session_path,
            "title": sqlite_row.get("title") if sqlite_row else None,
            "cwd": sqlite_row.get("cwd") if sqlite_row else None,
            "archived": bool(sqlite_row.get("archived")) if sqlite_row else False,
        }

    record = build_catalog(home, include_archived=True, include_sqlite=True).get(thread_id)
    if not record or not record.get("session_path"):
        raise MigrationError(f"Thread not found or missing session file: {thread_id}")
    return {
        "sqlite_row": record.get("source_sqlite_row"),
        "index_row": record.get("index_entry"),
        "session_path": Path(record["session_path"]),
        "title": record.get("title"),
        "cwd": record.get("cwd"),
        "archived": bool(record.get("archived")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--source-thread-id", required=True, help="Existing thread id to clone")
    parser.add_argument("--target-cwd", required=True, help="Workspace path for the cloned thread")
    parser.add_argument("--new-thread-id", help="Optional explicit thread id for the clone")
    parser.add_argument("--title", help="Optional title override for the cloned thread")
    parser.add_argument("--execute", action="store_true", help="Required to perform writes")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Refusing to mutate without --execute")

    home = ensure_codex_home(args.home)
    source = resolve_source(home, args.source_thread_id)
    new_thread_id = args.new_thread_id or uuid7_like()
    if new_thread_id == args.source_thread_id:
        raise MigrationError("New thread id must differ from source thread id")

    index_rows = load_session_index(home)
    sqlite_rows = load_sqlite_threads(home)
    if new_thread_id in index_rows or new_thread_id in sqlite_rows:
        raise MigrationError(f"Target thread id already exists: {new_thread_id}")

    source_session_path = source["session_path"]
    if not source_session_path.exists():
        raise MigrationError(f"Source session file does not exist: {source_session_path}")
    target_session_path = default_target_session_path(home, new_thread_id)
    if target_session_path.exists():
        raise MigrationError(f"Target session file already exists: {target_session_path}")

    backup_dir = create_backup_dir(home, "clone-thread")
    manifest = {
        "schema_version": 1,
        "created_at": now_utc_iso(),
        "source_thread_id": args.source_thread_id,
        "target_thread_id": new_thread_id,
        "target_cwd": args.target_cwd,
        "backup_dir": str(backup_dir),
        "target_session_path": str(target_session_path),
        "session_clone_counts": None,
        "session_index_backup": None,
        "sqlite_rows": [],
    }

    session_index_path = home / "session_index.jsonl"
    if session_index_path.exists():
        manifest["session_index_backup"] = str(backup_file(session_index_path, backup_dir).resolve())

    counts = clone_session_file(
        source_session_path,
        target_session_path,
        args.source_thread_id,
        new_thread_id,
        args.target_cwd,
    )
    manifest["session_clone_counts"] = counts

    title = args.title or (source.get("sqlite_row") or {}).get("title") or source.get("title") or new_thread_id
    updated_at = now_utc_iso()
    index_rows[new_thread_id] = {
        "id": new_thread_id,
        "thread_name": title,
        "updated_at": updated_at,
    }
    write_session_index(home, index_rows)

    sqlite_row = dict(source.get("sqlite_row") or {})
    now_epoch = int(dt.datetime.now(dt.timezone.utc).timestamp())
    sqlite_row.update(
        {
            "id": new_thread_id,
            "rollout_path": str(target_session_path),
            "cwd": args.target_cwd,
            "title": title,
            "archived": 0,
            "archived_at": None,
            "created_at": now_epoch,
            "updated_at": now_epoch,
        }
    )
    result = upsert_threads_sqlite(
        home,
        [
            {
                "id": new_thread_id,
                "title": title,
                "source_archived": False,
                "target_session_path": str(target_session_path),
                "target_cwd": args.target_cwd,
                "source_sqlite_row": sqlite_row,
                "source": sqlite_row.get("source") or "imported",
                "cli_version": sqlite_row.get("cli_version"),
                "model_provider": sqlite_row.get("model_provider"),
                "sandbox_policy": sqlite_row.get("sandbox_policy"),
                "approval_mode": sqlite_row.get("approval_mode"),
                "session_meta_timestamp": None,
                "last_timestamp": updated_at,
                "source_index_entry": index_rows[new_thread_id],
            }
        ],
        backup_dir / "sqlite_before",
    )
    manifest["sqlite_rows"] = result["rows"]

    manifest_path = backup_dir / "clone_manifest.json"
    write_json(manifest_path, manifest)
    print(
        json_dump(
            {
                "status": "ok",
                "source_thread_id": args.source_thread_id,
                "target_thread_id": new_thread_id,
                "source_cwd": source.get("cwd"),
                "target_cwd": args.target_cwd,
                "target_session_path": str(target_session_path),
                "backup_dir": str(backup_dir),
                "manifest": str(manifest_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
