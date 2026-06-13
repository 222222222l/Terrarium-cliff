---
title: T12 Memory Schema
summary: 私有 creature 模板生态的分层记忆 schema，定义 scope、来源、置信度、保留期与去重规则。
tags:
  - dev
  - memory
  - schema
  - governance
---

# T12 Memory Schema

这份文档定义长期记忆的结构边界。它不替代 2.0 现有 `.kohakutr` session store，也不提前实现 `curator`；它只给后续 `T13`、`T11`、`T14` 和治理插件提供共同契约。

## 1. 与现有 session 的边界

`.kohakutr` 仍是运行时事实源：

- 保存事件流、conversation snapshot、scratchpad、channel、jobs、subagent history。
- 支持 `kt resume`、`kt search`、`search_memory`。
- 记录“发生过什么”。

T12 schema 只保存被整理后的长期资产：

- 用户偏好。
- 项目规则。
- 工作区资产。
- 任务归档。
- 临时上下文。

也就是说，session 是原始历史，memory schema 是治理后的索引与资产层。

## 2. 五层结构

| Layer | Scope | Path | 用途 |
|---|---|---|---|
| `user-preferences` | user | `memory/user/preferences.yaml` | 跨项目用户偏好 |
| `project-rules` | project | `memory/project/rules.yaml` | 仓库规则、架构约束、编码约定 |
| `workspace-assets` | workspace | `memory/workspace/assets.yaml` | 本地路径、生成物、sibling checkout、可复用资源 |
| `task-archives` | session | `memory/tasks/archive.yaml` | 已完成任务摘要、验证结果、变更文件、后续指针 |
| `transient-context` | session | `memory/transient/context.yaml` | 当前任务短期上下文，必须过期或晋升 |

完整机器可读契约位于：

```text
examples/test-kit/memory-schema/schema.yaml
```

## 3. 统一字段

所有记录至少包含：

- `id`
- `layer`
- `scope`
- `title`
- `content`
- `source`
- `source_ref`
- `confidence`
- `retention`
- `dedupe_key`
- `created_at`
- `updated_at`
- `status`

可选字段：

- `tags`
- `applies_to`
- `expires_at`
- `supersedes`
- `related_records`
- `evidence`
- `owner`
- `review_after`

## 4. Scope 规则

- `user`：只放跨项目偏好，例如输出语言、验收节奏、交互习惯。
- `project`：只放当前仓库规则，例如 AGENTS 约束、蓝图阶段边界、包治理约定。
- `workspace`：只放本地环境状态，例如 sibling checkout 是否存在、生成物路径、临时工具路径。
- `session`：只放当前会话或任务图内有效的信息，例如任务归档与临时上下文。

禁止把 workspace-only 路径写成 user preference，也禁止把一次任务的临时假设直接写成 project rule。

## 5. 来源、置信度与保留期

`source` 必须是：

- `user`
- `session`
- `tool`
- `file`
- `mcp`
- `web`
- `inference`
- `curator`

置信度规则：

- 用户直接指令通常不低于 `0.9`。
- 仓库文件和 manifest 通常不低于 `0.8`。
- session 观察和工具输出通常从 `0.6` 起。
- inference 只能作为草案，不能直接写入 durable memory。

保留期：

- `permanent`
- `until-changed`
- `project-lifetime`
- `task-lifetime`
- `ephemeral`

`transient-context` 默认是 `ephemeral`，任务结束后必须删除或晋升。

## 6. 去重规则

去重键由三部分组成：

```text
layer + scope + dedupe_key
```

写入前需要做规范化：

- 小写化。
- 去除首尾空白。
- 合并内部连续空白。
- workspace path 统一路径分隔符。

重复时：

- 新记录置信度更高：替换内容，并通过 `supersedes` 记录被替换项。
- 置信度相同：只合并 evidence 与 `updated_at`。
- 新记录置信度更低：保留旧记录，必要时追加 source_ref。

## 7. 后续任务的使用方式

- `T13 curator`：读取 `schema.yaml`，按 layer 和 scope 写入 memory 文件。
- `T11 memory-curation skill`：只描述整理流程，不硬编码字段结构。
- `T14 task-team-learning`：任务完成后把执行结果沉淀到 `task-archives`，再由 curator 决定是否晋升。
- `T15-T17` 治理插件：基于 `source`、`confidence`、`retention` 与 `status` 做审批、预算和审计。

## 8. 验证命令

```bash
python .\examples\test-kit\scripts\verify_t12_memory_schema.py
```

通过标准：

- 五个 layer 全部存在。
- 每个 layer 都有 scope、storage path、retention、allowed sources。
- 统一 record contract 包含 source、confidence、retention、dedupe、status。
- identity boundaries 区分 user / project / workspace / session。
- transient context 有过期与晋升规则。
