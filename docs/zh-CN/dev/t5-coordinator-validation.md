# T5 `coordinator` 模板落地说明

本文件记录 `T5` 的实现边界、主流架构参考与最小验证方式。

## 1. 本次实现包含什么

已新增 package 级 creature 模板：

- `examples/test-kit/creatures/coordinator/config.yaml`
- `examples/test-kit/creatures/coordinator/prompts/system.md`

已新增最小验证脚本：

- `examples/test-kit/scripts/verify_t5_coordinator.py`

## 2. 参考了哪些主流模式

本次设计没有机械照搬单一框架，而是吸收 2026 年主流 coordinator /
triage / planner 模式里最稳定的共识：

### 2.1 LangGraph

保留其优点：

- 显式状态契约
- 明确节点职责
- 强调可审计、可恢复、可验证

落地方式：

- `coordinator` 的核心职责不是“讨论”，而是输出稳定的 `task_card`
- task card 字段固定，避免 downstream 角色靠猜

### 2.2 CrewAI

保留其优点：

- 经理 / 管理者只做分派与校验
- 任务按能力分配，而不是平均广播

规避其缺点：

- 不把 `coordinator` 做成高人格化经理角色
- 不让它产出长篇管理叙事

### 2.3 OpenAI Agents SDK

保留其优点：

- triage / handoff 模式非常适合入口分流
- orchestrator + subagents 的组合轻量且明确

规避其缺点：

- 不依赖隐式 handoff 魔法
- 将选路结果显式写入 `preferred_provider`

### 2.4 AutoGen

保留其优点：

- 当问题需要迭代澄清时，对话式协调是有价值的

规避其缺点：

- 不把 `coordinator` 做成“群聊主持人”
- 避免为了路由一个任务就产生多轮 turn churn

## 3. 为什么这个模板更集约

`coordinator` 当前版本遵循“最小可交付编排”原则：

- 工具面只保留轻量协调能力
- 不接文件、shell、browser、web 执行工具
- 只有当 provider 选择确实影响执行路径时，才调用 `provider_select`
- 优先输出单个 `task_card`，而不是冗长计划

## 4. 为什么它仍然泛用

泛用性不是靠加更多工具，而是靠契约稳定：

- `task_kind` 支持 code / docs / analysis / browser / service 等多类任务
- `preferred_provider` 与 `artifact_expectation` 已对接现有 CLI 抽象层
- `plan` / `explore` / `summarize` 足以覆盖大部分高质量编排前处理

因此它既能用于编码链路，也能用于研究、文档、浏览器与混合型任务。

## 5. 当前权限边界

`coordinator` 当前版本允许：

- 解析用户或 root 输入
- 压缩并归一化任务
- 输出稳定 `task_card`
- 调用 `provider_select` 做 provider 路由确认

`coordinator` 当前版本不允许：

- 自己执行任务
- 直接承担 worker 的工具调用职责
- 在信息不足时虚构约束、证据或输入
- 为了“显得聪明”而强行拆成多 worker

## 6. 为什么暂不实现 `structured-handoff` skill

蓝图里 `T9` 独立负责 skill 化的 handoff 协议。

因此 `T5` 先把 handoff 契约固化在 creature 模板里，确保主链可以继续向前推进；
等 `T9` 完成后，再把这份契约外提为可复用 skill，而不是现在提前把两个任务混在一起。

## 7. 最小验证方式

运行：

```bash
python .\examples\test-kit\scripts\verify_t5_coordinator.py
```

验证点：

- `test-kit` package 已声明 `coordinator` creature
- creature 配置存在且工具面保持为轻量协调集合
- prompt 明确包含 `task_card` 契约、禁止执行、自身边界与 provider 选路规则

## 8. 下一步建议

完成 `T5` 后，最自然的后续顺序是：

1. `T6` 实现 `worker-base`
2. `T7` 实现 `critic`
3. `T8` 用 `root-privileged + coordinator + worker-base + critic` 替换当前烟雾样板
