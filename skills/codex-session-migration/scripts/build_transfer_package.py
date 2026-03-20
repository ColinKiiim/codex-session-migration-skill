#!/usr/bin/env python3
"""Build a portable thread-transfer package from the formal skill."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

from codex_bundle_lib import (
    MigrationError,
    ensure_codex_home,
    json_dump,
    render_target_import_prompt,
    write_bundle,
    write_prompt_file,
)


SKILL_ROOT = Path(__file__).resolve().parents[1]


def ignore_names(_dir: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name == "__pycache__":
            ignored.add(name)
        if name.endswith(".pyc"):
            ignored.add(name)
    return ignored


def is_subpath(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def copy_tree_clean(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=ignore_names)


def add_path_to_zip(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
    info = zipfile.ZipInfo(arcname)
    info.create_system = 3
    if path.is_dir():
        if not arcname.endswith("/"):
            info.filename = arcname + "/"
        info.external_attr = 0o755 << 16
        archive.writestr(info, b"")
        return
    info.external_attr = 0o644 << 16
    archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


def zip_tree_posix(source_dir: Path, output_zip: Path) -> None:
    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(output_zip, "w") as archive:
        for path in sorted(source_dir.rglob("*")):
            relative = path.relative_to(source_dir).as_posix()
            add_path_to_zip(archive, path, relative)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-home", required=True, help="Source CODEX_HOME")
    parser.add_argument("--thread-id", required=True, help="Thread id to export into the package")
    parser.add_argument("--package-dir", required=True, help="Output package directory")
    parser.add_argument("--package-zip", required=True, help="Output portable zip file")
    parser.add_argument(
        "--extra-file",
        action="append",
        default=[],
        help="Optional extra file to copy into the package root (repeatable)",
    )
    parser.add_argument(
        "--notes-file",
        action="append",
        default=[],
        help="Backward-compatible alias for --extra-file",
    )
    parser.add_argument(
        "--target-platform",
        choices=["windows", "macos", "linux"],
        help="Optional target platform; when provided, also generate a target import prompt",
    )
    parser.add_argument("--target-package-path", help="Actual or placeholder package zip path on the target machine")
    parser.add_argument("--target-cwd", help="Actual or placeholder target workspace path on the target machine")
    parser.add_argument("--prompt-output", help="Optional path for the generated target prompt")
    args = parser.parse_args()

    source_home = ensure_codex_home(args.source_home)
    package_dir = Path(args.package_dir)
    package_zip = Path(args.package_zip)
    if is_subpath(package_dir, SKILL_ROOT):
        raise MigrationError("package-dir must live outside the formal skill directory")

    if package_dir.exists():
        shutil.rmtree(package_dir)
    (package_dir / "bundle").mkdir(parents=True, exist_ok=True)
    (package_dir / "tooling").mkdir(parents=True, exist_ok=True)

    copy_tree_clean(SKILL_ROOT, package_dir / "tooling" / "codex-session-migration")
    bundle_path = package_dir / "bundle" / f"{args.thread_id}.zip"
    export_result = write_bundle(source_home, args.thread_id, bundle_path)

    copied_files: list[str] = []
    for file_arg in [*args.extra_file, *args.notes_file]:
        file_path = Path(file_arg)
        target_path = package_dir / file_path.name
        shutil.copy2(file_path, target_path)
        copied_files.append(str(target_path))

    prompt_output = None
    prompt_text = None
    if args.target_platform:
        target_package_path = args.target_package_path or f"<replace with actual path to {package_zip.name} on the target machine>"
        target_cwd = args.target_cwd or "<replace with the target workspace path>"
        prompt_text = render_target_import_prompt(
            thread_id=args.thread_id,
            package_zip_path=target_package_path,
            target_cwd=target_cwd,
            target_platform=args.target_platform,
            package_contents=[
                f"bundle/{args.thread_id}.zip",
                "tooling/codex-session-migration/",
                *sorted(Path(path).name for path in copied_files),
            ],
        )
        prompt_output_path = Path(args.prompt_output) if args.prompt_output else package_dir / "target-import-prompt.md"
        write_prompt_file(prompt_text, prompt_output_path)
        prompt_output = str(prompt_output_path)

    zip_tree_posix(package_dir, package_zip)
    print(
        json_dump(
            {
                "status": "ok",
                "package_dir": str(package_dir),
                "package_zip": str(package_zip),
                "bundle_path": str(bundle_path),
                "thread_id": args.thread_id,
                "export": export_result,
                "copied_files": copied_files,
                "prompt_output": prompt_output,
                "prompt_text": prompt_text,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
