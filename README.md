# Codex Session Migration

If you want to install this skill, open [MANUAL.md](MANUAL.md) first.

如果你想安装这个 skill，请先打开 [MANUAL.md](MANUAL.md)。

## 中文简介

这是一个用于 Codex 对话历史迁移与重绑的 skill 仓库。

它不只支持不同 `CODEX_HOME` 目录之间的迁移，也支持：

- 同一台机器、同一个 `CODEX_HOME` 内，把线程重绑到新的工作目录
- 工作区文件夹改名、移动后，把“消失”的线程重新挂回正确路径
- 跨设备单线程 bundle 导出 / 导入
- 源机器生成导入 prompt，目标机器成功导入后再生成清理 prompt

仓库里的可安装 skill 位于：

- `skills/codex-session-migration`

如果你是第一次使用这个仓库，请直接看：

- [MANUAL.md](MANUAL.md)

如果你想了解安装方式，请看：

- [INSTALL.md](INSTALL.md)

如果你想了解当前验证边界，请看：

- [VALIDATION.md](VALIDATION.md)

## English Overview

This repository contains a Codex skill for migrating, rebinding, and transferring Codex conversation history.

It supports more than moving threads across different `CODEX_HOME` directories. It also supports:

- rebinding threads to a new workspace path inside the same `CODEX_HOME`
- recovering threads that disappear after a workspace folder is renamed or moved
- single-thread bundle export/import for cross-device transfer
- source-side import prompt generation and target-side cleanup prompt generation

The installable skill lives at:

- `skills/codex-session-migration`

If you are new to this repository, start here:

- [MANUAL.md](MANUAL.md)

For installation details:

- [INSTALL.md](INSTALL.md)

For the current validation boundary:

- [VALIDATION.md](VALIDATION.md)

## Repository Layout

```text
.
|-- README.md
|-- MANUAL.md
|-- INSTALL.md
|-- VALIDATION.md
`-- skills/
    `-- codex-session-migration/
        |-- SKILL.md
        |-- agents/
        |-- assets/
        |-- references/
        `-- scripts/
```

## Current Distribution Position

Today, this repository is ready for GitHub repo/path installation.

That does not automatically mean it will appear in Codex's built-in searchable skill catalog. A public GitHub repo is the right foundation, but searchable catalog installation usually also requires inclusion in a supported catalog source.
