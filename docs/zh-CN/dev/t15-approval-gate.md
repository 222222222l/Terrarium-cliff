---
title: T15 Approval Gate
summary: 基于内置 permgate 的私有生态审批策略，覆盖危险动作、新规则启用与拒绝反馈。
tags:
  - dev
  - governance
  - plugin
  - approval
---

# T15 Approval Gate

`T15` 的目标不是重写审批引擎。2.0 已经有内置 `permgate` 插件，能在工具执行前弹出确认事件，并在拒绝或超时时通过 `PluginBlockError` 阻断工具。

本任务只做项目级治理封装：

- 定义哪些动作必须审批。
- 定义审批前必须携带哪些元数据。
- 把高风险角色接入内置 `permgate`。
- 定义拒绝反馈格式。

## 1. 策略文件

机器可读策略位于：

```text
examples/test-kit/governance-policies/approval-gate.yaml
```

策略声明：

- `builtin_plugin.name: permgate`
- `protected_action_classes`
- `role_bindings`
- `metadata_contract`
- `denial_feedback`

## 2. 当前挂载范围

`worker-base`：

- gate `edit`
- gate `cli_invoke`
- allow read-only 工具与 `result_feedback`

`curator`：

- gate `write`
- gate `edit`
- allow schema 读取、搜索、scratchpad、反馈和报告工具

这样做的原因：

- worker 的主要风险是修改工作区或调用外部 CLI provider。
- curator 的主要风险是把草案、规则或记忆写成 active 状态。
- coordinator 和 critic 默认不写文件，不需要先接入审批 gate。

## 3. 审批元数据

危险动作在进入审批前应能说明：

- `action_kind`
- `risk_level`
- `source_ref`
- `approval_reason`
- `rollback_plan`

规则启用还需要：

- `proposal_id`
- `scope`

这些字段先作为治理契约存在，不要求 `permgate` 本身理解它们；后续 `audit-guard` 可以记录和校验这些字段。

## 4. 拒绝反馈

拒绝时使用最小反馈：

```yaml
approval_result:
  status: blocked
  blocked_by: approval-gate
  action_kind: workspace-write
  reason: user denied
  next_safe_step: keep the draft and ask for approval scope
```

拒绝后不得继续执行同一危险动作；只能缩小范围、保留草案或请求用户重新确认。

## 5. 验证命令

```bash
python .\examples\test-kit\scripts\verify_t15_approval_gate.py
```

通过标准：

- 策略复用内置 `permgate`。
- worker-base gate `edit` 与 `cli_invoke`。
- curator gate `write` 与 `edit`。
- metadata contract 包含来源、风险、理由和回滚字段。
- denial feedback 包含 blocked 状态和下一步安全动作。
