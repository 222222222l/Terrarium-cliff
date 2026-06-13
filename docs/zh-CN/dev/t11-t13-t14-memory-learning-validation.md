---
title: T11-T14 记忆学习收口验证
summary: memory-curation skill、curator creature 与 task-team-learning terrarium 的离线验证说明。
tags:
  - dev
  - memory
  - curator
  - terrarium
---

# T11-T14 记忆学习收口验证

这份文档覆盖三个任务：

- `T11`：`memory-curation` skill
- `T13`：`curator` creature 模板
- `T14`：`task-team-learning` terrarium

## 1. 设计边界

`T12` 已定义 memory schema。`T11-T14` 在此基础上做系统收口：

- skill 只定义整理流程，不拥有 Python 逻辑。
- curator 是低频记忆治理 creature，负责读 schema、去重、写 memory 文件和报告结果。
- learning terrarium 保持执行链与沉淀链解耦。

主执行链：

```text
root -> coordinator -> worker -> critic -> root
```

学习分支：

```text
critic -> curator -> root
```

## 2. 验证命令

```bash
python .\examples\test-kit\scripts\verify_t11_t14_memory_learning.py
```

也可以运行默认回归：

```bash
python .\examples\test-kit\scripts\verify_regression_suite.py
```

## 3. 通过标准

- `kohaku.yaml` 声明 `memory-curation` skill。
- `kohaku.yaml` 声明 `curator` creature。
- `curator` 显式挂载 `memory-curation`。
- `curator` 的 prompt 引用 schema、source、confidence、retention、dedupe。
- `task-team-learning` 声明 coordinator、worker、critic、curator。
- critic 同时 wired 到 root 与 curator。
- curator wired 回 root。
- terrarium 不依赖旧版 channel `type` 语义。
