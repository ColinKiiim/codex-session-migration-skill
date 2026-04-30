# Validation

Chinese version below.

Updated: 2026-04-30

## English

## Verified End-To-End

- `Windows -> Windows`
  - source export
  - transfer as zip
  - isolated import on a second Windows machine
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
- checksum failure on a tampered bundle
- workspace-path rebinding and SQLite synchronization
- recovery from workspace rename and path drift on Windows
- same-home migrate with source-thread archive on Windows
- macOS same-home diagnosis of sidebar invisibility across session files, `session_index.jsonl`, and sqlite
- repair of `session_index.jsonl` drift with missing ids plus duplicate ids
- restoration of sidebar remark names from an older index backup without reverting repaired `updated_at`
- workspace-scoped `updated_at` promotion on macOS to re-surface older threads in the sidebar
- dry-run repair tooling that reports and skips malformed session JSONL files instead of aborting
- metadata-only thread search by cwd/sidebar name/title against sqlite and `session_index.jsonl` on macOS
- direct same-home rebind dry-run for a known macOS thread id, including `thread_name` preservation and sidebar-promotion planning
- malformed-session diagnosis on a real macOS home with structured file paths and JSONL line numbers
- Codex Desktop may refresh repaired sidebar entries before a full restart; current docs now instruct operators to check the sidebar first

## Not Yet Verified

- `macOS -> macOS`
- archived-thread cross-device bundle transfer

## Claim Boundary

This repository intentionally avoids stronger claims than the evidence supports.

- Cross-device bundle transfer is described as verified only for `win -> win`, `win -> mac`, and `mac -> win`.
- Direct migration and rebind scripts are broader than the bundle validation matrix, but the docs do not overclaim untested host pairings.

## Same-Home Retirement Policy

### English

- Verified behavior on Windows: after a successful same-home migrate, the new target thread can stay active while the old source thread is archived and recoverable from Codex's archive UI.
- Recommended default policy: `copy -> keep-source`, `migrate -> archive-source`.

### 中文

- 已验证的 Windows 行为：同一 `CODEX_HOME` 内迁移成功后，新的目标线程可以保持活跃，而旧的源线程会被归档，并且仍可在 Codex 的归档界面中恢复。
- 建议的默认策略：`copy -> keep-source`，`migrate -> archive-source`。

## 中文

## 已完成端到端验证

- `Windows -> Windows`
  - 源端导出
  - 以 zip 形式转移
  - 在第二台 Windows 机器上做隔离导入
  - 真实导入到第二台机器的 `%USERPROFILE%\.codex`
  - 验证脚本通过
  - 完整重启 Codex
  - 在线程目标 Windows Codex UI 中可见

- `Windows -> macOS`
  - 源端导出
  - 以 zip 形式转移
  - 在 macOS 上做隔离导入
  - 真实导入到目标 `~/.codex`
  - 验证脚本通过
  - 完整重启 Codex
  - 在线程目标 macOS Codex UI 中可见

- `macOS -> Windows`
  - 源端导出
  - 以 zip 形式转移
  - 在 Windows 上做隔离导入
  - 真实导入到目标 `%USERPROFILE%\.codex`
  - 验证脚本通过
  - 完整重启 Codex
  - 在线程目标 Windows Codex UI 中可见

## 已验证的辅助行为

- 源端一步式 handoff 准备
- 基于标题片段的线程解析
- 源机器内联生成 `Prompt 1`
- 目标机器在成功导入后生成清理 prompt
- 被篡改 bundle 的校验失败检测
- 工作区路径重绑与 SQLite 同步
- Windows 上因工作区改名导致的路径漂移恢复
- macOS 上基于 session 文件、`session_index.jsonl` 和 sqlite 的同机侧栏不可见诊断
- 对缺 id 且有重复 id 的 `session_index.jsonl` 漂移修复
- 在不回退已修复 `updated_at` 的前提下，从旧 index 备份恢复侧栏备注名
- macOS 上按工作区提升 `updated_at`，让较旧线程重新进入侧栏
- dry-run 修复脚本在遇到损坏 session JSONL 文件时会报告并跳过，而不是直接中断
- macOS 上通过 sqlite 和 `session_index.jsonl` 进行基于 cwd、侧栏名、标题的元数据级线程搜索
- 已知 macOS 线程 id 的同机直接重绑 dry-run，包括保留 `thread_name` 与规划侧栏提升
- 在真实 macOS home 上诊断损坏 session 文件，并结构化报告文件路径和 JSONL 行号
- Codex 桌面端可能在完整重启前就刷新出修复后的侧栏条目；当前文档已改为提示操作者先检查侧栏

## 尚未验证

- `macOS -> macOS`
- 归档线程的跨设备 bundle 转移

## 声明边界

这个仓库会刻意避免做出超过证据范围的更强声明。

- 当前只把 `win -> win`、`win -> mac`、`mac -> win` 描述为“已验证”的跨设备 bundle 转移方向。
- 直接迁移和重绑脚本的适用范围比 bundle 验证矩阵更广，但文档不会对未测试的主机组合做过度宣称。
