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
- alternate local Codex home import from Antigravity/Codex instance directories into the main `~/.codex`
- rebind-only fixes inside one existing `CODEX_HOME`
- workspace-path repair after folder rename or move
- batch path-prefix repair after a parent workspace folder rename or path drift
- sidebar recovery for hidden threads caused by `session_index.jsonl` drift or old `updated_at`
- metadata-only search by thread id, title, sidebar remark, cwd, or first-message fragment
- malformed-session diagnosis that does not block unrelated repairs
- direct same-home multi-thread rebind with sidebar promotion
- cloning one thread into a second active thread under a new workspace path
- bundle-based cross-device transfer

## Alternate Local Codex Home / Antigravity Instance Import

Use this workflow when the user says a conversation created in a new Codex-like instance or Antigravity instance does not appear in the main Codex Desktop sidebar.

### Confirmed Practical Lessons

- A healthy main `~/.codex` can still have no trace of the target thread.
- Antigravity/Codex instance directories may be independent Codex homes with their own `sessions/`, `session_index.jsonl`, and `state_5.sqlite`.
- If the thread exists only in the instance home, the repair is `copy-selected` from that home into main `~/.codex`.
- Do not use `rebind_threads.py` or `bump_workspace_updated_at.py` when the main home does not contain the thread.
- If the main home already has the same id, stop and decide whether to skip, replace, or clone; do not overwrite by default.

### Example Commands

```bash
python scripts/search_thread_index.py --home "~/.codex" --query "/absolute/workspace/path" --format json
python scripts/inspect_codex_home.py --home "~/.codex"
python scripts/inspect_codex_home.py --home "~/.antigravity_cockpit/instances/codex/<instance-id>"
python scripts/search_thread_index.py --home "~/.antigravity_cockpit/instances/codex/<instance-id>" --query "/absolute/workspace/path" --format json
python scripts/search_thread_index.py --home "~/.codex" --query "<thread-id>" --format json
```

Use `copy-selected` when the id is absent from the main home:

```json
{
  "source_home": "~/.antigravity_cockpit/instances/codex/<instance-id>",
  "target_home": "~/.codex",
  "mode": "copy-selected",
  "include_archived": false,
  "thread_ids": ["<thread-id>"],
  "path_rules": [],
  "update_sqlite": true,
  "backup_label": "<short-label>"
}
```

```bash
python scripts/plan_migration.py --spec spec.json --output plan.json
python scripts/migrate_threads.py --plan plan.json --execute
python scripts/verify_migration.py --plan plan.json
python scripts/verify_thread_binding.py --home "~/.codex" --cwd "/absolute/workspace/path" --thread-id "<thread-id>"
```

After verification, check the main Codex sidebar first. Fully restart Codex only if the sidebar does not refresh.

## Sidebar Repair Inside One Existing `CODEX_HOME`

Use this workflow when the user says threads disappeared from the left sidebar but you are still working inside the same machine's real `CODEX_HOME`.

### Confirmed Practical Lessons

- A thread can still exist in `sessions/` and sqlite while being invisible in the sidebar because `session_index.jsonl` is missing the id.
- `session_index.jsonl -> thread_name` is the sidebar remark label. It may differ from sqlite `threads.title`.
- If you rebuild the index from sqlite `title` without preserving `thread_name`, you can destroy the user's short sidebar remarks.
- Some "no threads under this workspace" cases are actually recent-window problems. The thread exists, but its `updated_at` is too old to surface in the current sidebar window.
- A few malformed JSONL session files should not abort the whole repair. Good repair tooling should report and skip them.

### Recommended Order

1. Inspect the three-layer state.
2. Dry-run `repair_session_index.py`.
3. If the user cares about old sidebar remarks and an older index backup exists, pass it as `--name-source-index`.
4. Execute the repair.
5. Check the Codex sidebar first. Recent Desktop builds may refresh visible threads without a full restart.
6. If the workspace group still looks empty, test `bump_workspace_updated_at.py --limit 5`.
7. Only after a small test works, promote the whole workspace.
8. Fully restart Codex only if the sidebar does not refresh after the metadata repair or bump.

### Example Commands

```bash
python scripts/inspect_codex_home.py --home "~/.codex" --include-archived
python scripts/diagnose_sessions.py --home "~/.codex"
python scripts/search_thread_index.py --home "~/.codex" --query "/absolute/workspace/path" --format json
python scripts/repair_session_index.py --home "~/.codex" --include-archived
python scripts/repair_session_index.py --home "~/.codex" --include-archived --name-source-index "~/.codex/session_index.jsonl.bak-YYYYMMDD-HHMMSS" --execute
python scripts/bump_workspace_updated_at.py --home "~/.codex" --cwd "/absolute/workspace/path" --limit 5 --execute
python scripts/bump_workspace_updated_at.py --home "~/.codex" --cwd "/absolute/workspace/path" --execute
```

For known ids that only need to move to a different workspace grouping inside the same home:

```bash
python scripts/rebind_threads.py --home "~/.codex" --thread-id "<thread-id>" --target-cwd "/absolute/workspace/path" --promote-to-sidebar
python scripts/rebind_threads.py --home "~/.codex" --thread-id "<thread-id>" --target-cwd "/absolute/workspace/path" --promote-to-sidebar --execute
python scripts/verify_thread_binding.py --home "~/.codex" --cwd "/absolute/workspace/path" --thread-id "<thread-id>"
```

For a parent folder rename that affects many workspace groups, use the prefix workflow instead of manually collecting thread ids:

```bash
python scripts/rebind_path_prefix.py --home "~/.codex" --map "/old/root=/new/root" --include-archived --promote-to-sidebar --require-target-exists
python scripts/rebind_path_prefix.py --home "~/.codex" --map "/old/root=/new/root" --include-archived --promote-to-sidebar --require-target-exists --execute
```

Pass repeated `--map OLD=NEW` values if the rename maps multiple subtrees. The script preserves sidebar names, updates sqlite, updates parseable session metadata, preserves malformed JSONL lines, and promotes recency for sidebar visibility.

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
- 从 Antigravity/Codex 实例目录等本机 alternate Codex home 导入线程到主 `~/.codex`
- 同一个 `CODEX_HOME` 内的只重绑修复
- 工作区文件夹改名或移动后的路径修复
- 父级工作区目录改名或路径漂移后的批量前缀修复
- 修复由 `session_index.jsonl` 漂移或旧 `updated_at` 导致的侧栏隐藏线程
- 通过线程 id、标题、侧栏备注名、cwd 或首条消息片段做元数据级搜索
- 诊断损坏的 session 文件，同时不阻塞无关线程的修复
- 同一个 home 内多线程直接重绑，并可同时提升侧栏可见性
- 将一条线程克隆成另一条新 id 的活跃线程，并绑定到新的工作目录
- 基于 bundle 的跨设备线程转移

## 本机 Alternate Codex Home / Antigravity 实例导入

如果用户说新开 Codex-like 实例或 Antigravity 实例里创建的对话没有出现在主 Codex Desktop 侧栏，使用这个流程。

### 已确认的实践结论

- 主 `~/.codex` 三层结构正常，也可能完全没有目标线程。
- Antigravity/Codex 实例目录可能是独立 Codex home，拥有自己的 `sessions/`、`session_index.jsonl` 和 `state_5.sqlite`。
- 如果线程只存在于实例 home，正确修复是从实例 home `copy-selected` 到主 `~/.codex`。
- 当主 home 不含这条线程时，不要用 `rebind_threads.py`，也不要用 `bump_workspace_updated_at.py`。
- 如果主 home 已经有同 id，先停下来判断是 skip、replace 还是 clone；默认不要覆盖。

### 示例命令

```bash
python scripts/search_thread_index.py --home "~/.codex" --query "/absolute/workspace/path" --format json
python scripts/inspect_codex_home.py --home "~/.codex"
python scripts/inspect_codex_home.py --home "~/.antigravity_cockpit/instances/codex/<instance-id>"
python scripts/search_thread_index.py --home "~/.antigravity_cockpit/instances/codex/<instance-id>" --query "/absolute/workspace/path" --format json
python scripts/search_thread_index.py --home "~/.codex" --query "<thread-id>" --format json
```

当主 home 中没有这个 id 时，使用 `copy-selected`：

```json
{
  "source_home": "~/.antigravity_cockpit/instances/codex/<instance-id>",
  "target_home": "~/.codex",
  "mode": "copy-selected",
  "include_archived": false,
  "thread_ids": ["<thread-id>"],
  "path_rules": [],
  "update_sqlite": true,
  "backup_label": "<short-label>"
}
```

```bash
python scripts/plan_migration.py --spec spec.json --output plan.json
python scripts/migrate_threads.py --plan plan.json --execute
python scripts/verify_migration.py --plan plan.json
python scripts/verify_thread_binding.py --home "~/.codex" --cwd "/absolute/workspace/path" --thread-id "<thread-id>"
```

验证后先看主 Codex 侧栏。如果侧栏没有刷新，再完整重启 Codex。

## 同一个 `CODEX_HOME` 内的侧栏修复

如果用户说左侧侧栏里有线程“消失了”，但你仍然是在同一台机器、同一个真实 `CODEX_HOME` 里处理问题，就优先走这个流程。

### 今天已经确认过的实践结论

- 线程可能仍然存在于 `sessions/` 和 sqlite 中，但因为 `session_index.jsonl` 缺少对应 id，所以侧栏看不到。
- `session_index.jsonl -> thread_name` 才是侧栏备注名，它可能和 sqlite `threads.title` 不一样。
- 如果你直接用 sqlite `title` 重建 index，而不保留 `thread_name`，就可能把用户原来的短备注名全部覆盖掉。
- 有些“这个工作区下面没有线程”其实是 recent-thread 窗口问题：线程还在，但 `updated_at` 太旧，暂时不显示。
- 少量损坏的 JSONL session 文件不应该让整个修复流程中断。好的修复脚本应该把它们报告出来并跳过。
- 如果父目录改名导致多个工作区同时变灰或显示暂无对话，优先用 `rebind_path_prefix.py`，不要手工逐个收集线程 id。

### 建议顺序

1. 先检查三层状态。
2. 先 dry-run `repair_session_index.py`。
3. 如果用户在乎旧的侧栏备注名，而且存在较早的 index 备份，就通过 `--name-source-index` 指定它。
4. 再执行 index 修复。
5. 先直接看 Codex 侧栏。新版桌面端可能不需要完整重启就刷新出修复后的线程。
6. 如果工作区分组看起来仍然是空的，再先用 `bump_workspace_updated_at.py --limit 5` 做一个小范围测试。
7. 只有小测试成功后，再提升整个工作区。
8. 如果是父目录整体改名或路径前缀漂移，用 `rebind_path_prefix.py` 批量同步 session、sqlite 和 index。
9. 如果元数据修复或提升后侧栏仍未出现，再完整重启 Codex。

### 示例命令

```bash
python scripts/inspect_codex_home.py --home "~/.codex" --include-archived
python scripts/diagnose_sessions.py --home "~/.codex"
python scripts/search_thread_index.py --home "~/.codex" --query "/absolute/workspace/path" --format json
python scripts/repair_session_index.py --home "~/.codex" --include-archived
python scripts/repair_session_index.py --home "~/.codex" --include-archived --name-source-index "~/.codex/session_index.jsonl.bak-YYYYMMDD-HHMMSS" --execute
python scripts/bump_workspace_updated_at.py --home "~/.codex" --cwd "/absolute/workspace/path" --limit 5 --execute
python scripts/bump_workspace_updated_at.py --home "~/.codex" --cwd "/absolute/workspace/path" --execute
```

如果已经知道线程 id，只需要在同一个 home 内移动到另一个工作区分组：

```bash
python scripts/rebind_threads.py --home "~/.codex" --thread-id "<thread-id>" --target-cwd "/absolute/workspace/path" --promote-to-sidebar
python scripts/rebind_threads.py --home "~/.codex" --thread-id "<thread-id>" --target-cwd "/absolute/workspace/path" --promote-to-sidebar --execute
python scripts/verify_thread_binding.py --home "~/.codex" --cwd "/absolute/workspace/path" --thread-id "<thread-id>"
```

如果父级目录改名影响了多个工作区分组，用前缀修复流程：

```bash
python scripts/rebind_path_prefix.py --home "~/.codex" --map "/old/root=/new/root" --include-archived --promote-to-sidebar --require-target-exists
python scripts/rebind_path_prefix.py --home "~/.codex" --map "/old/root=/new/root" --include-archived --promote-to-sidebar --require-target-exists --execute
```

如果一次改名涉及多个子树，可以重复传入 `--map OLD=NEW`。这个脚本会保留侧栏备注名，更新 sqlite，更新可解析的 session 元数据，保留损坏 JSONL 行，并提升 `updated_at` 以便侧栏重新显示。

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
