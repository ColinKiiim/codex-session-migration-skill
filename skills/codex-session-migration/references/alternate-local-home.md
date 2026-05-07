# Alternate Local Codex Home

Use this note when the user says a conversation from a newly opened Codex-like instance, Antigravity instance, or alternate local Codex home does not appear in the main Codex Desktop sidebar.

## Confirmed Failure Mode

Observed repair case:

- searching the main `~/.codex` by full workspace cwd returned no matches
- searching the main `~/.codex` by title fragment returned no matches
- inspecting the main home showed healthy `sessions/`, `session_index.jsonl`, and `state_5.sqlite`
- raw session text in the main home did not contain the target workspace path
- the thread existed in an Antigravity/Codex instance home under `.antigravity_cockpit/instances/codex/<instance-id>`

Practical consequence:

- this is not `session_index.jsonl` drift in the main home
- this is not a recent-window or sidebar recency issue in the main home
- the main home cannot be repaired with `rebind_threads.py` or `bump_workspace_updated_at.py` because the thread is not there
- the correct operation is a same-machine cross-home `copy-selected` import from the instance home into the main `~/.codex`

## Recognition Cues

Trigger this workflow when the user says things like:

- a new instance conversation is missing from the main Codex sidebar
- an Antigravity instance conversation is not in the main Codex window
- the instance home is under `.antigravity_cockpit/instances/codex/`
- recover a Codex conversation from another local instance home into `~/.codex`

Common Antigravity/Codex instance home pattern:

```text
/Users/<user>/.antigravity_cockpit/instances/codex/<instance-id>
```

## Recommended Order

1. Search the main home first by full workspace cwd, title, or thread id.
2. If the main home has no match, inspect the main home only to confirm the storage layers are present.
3. Ask for the alternate instance path if the user has not provided it.
4. Inspect the alternate path and confirm it looks like a Codex home.
5. Search the alternate home by full workspace cwd or title.
6. Search the main home by the discovered thread id.
7. If the id is absent from the main home, use `copy-selected`.
8. If the id already exists in the main home, stop and decide whether to skip, replace, or clone. Do not overwrite by default.
9. Verify migration and binding.
10. Check the main Codex sidebar first; fully restart Codex only if the sidebar does not refresh.

## Commands

Search the main home:

```bash
python scripts/search_thread_index.py --home "~/.codex" --query "<workspace-cwd-or-title>" --format json
python scripts/inspect_codex_home.py --home "~/.codex"
```

Inspect and search the alternate instance home:

```bash
python scripts/inspect_codex_home.py --home "<alternate-codex-home>"
python scripts/search_thread_index.py --home "<alternate-codex-home>" --query "<workspace-cwd-or-title>" --format json
```

Confirm the id is absent from the main home:

```bash
python scripts/search_thread_index.py --home "~/.codex" --query "<thread-id>" --format json
```

Create a spec using `copy-selected`:

```json
{
  "source_home": "<alternate-codex-home>",
  "target_home": "~/.codex",
  "mode": "copy-selected",
  "include_archived": false,
  "thread_ids": ["<thread-id>"],
  "path_rules": [],
  "update_sqlite": true,
  "backup_label": "<short-label>"
}
```

Plan, execute, and verify:

```bash
python scripts/plan_migration.py --spec spec.json --output plan.json
python scripts/migrate_threads.py --plan plan.json --execute
python scripts/verify_migration.py --plan plan.json
python scripts/verify_thread_binding.py --home "~/.codex" --cwd "<workspace-cwd>" --thread-id "<thread-id>"
```

## Safety Rules

- Never mutate the alternate source home.
- Do not rebind or promote a thread that is absent from the main home.
- Do not overwrite an existing main-home thread id without an explicit user decision.
- Keep `path_rules` empty when the instance and main home are on the same machine and the workspace cwd should remain unchanged.
- Preserve `thread_name` from the alternate home unless the user asks to rename it.
