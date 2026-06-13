# Projectless To Workspace Move

Use this note when the user wants to move a conversation from the generic "Conversations" or "new chat" area into a project folder.

## Verified Result

Verified on macOS Codex Desktop:

- keeping the original thread id and rebinding its cwd did not move the thread out of the generic "对话" sidebar section, even after the three disk layers agreed and Codex Desktop was restarted
- cloning the same conversation under a new thread id with the target project cwd made the cloned thread appear immediately under the target project
- after the user confirmed the clone was visible, archiving the original thread completed the move while keeping the old thread recoverable

The verified move workflow is:

1. clone to a new id under the target project cwd
2. verify the new clone in the three disk layers
3. ask the user to confirm that the clone is visible under the target project
4. only after that UI confirmation, archive the original thread

Do not call a same-id rebind a successful move from the generic Conversations section into a project. It is still useful as a disk-metadata repair, but it does not change the observed Desktop grouping identity.

## Recognition Cues

Trigger this workflow when the user says things like:

- move this conversation into a project folder
- move the conversation from the "conversation" box to a project
- move a `new-chat` thread into a workspace
- bind this chat to `Codex-Mac`
- cwd is under `Documents/Codex/<date>/new-chat`

## Recommended Order

1. Search the main home by title, id, or generated cwd.
2. If the title is generic, use `cwd`, `updated_at`, and target context to choose the intended source thread.
3. Confirm the target project folder exists.
4. Clone the source thread to the target cwd with a new id. Use the original title unless the user requests a different title.
5. Verify the clone by its new id with `search_thread_index.py` and `verify_thread_binding.py`.
6. Ask the user to confirm that the clone is visible under the target project in Codex Desktop.
7. If the user confirms visibility, dry-run and execute `archive_thread.py` for the original source thread.
8. If the clone is not visible, do not archive the source. Continue diagnosis.

## Commands

Find candidates:

```bash
python scripts/search_thread_index.py --home "~/.codex" --query "<title-or-generated-cwd>" --format json
```

Clone into the project:

```bash
python scripts/clone_thread.py --home "~/.codex" --source-thread-id "<source-thread-id>" --target-cwd "<project-folder-cwd>" --title "<original-or-requested-title>" --execute
```

Verify the new clone:

```bash
python scripts/search_thread_index.py --home "~/.codex" --query "<new-thread-id>" --format json
python scripts/verify_thread_binding.py --home "~/.codex" --cwd "<project-folder-cwd>" --thread-id "<new-thread-id>"
```

After the user confirms the clone is visible:

```bash
python scripts/archive_thread.py --home "~/.codex" --thread-id "<source-thread-id>"
python scripts/archive_thread.py --home "~/.codex" --thread-id "<source-thread-id>" --execute
```

## Why Clone Instead Of Rebind

Observed comparison:

- project thread `测试-ami` cloned from Apple Music Import to `Codex-Mac` appeared immediately
- generic Conversations thread `测试` kept its original id after cwd rebind and remained in the generic section
- cloning that generic thread to a new id as `测试-dialog-clone` made it appear immediately under `Codex-Mac`

This comparison indicates that Desktop grouping for generic conversations is tied to thread identity or creation-time state that is not changed by rewriting the known disk metadata layers.

`clone_thread.py` removes `session_meta.payload.thread_source = "user"` from the cloned session when present. The new sqlite row is created as a normal project-thread row.

## Safety Rules

- Never archive the original before the user confirms the clone is visible in the target project.
- Preserve the original thread until clone verification and UI confirmation both pass.
- Use a new thread id; do not overwrite the source id.
- Prefer the original sidebar title unless the user requests a renamed clone.
- Treat unrelated malformed JSONL warnings as separate issues when the selected source and clone verify successfully.
- Same-id `rebind_threads.py` remains appropriate for ordinary workspace path correction, but not for moving a generic Conversations thread into a project sidebar group.
