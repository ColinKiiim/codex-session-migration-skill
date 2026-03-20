# Codex Session Migration

GitHub-ready repository layout for the `codex-session-migration` skill.

This repository is structured so the installable skill lives under `skills/codex-session-migration/`, while repository-level documentation stays at the root.

## What This Skill Does

- migrate Codex history between two accessible `CODEX_HOME` directories
- repair or rebind thread workspace grouping when the history is already present
- export and import single-thread bundles for cross-device transfer
- generate source-side handoff prompts and target-side cleanup prompts

## Repository Layout

```text
.
├─ README.md
├─ INSTALL.md
├─ VALIDATION.md
└─ skills/
   └─ codex-session-migration/
      ├─ SKILL.md
      ├─ agents/
      ├─ assets/
      ├─ references/
      └─ scripts/
```

## Verified Pairings

- `Windows -> Windows`
- `Windows -> macOS`
- `macOS -> Windows`

See [VALIDATION.md](VALIDATION.md) for the current claim boundary.

## Install Modes

There are two realistic install paths today:

1. Install from a GitHub repo/path
   - This repository layout is designed for that.
   - The install path would be `skills/codex-session-migration`.

2. Searchable skill-page install inside Codex
   - A public GitHub repo alone does not automatically make the skill appear in the built-in searchable skill catalog.
   - That usually requires the skill to be included in a supported catalog source such as the curated or experimental skill lists used by Codex.

## Next Step After Publishing

Once this repository is pushed to GitHub, the practical install target is:

- repo: `<owner>/<repo>`
- path: `skills/codex-session-migration`

See [INSTALL.md](INSTALL.md) for the exact shape.
