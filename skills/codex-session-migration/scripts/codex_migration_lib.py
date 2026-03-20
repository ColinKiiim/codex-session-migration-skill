#!/usr/bin/env python3
"""Shared helpers for codex-session-migration."""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import sqlite3
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

THREAD_ID_RE = re.compile(r"(019[0-9a-f-]+)\.jsonl$", re.IGNORECASE)
ROLLOUT_TS_RE = re.compile(
    r"rollout-(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})-(019[0-9a-f-]+)\.jsonl$",
    re.IGNORECASE,
)
VALID_MODES = {"copy-missing", "copy-selected", "replace-selected", "rebind-only"}


class MigrationError(RuntimeError):
    """Raised when migration inputs or state are invalid."""


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    # Path.write_text() newline= is not supported on older Python releases such as 3.9.
    path.write_text(json_dump(data) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return items


def write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False))
            handle.write("\n")


def parse_iso_to_epoch(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def extract_thread_id(path: Path) -> str | None:
    match = THREAD_ID_RE.search(path.name)
    return match.group(1) if match else None


def parse_rollout_timestamp(path: Path) -> int | None:
    match = ROLLOUT_TS_RE.search(path.name)
    if not match:
        return None
    value = match.group(1)
    try:
        stamp = dt.datetime.strptime(value, "%Y-%m-%dT%H-%M-%S")
    except ValueError:
        return None
    return int(stamp.replace(tzinfo=dt.timezone.utc).timestamp())


def ensure_codex_home(home: str | Path) -> Path:
    path = Path(home).expanduser()
    if not path.exists():
        raise MigrationError(f"Codex home does not exist: {path}")
    if not ((path / "sessions").exists() or (path / "session_index.jsonl").exists()):
        raise MigrationError(f"Path does not look like a Codex home: {path}")
    return path


def sqlite_path(home: Path) -> Path:
    return home / "state_5.sqlite"


def sqlite_sidecars(path: Path) -> list[Path]:
    return [path, path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm")]


def copy_sqlite_bundle(path: Path, backup_dir: Path) -> list[dict[str, str]]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, str]] = []
    for source in sqlite_sidecars(path):
        if not source.exists():
            continue
        target = backup_dir / source.name
        shutil.copy2(source, target)
        copied.append({"source": str(source), "backup": str(target)})
    return copied


def load_session_index(home: Path) -> dict[str, dict[str, Any]]:
    path = home / "session_index.jsonl"
    if not path.exists():
        return {}
    rows = read_jsonl(path)
    return {row["id"]: row for row in rows if row.get("id")}


def write_session_index(home: Path, rows: dict[str, dict[str, Any]]) -> None:
    ordered = sorted(rows.values(), key=lambda row: (row.get("updated_at", ""), row.get("id", "")))
    write_jsonl(home / "session_index.jsonl", ordered)


def load_sqlite_threads(home: Path, thread_ids: list[str] | None = None) -> dict[str, dict[str, Any]]:
    path = sqlite_path(home)
    if not path.exists():
        return {}
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cols = {row["name"] for row in cur.execute("PRAGMA table_info(threads)").fetchall()}
    except sqlite3.OperationalError:
        return {}
    if "id" not in cols:
        conn.close()
        return {}
    if thread_ids:
        placeholders = ",".join("?" for _ in thread_ids)
        query = f"SELECT * FROM threads WHERE id IN ({placeholders})"
        rows = cur.execute(query, thread_ids).fetchall()
    else:
        rows = cur.execute("SELECT * FROM threads").fetchall()
    data = {row["id"]: dict(row) for row in rows}
    conn.close()
    return data


def scan_session_files(home: Path, include_archived: bool) -> list[Path]:
    paths: list[Path] = []
    if (home / "sessions").exists():
        paths.extend(sorted((home / "sessions").rglob("rollout-*.jsonl")))
    if include_archived and (home / "archived_sessions").exists():
        paths.extend(sorted((home / "archived_sessions").rglob("rollout-*.jsonl")))
    return paths


def is_archived_session(home: Path, session_path: Path) -> bool:
    try:
        session_path.relative_to(home / "archived_sessions")
        return True
    except ValueError:
        return False


def first_payload(items: list[dict[str, Any]], item_type: str) -> dict[str, Any]:
    for item in items:
        if item.get("type") == item_type and isinstance(item.get("payload"), dict):
            return item["payload"]
    return {}


def summarize_session_file(home: Path, session_path: Path) -> dict[str, Any]:
    items = read_jsonl(session_path)
    meta = first_payload(items, "session_meta")
    turn_contexts = [
        item.get("payload", {})
        for item in items
        if item.get("type") == "turn_context" and isinstance(item.get("payload"), dict)
    ]
    session_id = meta.get("id") or extract_thread_id(session_path)
    cwd = None
    for context in turn_contexts:
        if context.get("cwd"):
            cwd = context["cwd"]
            break
    if not cwd:
        cwd = meta.get("cwd")
    sandbox_policy = None
    approval_mode = None
    for context in turn_contexts:
        if sandbox_policy is None and context.get("sandbox_policy") is not None:
            sandbox_policy = json.dumps(context["sandbox_policy"], ensure_ascii=False)
        if approval_mode is None and context.get("approval_policy") is not None:
            approval_mode = context["approval_policy"]
    timestamps = [item.get("timestamp") for item in items if item.get("timestamp")]
    return {
        "id": session_id,
        "session_path": str(session_path),
        "archived": is_archived_session(home, session_path),
        "cwd": cwd,
        "source": meta.get("source"),
        "cli_version": meta.get("cli_version"),
        "model_provider": meta.get("model_provider"),
        "session_meta_timestamp": meta.get("timestamp") or (timestamps[0] if timestamps else None),
        "last_timestamp": timestamps[-1] if timestamps else None,
        "sandbox_policy": sandbox_policy,
        "approval_mode": approval_mode,
    }


def build_catalog(home: Path, include_archived: bool = False, include_sqlite: bool = False) -> dict[str, dict[str, Any]]:
    index_rows = load_session_index(home)
    records: dict[str, dict[str, Any]] = {}
    for sid, row in index_rows.items():
        records[sid] = {
            "id": sid,
            "title": row.get("thread_name"),
            "updated_at": row.get("updated_at"),
            "cwd": None,
            "session_path": None,
            "archived": False,
            "index_entry": row,
            "source": None,
            "cli_version": None,
            "model_provider": None,
            "source_sqlite_row": None,
            "sandbox_policy": None,
            "approval_mode": None,
            "session_meta_timestamp": None,
            "last_timestamp": None,
        }
    files = scan_session_files(home, include_archived)
    files.sort(key=lambda path: (is_archived_session(home, path), str(path)))
    for session_path in files:
        summary = summarize_session_file(home, session_path)
        sid = summary["id"]
        if not sid:
            continue
        record = records.setdefault(
            sid,
            {
                "id": sid,
                "title": None,
                "updated_at": None,
                "cwd": None,
                "session_path": None,
                "archived": False,
                "index_entry": None,
                "source": None,
                "cli_version": None,
                "model_provider": None,
                "source_sqlite_row": None,
                "sandbox_policy": None,
                "approval_mode": None,
                "session_meta_timestamp": None,
                "last_timestamp": None,
            },
        )
        if record["session_path"] and not record["archived"] and summary["archived"]:
            continue
        record.update(summary)
    if include_sqlite:
        sqlite_rows = load_sqlite_threads(home)
        for sid, row in sqlite_rows.items():
            record = records.setdefault(
                sid,
                {
                    "id": sid,
                    "title": row.get("title"),
                    "updated_at": None,
                    "cwd": row.get("cwd"),
                    "session_path": None,
                    "archived": bool(row.get("archived")),
                    "index_entry": None,
                    "source": row.get("source"),
                    "cli_version": row.get("cli_version"),
                    "model_provider": row.get("model_provider"),
                    "source_sqlite_row": None,
                    "sandbox_policy": row.get("sandbox_policy"),
                    "approval_mode": row.get("approval_mode"),
                    "session_meta_timestamp": None,
                    "last_timestamp": None,
                },
            )
            record["source_sqlite_row"] = row
            if not record.get("cwd"):
                record["cwd"] = row.get("cwd")
            if not record.get("title"):
                record["title"] = row.get("title")
            if bool(row.get("archived")):
                session_path = record.get("session_path")
                if not session_path and row.get("rollout_path"):
                    record["session_path"] = row.get("rollout_path")
                    record["archived"] = True
                elif session_path:
                    try:
                        Path(session_path).relative_to(home / "archived_sessions")
                        record["archived"] = True
                    except ValueError:
                        pass
    return records


def detect_path_style(value: str) -> str:
    if value.startswith("\\\\") or value.startswith("\\\\?\\") or re.match(r"^[a-zA-Z]:\\", value):
        return "windows"
    return "posix"


def parent_path(value: str, levels: int) -> str:
    current: PureWindowsPath | PurePosixPath
    current = PureWindowsPath(value) if detect_path_style(value) == "windows" else PurePosixPath(value)
    for _ in range(max(levels, 0)):
        current = current.parent
    return str(current)


def validate_path_rules(path_rules: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    for idx, rule in enumerate(path_rules):
        rtype = rule.get("type")
        if rtype not in {"exact", "prefix", "parent"}:
            issues.append(f"path_rules[{idx}] has unsupported type: {rtype!r}")
            continue
        if rtype in {"exact", "prefix"} and ("from" not in rule or "to" not in rule):
            issues.append(f"path_rules[{idx}] must include 'from' and 'to'")
        if rtype == "parent":
            if "from" not in rule:
                issues.append(f"path_rules[{idx}] parent rule must include 'from'")
            if "levels" not in rule and "to" not in rule:
                issues.append(f"path_rules[{idx}] parent rule must include 'levels' or 'to'")
    return issues


def apply_path_rules(value: str | None, path_rules: list[dict[str, Any]]) -> str | None:
    if value is None:
        return None
    for rule in [item for item in path_rules if item.get("type") == "exact"]:
        if value == rule["from"]:
            return rule["to"]
    prefix_rules = [item for item in path_rules if item.get("type") == "prefix" and value.startswith(item["from"])]
    if prefix_rules:
        winner = max(prefix_rules, key=lambda item: len(item["from"]))
        return winner["to"] + value[len(winner["from"]) :]
    for rule in [item for item in path_rules if item.get("type") == "parent"]:
        if value == rule["from"]:
            return rule.get("to") or parent_path(value, int(rule.get("levels", 1)))
    return value


def rewrite_session_cwd(session_path: Path, new_cwd: str) -> dict[str, int]:
    items = read_jsonl(session_path)
    counts = {"session_meta": 0, "turn_context": 0}
    for item in items:
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        if item.get("type") == "session_meta" and payload.get("cwd") != new_cwd:
            payload["cwd"] = new_cwd
            item["payload"] = payload
            counts["session_meta"] += 1
        if item.get("type") == "turn_context" and payload.get("cwd") != new_cwd:
            payload["cwd"] = new_cwd
            item["payload"] = payload
            counts["turn_context"] += 1
    write_jsonl(session_path, items)
    return counts


def sanitize_label(value: str | None) -> str:
    if not value:
        return "migration"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return cleaned or "migration"


def create_backup_dir(target_home: Path, label: str | None) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = target_home / "migration_backups" / f"{stamp}-{sanitize_label(label)}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    return backup_dir


def parse_spec(spec_path: Path) -> dict[str, Any]:
    spec = read_json(spec_path)
    if not isinstance(spec, dict):
        raise MigrationError("Spec must be a JSON object")
    mode = spec.get("mode", "copy-missing")
    if mode not in VALID_MODES:
        raise MigrationError(f"Unsupported mode: {mode}")
    path_rules = spec.get("path_rules", [])
    if not isinstance(path_rules, list):
        raise MigrationError("'path_rules' must be a list")
    issues = validate_path_rules(path_rules)
    if issues:
        raise MigrationError("; ".join(issues))
    thread_ids = spec.get("thread_ids", [])
    if thread_ids and not isinstance(thread_ids, list):
        raise MigrationError("'thread_ids' must be a list when provided")
    if mode in {"copy-selected", "replace-selected", "rebind-only"} and not thread_ids:
        raise MigrationError(f"Mode '{mode}' requires 'thread_ids'")
    if "target_home" not in spec:
        raise MigrationError("Spec must include 'target_home'")
    if mode != "rebind-only" and "source_home" not in spec:
        raise MigrationError(f"Mode '{mode}' requires 'source_home'")
    return {
        **spec,
        "mode": mode,
        "include_archived": bool(spec.get("include_archived", False)),
        "update_sqlite": bool(spec.get("update_sqlite", True)),
        "thread_ids": thread_ids,
        "path_rules": path_rules,
    }


def plan_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    mode = spec["mode"]
    source_home = ensure_codex_home(spec.get("source_home") or spec["target_home"])
    target_home = ensure_codex_home(spec["target_home"])
    include_archived = spec["include_archived"]
    source_catalog = build_catalog(source_home, include_archived=include_archived, include_sqlite=True)
    target_catalog = build_catalog(target_home, include_archived=True, include_sqlite=True)
    target_has_sqlite = sqlite_path(target_home).exists()
    selected_ids = sorted(sid for sid in source_catalog if sid not in target_catalog) if mode == "copy-missing" else list(spec["thread_ids"])
    threads: list[dict[str, Any]] = []
    errors: list[str] = []

    for sid in selected_ids:
        source_record = source_catalog.get(sid) if mode != "rebind-only" else target_catalog.get(sid)
        target_record = target_catalog.get(sid)
        if not source_record:
            errors.append(f"Thread not found in source selection: {sid}")
            continue
        source_session_path = Path(source_record["session_path"]) if source_record.get("session_path") else None
        target_session_path = None
        if mode == "rebind-only":
            if target_record and target_record.get("session_path"):
                target_session_path = Path(target_record["session_path"])
        elif source_session_path:
            try:
                target_session_path = target_home / source_session_path.relative_to(source_home)
            except ValueError as exc:
                errors.append(f"Cannot compute relative session path for {sid}: {exc}")
                continue
        else:
            errors.append(f"Thread has no source session file: {sid}")
            continue
        target_cwd = apply_path_rules(source_record.get("cwd"), spec["path_rules"])
        target_index_exists = bool(target_record and target_record.get("index_entry"))
        target_session_exists = bool(target_record and target_record.get("session_path"))
        if mode == "copy-missing":
            copy_action = "copy" if not target_session_exists and not target_index_exists else "skip"
            index_action = "add" if not target_index_exists else "keep"
        elif mode == "copy-selected":
            copy_action = "copy" if not target_session_exists else "skip"
            index_action = "add" if not target_index_exists else "keep"
        elif mode == "replace-selected":
            copy_action = "replace" if target_session_exists else "copy"
            index_action = "replace" if source_record.get("index_entry") else "keep"
        else:
            copy_action = "none"
            index_action = "keep"
        sqlite_action = "upsert" if spec["update_sqlite"] and target_has_sqlite else "none"
        threads.append(
            {
                "id": sid,
                "title": source_record.get("title"),
                "source_archived": bool(source_record.get("archived")),
                "source_session_path": str(source_session_path) if source_session_path else None,
                "target_session_path": str(target_session_path) if target_session_path else None,
                "source_cwd": source_record.get("cwd"),
                "target_cwd": target_cwd,
                "copy_action": copy_action,
                "index_action": index_action,
                "sqlite_action": sqlite_action,
                "target_index_exists": target_index_exists,
                "target_session_exists": target_session_exists,
                "source_index_entry": source_record.get("index_entry"),
                "source_sqlite_row": source_record.get("source_sqlite_row"),
                "source": source_record.get("source"),
                "cli_version": source_record.get("cli_version"),
                "model_provider": source_record.get("model_provider"),
                "sandbox_policy": source_record.get("sandbox_policy"),
                "approval_mode": source_record.get("approval_mode"),
                "session_meta_timestamp": source_record.get("session_meta_timestamp"),
                "last_timestamp": source_record.get("last_timestamp"),
            }
        )
    summary = {
        "selected_threads": len(threads),
        "copy": sum(1 for item in threads if item["copy_action"] == "copy"),
        "replace": sum(1 for item in threads if item["copy_action"] == "replace"),
        "skip": sum(1 for item in threads if item["copy_action"] == "skip"),
        "upsert_sqlite": sum(1 for item in threads if item["sqlite_action"] == "upsert"),
    }
    return {
        "schema_version": 1,
        "generated_at": now_utc_iso(),
        "source_home": str(source_home),
        "target_home": str(target_home),
        "mode": mode,
        "include_archived": include_archived,
        "update_sqlite": spec["update_sqlite"],
        "backup_label": spec.get("backup_label"),
        "path_rules": spec["path_rules"],
        "thread_ids": selected_ids,
        "errors": errors,
        "summary": summary,
        "threads": threads,
    }


def derive_thread_row(thread: dict[str, Any], target_session_path: Path, existing_row: dict[str, Any] | None = None) -> dict[str, Any]:
    source_row = thread.get("source_sqlite_row") or {}
    existing_row = existing_row or {}
    title = source_row.get("title") or thread.get("title") or existing_row.get("title") or thread["id"]
    created_at = (
        source_row.get("created_at")
        or existing_row.get("created_at")
        or parse_iso_to_epoch(thread.get("session_meta_timestamp"))
        or parse_rollout_timestamp(target_session_path)
        or int(target_session_path.stat().st_mtime)
    )
    updated_at = (
        source_row.get("updated_at")
        or existing_row.get("updated_at")
        or parse_iso_to_epoch(thread.get("last_timestamp"))
        or parse_iso_to_epoch((thread.get("source_index_entry") or {}).get("updated_at"))
        or created_at
    )
    archived = 1 if thread.get("source_archived") else 0
    return {
        "id": thread["id"],
        "rollout_path": str(target_session_path),
        "created_at": int(created_at),
        "updated_at": int(updated_at),
        "source": source_row.get("source") or thread.get("source") or existing_row.get("source") or "imported",
        "model_provider": source_row.get("model_provider") or thread.get("model_provider") or existing_row.get("model_provider") or "openai",
        "cwd": thread.get("target_cwd") or existing_row.get("cwd") or source_row.get("cwd"),
        "title": title,
        "sandbox_policy": source_row.get("sandbox_policy") or thread.get("sandbox_policy") or existing_row.get("sandbox_policy") or "{}",
        "approval_mode": source_row.get("approval_mode") or thread.get("approval_mode") or existing_row.get("approval_mode") or "never",
        "tokens_used": int(source_row.get("tokens_used") or existing_row.get("tokens_used") or 0),
        "has_user_event": int(source_row.get("has_user_event") or existing_row.get("has_user_event") or 0),
        "archived": archived,
        "archived_at": source_row.get("archived_at") if archived else None,
        "git_sha": source_row.get("git_sha") or existing_row.get("git_sha"),
        "git_branch": source_row.get("git_branch") or existing_row.get("git_branch"),
        "git_origin_url": source_row.get("git_origin_url") or existing_row.get("git_origin_url"),
        "cli_version": source_row.get("cli_version") or thread.get("cli_version") or existing_row.get("cli_version") or "",
        "first_user_message": source_row.get("first_user_message") or existing_row.get("first_user_message") or title,
        "agent_nickname": source_row.get("agent_nickname") or existing_row.get("agent_nickname"),
        "agent_role": source_row.get("agent_role") or existing_row.get("agent_role"),
        "memory_mode": source_row.get("memory_mode") or existing_row.get("memory_mode") or "enabled",
    }


def upsert_threads_sqlite(home: Path, threads: list[dict[str, Any]], backup_dir: Path | None = None) -> dict[str, Any]:
    db_path = sqlite_path(home)
    if not db_path.exists():
        raise MigrationError(f"Target sqlite file does not exist: {db_path}")
    copied = copy_sqlite_bundle(db_path, backup_dir) if backup_dir is not None else []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    columns = [row["name"] for row in cur.execute("PRAGMA table_info(threads)").fetchall()]
    if not columns:
        conn.close()
        raise MigrationError("Target sqlite does not contain a threads table")
    existing_rows = load_sqlite_threads(home, [thread["id"] for thread in threads])
    ordered_columns = [
        "id",
        "rollout_path",
        "created_at",
        "updated_at",
        "source",
        "model_provider",
        "cwd",
        "title",
        "sandbox_policy",
        "approval_mode",
        "tokens_used",
        "has_user_event",
        "archived",
        "archived_at",
        "git_sha",
        "git_branch",
        "git_origin_url",
        "cli_version",
        "first_user_message",
        "agent_nickname",
        "agent_role",
        "memory_mode",
    ]
    missing = [column for column in ordered_columns if column not in columns]
    if missing:
        conn.close()
        raise MigrationError(f"Target sqlite threads schema is missing columns: {missing}")
    placeholders = ",".join("?" for _ in ordered_columns)
    updates = ",".join(f"{column}=excluded.{column}" for column in ordered_columns[1:])
    sql = (
        f"INSERT INTO threads ({','.join(ordered_columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}"
    )
    written: list[dict[str, Any]] = []
    for thread in threads:
        row = derive_thread_row(thread, Path(thread["target_session_path"]), existing_rows.get(thread["id"]))
        cur.execute(sql, [row[column] for column in ordered_columns])
        written.append({"id": thread["id"], "cwd": row["cwd"], "title": row["title"]})
    conn.commit()
    conn.close()
    return {"sqlite_backup_files": copied, "rows": written}


def backup_file(source: Path, backup_dir: Path, relative_to: Path | None = None) -> Path:
    destination = backup_dir / source.name if relative_to is None else backup_dir / source.relative_to(relative_to)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination
