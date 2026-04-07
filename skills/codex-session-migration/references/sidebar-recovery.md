# Sidebar Recovery

Use this note when Codex threads appear to be "missing" from the left sidebar even though the raw session files still exist.

## Confirmed Failure Modes

### 1. `session_index.jsonl` drift

Observed repair case:

- session files still existed on disk
- sqlite `threads` rows still existed
- `session_index.jsonl` had both missing ids and duplicate ids
- the sidebar stopped showing some threads

Practical consequence:

- "missing from sidebar" does not automatically mean the thread data is deleted
- the first reliable check is always the three-layer model:
  - `sessions/` and `archived_sessions/`
  - `session_index.jsonl`
  - `state_5.sqlite` -> `threads`

### 2. Sidebar remark names are stored in `session_index.jsonl`

Confirmed distinction:

- sidebar remark-like short names live in `session_index.jsonl` -> `thread_name`
- sqlite `threads.title` may instead hold a long first prompt or another machine-generated title

Practical consequence:

- do not rebuild `session_index.jsonl` by blindly copying sqlite `title` into `thread_name`
- if the user relies on sidebar remark names, preserve existing index names or restore them from an older index backup

### 3. Recent-thread window behavior

Observed repair case:

- all three layers already contained the workspace threads
- the sidebar group still rendered as if the workspace had no threads
- the affected workspace threads were much older than the rest of the recent sidebar entries
- promoting only `updated_at` was enough to make them reappear

Practical consequence:

- some "empty workspace" reports are actually recency-window problems, not missing data
- test by bumping only the newest few matching threads first before rewriting an entire workspace

### 4. Malformed or truncated session files

Observed repair case:

- a few raw session JSONL files were malformed
- naive scripts that tried to parse every session file aborted the whole repair

Practical consequence:

- repair scripts should report malformed session files and skip them instead of crashing the whole dry-run
- keep the skipped file list in the report so the operator can decide whether those specific threads need separate recovery

## Recommended Repair Order

1. Inspect the home with `inspect_codex_home.py`.
2. Dry-run `repair_session_index.py`.
3. If sidebar remark names matter and an older index backup exists, pass it via `--name-source-index`.
4. Execute the index repair.
5. Restart Codex and check the sidebar again.
6. If the workspace group still looks empty even though the threads now exist in all three layers, test `bump_workspace_updated_at.py --limit 5`.
7. If the small test works, repeat without `--limit` for the whole workspace.
8. If the report lists malformed session files, treat them as a separate recovery problem instead of mixing them into the same index rewrite.

## Example Commands

Dry-run index repair:

```bash
python scripts/repair_session_index.py --home "~/.codex" --include-archived
```

Restore sidebar names from an older index backup while repairing the current index:

```bash
python scripts/repair_session_index.py --home "~/.codex" --include-archived --name-source-index "~/.codex/session_index.jsonl.bak-YYYYMMDD-HHMMSS" --execute
```

Test a 5-thread recency promotion for one workspace:

```bash
python scripts/bump_workspace_updated_at.py --home "~/.codex" --cwd "/absolute/workspace/path" --limit 5 --execute
```

Promote the whole workspace after the small test succeeds:

```bash
python scripts/bump_workspace_updated_at.py --home "~/.codex" --cwd "/absolute/workspace/path" --execute
```

## Safety Rules

- Back up `session_index.jsonl` before rewriting it.
- Back up sqlite before changing sqlite-backed metadata.
- Prefer metadata-only repairs first.
- Do not rewrite session content when the problem is only discoverability, naming, or ordering.
