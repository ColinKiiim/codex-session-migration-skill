# Path Mapping

Path mapping controls where a migrated thread appears in the target app.

The main field that determines grouping is the thread `cwd`.

## Supported Rule Types

### `exact`

Match one path exactly and replace it with another.

```json
{
  "type": "exact",
  "from": "F:\\old\\child",
  "to": "F:\\old"
}
```

Use this when a single thread should move to a specific folder.

### `prefix`

Replace a leading path prefix.

```json
{
  "type": "prefix",
  "from": "/mnt/d/projects/",
  "to": "D:\\projects\\"
}
```

Use this for broad cross-host translation.

### `parent`

Move a path up one or more levels when it matches exactly.

```json
{
  "type": "parent",
  "from": "F:\\folder\\child\\leaf",
  "levels": 1
}
```

This is a shorthand for rebinding to a parent path without spelling out the final target.

## Precedence

Apply rules in this order:

1. exact
2. longest matching prefix
3. parent

This avoids ambiguous rewrites.

## Common Examples

### Same-machine workspace rename

Use `rebind_path_prefix.py` when a workspace root was renamed or moved inside the same `CODEX_HOME` and multiple sidebar groups now point at stale `cwd` values.

Dry-run first:

```bash
python scripts/rebind_path_prefix.py --home "~/.codex" \
  --map "/Users/alice/OldRoot/开发=/Users/alice/NewRoot/Develop" \
  --map "/Users/alice/OldRoot/NUS=/Users/alice/NewRoot/NUS" \
  --include-archived --promote-to-sidebar --require-target-exists
```

Then execute the same command with `--execute`.

This script updates sqlite `threads.cwd`, `session_index.jsonl` recency, `session_meta.cwd`, `turn_context.cwd`, and nested `turn_context.sandbox_policy` path strings. If a session JSONL file is malformed, it rewrites only parseable metadata lines and preserves malformed lines unchanged.

### WSL mount to Windows

```json
{
  "type": "prefix",
  "from": "/mnt/d/projects/",
  "to": "D:\\projects\\"
}
```

### Linux home to WSL UNC

```json
{
  "type": "prefix",
  "from": "/home/alice/",
  "to": "\\\\wsl.localhost\\Ubuntu\\home\\alice\\"
}
```

### Move one thread to a parent folder

```json
{
  "type": "exact",
  "from": "D:\\projects\\client\\notes",
  "to": "D:\\projects\\client"
}
```

Prefer `exact` over `parent` when the final target needs to be explicit.
