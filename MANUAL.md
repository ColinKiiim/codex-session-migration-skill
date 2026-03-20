# Operation Manual

## What To Open First

If you found this repository and want to install or use the skill, start with this file.

## Option A: Ask Codex To Install Directly From GitHub

Based on Codex's built-in skill installer flow, Codex can install a skill directly from a GitHub repo/path.

Repository:

- `ColinKiiim/codex-session-migration-skill`

Skill path:

- `skills/codex-session-migration`

### Prompt For Another Computer's Codex

Send this directly to the Codex on the target computer:

```text
请使用 $skill-installer 从 GitHub 安装一个 Codex skill。

已知信息：
1. GitHub 仓库是：
   `ColinKiiim/codex-session-migration-skill`
2. skill 在仓库中的路径是：
   `skills/codex-session-migration`

你的任务：
1. 从这个 GitHub repo/path 安装该 skill
2. 安装完成后告诉我 skill 被安装到了哪个本地路径
3. 提醒我重启 Codex 以加载新技能
4. 如果安装失败，先告诉我失败原因，不要自己猜别的来源
```

### Expected Result

If direct GitHub install works, the target Codex should install the skill into its local `CODEX_HOME/skills/` directory and then ask the user to restart Codex.

## Option B: Manual Fallback If Direct GitHub Install Fails

Use this fallback if:

- the target Codex cannot install directly from GitHub
- network restrictions prevent repo download
- the user prefers manual download/copy

### What The User Should Download

Download this repository, then locate this folder inside it:

- `skills/codex-session-migration`

That is the only folder that needs to be copied for manual installation.

### Manual Fallback Prompt

If the user has already downloaded the repository to the target machine, send this to the target computer's Codex after replacing the placeholder path:

```text
我已经把这个 GitHub 仓库下载并解压到本机了。

请帮我安装其中的 skill。已知信息：
1. 仓库本地路径是：
   <把这里替换成这台电脑上仓库解压后的实际路径>
2. 需要安装的 skill 子目录是：
   `skills/codex-session-migration`

你的任务：
1. 先检查这个本地仓库路径是否存在
2. 找到 `<仓库路径>\\skills\\codex-session-migration`
3. 把这个 skill 安装到本机的 `CODEX_HOME/skills/` 下
4. 告诉我实际安装到了哪个路径
5. 提醒我重启 Codex
6. 如果路径不存在或安装失败，先停止并告诉我失败点
```

## What This Skill Can Do

This skill supports:

- migration between different `CODEX_HOME` directories
- rebind-only fixes inside one existing `CODEX_HOME`
- workspace-path repair after folder rename or move
- bundle-based cross-device transfer

## Validation Boundary

Before using the skill for a critical migration, read:

- [VALIDATION.md](VALIDATION.md)

The current verified end-to-end pairings are:

- `Windows -> Windows`
- `Windows -> macOS`
- `macOS -> Windows`

The following are still intentionally unverified:

- `macOS -> macOS`
- archived-thread cross-device bundle transfer
