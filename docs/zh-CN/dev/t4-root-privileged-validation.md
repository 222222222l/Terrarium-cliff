# T4 `root-privileged` 模板落地说明

本文件记录 `T4` 的实现边界、设计取舍与最小验证方式。

## 1. 本次实现包含什么

已新增 package 级 creature 模板：

- `examples/test-kit/creatures/root-privileged/config.yaml`
- `examples/test-kit/creatures/root-privileged/prompts/system.md`

已新增最小验证脚本：

- `examples/test-kit/scripts/verify_t4_root_privileged.py`

## 2. 设计取舍

### 2.1 继承 Hermes 的优点

参考 `Hermes` 当前多智能体路线，保留以下优点：

- 用户只面对一个可见入口，而不是和所有角色混聊。
- root 只负责编排、路由、综合，不自己下场做 worker 工作。
- 子角色应保持职责清晰、上下文聚焦、工具边界明确。

### 2.2 避开 Hermes 当前的缺点

`Hermes` 当前公开设计里，多智能体仍在从“父委派子”向“真正协作”演进，已有问题包括：

- 容易停留在一次性委派而非稳定团队协作。
- 若入口角色不受约束，容易退化成既编排又执行的超级 agent。

因此本模板明确限制：

- root 不直接承担文件、shell、browser、web 执行职责。
- root 必须先看 `group_status`，再决定是否变更图结构。
- root 默认优先复用现有节点，不鼓励拓扑膨胀。

### 2.3 继承 OpenClaw 的优点

参考 `OpenClaw` 的 control plane / runtime 分层，保留以下优点：

- 把“控制面”和“执行面”显式分开。
- root 负责图管理、审批触发、状态综合，不负责具体执行。
- 让 worker / critic 保持在执行面，避免入口角色过度肥大。

### 2.4 避开 OpenClaw 当前的缺点

`OpenClaw` 相关设计讨论里暴露过几类风险：

- 过强隔离会造成信息孤岛。
- 多层转述会放大 token 成本。
- 若没有预算与治理约束，入口层容易无限派发。

因此本模板明确限制：

- root 只发送紧凑 task card，不传长链路叙述。
- root 不创建投机性 channel，不重复生成相同 worker。
- 高风险 graph 变更、破坏性 teardown、模糊路由决策默认回到用户确认。

## 3. 当前权限边界

`root-privileged` 当前版本允许：

- 通过 `group_*` 工具读取和编辑 terrarium 图。
- 通过 `ask_user` 请求补充条件或审批。
- 通过 `plan` / `summarize` 子代理做轻量规划与收束。
- 通过 `lab_report` 持久化编排实验结果。

`root-privileged` 当前版本不允许：

- 直接承担 worker 的文件读写、命令执行、网页操作职责。
- 在没有用户明确要求时生成新的 privileged node。
- 在没有 review 环节时默认跳过 critic。

## 4. 为什么现在不接入审批 / 预算 plugin

蓝图里 `T15-T16` 已明确：

- `approval-gate` 应优先复用 2.0 内置 `permgate`
- `budget-policy` 应优先复用 2.0 内置 `budget`

因此 `T4` 先完成 creature 模板本身，不提前把后续治理插件硬编码进模板，避免把阶段边界打乱。

## 5. 最小验证方式

运行：

```bash
python .\examples\test-kit\scripts\verify_t4_root_privileged.py
```

验证点：

- `test-kit` package 已声明 `root-privileged` creature
- creature 配置存在且引用正确的 `system.md`
- 工具面保持为 control-plane 最小集合
- prompt 明确包含权限边界与编排职责

## 6. 下一步建议

完成 `T4` 后，最自然的后续顺序是：

1. `T5` 实现 `coordinator`
2. `T6` 实现 `worker-base`
3. `T7` 实现 `critic`
4. `T8` 用上述模板替换现有烟雾样板，形成真正的 `task-team-minimal`
