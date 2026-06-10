# T7 `critic` 模板落地说明

本文件记录 `T7` 的实现边界、主流架构参考与最小验证方式。

## 1. 本次实现包含什么

已新增 package 级 creature 模板：

- `examples/test-kit/creatures/critic/config.yaml`
- `examples/test-kit/creatures/critic/prompts/system.md`

已新增最小验证脚本：

- `examples/test-kit/scripts/verify_t7_critic.py`

## 2. 这次不是做“小模型友好”模板，而是做“强模型友好”模板

和 `worker-base` 正好相反，`critic` 的目标不是极限收缩，而是在以下前提下保持稳健：

- 适配 `Gemini`、`DeepSeek V3` 等价格相对低但能力全面的通用强模型
- 复杂任务时可切换到闭源 SOTA 模型
- 能消化共享上下文或结构化压缩上下文
- 能把复杂 review 结果继续压缩成上游 agent 可直接注入的反馈包

## 3. 参考了哪些主流模式

### 3.1 LangGraph

保留其优点：

- 强调显式共享状态
- 复杂循环里优先依赖状态对象，而不是靠隐式聊天记忆
- 人工介入点与恢复点可以被明确建模

落地方式：

- `critic` 明确接受 `shared_context` 或 `shared_context_packet`
- 输出 `root_context_patch`，让上游 agent 可以继续迭代而不必重放整个评审过程

### 3.2 OpenAI Agents SDK

保留其优点：

- handoff 默认携带历史
- 在需要降低成本时可通过 context transform / input filter 只传递必要上下文

落地方式：

- `critic` 同时支持“共享完整上下文”和“结构化压缩注入”两种模式
- `context_basis` 字段显式标记当前 review 的依据范围

### 3.3 AutoGen / Microsoft Agent Framework

保留其优点：

- reflection / writer-reviewer 循环依赖明确的消息协议
- reviewer 输出应是 typed message，而不是随意吐槽

落地方式：

- `critic` 输出固定 `review_result` 契约
- `status`、`required_changes`、`route_to`、`next_iteration_goal` 等字段直接服务于下一轮循环

### 3.4 CrewAI

保留其优点：

- reviewer 能消费前序任务上下文
- Human-in-the-Loop 可以在 review 后介入，而不是只在最开始审批

规避其缺点：

- 不让 `critic` 变成高 token chatter 的角色
- 不让 review 结果变成只能给人看、不能给 agent 继续消费的长文本

落地方式：

- `critic` 接入 `result_feedback`
- 复杂 review 可同时生成用户侧摘要和 agent 侧结构化反馈

## 4. 为什么这版 `critic` 更适合强模型

`critic` 当前版本不是靠更多工具取胜，而是靠更强的上下文处理边界：

- 能吃共享上下文
- 能吃压缩包
- 能基于 artifact 直接裁定
- 能把复杂 judgment 再压缩成上游可继续迭代的结构化结果

这类工作更适合能力全面、上下文耐受性更高的模型，而不适合作为本地 8B worker 的默认职责。

## 5. 当前工具面为什么是中等宽度

当前 `critic` 保留：

- `read`
- `glob`
- `grep`
- `json_read`
- `scratchpad`
- `think`
- `ask_user`
- `info`
- `stop_task`
- `result_feedback`
- `lab_report`

这样做的原因是：

- 它需要直接读取 artifact 和结构化结果
- 它需要在复杂 review 时做上下文压缩
- 它需要保留人类可中断、可插话的通道

但它依然不直接承担 worker 的 shell / Python / Web 执行职责。

## 6. 为什么默认模型配置偏云端通用强模型

当前配置默认值为：

- `model: ${CRITIC_LLM_MODEL:deepseek/deepseek-chat-v3}`
- `base_url: https://openrouter.ai/api/v1`

这样做的原因不是强绑定某家 provider，而是：

- 默认给出一个“成本较低但能力较强”的通用 critic 起点
- 通过环境变量可快速切到 `Gemini` 或更强的闭源模型

例如后续可以切到：

- `Gemini` 系列强模型
- 更强的 `OpenAI` / `Claude` 级审查模型
- 其他兼容 OpenAI API 的高上下文模型

## 7. 这次最关键的新增能力

### 7.1 双上下文模式

`critic` 不再默认假设自己一定有完整历史，而是接受三种审查依据：

- `shared_context`
- `compressed_context`
- `artifact_only`

这让它既能在“顶层共享完整上下文”的稳健模式里工作，也能在“只注入压缩包”的低成本模式里工作。

### 7.2 上游回注通道

`critic` 的输出不是单纯给人看，而是要继续喂给上游 agent。

因此模板要求输出：

- `root_feedback_summary`
- `root_context_patch`
- `route_to`
- `next_iteration_goal`

这些字段能直接进入下一轮 `root` 或 `coordinator` 决策。

### 7.3 用户可打断通道

模板显式支持：

- `user_interrupt_recommended`
- `user_interrupt_reason`

并允许在真正需要人类判断时调用 `ask_user` 或用 `result_feedback` 生成面向用户的暂停摘要。

## 8. 为什么暂不实现 `review-protocol` skill

蓝图里 `T10` 独立负责 skill 化的 review 协议。

因此 `T7` 先把最重要的审查契约固化在 creature 模板里，确保主链继续推进；
等 `T10` 完成后，再把这份协议外提为独立 skill。

## 9. 最小验证方式

运行：

```bash
python .\examples\test-kit\scripts\verify_t7_critic.py
```

验证点：

- `test-kit` package 已声明 `critic` creature
- creature 配置存在且默认模型偏强通用 critic
- prompt 明确包含共享上下文 / 压缩上下文双模式
- prompt 明确包含 `review_result` 契约、上游回注字段和用户中断字段
- 模板已接入 `result_feedback`

## 10. 下一步建议

完成 `T7` 后，最自然的后续顺序是：

1. `T8` 用 `root-privileged + coordinator + worker-base + critic` 组成真正的最小闭环
2. `T10` 将当前 review 契约外提为独立 `review-protocol` skill
