---
title: 外部 CLI 兼容抽象层设计
summary: 为 CLI-Anything 与 OpenCLI 设计统一的私有兼容抽象、registry 约定与静默执行调用协议。
tags:
  - dev
  - cli
  - compatibility
  - architecture
---

# 外部 CLI 兼容抽象层设计

本文档对应 `T20`，目标是在不扩大核心改造面的前提下，为 `CLI-Anything` 与 `OpenCLI` 设计一层统一、可控、低 token 的私有兼容抽象。

## 1. 设计目标

本抽象层必须同时满足四个约束：

1. `CLI-Anything` 能作为主兼容标准接入。
2. `OpenCLI` 能作为浏览器 / 登录态专项 provider 接入。
3. 执行层默认静默，不把过程 token 回传给模型。
4. 尽量复用 `KohakuTerrarium` 现有扩展点，不新增高成本核心协议。

## 2. 第一性原则

先从问题本身出发，而不是从外部项目的目录结构出发。

私有 agent 生态真正需要的不是“兼容两个仓库的全部实现”，而是兼容三种最小能力：

- **发现**：知道当前有哪些外部 CLI 能力可用。
- **选择**：在编排阶段为任务选对 provider。
- **调用**：以结构化、静默、可审计的方式执行命令并回收结果。

因此本阶段不追求：

- 复制 `CLI-Anything` 的全量 hub/runtime
- 复制 `OpenCLI` 的全部 adapter/runtime
- 修改 KT 核心去新增专用 manifest 槽位

## 3. 现有扩展点已经足够

当前仓库已有的扩展点已经能承载兼容层，不需要先改核心抽象：

- `package`：
  - `kohaku.yaml` 已能分发 `tools`、`plugins`、`skills`、`prompts`、`commands`
  - 适合承载私有 CLI registry、封装工具、策略插件和 skill
- `tool`：
  - `ToolContext` 已提供 `working_dir`、`memory_path`、`runtime_services`
  - 适合承载统一命令调用包装器
- `plugin`：
  - `pre_tool_dispatch`、`pre_tool_execute`、`post_tool_execute`
  - `runtime_services()`
  - 适合做 provider 探测、权限控制、预算、静默执行守卫、结果标准化
- `skill`：
  - 适合承载 provider 选择规则、任务模板、反馈模板

结论：`T20` 的最优路径不是改 KT 核心协议，而是在私有 package 内建立一层兼容规范。

## 4. 兼容层总架构

兼容层分为四层：

1. **Registry 层**
   - 记录有哪些 provider / harness / capability 可用
2. **Routing 层**
   - 根据任务类型与约束选择 `CLI-Anything` 或 `OpenCLI`
3. **Invocation 层**
   - 以统一参数调用外部 CLI
4. **Result 层**
   - 回收结构化结果、产物路径、错误摘要，默认不回传执行过程

## 5. 为什么不新增核心 manifest 槽位

本阶段不建议在 `kohaku.yaml` 顶层新增如 `cli_providers:` 的核心槽位，原因如下：

- 这会把一个仍在探索的私有抽象提前固化到框架层
- `T21-T25` 还没有完成，过早进入核心协议会放大回滚成本
- 当前 `tools/plugins/skills/prompts` 已足够表达这层能力
- 私有 agent 生态首先需要的是“能跑、可控、可审计”，而不是“漂亮的新全局 schema”

因此 `v1` 采用：

- `kohaku.yaml` 只声明承载兼容层的 `tool/plugin/skill`
- 私有 CLI registry 使用 package 内自定义文件约定

## 6. 推荐目录约定

建议把兼容层做成私有 package 的一部分，目录如下：

```text
my-private-pack/
  kohaku.yaml
  cli_registry/
    registry.yaml
    providers/
      cli_anything.yaml
      opencli.yaml
  skills/
    cli-provider-selection/
      SKILL.md
    cli-result-analysis/
      SKILL.md
  my_private_pack/
    tools/
      cli_invoke.py
    plugins/
      cli_provider_registry.py
      cli_execution_policy.py
      cli_audit.py
```

说明：

- `cli_registry/` 是 **包内私有协议**，不是 KT 核心协议
- `cli_invoke.py` 是统一入口工具
- `cli_provider_registry.py` 负责加载 registry，并通过 `runtime_services()` 暴露给 tool
- `cli_execution_policy.py` 负责静默执行、白名单、失败升级
- `cli_audit.py` 负责结果留痕

## 7. 统一抽象对象

### 7.1 `CliProviderSpec`

表示一个外部 CLI provider 的基础能力。

建议字段：

```yaml
name: cli-anything
kind: harness
enabled: true
priority: 100
command: cla
install_hint: pip install cli-anything
healthcheck:
  - cla --version
supports:
  - local_software
  - desktop_app
  - private_tool
restrictions:
  requires_network: false
  requires_browser_session: false
```

字段解释：

- `name`：私有系统内的 provider 名称
- `kind`：`harness` / `browser` / `hybrid`
- `command`：命令前缀或入口
- `healthcheck`：可用性探测命令
- `supports`：能力标签
- `restrictions`：执行前约束

### 7.2 `CliCapabilitySpec`

表示 provider 提供的某类能力，而不是某个原生命令的全量镜像。

建议字段：

```yaml
name: browser_fetch
provider: opencli
task_kinds:
  - web_research
  - social_ops
invoke_mode: silent
artifacts:
  - markdown_report
  - screenshot
```

设计原则：

- 私有生态暴露的是“能力名”，不是外部 CLI 的全部子命令
- 这样才能避免把外部命令全集直接暴露给所有 creature

### 7.3 `CliInvocation`

表示一次统一调用请求。

建议字段：

```yaml
provider_name: cli-anything
capability: local_software_task
task_id: task-001
goal: Generate a release report
arguments:
  app: excel
  action: export
artifact_dir: .kohaku/artifacts/task-001/
timeout_s: 120
token_budget_mode: silent
```

### 7.4 `CliExecutionRecord`

表示一次调用后的统一结果。

建议字段：

```yaml
provider_name: cli-anything
capability: local_software_task
success: true
exit_code: 0
stdout_summary: report exported
stderr_summary: ""
artifact_paths:
  - .kohaku/artifacts/task-001/report.xlsx
duration_ms: 8421
raw_log_path: .kohaku/logs/task-001.jsonl
retryable: false
```

## 8. Registry 协议

`registry.yaml` 只维护私有抽象，不直接照搬外部项目格式。

建议结构：

```yaml
version: 1
providers:
  - name: cli-anything
    spec_file: providers/cli_anything.yaml
  - name: opencli
    spec_file: providers/opencli.yaml
capabilities:
  - name: local_software_task
    provider: cli-anything
    task_kinds: [ops, docs, research]
  - name: browser_fetch
    provider: opencli
    task_kinds: [web_research, social_ops]
defaults:
  provider_order:
    - cli-anything
    - opencli
```

优势：

- registry 面向 **私有任务语义**，不是外部命令语义
- 后续即使替换 provider，只要 capability 不变，上层任务协议就不必大改

## 9. 与两个外部 CLI 的映射方式

### 9.1 `CLI-Anything`

定位：

- 主兼容标准
- 承担通用软件工具、私有 harness、专业应用调用

映射原则：

- 私有 capability 优先映射到 `CLI-Anything` harness
- 不透传其完整内部方法论给上层 creature
- 上层只感知：
  - 它能做什么
  - 如何探活
  - 调用要哪些参数
  - 会产出什么 artifact

### 9.2 `OpenCLI`

定位：

- 浏览器 / 登录态 / Web / Electron 专项 provider

映射原则：

- 只映射为专项 capability
- 默认不进入 provider 默认优先级首位
- 必须受浏览器会话、权限、登录态检测约束

## 10. 统一调用协议

兼容层的调用流程固定如下：

1. `coordinator` 生成 task card，并声明：
   - `task_kind`
   - `preferred_provider`
   - `artifact_expectation`
   - `token_budget_mode`
2. `worker-base` 调用统一工具 `cli_invoke`
3. `cli_invoke` 从 `runtime_services["cli_registry"]` 读取 provider/capability 映射
4. `cli_execution_policy` plugin 在 `pre_tool_execute` 中做：
   - provider 是否可用
   - 参数是否合法
   - 是否允许静默执行
   - 是否需要审批
5. 工具执行命令并把原始输出写入文件，而不是长流返回
6. `post_tool_execute` 将结果标准化为 `CliExecutionRecord`
7. `critic` / `curator` 仅读取摘要与 artifact

## 11. 静默执行协议

这是本抽象层最重要的约束。

### 11.1 默认规则

- 正常执行时：
  - 不回传完整 stdout
  - 不逐步解释命令动作
  - 不让模型消费过程 token
- 只返回：
  - 成功 / 失败
  - 最小摘要
  - artifact 路径
  - 原始日志路径

### 11.2 何时允许升级为“最小诊断模式”

只有以下情况才允许给模型额外上下文：

- 退出码非零
- `stderr_summary` 无法归类
- 规则化重试失败
- 执行结果与 `artifact_expectation` 明显不符

即使升级，也只允许回传：

- 最小错误片段
- 被调用的 capability
- provider 名称
- artifact 缺失信息

### 11.3 为什么这样设计

- 任务编排阶段需要 token，因为要做任务理解和 provider 选择
- 结果分析阶段需要 token，因为要做效果判断和记忆沉淀
- 执行阶段本质是确定性命令过程，不应持续占用 token

## 12. 与 KT 现有模块的映射

### `package`

负责：

- 分发 registry 文件
- 分发 `cli_invoke` 工具
- 分发 provider 相关 plugin 与 skill

### `tool`

负责：

- 统一执行入口
- 命令调用
- 产物路径回收

不负责：

- provider 选择策略
- 权限判定
- 审计策略

### `plugin`

负责：

- provider 探活
- 权限控制
- 预算限制
- 静默执行策略
- 审计记录

### `skill`

负责：

- provider 选择规则
- task card 中的字段规范
- 结果分析协议

## 13. `T21-T25` 的直接接口

这份抽象设计为后续任务提供边界：

- `T21`
  - 只需要实现 `CLI-Anything -> CliProviderSpec/CliCapabilitySpec` 的映射
- `T22`
  - 只需要实现 `OpenCLI -> CliProviderSpec/CliCapabilitySpec` 的映射
- `T23`
  - 只需要围绕 `CliExecutionRecord` 落地静默执行
- `T24`
  - 只需要让 task card 补齐 provider 选择字段
- `T25`
  - 只需要定义基于 `CliExecutionRecord + artifacts` 的分析协议

## 14. 决策总结

`T20` 的最终设计决策如下：

1. 主兼容标准选 `CLI-Anything`
2. `OpenCLI` 只做专项 provider
3. 不新增 KT 核心 manifest 槽位
4. 兼容层先做成私有 package 内协议
5. 统一入口是 `cli_invoke`
6. 统一结果是 `CliExecutionRecord`
7. 执行层默认静默，失败才最小升级

## 15. 审阅重点

审阅本设计时，优先看以下问题：

1. 这层抽象是否真的避免了把外部 CLI 的全部复杂性暴露给上层 creature？
2. `CLI-Anything` 作为主兼容标准、`OpenCLI` 作为专项 provider 的分工是否足够清晰？
3. 不新增核心 manifest 槽位，是否符合当前阶段“最小成本验证”的目标？
4. `CliExecutionRecord` 是否足以支撑后续静默执行、反馈分析和审计？
