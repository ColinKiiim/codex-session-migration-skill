# Codex Session Migration

Chinese version below.

## English

If you want to install this skill, open [MANUAL.md](MANUAL.md) first.

This repository contains a Codex skill for migrating, rebinding, repairing, and transferring Codex conversation history.

It supports more than moving threads across different `CODEX_HOME` directories. It also supports:

- rebinding threads to a new workspace path inside the same `CODEX_HOME`
- repairing threads that disappear after a workspace folder is renamed or moved
- repairing sidebar invisibility caused by `session_index.jsonl` drift
- preserving sidebar remark names stored in `session_index.jsonl -> thread_name`
- metadata-only recency promotion to re-surface older workspace threads in the sidebar
- cloning one existing thread into a second active thread under a new workspace path
- single-thread bundle export and import for cross-device transfer
- source-side handoff prompt generation and target-side cleanup prompt generation
- same-home migrate with source-thread archiving after the new target thread is verified

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

## Migration Retirement Behavior

### English

- `copy` keeps the source thread active and creates a second active thread at the new workspace path.
- `migrate` creates the new target thread first, verifies it, and then archives the old source thread instead of leaving two active copies behind.

## Sidebar Recovery

### English

This repository now also covers a same-home repair class that is easy to misdiagnose as "thread loss":

- session files still exist
- sqlite rows still exist
- `session_index.jsonl` is missing ids or contains duplicate ids
- or the workspace only looks empty because its threads are too old for the current recent-thread window

The practical repair boundary is:

- repair `session_index.jsonl` without destroying `thread_name`
- treat `thread_name` as the sidebar remark label
- test a small `updated_at` bump before promoting an entire workspace
- restart Codex after metadata repair

### 中文

- `copy` 会保留源线程为活跃状态，同时在新的工作目录下创建第二个活跃线程。
- `migrate` 会先创建并验证新的目标线程，然后把旧的源线程归档，而不是在主列表里保留两个活跃副本。

### 中文

这个仓库现在也覆盖了一类容易被误判为“线程丢失”的同机修复场景：

- session 文件还在
- sqlite 行还在
- `session_index.jsonl` 缺 id 或有重复 id
- 或者工作区只是因为线程太旧，暂时掉出了当前的 recent-thread 窗口

实践上的修复边界是：

- 修 `session_index.jsonl` 时不要破坏 `thread_name`
- 把 `thread_name` 当成侧栏备注名
- 先做小范围 `updated_at` 测试，再决定是否提升整个工作区
- 元数据修完后重启 Codex

## 中文

如果你想安装这个 skill，请先打开 [MANUAL.md](MANUAL.md)。

这个仓库提供了一个用于迁移、重绑、修复和跨设备转移 Codex 对话历史的 skill。

它不只支持不同 `CODEX_HOME` 目录之间的迁移，也支持：

- 在同一个 `CODEX_HOME` 中，把线程重绑到新的工作目录
- 在工作区文件夹改名或移动后，修复“消失”的线程
- 修复由 `session_index.jsonl` 漂移导致的侧栏线程不可见
- 保留 `session_index.jsonl -> thread_name` 中的侧栏备注名
- 通过只改元数据的 `updated_at` 提升，让较旧工作区重新出现在侧栏中
- 将一条已有线程克隆成另一条新 id 的活跃线程，并绑定到新的工作目录
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
