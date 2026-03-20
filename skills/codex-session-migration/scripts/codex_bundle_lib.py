#!/usr/bin/env python3
"""Bundle-based Codex thread transfer helpers."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from codex_migration_lib import (
    MigrationError,
    backup_file,
    create_backup_dir,
    ensure_codex_home,
    json_dump,
    load_session_index,
    load_sqlite_threads,
    read_jsonl,
    rewrite_session_cwd,
    summarize_session_file,
    sqlite_path,
    upsert_threads_sqlite,
    write_json,
    write_session_index,
)


REQUIRED_BUNDLE_FILES = {
    "manifest.json",
    "session.jsonl",
    "index-entry.json",
    "thread-row.json",
    "checksums.json",
}


def json_bytes(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def relative_session_path_as_posix(home: Path, session_path: Path) -> str:
    return session_path.relative_to(home).as_posix()


def bundle_session_path_from_manifest(manifest: dict[str, Any]) -> Path:
    rel = manifest.get("source_session_relative_path")
    if not rel:
        raise MigrationError("Bundle manifest is missing source_session_relative_path")
    return Path(*PurePosixPath(rel).parts)


def find_session_candidates_for_thread(home: Path, thread_id: str) -> list[Path]:
    pattern = f"rollout-*{thread_id}.jsonl"
    candidates: list[Path] = []
    if (home / "sessions").exists():
        candidates.extend(sorted((home / "sessions").rglob(pattern)))
    if (home / "archived_sessions").exists():
        candidates.extend(sorted((home / "archived_sessions").rglob(pattern)))
    candidates.sort(key=lambda path: (path.parts[0] if path.parts else "", str(path)))
    return candidates


def build_export_record(home: Path, thread_id: str) -> dict[str, Any]:
    index_entry = load_session_index(home).get(thread_id)
    sqlite_row = load_sqlite_threads(home, [thread_id]).get(thread_id) if sqlite_path(home).exists() else None
    record: dict[str, Any] = {
        "id": thread_id,
        "title": (index_entry or {}).get("thread_name") or (sqlite_row or {}).get("title"),
        "updated_at": (index_entry or {}).get("updated_at"),
        "cwd": (sqlite_row or {}).get("cwd"),
        "session_path": None,
        "archived": bool((sqlite_row or {}).get("archived")),
        "index_entry": index_entry,
        "source": (sqlite_row or {}).get("source"),
        "cli_version": (sqlite_row or {}).get("cli_version"),
        "model_provider": (sqlite_row or {}).get("model_provider"),
        "source_sqlite_row": sqlite_row,
        "sandbox_policy": (sqlite_row or {}).get("sandbox_policy"),
        "approval_mode": (sqlite_row or {}).get("approval_mode"),
        "session_meta_timestamp": None,
        "last_timestamp": None,
    }

    errors: list[str] = []
    for session_path in find_session_candidates_for_thread(home, thread_id):
        try:
            summary = summarize_session_file(home, session_path)
        except json.JSONDecodeError as exc:
            errors.append(f"{session_path}: {exc}")
            continue
        if summary.get("id") and summary["id"] != thread_id:
            errors.append(f"{session_path}: mismatched session id {summary['id']}")
            continue
        record.update(summary)
        break

    if not record.get("session_path"):
        if errors:
            raise MigrationError(
                "Thread session file(s) were found but could not be parsed for export:\n- "
                + "\n- ".join(errors)
            )
        raise MigrationError(f"Thread has no session file: {thread_id}")
    return record


def build_export_payload(home: Path, thread_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], bytes]:
    record = build_export_record(home, thread_id)
    session_path = Path(record["session_path"])
    session_bytes = session_path.read_bytes()
    index_entry = record.get("index_entry") or {
        "id": thread_id,
        "thread_name": record.get("title") or thread_id,
        "updated_at": record.get("updated_at"),
    }
    thread_row = record.get("source_sqlite_row") or {}
    manifest = {
        "schema_version": 1,
        "thread_id": thread_id,
        "thread_title": record.get("title"),
        "exported_at": record.get("last_timestamp"),
        "source_home": str(home),
        "source_cwd": record.get("cwd"),
        "source_archived": bool(record.get("archived")),
        "source_session_relative_path": relative_session_path_as_posix(home, session_path),
        "source_index_present": record.get("index_entry") is not None,
        "source_sqlite_present": bool(thread_row),
        "source": record.get("source"),
        "cli_version": record.get("cli_version"),
        "model_provider": record.get("model_provider"),
        "session_meta_timestamp": record.get("session_meta_timestamp"),
        "last_timestamp": record.get("last_timestamp"),
    }
    return manifest, index_entry, thread_row, session_bytes


def write_bundle(home: Path, thread_id: str, bundle_path: Path) -> dict[str, Any]:
    manifest, index_entry, thread_row, session_bytes = build_export_payload(home, thread_id)
    files = {
        "manifest.json": json_bytes(manifest),
        "session.jsonl": session_bytes,
        "index-entry.json": json_bytes(index_entry),
        "thread-row.json": json_bytes(thread_row),
    }
    checksum_payload = {
        "algorithm": "sha256",
        "files": {name: sha256_bytes(payload) for name, payload in files.items()},
    }
    files["checksums.json"] = json_bytes(checksum_payload)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return {
        "status": "ok",
        "bundle_path": str(bundle_path),
        "thread_id": thread_id,
        "source_cwd": manifest.get("source_cwd"),
    }


def load_bundle(bundle_path: Path) -> dict[str, Any]:
    if not bundle_path.exists():
        raise MigrationError(f"Bundle does not exist: {bundle_path}")
    with zipfile.ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
        missing = sorted(REQUIRED_BUNDLE_FILES - names)
        if missing:
            raise MigrationError(f"Bundle is missing files: {missing}")
        payloads = {name: archive.read(name) for name in REQUIRED_BUNDLE_FILES}

    checksums = json.loads(payloads["checksums.json"].decode("utf-8"))
    expected = checksums.get("files") or {}
    for name in REQUIRED_BUNDLE_FILES - {"checksums.json"}:
        digest = sha256_bytes(payloads[name])
        if expected.get(name) != digest:
            raise MigrationError(f"Checksum mismatch for {name}")

    manifest = json.loads(payloads["manifest.json"].decode("utf-8"))
    index_entry = json.loads(payloads["index-entry.json"].decode("utf-8"))
    thread_row = json.loads(payloads["thread-row.json"].decode("utf-8"))
    bundle_thread_id = manifest.get("thread_id")
    if index_entry.get("id") and bundle_thread_id and index_entry["id"] != bundle_thread_id:
        raise MigrationError("Bundle thread id mismatch between manifest and index-entry")
    if thread_row.get("id") and bundle_thread_id and thread_row["id"] != bundle_thread_id:
        raise MigrationError("Bundle thread id mismatch between manifest and thread-row")
    return {
        "manifest": manifest,
        "index_entry": index_entry,
        "thread_row": thread_row,
        "session_bytes": payloads["session.jsonl"],
    }


def collect_session_cwds(session_path: Path) -> list[str]:
    values = []
    for item in read_jsonl(session_path):
        payload = item.get("payload")
        if item.get("type") in {"session_meta", "turn_context"} and isinstance(payload, dict) and payload.get("cwd"):
            values.append(payload["cwd"])
    return sorted(set(values))


def build_import_thread(
    manifest: dict[str, Any],
    index_entry: dict[str, Any],
    thread_row: dict[str, Any],
    target_session_path: Path,
    target_cwd: str,
) -> dict[str, Any]:
    return {
        "id": manifest["thread_id"],
        "title": manifest.get("thread_title"),
        "source_archived": bool(manifest.get("source_archived")),
        "target_session_path": str(target_session_path),
        "target_cwd": target_cwd,
        "source_sqlite_row": thread_row,
        "source": manifest.get("source"),
        "cli_version": manifest.get("cli_version"),
        "model_provider": manifest.get("model_provider"),
        "sandbox_policy": thread_row.get("sandbox_policy"),
        "approval_mode": thread_row.get("approval_mode"),
        "session_meta_timestamp": manifest.get("session_meta_timestamp"),
        "last_timestamp": manifest.get("last_timestamp"),
        "source_index_entry": index_entry,
    }


def import_bundle(
    bundle_path: Path,
    target_home: Path,
    target_cwd: str,
    allow_replace: bool = False,
) -> dict[str, Any]:
    bundle = load_bundle(bundle_path)
    manifest = bundle["manifest"]
    index_entry = bundle["index_entry"]
    thread_row = bundle["thread_row"]

    target_home = ensure_codex_home(target_home)
    relative_session_path = bundle_session_path_from_manifest(manifest)
    target_session_path = target_home / relative_session_path
    if target_session_path.exists() and not allow_replace:
        raise MigrationError(f"Target session path already exists: {target_session_path}")

    backup_dir = create_backup_dir(target_home, f"bundle-import-{manifest['thread_id']}")
    import_manifest = {
        "schema_version": 1,
        "bundle_path": str(bundle_path.resolve()),
        "target_home": str(target_home),
        "thread_id": manifest["thread_id"],
        "target_cwd": target_cwd,
        "target_session_path": str(target_session_path),
        "created_session_files": [],
        "overwritten_session_backups": [],
        "session_index_backup": None,
        "sqlite_backup_files": [],
    }

    session_index_path = target_home / "session_index.jsonl"
    if session_index_path.exists():
        import_manifest["session_index_backup"] = str(backup_file(session_index_path, backup_dir).resolve())

    target_session_path.parent.mkdir(parents=True, exist_ok=True)
    if target_session_path.exists():
        backup_path = backup_file(target_session_path, backup_dir / "overwritten_sessions", target_home)
        import_manifest["overwritten_session_backups"].append(
            {"original": str(target_session_path), "backup": str(backup_path)}
        )
    else:
        import_manifest["created_session_files"].append(str(target_session_path))

    target_session_path.write_bytes(bundle["session_bytes"])
    rewrite_session_cwd(target_session_path, target_cwd)

    target_index = load_session_index(target_home)
    target_index[manifest["thread_id"]] = index_entry
    write_session_index(target_home, target_index)

    sqlite_rows = []
    if sqlite_path(target_home).exists():
        thread = build_import_thread(manifest, index_entry, thread_row, target_session_path, target_cwd)
        sqlite_backup_dir = backup_dir / "sqlite_before"
        sqlite_backup_dir.mkdir(parents=True, exist_ok=True)
        result = upsert_threads_sqlite(target_home, [thread], sqlite_backup_dir)
        import_manifest["sqlite_backup_files"] = result.get("sqlite_backup_files", [])
        sqlite_rows = result.get("rows", [])

    manifest_path = backup_dir / "import_manifest.json"
    write_json(manifest_path, import_manifest)
    return {
        "status": "ok",
        "thread_id": manifest["thread_id"],
        "target_session_path": str(target_session_path),
        "backup_dir": str(backup_dir),
        "manifest_path": str(manifest_path),
        "sqlite_rows": sqlite_rows,
    }


def verify_bundle_import(bundle_path: Path, target_home: Path, target_cwd: str) -> dict[str, Any]:
    bundle = load_bundle(bundle_path)
    manifest = bundle["manifest"]
    target_home = ensure_codex_home(target_home)
    target_session_path = target_home / bundle_session_path_from_manifest(manifest)

    target_index = load_session_index(target_home)
    sqlite_rows = load_sqlite_threads(target_home, [manifest["thread_id"]]) if sqlite_path(target_home).exists() else {}
    sqlite_row = sqlite_rows.get(manifest["thread_id"])
    session_cwds = collect_session_cwds(target_session_path) if target_session_path.exists() else []
    check = {
        "thread_id": manifest["thread_id"],
        "target_session_path": str(target_session_path),
        "file_exists": target_session_path.exists(),
        "index_exists": manifest["thread_id"] in target_index,
        "session_cwds": session_cwds,
        "sqlite_row_exists": sqlite_row is not None,
        "sqlite_cwd": sqlite_row.get("cwd") if sqlite_row else None,
        "expected_cwd": target_cwd,
    }

    failures = []
    if not check["file_exists"]:
        failures.append("session file missing")
    if not check["index_exists"]:
        failures.append("session index entry missing")
    if session_cwds != [target_cwd]:
        failures.append("session cwd mismatch")
    if sqlite_path(target_home).exists():
        if sqlite_row is None:
            failures.append("sqlite row missing")
        elif sqlite_row.get("cwd") != target_cwd:
            failures.append("sqlite cwd mismatch")

    return {"status": "ok" if not failures else "failed", "check": check, "failures": failures}


def rollback_bundle_import(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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

    return {"status": "ok", "restored": restored}


def create_minimal_target_home(source_home: Path, target_home: Path) -> dict[str, Any]:
    source_home = ensure_codex_home(source_home)
    target_home = Path(target_home)
    if target_home.exists():
        shutil.rmtree(target_home)
    (target_home / "sessions").mkdir(parents=True, exist_ok=True)
    (target_home / "session_index.jsonl").write_text("", encoding="utf-8")

    source_db = sqlite_path(source_home)
    if source_db.exists():
        conn_src = sqlite3.connect(source_db)
        cur_src = conn_src.cursor()
        row = cur_src.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='threads'"
        ).fetchone()
        conn_src.close()
        if row and row[0]:
            conn_dst = sqlite3.connect(target_home / "state_5.sqlite")
            cur_dst = conn_dst.cursor()
            cur_dst.execute(row[0])
            conn_dst.commit()
            conn_dst.close()
    return {"status": "ok", "target_home": str(target_home)}


def default_real_home_hint(target_platform: str) -> str:
    mapping = {
        "windows": r"%USERPROFILE%\.codex",
        "macos": "~/.codex",
        "linux": "~/.codex",
    }
    return mapping[target_platform]


def default_isolated_home_hint(target_platform: str) -> str:
    mapping = {
        "windows": r"%TEMP%\codex-bundle-target-test",
        "macos": "~/codex-bundle-target-test",
        "linux": "~/codex-bundle-target-test",
    }
    return mapping[target_platform]


def target_platform_label(target_platform: str) -> str:
    mapping = {
        "windows": "Windows",
        "macos": "Mac",
        "linux": "Linux",
    }
    return mapping[target_platform]


def is_placeholder_value(value: str) -> bool:
    if not value:
        return True
    markers = ("REPLACE_WITH", "YOUR_NAME", "ACTUAL_FOLDER", "TARGET_WORKSPACE", "<", ">")
    return any(marker in value for marker in markers)


def render_known_or_placeholder(value: str, placeholder: str) -> str:
    if is_placeholder_value(value):
        return placeholder
    return f"`{value}`"


def render_target_import_prompt(
    *,
    thread_id: str,
    package_zip_path: str,
    target_cwd: str,
    target_platform: str,
    package_contents: list[str] | None = None,
    real_home_hint: str | None = None,
    isolated_home_hint: str | None = None,
) -> str:
    real_home = real_home_hint or default_real_home_hint(target_platform)
    isolated_home = isolated_home_hint or default_isolated_home_hint(target_platform)
    platform_label = target_platform_label(target_platform)
    contents = package_contents or [f"bundle/{thread_id}.zip", "tooling/codex-session-migration/"]
    contents_block = "\n".join(f"- `{item}`" for item in contents)
    package_display = render_known_or_placeholder(
        package_zip_path,
        f"<把这里替换成目标{platform_label}电脑上这个 zip 的实际路径>",
    )
    target_cwd_display = render_known_or_placeholder(
        target_cwd,
        f"<把这里替换成目标{platform_label}电脑上的实际工作目录>",
    )
    return "\n".join(
        [
            f"请帮我做一次 Codex 线程的 {platform_label} 目标机导入测试，然后在隔离测试成功后继续导入到这台机器的真实 `{real_home}`。",
            "",
            "开始前请注意：",
            "- 如果下面“测试包路径”或“目标工作目录”仍然是尖括号占位提示，请先替换成真实值再发送。",
            "- 测试包可以放在你方便的位置，不一定是桌面。",
            "- 如果下面的路径和你的实际环境不一致，以你自己的真实路径为准。",
            "",
            "已知信息：",
            "1. 测试包路径：",
            package_display,
            "",
            "2. 目标工作目录：",
            target_cwd_display,
            "",
            "3. 这个测试包里包含：",
            contents_block,
            "",
            "你的任务：",
            f"1. 先确认真实 `{real_home}` 存在",
            "2. 先确认目标工作目录存在",
            "3. 先解压这个测试包到一个临时目录",
            f"4. 不要直接修改真实 `{real_home}`",
            f"5. 先用测试包里的 `tooling/codex-session-migration/scripts/prepare_minimal_target_home.py` 创建一个临时 target `CODEX_HOME`，例如 `{isolated_home}`",
            f"6. 把 `bundle/{thread_id}.zip` 导入到这个临时 target `CODEX_HOME`",
            "7. 导入时把线程 `cwd` 绑定到我给你的目标路径",
            "8. 导入后运行验证脚本",
            "9. 如果隔离测试成功：",
            f"- 先备份真实 `{real_home}`",
            f"- 再把同一个 bundle 导入到真实 `{real_home}`",
            "- 再运行验证脚本",
            "10. 最后告诉我：",
            "- 你实际解压到哪里",
            "- 你实际执行了哪些命令",
            "- 隔离导入的输出",
            "- 隔离验证的输出",
            "- 真实导入前的备份放在哪里",
            "- 真实导入的输出",
            "- 真实验证的输出",
            "- 是否成功",
            "- 是否建议我完全重启 Codex 查看 UI",
            "11. 如果真实导入和验证都成功，请留在这个同一个对话里，等我确认重启后的 UI 成功后，再帮我生成一份“安全清理 prompt”。那份清理 prompt 必须使用你这次实际用到的目标机路径，而不是猜测路径。",
            "",
            "重要要求：",
            "- 如果“测试包路径”或“目标工作目录”仍然是占位值，先停下来让我补真实路径，不要自己猜默认目录。",
            "- 第一阶段必须先做隔离测试",
            f"- 如果隔离测试失败，先停止，不要继续写真实 `{real_home}`",
            "- 不要猜测路径，先自行检查",
            f"- 如果脚本启动失败，可以在临时解压目录里的 `tooling/codex-session-migration/scripts/` 范围内修复，但不要修改真实 `{real_home}`",
            "- 如果你修了临时工具脚本，必须告诉我：",
            "  - 改了哪个文件",
            "  - 改了什么",
            "  - 为什么这样改",
            "  - 改完后怎么验证的",
            "",
        ]
    )


def render_cleanup_prompt(
    *,
    thread_id: str,
    target_cwd: str,
    extract_dir: str,
    isolated_home: str,
    real_home: str,
    real_import_backup_dir: str,
    external_backup_dir: str | None = None,
    bundle_zip_path: str | None = None,
) -> str:
    lines = [
        "请基于你刚刚完成的那次 bundle 导入记录，帮我做一次“迁移成功后的安全清理”。",
        "",
        "前提：",
        "1. 我已经完全重启过 Codex",
        f"2. 我已经确认线程 `{thread_id}` 能在 `{target_cwd}` 下正常看到并打开",
        "3. 这次只做“安全可删”的清理，不做激进删除",
        "",
        "这次清理目标：",
        f"1. 删除临时解压目录：\n   `{extract_dir}`",
        f"2. 删除隔离测试用的临时 target CODEX_HOME：\n   `{isolated_home}`",
        "",
        "这次不要删除：",
        f"1. 不要删除真实 `{real_home}` 下的任何现有会话数据",
        f"2. 不要删除真实导入留下的：\n   `{real_import_backup_dir}`",
    ]
    if external_backup_dir:
        lines.append(f"3. 不要删除外部完整备份：\n   `{external_backup_dir}`")
    if bundle_zip_path:
        lines.append(f"4. 不要删除 bundle zip，除非你先问我：\n   `{bundle_zip_path}`")
    else:
        lines.append("4. 不要删除 bundle zip，除非你先问我")
    lines.extend(
        [
            "",
            "你的任务顺序：",
            "1. 先检查上面两个临时路径是否存在",
            "2. 如果存在，就删除它们",
            "3. 删除后再次检查，确认它们已不存在",
            "4. 最后告诉我：",
            "- 你实际执行了哪些命令",
            "- 哪些路径原本存在",
            "- 哪些路径已成功删除",
            "- 哪些备份被保留了",
            "- 是否还有你认为可以删、但这次按要求没有删除的文件",
            "",
            "重要要求：",
            "- 如果任何一步发现这些路径和你刚刚迁移记录中的路径不一致，先停止并告诉我",
            "- 不要猜测路径",
            "- 不要删除任何完整 `.codex` 备份或真实导入产生的 `migration_backups`",
            "- 不要删除 bundle zip，除非我明确要求",
        ]
    )
    return "\n".join(lines) + "\n"


def write_prompt_file(prompt_text: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt_text, encoding="utf-8")
    return output_path
