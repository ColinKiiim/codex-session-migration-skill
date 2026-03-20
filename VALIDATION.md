# Validation

Chinese version below.

Updated: 2026-03-20

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

## 尚未验证

- `macOS -> macOS`
- 归档线程的跨设备 bundle 转移

## 声明边界

这个仓库会刻意避免做出超过证据范围的更强声明。

- 当前只把 `win -> win`、`win -> mac`、`mac -> win` 描述为“已验证”的跨设备 bundle 转移方向。
- 直接迁移和重绑脚本的适用范围比 bundle 验证矩阵更广，但文档不会对未测试的主机组合做过度宣称。
