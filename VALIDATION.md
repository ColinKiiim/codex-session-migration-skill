# Validation

Updated: 2026-03-20

## Verified End-To-End

- `Windows -> Windows`
  - source export
  - transfer as zip
  - isolated import on second Windows machine
  - real import into the second machine's `%USERPROFILE%\.codex`
  - verify script success
  - full Codex restart
  - visible thread in the target Windows Codex UI

- `Windows -> macOS`
  - source export
  - transfer as zip
  - isolated import on macOS
  - real import into target `~/.codex`
  - verify script success
  - full Codex restart
  - visible thread in the target macOS Codex UI

- `macOS -> Windows`
  - source export
  - transfer as zip
  - isolated import on Windows
  - real import into target `%USERPROFILE%\.codex`
  - verify script success
  - full Codex restart
  - visible thread in the target Windows Codex UI

## Verified Supporting Behaviors

- one-shot source-side handoff preparation
- title-fragment thread resolution
- inline `Prompt 1` generation on the source machine
- target-side cleanup prompt generation after a successful import
- checksum failure on tampered bundle
- workspace-path rebinding and SQLite synchronization
- recovery from workspace rename/path drift on Windows

## Not Yet Verified

- `macOS -> macOS`
- archived-thread cross-device bundle transfer

## Claim Boundary

This repository intentionally avoids stronger claims than the evidence supports.

- Cross-device bundle transfer is described as verified only for `win -> win`, `win -> mac`, and `mac -> win`.
- Direct migration and rebind scripts are broader than the bundle validation matrix, but the docs do not overclaim untested host pairings.
