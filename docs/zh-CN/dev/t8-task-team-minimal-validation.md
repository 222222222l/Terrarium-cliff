# T8 `task-team-minimal` 最小闭环落地说明

本文件记录 `T8` 的实现边界、为什么采用这条最短闭环、以及最小验证与联调方式。

## 1. 本次实现包含什么

已新增 package 级 terrarium：

- `examples/test-kit/terrariums/task-team-minimal/terrarium.yaml`

已新增 terrarium 专属 prompt：

- `examples/test-kit/terrariums/task-team-minimal/prompts/root.md`
- `examples/test-kit/terrariums/task-team-minimal/prompts/coordinator.md`
- `examples/test-kit/terrariums/task-team-minimal/prompts/worker.md`
- `examples/test-kit/terrariums/task-team-minimal/prompts/critic.md`

已新增最小验证脚本：

- `examples/test-kit/scripts/verify_t8_task_team_minimal.py`

## 2. 为什么这是“最短闭环”

当前闭环固定为：

- `root -> coordinator -> worker -> critic -> root`

其中特意采用：

- `root` 负责入口与最终决策
- `coordinator` 只编译 `task_card`
- `worker` 只执行
- `critic` 只审查并回注

中间三条边采用 `output_wiring`：

- `coordinator -> worker`
- `worker -> critic`
- `critic -> root`

这样做的原因是：

1. 它是最少角色数的完整主链
2. 中间传递不依赖角色自己记得发频道消息
3. `critic -> root` 回注后，root 可决定停止、追问用户或发起下一轮

这就形成了真正意义上的最小可复用闭环，而不是只把四个 creature 摆在一个文件里。

## 3. 为什么这里不用动态改图

`T4` 已经把 root 的图治理能力建好了，但 `T8` 的目标不是展示“会不会改图”，而是证明：

- 主链角色边界是否成立
- handoff 是否能稳定传递
- 执行与评审是否能闭环

所以这里故意把 `task-team-minimal` 固定成静态四节点基线团队，避免把运行稳定性建立在临时拓扑操作上。

## 4. 为什么增加 terrarium 专属 prompt

前面的 `T4-T7` 模板是通用模板，不应写死某个团队的接线习惯。

但 `T8` 要解决的是“这些通用模板接在一起后是否真的能跑”，所以这里增加了一层 terrarium 专属补充 prompt，用来把团队内约定压实：

- root 用 `group_send` 派发到 `coordinator`
- coordinator 在本团队中只输出 `task_card`
- worker 在本团队中只输出 `execution_packet`
- critic 在本团队中只输出 `review_result`

这不是和前面的模板重复，而是把“通用角色模板”和“特定团队配方”明确分层。

## 5. 为什么 recipe 级覆盖模型配置

`worker-base` 的默认配置偏本地 8B-9B 模型，
`critic` 的默认配置偏强通用审查模型，
这是正确的模板边界。

但在联调时，经常需要：

- 四个角色统一切到同一个兼容 API
- 用一个价格较低但能力足够的模型先跑通闭环

因此这里采用 recipe 级 controller 覆盖：

- `model: ${TASK_TEAM_MODEL:gemini-3-flash-preview}`
- `api_key_env: TASK_TEAM_API_KEY`
- `base_url: ${TASK_TEAM_BASE_URL:https://openrouter.ai/api/v1}`

这样不会污染基础模板，但可以快速切换整条团队链路。

## 6. 为什么它适合这次 A 股测试

你要的测试重点是“先跑通”：

- 用户给一个 A 股股票代码
- 系统查询该上市公司股票现状
- 给出简要分析与投资建议

`task-team-minimal` 适合这个测试，因为：

1. `coordinator` 能把请求压成单个 `task_card`
2. `worker` 能把它当成 `service_cli_task`，用 `cli_invoke` 调用命令式 HTTP 请求
3. `critic` 能基于执行结果给出结构化 review，并压缩回注给 root
4. root 能把最后结果直接回复用户，且中间始终保留打断入口

## 7. 最小验证方式

运行：

```bash
python .\examples\test-kit\scripts\verify_t8_task_team_minimal.py
```

验证点：

- `test-kit` package 已声明 `task-team-minimal` terrarium
- recipe 存在且 wiring 为 `coordinator -> worker -> critic -> root`
- recipe 采用 `TASK_TEAM_*` 级别的模型覆盖
- 四个 terrarium 专属 prompt 均已落盘

## 8. 联调建议

最简单的联调方式是：

1. 设置 `TASK_TEAM_BASE_URL`
2. 设置 `TASK_TEAM_API_KEY`
3. 设置 `TASK_TEAM_MODEL`
4. 运行 `task-team-minimal`
5. 直接向 root 输入任务

如果要自动化脚本验证，可用 `Terrarium.from_recipe(...)` 程序化加载后，对 `root` 调用 `inject_input(...)` 或 `chat(...)`。
