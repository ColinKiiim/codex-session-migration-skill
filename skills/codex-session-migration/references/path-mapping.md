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
