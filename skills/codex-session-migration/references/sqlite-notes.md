# SQLite Notes

Desktop visibility can depend on `state_5.sqlite`, not only the JSONL files.

## Why The Skill Updates SQLite

Observed failure mode:

1. Session JSONL is copied correctly
2. `session_index.jsonl` is merged correctly
3. The desktop app still groups the thread under the wrong workspace or does not surface it where expected

The usual reason is a stale row in `state_5.sqlite` -> `threads`.

## What Matters Most

The most important column for workspace grouping is:

- `cwd`

Other useful fields for upsert:

- `rollout_path`
- `title`
- `archived`
- `updated_at`
- `source`
- `cli_version`
- `first_user_message`

## Safety Guidance

- Use transactions.
- Back up the target sqlite file before mutation.
- Do not edit WAL/SHM files directly.
- Fail if the target sqlite schema does not contain `threads`.

## Practical Rule

If the target home has `state_5.sqlite`, assume it needs synchronization unless a dry-run inspection proves the relevant thread rows are already correct.
