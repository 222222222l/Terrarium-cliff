# T6 `worker-base` 模板落地说明

本文件记录 `T6` 的实现边界、面向小参数模型的设计取舍与最小验证方式。

## 1. 本次实现包含什么

已新增 package 级 creature 模板：

- `examples/test-kit/creatures/worker-base/config.yaml`
- `examples/test-kit/creatures/worker-base/prompts/system.md`

已新增最小验证脚本：

- `examples/test-kit/scripts/verify_t6_worker_base.py`

## 2. 这次不是做“最强 worker”，而是做“最稳 worker”

`T6` 的目标不是在 base 模板里塞满工具和能力，而是在以下约束下尽量提高完成率：

- 可由 `qwen3-8b`、`qwen3.5-9b` 这类小参数模型驱动
- 默认本地部署友好
- 在有限工具面下仍能完成真实执行任务
- 后续可被 `swe-worker`、`docs-worker`、`ops-worker` 等派生模板继承

## 3. 参考了哪些主流结论

### 3.1 LangGraph / OpenAI Agents SDK 的共识

主流执行型 agent 都证明了一点：

- 真正影响稳定性的，不只是模型大小，更是执行 harness 是否受控
- 工具错误、重试、结构化结果和显式边界，比“多想几步”更重要

因此本模板采取：

- 窄工具面
- 显式输入契约
- 静默执行优先
- 结构化结果优先

### 3.2 Qwen / 本地 agent 相关结论

围绕 Qwen3 / Qwen3.5 与本地 tool calling 的公开资料，能提炼出几条非常稳定的经验：

1. 小模型更依赖原生工具调用与低温度设置
2. 工具数过多会显著降低调用稳定性
3. 对小模型来说，“知道何时不调用工具”与“知道如何调用工具”同样重要
4. 多步复杂规划应尽量上移到 `coordinator`，执行层只保留最小正确动作

因此本模板明确做了四个限制：

- 默认 `temperature: 0.0`
- 工具数量压到 8 个
- 不接 `bash` / `python` / `web_*` 这类高自由度工具
- 默认单步决策、单个动作推进

## 4. 为什么工具面要这么窄

当前 `worker-base` 只保留：

- `read`
- `edit`
- `glob`
- `grep`
- `json_read`
- `cli_invoke`
- `result_feedback`
- `stop_task`

原因不是这些工具“最全”，而是它们刚好覆盖了最常见的低歧义执行路径：

- 找目标：`glob` / `grep`
- 看内容：`read` / `json_read`
- 改内容：`edit`
- 跑命令：`cli_invoke`
- 收结果：`result_feedback`
- 终止：`stop_task`

更高自由度的工具交给派生 worker 再按需加上，避免 base 模板一开始就把小模型压垮。

## 5. 为什么默认模型配置偏本地

当前配置默认值为：

- `model: ${WORKER_LLM_MODEL:qwen3.5:9b}`
- `base_url: ${WORKER_LLM_BASE_URL:http://127.0.0.1:11434/v1}`

这不是强绑定 Ollama，而是把默认路径放在最符合“本地小模型执行端”的位置。

如果后续需要：

- 切到 vLLM
- 切到 LM Studio
- 切到远端 OpenAI-compatible provider

只需要改环境变量，不需要重写模板本身。

## 6. 当前权限边界

`worker-base` 当前版本允许：

- 在明确 `task_card` 约束下进行小步执行
- 调用静默执行工具并返回结构化结果
- 基于最小证据完成文件检查、局部修改和命令验证

`worker-base` 当前版本不允许：

- 重新规划整个任务
- 承担 root / coordinator 的职责
- 直接拥有高自由度 shell / Python / Web 执行面
- 在信息不足时凭空猜测并继续推进

## 7. 为什么不直接复用 `lab-runner`

`lab-runner` 是功能齐全的实验 creature，不是小模型友好的执行骨架。

它的问题不是“设计错了”，而是对 `worker-base` 来说太宽：

- 工具太多
- 子代理太多
- 更适合人工实验和能力验证
- 不适合作为 8B-9B 本地执行模型的默认模板

所以 `T6` 不是改造 `lab-runner`，而是提炼一个更窄、更稳、更可继承的基础层。

## 8. 最小验证方式

运行：

```bash
python .\examples\test-kit\scripts\verify_t6_worker_base.py
```

验证点：

- `test-kit` package 已声明 `worker-base` creature
- creature 配置存在且默认模型偏本地小模型
- 工具面被限制为 8 个
- prompt 明确包含小模型执行规则、任务卡输入契约、静默执行策略

## 9. 下一步建议

完成 `T6` 后，最自然的后续顺序是：

1. `T7` 实现 `critic`
2. `T8` 用 `root-privileged + coordinator + worker-base + critic` 接成真正的最小闭环
