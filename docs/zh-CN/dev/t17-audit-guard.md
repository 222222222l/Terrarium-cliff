---
title: T17 Audit Guard
summary: 针对关键变更与演化行为的项目级审计插件和策略。
tags:
  - dev
  - governance
  - audit
  - plugin
---

# T17 Audit Guard

`T17` 补齐可追溯性。它不阻断动作；阻断由 `approval-gate` 和 `budget-policy` 负责。`audit-guard` 只记录关键动作发生过什么、由谁触发、在哪个 session、哪个 tool/job，以及简短参数和结果摘要。

## 1. 插件

插件文件：

```text
examples/test-kit/test_kit/plugins/audit_guard.py
```

package manifest 中声明：

```yaml
plugins:
  - name: audit_guard
    module: test_kit.plugins.audit_guard
    class: AuditGuardPlugin
```

默认审计路径：

```text
.kohaku/audit/audit-guard.jsonl
```

## 2. 当前挂载范围

`worker-base`：

- `edit`
- `cli_invoke`

`curator`：

- `write`
- `edit`

这两个角色同时也是当前最高风险点：

- worker 会修改工作区或调用外部 provider。
- curator 会把任务结果、规则或偏好沉淀进 memory。

## 3. 记录格式

每条记录是短 JSONL：

```json
{
  "schema_version": "audit-guard.v1",
  "timestamp": "...",
  "agent_name": "worker",
  "session_id": "...",
  "tool_name": "edit",
  "job_id": "...",
  "source": "post_tool_execute",
  "args_summary": "...",
  "result_preview": "..."
}
```

只记录短摘要，不保存完整原始日志。

## 4. 策略文件

```text
examples/test-kit/governance-policies/audit-guard.yaml
```

策略定义：

- `tracked_action_classes`
- `role_bindings`
- `retention`

## 5. 验证命令

```bash
python .\examples\test-kit\scripts\verify_t17_audit_guard.py
```

通过标准：

- package manifest 声明 `audit_guard` plugin。
- worker/curator 实际挂载该 plugin。
- 插件实现 `post_tool_execute`。
- 策略覆盖 workspace write、external execution、evolution draft。
- 审计记录不要求完整日志，只要求 bounded summary。
