# Install

## GitHub Repo/Path Install

This repository is laid out so the skill can be installed from:

- repo: `<owner>/<repo>`
- path: `skills/codex-session-migration`

Using Codex's GitHub-based skill installer flow, the equivalent install target is:

```text
skills/codex-session-migration
```

## Resulting Local Layout

After installation, the target machine should have:

```text
<CODEX_HOME>
  skills/
    codex-session-migration/
      SKILL.md
      agents/
      assets/
      references/
      scripts/
```

## Typical `CODEX_HOME`

- Windows: `%USERPROFILE%\.codex`
- macOS: `~/.codex`
- Linux: `~/.codex`

## Manual Fallback Install

If needed, the skill folder can still be copied manually:

1. Copy `skills/codex-session-migration/`
2. Paste it into `<CODEX_HOME>/skills/`
3. Restart Codex

## Notes

- The repository root docs are for humans.
- The actual installable skill is only the folder at `skills/codex-session-migration/`.
- For cross-device transfer, unknown target-machine paths should remain placeholders until the user provides real values.
