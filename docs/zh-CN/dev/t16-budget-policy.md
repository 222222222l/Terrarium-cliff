---
title: T16 Budget Policy
summary: 基于内置 budget 插件的角色级预算策略，覆盖 root、coordinator、worker、critic、curator。
tags:
  - dev
  - governance
  - budget
  - plugin
---

# T16 Budget Policy

`T16` 复用 2.0 内置 `budget` 插件，不重写 token、turn 或 tool-call 计数器。项目层只负责定义不同角色的预算建议，并把它们写入 creature config。

## 1. 策略文件

```text
examples/test-kit/governance-policies/budget-policy.yaml
```

策略声明：

- `builtin_plugin.name: budget`
- `role_budgets`
- `budget_rules`
- `fallback_behavior`

## 2. 当前角色预算

| Role | Turn Budget | Tool Call Budget | 说明 |
|---|---:|---:|---|
| `root-privileged` | 80 / 120 | 120 / 180 | 用户入口与编排，允许较长会话 |
| `coordinator` | 30 / 45 | 30 / 50 | 任务卡编译，应保持短小 |
| `worker-base` | 50 / 80 | 80 / 130 | 执行与验证，需要较多工具预算 |
| `critic` | 45 / 70 | 60 / 100 | 评审比 coordinator 更宽，但少于 worker |
| `curator` | 30 / 50 | 50 / 80 | 低频记忆治理，应紧凑保守 |

暂不设置 `walltime_budget`，因为当前 test-kit 的主要风险是 turn/tool 膨胀，不是墙钟时间。

## 3. 与 Approval Gate 的关系

`budget` 和 `permgate` 保持独立：

- `budget` 管成本。
- `permgate` 管风险确认。
- worker 与 curator 同时挂载二者时，预算不替代审批，审批也不替代预算。

## 4. 验证命令

```bash
python .\examples\test-kit\scripts\verify_t16_budget_policy.py
```

通过标准：

- 策略复用内置 `budget`。
- 五个核心角色都有不同预算。
- creature config 中实际挂载 `budget` 插件。
- worker 与 curator 同时保留 `permgate`。
- 策略定义 soft/hard、hard wall 与 soft alarm 行为。
