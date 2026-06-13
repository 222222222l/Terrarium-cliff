---
title: T18-T19 Evolver
summary: 可控演化草案协议与只产出草案的 evolver 原型。
tags:
  - dev
  - evolution
  - governance
  - creature
---

# T18-T19 Evolver

`T18-T19` 补齐可控演化闭环的最后一段：系统可以提出改进草案，但不能直接把草案应用到正式模板。

## 1. 草案协议

机器可读协议：

```text
examples/test-kit/evolution-schema/draft-protocol.yaml
```

Skill：

```text
examples/test-kit/skills/evolution-draft-protocol/SKILL.md
```

协议要求每个 proposal 至少包含：

- `proposal_id`
- `proposal_type`
- `scope`
- `source_refs`
- `problem`
- `proposed_change`
- `expected_benefit`
- `risk_level`
- `approval_required`
- `audit_required`
- `rollback_plan`
- `status`

## 2. Evolver 原型

模板路径：

```text
examples/test-kit/creatures/evolver/
```

它只具备只读工具、`result_feedback` 和 `lab_report`，默认不带 `write` / `edit`。

这意味着它可以：

- 读取现有文档、schema、policy、prompt。
- 输出 `evolution_proposal`。
- 生成草案报告。

它不能：

- 直接修改正式 skill。
- 直接修改 prompt。
- 直接启用 policy。
- 直接写 durable memory。

任何从 `draft/proposed` 进入 `approved/applied` 的状态变化，都必须走 `approval-gate` 与 `audit-guard`。

## 3. 验证命令

```bash
python .\examples\test-kit\scripts\verify_t18_t19_evolver.py
```

通过标准：

- manifest 声明 `evolution-draft-protocol` skill。
- manifest 声明 `evolver` creature。
- evolver 挂载该 skill。
- evolver 不包含 `write` / `edit`。
- draft protocol 包含 source refs、risk、approval、audit、rollback 与 status。
