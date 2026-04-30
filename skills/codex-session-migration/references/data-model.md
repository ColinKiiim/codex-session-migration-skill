# Data Model

This skill treats a Codex home as a directory that usually contains:

- `session_index.jsonl`
- `sessions/`
- optional `archived_sessions/`
- optional `state_5.sqlite`

For cross-device bundle transfer, this skill also uses a portable bundle zip that contains:

- `manifest.json`
- `session.jsonl`
- `index-entry.json`
- `thread-row.json`
- `checksums.json`

## Migration Layers

### 1. Session files

`sessions/.../*.jsonl` and `archived_sessions/*.jsonl` hold the raw conversation data.

Important fields commonly used by this skill:

- `session_meta.payload.id`
- `session_meta.payload.cwd`
- `session_meta.payload.source`
- `session_meta.payload.cli_version`
- `session_meta.payload.model_provider`
- `turn_context.payload.cwd`
- `turn_context.payload.sandbox_policy`
- `turn_context.payload.approval_policy`

### 2. Session index

`session_index.jsonl` is the thread list entry point. A thread can exist on disk but still be hard to discover in the UI if the index is missing or stale.

Important fields:

- `id`
- `thread_name`
- `updated_at`

Practical note:

- `thread_name` is the safest source of the sidebar remark label.
- sqlite `threads.title` may be a different value, often longer and less user-friendly.
- rebind and index-repair tools should preserve an existing `thread_name` unless the user explicitly wants it renamed.

### 3. SQLite cache

`state_5.sqlite` often contains a `threads` table used by the app for thread metadata and grouping.

Important columns:

- `id`
- `rollout_path`
- `cwd`
- `title`
- `archived`
- `updated_at`
- `source`
- `cli_version`
- `first_user_message`

Practical note:

- `updated_at` in sqlite can affect whether a workspace still appears to have recent threads in the desktop sidebar.
- if sqlite and index both contain the thread but the workspace still looks empty, recency-window behavior is a plausible explanation.
- same-home rebind repairs should update sqlite `cwd` together with session JSONL cwd fields.

## Practical Consequence

A reliable migration usually needs all three layers to agree on:

- thread id
- thread file location
- target `cwd`
- title and archived state

If session files and index are copied but sqlite is not synchronized, the target app may still group the thread under the wrong workspace or fail to surface it until later.

Malformed or truncated session JSONL files are not necessarily evidence that every thread is unusable. Metadata-only operations can still use `session_index.jsonl` and sqlite rows to resolve unrelated thread ids, repair index drift, or report the bad file list for separate recovery.

## Bundle Consequence

The bundle zip is intentionally single-thread scoped.

It is not a full `CODEX_HOME` export. Instead, it captures enough data to recreate one thread in another Codex home and then lets the target-side import synchronize the target index and sqlite cache.

## Practical Search Consequence

When a user refers to a thread by a human-readable title fragment rather than a thread id, the skill should resolve that fragment against the catalog first instead of manually scanning raw files.

If parsing the raw catalog is blocked by malformed JSONL files, use metadata-only lookup against sqlite and `session_index.jsonl` instead.
