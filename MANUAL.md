# Operation Manual

Chinese version below.

## English

## What To Open First

If you found this repository and want to install or use the skill, start with this file.

## Option A: Ask Codex To Install Directly From GitHub

Based on Codex's built-in skill installer flow, Codex can install a skill directly from a GitHub repo/path.

Repository:

- `ColinKiiim/codex-session-migration-skill`

Skill path:

- `skills/codex-session-migration`

### English Prompt For Another Computer's Codex

Send this to the Codex on the target computer if that Codex is operating in an English-language workflow:

```text
Please use $skill-installer to install a Codex skill from GitHub.

Known information:
1. The GitHub repository is:
   `ColinKiiim/codex-session-migration-skill`
2. The skill path inside the repository is:
   `skills/codex-session-migration`

Your task:
1. Install this skill from the GitHub repo/path above.
2. After installation, tell me which local path the skill was installed to.
3. Remind me to restart Codex so the new skill can be loaded.
4. If the first install attempt fails because of a local runtime issue, you may do minimal local environment repair needed to complete the same GitHub install flow. Examples include using a real Python interpreter instead of a broken launcher alias, fixing the certificate path for Python HTTPS requests, or using the installer's git method when appropriate.
5. Do not switch to a different installation source unless you tell me why first.
6. If the GitHub install still fails after reasonable local runtime fixes, stop and tell me the failure reason.
```

### Chinese Prompt For Another Computer's Codex

Send this to the Codex on the target computer if that Codex is operating in a Chinese-language workflow:

```text
请使用 $skill-installer 从 GitHub 安装一个 Codex skill。

已知信息：
1. GitHub 仓库是：
   `ColinKiiim/codex-session-migration-skill`
2. skill 在仓库中的路径是：
   `skills/codex-session-migration`

你的任务：
1. 从上面的 GitHub repo/path 安装这个 skill。
2. 安装完成后，告诉我这个 skill 被安装到了本地哪个路径。
3. 提醒我重启 Codex，以便加载这个新 skill。
4. 如果第一次安装失败是因为本机运行环境问题，你可以做“最小必要”的本地环境修复，以继续完成同一个 GitHub 安装流程。
   例如：改用真实可用的 Python 解释器而不是失效的启动别名、修正 Python HTTPS 请求使用的证书路径、在合适时改用安装器自带的 git 方法。
5. 不要在没有先告诉我的情况下，擅自改用别的安装来源。
6. 如果在做了合理的本地环境修复后，GitHub 安装仍然失败，再停止并告诉我失败原因。
```

### Expected Result

If direct GitHub install works, the target Codex should install the skill into its local `CODEX_HOME/skills/` directory and then ask the user to restart Codex.

## Option B: Manual Fallback If Direct GitHub Install Fails

Use this fallback if:

- the target Codex cannot install directly from GitHub
- network restrictions prevent repo download
- the user prefers manual download and copy

### Common Runtime Blockers Before Falling Back

Before switching to manual fallback, it is reasonable to check a few common local blockers on the target machine:

- `python` points to a broken Windows Store alias instead of a real interpreter
- the available Python cannot validate HTTPS certificates correctly
- git-based fallback is unavailable because `git` is not installed or not on `PATH`

If one of these issues can be repaired locally without changing the installation source, it is usually better to complete the same GitHub install flow first.

### What The User Should Download

Download this repository, then locate this folder inside it:

- `skills/codex-session-migration`

That is the only folder needed for manual installation.

### English Manual Fallback Prompt

Use this prompt if the repository has already been downloaded to the target machine and the target Codex is operating in English:

```text
I have already downloaded and extracted this GitHub repository on this computer.
Please help me install the skill from it.

Known information:
1. The local repository path is:
   <replace this with the real extracted repository path on this computer>
2. The skill subdirectory that should be installed is:
   `skills/codex-session-migration`

Your task:
1. First check whether this local repository path exists.
2. Find `<repo-path>\\skills\\codex-session-migration`.
3. Install that skill into this machine's `CODEX_HOME/skills/`.
4. Tell me the actual path where it was installed.
5. Remind me to restart Codex.
6. If the path does not exist or installation fails, stop and tell me the failure point.
```

### Chinese Manual Fallback Prompt

Use this prompt if the repository has already been downloaded to the target machine and the target Codex is operating in Chinese:

```text
我已经把这个 GitHub 仓库下载并解压到这台电脑上了。
请帮我安装其中的 skill。

已知信息：
1. 仓库在本机上的路径是：
   <把这里替换成这台电脑上仓库解压后的实际路径>
2. 需要安装的 skill 子目录是：
   `skills/codex-session-migration`

你的任务：
1. 先检查这个本地仓库路径是否存在。
2. 找到 `<仓库路径>\\skills\\codex-session-migration`。
3. 把这个 skill 安装到本机的 `CODEX_HOME/skills/` 中。
4. 告诉我实际安装到了哪个路径。
5. 提醒我重启 Codex。
6. 如果路径不存在或安装失败，先停止并告诉我失败点。
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

## 中文

## 先看什么

如果你是第一次来到这个仓库，并且想安装或使用这个 skill，请先看这份手册。

## 方案 A：让 Codex 直接从 GitHub 安装

根据 Codex 内置的 skill installer 流程，Codex 可以直接从 GitHub 的 repo/path 安装 skill。

仓库：

- `ColinKiiim/codex-session-migration-skill`

skill 路径：

- `skills/codex-session-migration`

### 给英文环境 Codex 的提示词

如果目标电脑上的 Codex 更适合英文工作流，可以直接发上面的英文提示词。

### 给中文环境 Codex 的提示词

如果目标电脑上的 Codex 更适合中文工作流，可以直接发上面的中文提示词。

### 预期结果

如果 GitHub 直接安装成功，目标机器上的 Codex 应该会把这个 skill 安装到本地 `CODEX_HOME/skills/` 目录里，然后提醒用户重启 Codex。

## 方案 B：如果 GitHub 直接安装失败，就走手动兜底

以下情况适合走这个方案：

- 目标机器上的 Codex 不能直接从 GitHub 安装
- 网络限制阻止了仓库下载
- 用户更希望手动下载和复制

### 切换到手动安装前，值得先检查的常见运行环境问题

在转去手动兜底之前，目标机器上常见、而且值得先排查的本地阻塞包括：

- `python` 指向了失效的 Windows Store 别名，而不是真正可用的解释器
- 本机可用的 Python 无法正确校验 HTTPS 证书
- 想走 git 兜底时，系统里没有可用的 `git`，或者 `git` 不在 `PATH` 中

如果这些问题可以在不改变安装来源的前提下通过本地修复解决，通常更建议先完成同一个 GitHub 安装流程。

### 用户需要下载什么

下载整个仓库后，只需要找到其中这个目录：

- `skills/codex-session-migration`

手动安装时，真正需要复制的只有这个文件夹。

### 给英文环境 Codex 的手动安装提示词

如果目标机器上的 Codex 使用英文更方便，就发送上面的英文手动兜底提示词。

### 给中文环境 Codex 的手动安装提示词

如果目标机器上的 Codex 使用中文更方便，就发送上面的中文手动兜底提示词。

## 这个 skill 能做什么

这个 skill 支持：

- 不同 `CODEX_HOME` 目录之间的迁移
- 同一个 `CODEX_HOME` 内的只重绑修复
- 工作区文件夹改名或移动后的路径修复
- 基于 bundle 的跨设备线程转移

## 验证边界

如果你要把它用于关键迁移，请先阅读：

- [VALIDATION.md](VALIDATION.md)

当前已经完成端到端验证的方向：

- `Windows -> Windows`
- `Windows -> macOS`
- `macOS -> Windows`

当前仍然有意保守、不声明已验证的方向：

- `macOS -> macOS`
- 归档线程的跨设备 bundle 转移
