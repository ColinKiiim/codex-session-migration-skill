#!/usr/bin/env python3
"""Rebind all threads whose workspace cwd matches one or more path prefixes."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any

from codex_migration_lib import (
    MigrationError,
    backup_file,
    copy_sqlite_bundle,
    create_backup_dir,
    ensure_codex_home,
    find_session_path_by_thread_id,
    json_dump,
    load_session_index,
    load_sqlite_threads,
    parse_iso_to_epoch,
    write_json,
    write_session_index,
)


UI_REFRESH_HINT = (
    "Check the Codex Desktop sidebar first. Recent Desktop builds may refresh visible threads "
    "without a full restart. If the threads do not appear, fully restart Codex Desktop to force a reload."
)


def epoch_to_iso(value: int) -> str:
    return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_mapping(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise MigrationError(f"Path mapping must be OLD=NEW: {value}")
    old, new = value.split("=", 1)
    if not old or not new:
        raise MigrationError(f"Path mapping must include both OLD and NEW: {value}")
    return old.rstrip("/\\"), new.rstrip("/\\")


def build_mappings(args: argparse.Namespace) -> list[tuple[str, str]]:
    mappings = [parse_mapping(item) for item in args.map or []]
    if args.old_prefix or args.new_prefix:
        if not (args.old_prefix and args.new_prefix):
            raise MigrationError("--old-prefix and --new-prefix must be used together")
        mappings.append((args.old_prefix.rstrip("/\\"), args.new_prefix.rstrip("/\\")))
    if not mappings:
        raise MigrationError("Pass at least one --map OLD=NEW or --old-prefix/--new-prefix pair")
    return mappings


def apply_prefix(value: str | None, mappings: list[tuple[str, str]]) -> str | None:
    if value is None:
        return None
    matches = [(old, new) for old, new in mappings if value == old or value.startswith(old + "/") or value.startswith(old + "\\")]
    if not matches:
        return value
    old, new = max(matches, key=lambda item: len(item[0]))
    return new + value[len(old) :]


def replace_prefixes(value: Any, mappings: list[tuple[str, str]]) -> Any:
    if isinstance(value, str):
        return apply_prefix(value, mappings)
    if isinstance(value, list):
        return [replace_prefixes(item, mappings) for item in value]
    if isinstance(value, dict):
        return {key: replace_prefixes(item, mappings) for key, item in value.items()}
    return value


def replace_sqlite_json_string(value: Any, mappings: list[tuple[str, str]]) -> Any:
    if not isinstance(value, str):
        return replace_prefixes(value, mappings)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return replace_prefixes(value, mappings)
    replaced = replace_prefixes(parsed, mappings)
    return json.dumps(replaced, ensure_ascii=False) if replaced != parsed else value


def parse_jsonl_line(path: Path, line_no: int, line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        wrapped = json.JSONDecodeError(f"{exc.msg} in {path} at line {line_no}", exc.doc, exc.pos)
        wrapped.jsonl_path = str(path)
        wrapped.jsonl_line = line_no
        wrapped.jsonl_column = exc.colno
        raise wrapped from exc


def scan_session_update_counts(session_path: Path, mappings: list[tuple[str, str]]) -> dict[str, int]:
    counts = {"session_meta": 0, "turn_context": 0, "sandbox_policy": 0, "invalid_lines": 0}
    for line_no, line in enumerate(session_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            item = parse_jsonl_line(session_path, line_no, line)
        except json.JSONDecodeError:
            counts["invalid_lines"] += 1
            continue
        if not item:
            continue
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        item_type = item.get("type")
        if item_type in {"session_meta", "turn_context"} and "cwd" in payload:
            next_cwd = apply_prefix(payload.get("cwd"), mappings)
            if next_cwd != payload.get("cwd"):
                counts[item_type] += 1
        if item_type == "turn_context" and "sandbox_policy" in payload:
            next_policy = replace_prefixes(payload.get("sandbox_policy"), mappings)
            if next_policy != payload.get("sandbox_policy"):
                counts["sandbox_policy"] += 1
    return counts


def rewrite_session_metadata(session_path: Path, mappings: list[tuple[str, str]]) -> dict[str, int]:
    counts = {"session_meta": 0, "turn_context": 0, "sandbox_policy": 0, "invalid_lines": 0}
    output: list[str] = []
    for line_no, line in enumerate(session_path.read_text(encoding="utf-8").splitlines(keepends=True), 1):
        ending = "\n" if line.endswith("\n") else ""
        raw = line[:-1] if ending else line
        try:
            item = parse_jsonl_line(session_path, line_no, raw)
        except json.JSONDecodeError:
            output.append(line)
            counts["invalid_lines"] += 1
            continue
        if not item:
            output.append(line)
            continue

        payload = item.get("payload")
        changed = False
        if isinstance(payload, dict) and item.get("type") in {"session_meta", "turn_context"}:
            if "cwd" in payload:
                next_cwd = apply_prefix(payload.get("cwd"), mappings)
                if next_cwd != payload.get("cwd"):
                    payload["cwd"] = next_cwd
                    counts[item["type"]] += 1
                    changed = True
            if item.get("type") == "turn_context" and "sandbox_policy" in payload:
                next_policy = replace_prefixes(payload.get("sandbox_policy"), mappings)
                if next_policy != payload.get("sandbox_policy"):
                    payload["sandbox_policy"] = next_policy
                    counts["sandbox_policy"] += 1
                    changed = True
        output.append(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + ending if changed else line)
    session_path.write_text("".join(output), encoding="utf-8")
    return counts


def select_threads(home: Path, mappings: list[tuple[str, str]], *, include_archived: bool) -> list[dict[str, Any]]:
    rows = load_sqlite_threads(home)
    selected: list[dict[str, Any]] = []
    for thread_id, row in rows.items():
        if row.get("archived") and not include_archived:
            continue
        cwd = row.get("cwd")
        target_cwd = apply_prefix(cwd, mappings)
        if target_cwd and target_cwd != cwd:
            selected.append({"id": thread_id, "source_sqlite_row": row, "before_cwd": cwd, "after_cwd": target_cwd})
    selected.sort(key=lambda item: (item["after_cwd"], -int(item["source_sqlite_row"].get("updated_at") or 0), item["id"]))
    return selected


def sqlite_thread_columns(home: Path) -> set[str]:
    path = home / "state_5.sqlite"
    if not path.exists():
        return set()
    conn = sqlite3.connect(path)
    try:
        return {row[1] for row in conn.execute("PRAGMA table_info(threads)").fetchall()}
    finally:
        conn.close()


def update_sqlite_rows(home: Path, planned: list[dict[str, Any]], *, backup_dir: Path | None) -> list[dict[str, str]]:
    path = home / "state_5.sqlite"
    if not path.exists():
        raise MigrationError(f"Missing sqlite database: {path}")
    copied = copy_sqlite_bundle(path, backup_dir) if backup_dir else []
    columns = sqlite_thread_columns(home)
    conn = sqlite3.connect(path)
    try:
        for item in planned:
            row = dict(item["source_sqlite_row"])
            sandbox_policy = replace_sqlite_json_string(row.get("sandbox_policy"), item["mappings"])
            updates: dict[str, Any] = {"cwd": item["after_cwd"], "sandbox_policy": sandbox_policy}
            if item.get("after_updated_epoch"):
                updates["updated_at"] = item["after_updated_epoch"]
                if "updated_at_ms" in columns:
                    updates["updated_at_ms"] = int(item["after_updated_epoch"]) * 1000
            assignments = ", ".join(f"{key}=?" for key in updates)
            conn.execute(
                f"UPDATE threads SET {assignments} WHERE id=?",
                [*updates.values(), item["id"]],
            )
        conn.commit()
    finally:
        conn.close()
    return copied


def validate_target_paths(planned: list[dict[str, Any]], *, require_target_exists: bool) -> list[str]:
    missing = sorted({item["after_cwd"] for item in planned if not Path(item["after_cwd"]).exists()})
    if missing and require_target_exists:
        preview = "; ".join(missing[:10])
        raise MigrationError(f"Mapped target cwd does not exist: {preview}")
    return missing


def build_plan(
    home: Path,
    mappings: list[tuple[str, str]],
    *,
    include_archived: bool,
    promote_to_sidebar: bool,
    base_epoch: int,
    spacing_seconds: int,
) -> list[dict[str, Any]]:
    index_rows = load_session_index(home)
    planned = select_threads(home, mappings, include_archived=include_archived)
    for idx, item in enumerate(planned):
        row = item["source_sqlite_row"]
        session_path = find_session_path_by_thread_id(home, item["id"], sqlite_row=row, include_archived=True)
        if not session_path:
            raise MigrationError(f"Thread is missing a session file: {item['id']}")
        before_updated_epoch = int(row.get("updated_at") or parse_iso_to_epoch((index_rows.get(item["id"]) or {}).get("updated_at")) or 0)
        after_updated_epoch = base_epoch - (idx * max(spacing_seconds, 1)) if promote_to_sidebar else before_updated_epoch
        item.update(
            {
                "session_path": str(session_path),
                "archived": bool(row.get("archived")),
                "sqlite_title": row.get("title"),
                "session_index_thread_name": (index_rows.get(item["id"]) or {}).get("thread_name"),
                "thread_name_preserved": bool((index_rows.get(item["id"]) or {}).get("thread_name")),
                "before_updated_at": epoch_to_iso(before_updated_epoch) if before_updated_epoch else None,
                "after_updated_epoch": after_updated_epoch,
                "after_updated_at": epoch_to_iso(after_updated_epoch) if after_updated_epoch else None,
                "session_update_counts": scan_session_update_counts(session_path, mappings),
                "mappings": mappings,
            }
        )
    return planned


def public_thread_report(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "session_path": item["session_path"],
        "before_cwd": item["before_cwd"],
        "after_cwd": item["after_cwd"],
        "sqlite_title": item.get("sqlite_title"),
        "session_index_thread_name": item.get("session_index_thread_name"),
        "thread_name_preserved": item.get("thread_name_preserved"),
        "archived": item.get("archived"),
        "before_updated_at": item.get("before_updated_at"),
        "after_updated_at": item.get("after_updated_at"),
        "session_update_counts": item.get("session_update_counts"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, help="Path to a CODEX_HOME directory")
    parser.add_argument("--map", action="append", help="Path prefix mapping in OLD=NEW form. May be repeated.")
    parser.add_argument("--old-prefix", help="Single source path prefix. Use with --new-prefix.")
    parser.add_argument("--new-prefix", help="Single target path prefix. Use with --old-prefix.")
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument("--promote-to-sidebar", action="store_true", help="Bump updated_at metadata so Desktop is more likely to surface the threads")
    parser.add_argument("--spacing-seconds", type=int, default=60)
    parser.add_argument("--base-time", help="Optional ISO timestamp for the newest promoted thread")
    parser.add_argument("--require-target-exists", action="store_true", help="Fail if any mapped target cwd does not exist on this machine")
    parser.add_argument("--report-path")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    home = ensure_codex_home(args.home)
    mappings = build_mappings(args)
    base_epoch = parse_iso_to_epoch(args.base_time) if args.base_time else None
    if base_epoch is None:
        base_epoch = int(dt.datetime.now(dt.timezone.utc).timestamp())
    planned = build_plan(
        home,
        mappings,
        include_archived=args.include_archived,
        promote_to_sidebar=args.promote_to_sidebar,
        base_epoch=base_epoch,
        spacing_seconds=args.spacing_seconds,
    )
    missing_targets = validate_target_paths(planned, require_target_exists=args.require_target_exists)
    report: dict[str, Any] = {
        "status": "planned",
        "home": str(home),
        "mappings": [{"from": old, "to": new} for old, new in mappings],
        "include_archived": args.include_archived,
        "promote_to_sidebar": args.promote_to_sidebar,
        "require_target_exists": args.require_target_exists,
        "selected_count": len(planned),
        "missing_target_cwds": missing_targets,
        "ui_refresh_hint": UI_REFRESH_HINT,
        "backup_dir": None,
        "threads": [public_thread_report(item) for item in planned],
    }

    if args.execute:
        backup_dir = create_backup_dir(home, "rebind-path-prefix")
        report["backup_dir"] = str(backup_dir)
        index_path = home / "session_index.jsonl"
        if index_path.exists():
            report["session_index_backup"] = str(backup_file(index_path, backup_dir).resolve())

        current_index = load_session_index(home)
        rewritten = []
        for item in planned:
            session_path = Path(item["session_path"])
            backup_file(session_path, backup_dir / "session_backups", home)
            counts = rewrite_session_metadata(session_path, mappings)
            rewritten.append({"id": item["id"], "path": str(session_path), "counts": counts})
            row = current_index.get(
                item["id"],
                {"id": item["id"], "thread_name": item.get("session_index_thread_name") or item.get("sqlite_title") or item["id"]},
            )
            if not row.get("thread_name"):
                row["thread_name"] = item.get("session_index_thread_name") or item.get("sqlite_title") or item["id"]
            if args.promote_to_sidebar and item.get("after_updated_at"):
                row["updated_at"] = item["after_updated_at"]
            current_index[item["id"]] = row
        write_session_index(home, current_index)
        report["sqlite_backup_files"] = update_sqlite_rows(home, planned, backup_dir=backup_dir / "sqlite_before")
        report["status"] = "ok"
        report["rewritten"] = rewritten
        report["remaining_old_prefix_sqlite_count"] = len(select_threads(home, mappings, include_archived=True))
        write_json(backup_dir / "rebind_path_prefix_report.json", report)

    if args.report_path:
        write_json(Path(args.report_path).expanduser(), report)
    print(json_dump(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
