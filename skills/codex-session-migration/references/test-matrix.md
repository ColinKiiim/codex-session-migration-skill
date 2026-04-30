# Test Matrix

Use this matrix when validating the skill.

## Host Pairings

- Windows -> Windows
- Windows -> macOS
- WSL -> Windows
- macOS -> Windows
- macOS -> macOS
- Windows -> WSL
- WSL -> WSL

## Operation Modes

- copy-missing
- copy-selected
- replace-selected
- rebind-only
- single-thread bundle export
- single-thread bundle import
- transfer-package handoff
- post-success cleanup prompt generation
- title-fragment thread resolution
- one-shot source-side handoff preparation
- session index drift repair
- sidebar remark-name preservation from an older index backup
- workspace-scoped `updated_at` promotion
- metadata-only thread search by id/title/cwd/index name
- direct same-home multi-thread rebind
- malformed-session diagnosis without aborting unrelated repairs
- post-rebind binding verification

## Thread States

- active thread
- archived thread
- thread with missing index entry
- thread with missing sqlite row
- thread with duplicate index entries
- thread visible in data layers but not visible in the recent sidebar window
- malformed or truncated JSONL session file
- valid target thread in a home that also contains unrelated malformed session files

## Path Cases

- Windows drive path
- `/mnt/<drive>/...`
- WSL UNC path
- native Linux home path
- Unicode path segment
- macOS path with Chinese workspace segments

## Validation Checks

- session file exists in target
- `session_index.jsonl` contains the thread id
- sqlite `threads` row exists when sqlite is present
- JSONL `cwd` matches planned `cwd`
- sqlite `cwd` matches planned `cwd`
- rollback can restore the target state
- bundle checksum validation fails on tampered bundle
- portable transfer package contains the bundle plus the skill tooling
- transfer-package builder returns inline prompt text in command output
- target import prompt can be generated on the source machine
- cleanup prompt is generated on the target machine from actual runtime paths
- normalized title-fragment search tolerates spacing and punctuation differences
- metadata-only search does not parse session JSONL bodies
- malformed session files are reported as warnings with file paths and JSONL line numbers
- direct rebind preserves `session_index.jsonl -> thread_name`
- direct rebind updates JSONL cwd and sqlite cwd for every selected thread
- sidebar recovery reports that Desktop may refresh live before a restart
