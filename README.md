# Codex Session Migration

Chinese version below.

## English

If you want to install this skill, open [MANUAL.md](MANUAL.md) first.

This repository contains a Codex skill for migrating, rebinding, repairing, and transferring Codex conversation history.

It supports more than moving threads across different `CODEX_HOME` directories. It also supports:

- rebinding threads to a new workspace path inside the same `CODEX_HOME`
- repairing threads that disappear after a workspace folder is renamed or moved
- single-thread bundle export and import for cross-device transfer
- source-side handoff prompt generation and target-side cleanup prompt generation

The installable skill lives at:

- `skills/codex-session-migration`

Recommended reading order:

1. [MANUAL.md](MANUAL.md)
2. [INSTALL.md](INSTALL.md)
3. [VALIDATION.md](VALIDATION.md)

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

This repository is ready for GitHub repo/path installation.

That does not automatically mean it will appear in Codex's built-in searchable skill catalog. A public GitHub repository is the right foundation, but searchable catalog installation usually also requires inclusion in a supported catalog source.

## 中文

如果你想安装这个 skill，请先打开 [MANUAL.md](MANUAL.md)。

这个仓库提供了一个用于迁移、重绑、修复和跨设备转移 Codex 对话历史的 skill。

它不只支持不同 `CODEX_HOME` 目录之间的迁移，也支持：

- 在同一个 `CODEX_HOME` 中，把线程重绑到新的工作目录
- 在工作区文件夹改名或移动后，修复“消失”的线程
- 面向跨设备转移的单线程 bundle 导出与导入
- 源机器生成交接 prompt，目标机器在成功导入后生成清理 prompt

可安装的 skill 位于：

- `skills/codex-session-migration`

建议阅读顺序：

1. [MANUAL.md](MANUAL.md)
2. [INSTALL.md](INSTALL.md)
3. [VALIDATION.md](VALIDATION.md)

## 仓库结构

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

## 当前发布定位

这个仓库已经适合通过 GitHub 的 repo/path 方式安装。

但这并不自动意味着它会出现在 Codex 内置的可搜索技能目录里。公开 GitHub 仓库是正确基础，但想实现“搜索并点加号安装”，通常还需要被纳入 Codex 支持的 catalog 来源。
