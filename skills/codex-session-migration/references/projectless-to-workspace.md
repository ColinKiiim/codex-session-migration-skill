# Projectless To Workspace Rebind

Use this note when the user wants to move a conversation from the generic "conversation" or "new chat" area into a project folder.

## Confirmed Failure Mode

Observed repair case:

- the target thread existed in the main `~/.codex`
- sqlite had a valid row and session file path
- the thread cwd pointed at a generated projectless folder such as `Documents/Codex/<date>/new-chat`
- `session_index.jsonl` did not contain the thread yet
- after rebind, `rebind_threads.py` created the missing index row using the sqlite title as `thread_name`
- projectless rows may carry sqlite `thread_source = "user"`; when moving them into a project workspace, `rebind_threads.py` clears that value to `NULL` so Desktop can treat the row like other project threads

Practical consequence:

- this is not alternate-home import
- this is not a clone/copy request unless the user explicitly wants a second active copy
- this is a same-home workspace rebind from generated cwd to the real project cwd

## Recognition Cues

Trigger this workflow when the user says things like:

- move this conversation into a project folder
- move the conversation from the "conversation" box to a project
- move a `new-chat` thread into a workspace
- bind this chat to `Codex-Mac`
- cwd is under `Documents/Codex/<date>/new-chat`

## Recommended Order

1. Search the main home by title, id, or generated cwd.
2. If the title is generic, use `cwd`, `updated_at`, and target context to choose the intended thread.
3. Confirm the target project folder exists.
4. Dry-run `rebind_threads.py`.
5. Confirm `before_cwd` is the generated/projectless cwd and `after_cwd` is the real project cwd.
6. Execute `rebind_threads.py --execute`.
7. Verify by id with `search_thread_index.py`.
8. Verify binding with `verify_thread_binding.py`.
9. If the sidebar still does not show the thread, inspect sqlite `thread_source`; for moved projectless conversations it should be `NULL`, not `user`.
10. Check the Codex sidebar first; fully restart Codex only if it does not refresh.

## Commands

Find candidates:

```bash
python scripts/search_thread_index.py --home "~/.codex" --query "<title-or-generated-cwd>" --format json
```

Dry-run and execute:

```bash
python scripts/rebind_threads.py --home "~/.codex" --thread-id "<thread-id>" --target-cwd "<project-folder-cwd>" --promote-to-sidebar
python scripts/rebind_threads.py --home "~/.codex" --thread-id "<thread-id>" --target-cwd "<project-folder-cwd>" --promote-to-sidebar --execute
```

Verify:

```bash
python scripts/search_thread_index.py --home "~/.codex" --query "<thread-id>" --format json
python scripts/verify_thread_binding.py --home "~/.codex" --cwd "<project-folder-cwd>" --thread-id "<thread-id>"
```

## Safety Rules

- Do not use `copy-selected` for a thread already present in the main home unless the user explicitly wants a duplicate.
- Do not use `clone_thread.py` unless the user wants two active copies.
- If `session_index` is missing but sqlite and the session file exist, continue with dry-run; `rebind_threads.py` can create the missing index row.
- For sqlite schemas with a `thread_source` column, do not leave moved projectless conversations as `thread_source = "user"`. Project workspace rows observed in Desktop use `NULL`; `subagent` should still be preserved.
- If the target project path is ambiguous, resolve it before writing.
- Preserve or derive a sidebar name from `session_index.thread_name`, sqlite title, or the thread id in that order.
