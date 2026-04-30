---
name: codex-session-migration
description: Migrate, merge, copy, clone, repair, diagnose, or rebind Codex conversation history between CODEX_HOME directories and workspace paths across Windows, macOS, WSL, and Linux. Use when Codex threads need to be moved between hosts, restored from another .codex directory, merged into a desktop history, searched by id/title/cwd/index name, reclassified under a different cwd, recovered after disappearing from the sidebar or recent-thread window, diagnosed despite malformed or truncated session JSONL files, repaired through session_index.jsonl/state_5.sqlite synchronization, or verified across sessions, session_index.jsonl, and state_5.sqlite.
---

# Codex Session Migration

Use this skill as a scripts-first workflow. Do not manually copy JSONL files and stop there. A reliable migration must inspect and usually synchronize three layers:

1. `sessions/.../*.jsonl`
2. `session_index.jsonl`
3. `state_5.sqlite` -> `threads`

This skill also includes a first-pass bundle workflow for cross-device transfer when the source and target Codex homes are not directly accessible from the same machine.

## Preflight

Inspect both homes first:

```bash
python scripts/inspect_codex_home.py --home "<source-codex-home>"
python scripts/inspect_codex_home.py --home "<target-codex-home>"
```

If inspection reports `skipped_invalid_session_files`, do not let those files block metadata-only repair or unrelated thread migration. Use `diagnose_sessions.py` to list malformed files, then treat those specific threads as a separate recovery problem.

List or diff threads before planning writes:

```bash
python scripts/list_threads.py --home "<source-codex-home>" --include-archived
python scripts/diff_threads.py --source-home "<source-codex-home>" --target-home "<target-codex-home>" --include-archived
```

## Default Workflow

1. Write or adapt a migration spec JSON. Start from `assets/example-migration-spec.json`.
2. Generate a dry-run plan.
3. Review the plan before touching any data.
4. Execute the migration.
5. Verify the result.
6. Check Codex Desktop first, then fully restart Codex if the target app has not refreshed its local state.

Dry-run planning:

```bash
python scripts/plan_migration.py --spec assets/example-migration-spec.json --output plan.json
```

Execution:

```bash
python scripts/migrate_threads.py --plan plan.json --execute
```

Verification:

```bash
python scripts/verify_migration.py --plan plan.json
```

## Rebind-Only Workflow

Use rebind-only when the thread data is already in the target home and only the workspace grouping is wrong.

For one or more known thread ids, prefer the direct same-home rebind script:

```bash
python scripts/rebind_threads.py --home "<codex-home>" --thread-id "<thread-id>" --target-cwd "<new-workspace-cwd>" --promote-to-sidebar
python scripts/rebind_threads.py --home "<codex-home>" --thread-id "<thread-id>" --target-cwd "<new-workspace-cwd>" --promote-to-sidebar --execute
python scripts/verify_thread_binding.py --home "<codex-home>" --cwd "<new-workspace-cwd>" --thread-id "<thread-id>"
```

Pass repeated `--thread-id` values to rebind a small set together. The script preserves `session_index.jsonl -> thread_name`, updates sqlite, rewrites session cwd fields, and emits a `ui_refresh_hint` telling the operator to check the sidebar before restarting.

If the user only gives a title, sidebar remark, or workspace fragment, resolve likely ids without parsing raw JSONL bodies:

```bash
python scripts/search_thread_index.py --home "<codex-home>" --query "<title-or-cwd-fragment>" --format json
```

Use the spec-based `"mode": "rebind-only"` workflow when you need complex path mapping rules or cross-home planning:

If you need to adjust `cwd` without a full migration, use:

```bash
python scripts/rewrite_cwd.py --home "<target-codex-home>" --spec rebind-spec.json --thread-id "<thread-id>"
python scripts/sync_sqlite_threads.py --home "<target-codex-home>" --spec rebind-spec.json --thread-id "<thread-id>" --execute
```

## Sidebar Recovery Workflow

Use this when the user says threads disappeared from the left sidebar inside one existing `CODEX_HOME`.

1. Inspect the three layers first.
2. Repair `session_index.jsonl` if ids are missing or duplicated.
3. Preserve sidebar remark names from an older index backup if needed.
4. Check the Codex Desktop sidebar first. Recent Desktop builds may refresh visible threads without a full restart.
5. If the workspace group still looks empty even though the thread exists in all three layers, test a metadata-only `updated_at` bump for only the newest few matching threads first.
6. Fully restart Codex only if the sidebar does not refresh after the metadata repair or bump.

Dry-run and then execute index repair:

```bash
python scripts/repair_session_index.py --home "<codex-home>" --include-archived
python scripts/repair_session_index.py --home "<codex-home>" --include-archived --name-source-index "<older-index-backup>" --execute
```

Test a small recency bump first:

```bash
python scripts/bump_workspace_updated_at.py --home "<codex-home>" --cwd "<workspace-cwd>" --limit 5 --execute
```

Then promote the whole workspace if the small test works:

```bash
python scripts/bump_workspace_updated_at.py --home "<codex-home>" --cwd "<workspace-cwd>" --execute
```

## Copy vs. Migrate Inside One CODEX_HOME

When both the source and target workspace paths live inside the same `CODEX_HOME`, distinguish between these two intents:

- `copy`: keep the source thread active and create another active thread under the new workspace path.
- `migrate`: create the new target thread first, verify it, then archive the source thread so it leaves the active list but remains recoverable in Codex's archive UI.

Do not archive the source thread until the new target thread has been written and verified.

After a successful same-home migrate, archive the old source thread with:

```bash
python scripts/archive_thread.py --home "<codex-home>" --thread-id "<source-thread-id>" --execute
```

If the user explicitly wants a second active copy of one existing thread under a new thread id and workspace path, use:

```bash
python scripts/clone_thread.py --home "<codex-home>" --source-thread-id "<source-thread-id>" --target-cwd "<target-workspace-cwd>" --execute
```

## Bundle Transfer Workflow

Use the bundle workflow when you need to move one thread between different machines or hosts.

## Interaction Contract

When you use this skill in a conversation, do these things explicitly:

1. Say that you are using `$codex-session-migration`.
2. If the user asks for cross-device transfer, default to the shortest reliable path:
   - resolve the thread
   - use the single-command handoff builder first unless it fails
   - return the bundle path
   - paste `Prompt 1` directly in the reply as a copyable fenced block
3. Do not hide the target import prompt only inside a generated file if you can paste it directly in the response.
4. Do not create extra README-style helper files unless the user asks for them or the workflow truly needs them.
5. For cleanup, do not pre-fill machine-specific temp paths from the source machine. Let the target machine generate `Prompt 2` after a successful import.
6. If the user did not provide the target workspace path, do not silently assume the source path is correct on the other machine. Use an explicit placeholder or state the assumption very clearly.
7. Do not inspect script source code just to rediscover CLI arguments if `--help` or this skill document already covers them.
8. If `build_transfer_package.py` already returns `prompt_text`, paste that directly into the reply instead of reopening the saved prompt file unless you specifically need the file artifact.
9. Do not assume the user will place the transfer zip on the Desktop. If the actual target-machine location is unknown, keep a placeholder and tell the user to replace it with the real path.
10. Do not phrase guessed values as if they are already true. The target package path and target workspace path must be clearly marked as user-supplied unless they were explicitly provided.
11. In `Prompt 1`, prefer a readable label-and-value layout for unknown target-side paths:
   - `1. Package path:`
   - `<replace this with the real path to the zip on the target computer>`
   - `2. Target workspace path:`
   - `<replace this with the real target workspace path on the target computer>`
   Do not wrap unknown placeholder values in misleading prose such as "I will first place the zip..." because that makes the prompt harder to scan.
12. When the request is a straightforward source-side cross-device transfer and `scripts/prepare_transfer_handoff.py` is available, call it first. Do not spend extra turns listing the scripts directory, reading script source, or probing obvious paths unless that one-shot command fails.
13. When repairing sidebar visibility, treat `session_index.jsonl` -> `thread_name` as the sidebar remark label. Do not blindly overwrite it with sqlite `threads.title`.
14. If all three layers already contain the thread but the sidebar workspace group still says "no threads", consider recent-thread window behavior before concluding the data is gone.
15. If raw session parsing fails because one or more JSONL files are malformed, use `search_thread_index.py` for metadata-only lookup and `diagnose_sessions.py` for the malformed-file list. Do not abandon unrelated repair work just because a different session file is truncated.
16. For same-home rebind of known ids, prefer `rebind_threads.py` over hand-chaining `rewrite_cwd.py` and `sync_sqlite_threads.py`; it preserves sidebar names, updates sqlite, and can promote recency in one reviewed dry-run.
17. After metadata-only sidebar recovery, tell the user to check the sidebar first. If the thread is still missing, then ask them to fully restart Codex.

When the user gives a thread title or fragment rather than a thread id, prefer:

```bash
python scripts/search_threads.py --home "<source-codex-home>" --query "<title-fragment>" --format json
```

For the common source-side handoff case, use this single command first instead of manually chaining search + package build:

```bash
python scripts/prepare_transfer_handoff.py --source-home "<source-codex-home>" --query "<title-fragment>" --target-platform windows
```

Avoid exploratory `rg`, raw session-file scans, repeated `--help` calls, or source-code inspection unless the one-shot handoff builder fails or the result is ambiguous.

### Source-Machine Phase

Bundle export only:

```bash
python scripts/export_thread_bundle.py --home "<source-codex-home>" --thread-id "<thread-id>" --output "<bundle-zip>"
```

Portable transfer package:

```bash
python scripts/build_transfer_package.py --source-home "<source-codex-home>" --thread-id "<thread-id>" --package-dir "<package-dir>" --package-zip "<transfer-package-zip>" --target-platform windows --target-package-path "<path-on-target-machine>" --target-cwd "<target-workspace-path>"
```

Preferred one-shot handoff builder:

```bash
python scripts/prepare_transfer_handoff.py --source-home "<source-codex-home>" --query "<thread-title-or-id>" --target-platform windows --target-package-path "<path-on-target-machine>" --target-cwd "<target-workspace-path>"
```

This command already returns the generated target import prompt text in its JSON output. Prefer using that inline instead of separately opening the prompt file unless you need to inspect the saved artifact.

Generate only the target-machine import prompt:

```bash
python scripts/generate_target_import_prompt.py --thread-id "<thread-id>" --target-platform windows --package-path "<path-on-target-machine>" --target-cwd "<target-workspace-path>" --output "<prompt-file>"
```

### Target-Machine Phase

Prepare a disposable target home:

```bash
python scripts/prepare_minimal_target_home.py --source-home "<real-target-codex-home>" --target-home "<temp-target-home>"
```

Import:

```bash
python scripts/import_thread_bundle.py --bundle "<bundle-zip>" --target-home "<target-home>" --target-cwd "<target-workspace-path>" --execute
```

Verify:

```bash
python scripts/verify_bundle_import.py --bundle "<bundle-zip>" --target-home "<target-home>" --target-cwd "<target-workspace-path>"
```

Rollback if needed:

```bash
python scripts/rollback_bundle_import.py --manifest "<import-manifest-json>"
```

### Post-Success Cleanup Prompt

Generate the cleanup prompt on the target machine after the real import succeeds and the user has restarted Codex and confirmed the UI. Do not assume the source machine knows the target machine's actual temporary paths.

```bash
python scripts/generate_cleanup_prompt.py --thread-id "<thread-id>" --target-cwd "<confirmed-target-workspace>" --extract-dir "<actual-extract-dir>" --isolated-home "<actual-temp-home>" --real-home "<real-target-home>" --real-import-backup-dir "<actual-migration-backup-dir>" --external-backup-dir "<optional-full-backup-dir>" --bundle-zip-path "<optional-transfer-package-zip>" --output "<cleanup-prompt-file>"
```

## Rules

- Default to dry-run first.
- Never mutate the source Codex home.
- Always create target-side backups before writing.
- Prefer exact or prefix path rules over ad hoc string replacement.
- Include archived threads only when the user explicitly wants them.
- Treat `state_5.sqlite` synchronization as required for desktop visibility unless inspection proves otherwise.
- For cross-device transfer, prefer generating the target import prompt on the source machine and the cleanup prompt on the target machine.
- Do not delete rollback-capable backups automatically unless the user explicitly asks for aggressive cleanup.
- For same-home relocation, default to `keep-source` for copy and `archive-source` for migrate unless the user explicitly asks for a different retirement policy.
- When adding or changing supported workflows in this skill, update the frontmatter `description`, `agents/openai.yaml`, and relevant repo-level user docs before declaring the update complete.

## References

Open only what is needed:

- Data model: `references/data-model.md`
- Path mapping rules: `references/path-mapping.md`
- SQLite behavior: `references/sqlite-notes.md`
- Sidebar recovery: `references/sidebar-recovery.md`
- Validation coverage: `references/test-matrix.md`

## Scripts

- `scripts/inspect_codex_home.py`
- `scripts/list_threads.py`
- `scripts/search_threads.py`
- `scripts/search_thread_index.py`
- `scripts/diagnose_sessions.py`
- `scripts/repair_session_index.py`
- `scripts/prepare_transfer_handoff.py`
- `scripts/diff_threads.py`
- `scripts/plan_migration.py`
- `scripts/migrate_threads.py`
- `scripts/rebind_threads.py`
- `scripts/rewrite_cwd.py`
- `scripts/sync_sqlite_threads.py`
- `scripts/bump_workspace_updated_at.py`
- `scripts/verify_thread_binding.py`
- `scripts/verify_migration.py`
- `scripts/rollback_from_backup.py`
- `scripts/codex_bundle_lib.py`
- `scripts/export_thread_bundle.py`
- `scripts/import_thread_bundle.py`
- `scripts/prepare_minimal_target_home.py`
- `scripts/verify_bundle_import.py`
- `scripts/rollback_bundle_import.py`
- `scripts/build_transfer_package.py`
- `scripts/generate_target_import_prompt.py`
- `scripts/generate_cleanup_prompt.py`
- `scripts/archive_thread.py`
- `scripts/clone_thread.py`

Use the scripts instead of rewriting migration logic in the prompt.
