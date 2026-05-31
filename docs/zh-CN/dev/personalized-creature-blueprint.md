---
title: 个性化 Creature 蓝图（2.0 校正版）
summary: 面向 KohakuTerrarium 2.0 的个性化 creature 模板生态蓝图、2.0 基线约束、任务拆解与持续追踪清单。
tags:
  - dev
  - creature
  - roadmap
  - personalization
  - kt2
---
# 个性化 Creature 模板体系开发蓝图（2.0 校正版）
本文档是后续开发的唯一追踪入口，目标是在 `KohakuTerrarium 2.0` 现有 runtime、package、Studio 与 API 能力之上，补出一层高度通用、可复用、可治理、可演化的 creature 模板生态。

本版文档结合以下两类事实重新整理：
- 既有会话推进过程中已经完成的设计、验证与实验资产。
- 基于当前仓库 2.0 代码树与文档现实得到的校正结论。

旧版文档已备份到：`docs/zh-CN/dev/personalized-creature-blueprint.backup-pre-v2-rewrite.md`。

## 1. 文档定位
本文件同时承担三项职责，但优先级明确如下：
1. **架构追踪入口**：说明目标、边界、不变量与阶段路线。
2. **任务台账**：原地更新状态，不再维护第二份 todo 文档。
3. **2.0 校正记录**：明确哪些 1.0 时代的设计可以继承，哪些必须重构后才能在 2.0 生效。

状态值说明：
- `已完成`：已在当前仓库完成，且与 2.0 现实一致。
- `进行中`：已开始，但尚未达到完成标准。
- `待开始`：尚未开始实现。
- `待重构`：历史上已做过设计或实现，但在 2.0 下尚未按真实运行方式落地。

## 2. 2.0 基线结论
以下判断是后续一切任务拆解的前提：

| 主题 | 2.0 现实 | 结论 |
|---|---|---|
| package manifest | `kohaku.yaml` 仍是标准入口 | 可直接继承 |
| creature 配置 | `config.yaml/.yml/.json/.toml` 仍受支持 | 可直接继承 |
| plugin hooks | `on_load`、`pre_tool_dispatch`、`pre_tool_execute`、`post_tool_execute` 等都存在 | 可直接继承 |
| ToolContext | `working_dir`、`memory_path`、`runtime_services` 等能力存在 | 可直接继承 |
| 原生 skill | `SKILL.md` 仍是框架原生格式 | 格式可继承 |
| 项目级 skill 路径 | 2.0 不扫描 `.trae/skills/`；应使用 `.kt/skills/`、`.claude/skills/`、`.agents/skills/` 或 package `skills:` | 必须重构 |
| terrarium channel `type` | 2.0 中 `type: queue/broadcast` 不再是有效语义，channel 实际按 broadcast 处理 | 必须清理 |
| cross-cutting plugin | 2.0 已内置 `permgate`、`budget`、`sandbox`、`compact.auto` | 需复用而非重复造轮子 |
| identity | 多用户与权限隔离位于 API / Studio 边界，不应下沉到 creature prompt | 必须纳入蓝图不变量 |
| package / marketplace | 2.0 已有 package 安装、来源、缓存与 marketplace 机制 | 应纳入分发治理设计 |
| MCP | 2.0 已把 MCP 作为正式能力接入面 | 应纳入统一能力路由 |

## 3. 项目目标
本蓝图要解决的不是“再做几个 agent 配置”，而是以下六个项目级问题：
1. **模板生态薄弱**：框架能力强，但缺少可直接复用的高质量 creature 模板与 package 骨架。
2. **个性化沉淀不足**：会话、memory、compaction 已有基础，但缺少稳定的“用户偏好 / 项目规则 / 操作习惯”治理层。
3. **演化闭环缺失**：尚无“从历史会话中提取规则 -> 生成 skill 草案 -> 审批 -> 生效 -> 回滚”的标准路径。
4. **多 agent 成本高**：角色拆分后容易出现通信膨胀、语义漂移和维护成本上升，缺少一套低耦合的模块边界。
5. **能力路由不统一**：2.0 下已有 built-in tools、MCP、package、CLI provider 等多种能力来源，但缺少统一选路策略。
6. **2.0 适配断层**：已有部分设计与文档在方向上正确，但未按 2.0 的真实发现路径、channel 语义与内置插件体系落地。

## 4. 设计原则
1. **先补能力层，再补角色数量**：优先沉淀可复用模板、协议和治理机制，而不是堆更多常驻 creature。
2. **个性化能力保持外挂层**：尽量叠加在 KT 2.0 原生 runtime 之上，不深侵入正在高频演化的核心模块。
3. **主工作流最小化**：高频主链只保留 `root -> coordinator -> worker -> critic` 这条最短路径。
4. **学习与执行解耦**：`curator` 和 `evolver` 不进入每次任务的主链路，优先做后台或低频触发角色。
5. **跨切面问题不用 creature 承担**：预算、审批、安全、审计优先用 plugin 或 API 边界能力处理，而不是单独做“守门员 creature”。
6. **skill 与 package 必须走原生发现路径**：不再依赖 `.trae` 一类 IDE 私有目录约定。
7. **terrarium 不再假设队列语义**：以 `listen` / `can_send`、DM channel、output wiring 等 2.0 真实能力组织协作。
8. **执行层默认静默**：能只用命令行完成的步骤就只走命令行，不向模型持续回传执行细节。
9. **只在必要节点消耗 token**：默认只在“任务编排与派发”和“执行完成后的效果反馈分析”两个阶段输出 token。
10. **准确性优先于可见性**：执行过程可以不输出，但必须保留结构化结果、退出码、错误摘要和可审计日志。
11. **长链路控制必须有正式完成判定**：不得依赖“assistant 消息数”“文件时间戳”之类弱信号，统一以 turn barrier / idle barrier 作为脚本与服务层的完成协议。
12. **模块先自描述，再暴露配置**：新增 tool / plugin / adapter 时先声明默认配置与可调 schema，再决定是否自动写回具体 agent 配置文件。
13. **身份边界不进入 runtime 设计**：多用户、管理员、主机级权限属于 API / Studio / identity 层，不混入 creature 模板的人格定义。
14. **发布与回滚必须可治理**：skill、package、prompt、memory schema 的升级都要有来源、版本与回滚策略。

## 5. 系统不变量
以下规则在后续实现中不应被破坏：
1. `root-privileged` 是团队外部总入口，不是 terrarium 内的平级节点。
2. creature 负责角色化执行，terrarium 只负责 wiring，不承担额外智能。
3. identity、账户、主机级权限与多用户隔离发生在 API / Studio 边界，不强行塞进 creature prompt。
4. MCP、built-in tools、`CLI-Anything`、`OpenCLI` 都只是能力来源，不等同于角色本身。
5. 正常执行默认只回收结构化产物，不把长过程 token 直接回放给模型。
6. 任何自动生成的 skill、prompt、rule、memory 升级都必须先形成草案，再审批，再生效。
7. 当前项目的私有扩展优先保持为 package、skills、plugins、docs、examples 与少量独立模块，不直接深改 2.0 核心运行时。

## 6. 模块归属规则
以下边界是后续开发时的判断准绳：

| 需求类型 | 推荐模块 | 解决的问题 | 不建议放在哪里 |
|---|---|---|---|
| 角色职责、语气、行为边界 | `creature` | 复用角色模板，保持人格与工作方式一致 | `plugin` |
| 单个 creature 内部的只读/局部协作 | `subagent` | 降低横向通信成本 | `terrarium` |
| 跨任务可复用的流程知识、handoff 协议、评审规范 | `skill` | 避免 prompt 重复堆砌 | `system.md` 长文本硬编码 |
| 安全、审批、预算、审计、策略拦截 | `plugin` | 处理 cross-cutting concern | 额外的“守门 creature” |
| 多 creature 拓扑、channel、output wiring | `terrarium` | 组织高频主链协作 | `subagent` |
| 目录结构、共享模板、私有工具、技能集合 | `package` | 提升安装复用能力 | 单个 `examples/` 目录 |
| 短期工作记忆、事件检索、resume、压缩 | `session` / `memory` / `compact` | 复用现有 runtime 能力 | 自建第二套 memory 系统 |
| 个性化长期治理 | `curator creature + memory schema + plugin guard` | 把 session 信息变成可持续资产 | 只靠 `memory_write` 直接写文件 |
| 外部 CLI 生态兼容、安装、发现、调用适配 | `package` + `plugin` + `worker-base` | 把外部能力纳入私有 agent 生态，同时控制 token 开销 | 直接把外部 CLI 暴露给所有 creature |
| 第三方工具动态接入 | `MCP` + `mcp_servers` + meta-tools | 让外部 server 能被标准方式接入 | 私有 CLI 模拟一切 |
| 用户、管理员、主机级身份与设置治理 | `API` + `Studio` + `identity` | 把权限边界放在正确层次 | `creature` prompt |
| package 分发、来源、缓存、安装、更新 | `marketplace` + `package` | 管理可安装资产的生命周期 | 把安装协议写死在单个 skill |

## 7. 推荐模板体系
第一阶段继续采用 `4+1+1` 模型，但按 2.0 现实补全边界：
- `root-privileged`：用户入口、权限审批、group 管理、最终汇报。
- `coordinator`：需求拆解、任务派发、结构化 handoff、能力选路。
- `worker-base`：统一执行骨架，再派生出具体工作型 worker。
- `critic`：结构化验收、风险判断、驳回与补证据。
- `curator`：记忆治理、归档、压缩、去重、价值升级。
- `evolver`：从历史中提出 skill / prompt / rule 草案，默认离线或低频触发。

推荐分层：
- **管理面**：`root-privileged` + `Studio/catalog/identity`。
- **执行面**：`coordinator + worker-base + critic`。
- **学习面**：`curator + evolver`。

## 8. 统一能力路由策略
2.0 之后，模板体系不应只围绕 CLI 兼容层设计，而应统一按以下顺序选路：
1. **内建工具 / 内建子代理**：优先使用框架原生能力。
2. **MCP**：当外部能力已有标准 MCP server 时，优先走 MCP。
3. **`CLI-Anything`**：用于通用本地软件能力、私有 registry 与 CLI harness。
4. **`OpenCLI`**：用于网页登录态、浏览器、桌面自动化等专项 provider。
5. **自定义外部桥接**：仅在以上路径都不合适时补充。

约束：
- `coordinator` 只做选路与任务卡标注，不直接执行高噪声命令。
- `worker-base` 负责执行包装、产物落盘与失败分级。
- `critic` 和 `curator` 只消费结构化产物，不回放完整执行过程。

## 9. 统一协议清单
后续所有模板、skill、tool、plugin 尽量围绕以下五类协议收敛：
1. `task_card`
   - 关键字段：`task_id`、`goal`、`constraints`、`inputs`、`deliverable`、`evidence_needed`、`done_definition`、`preferred_provider`、`artifact_expectation`、`open_questions`
2. `execution_artifact`
   - 关键字段：`exit_code`、`stdout_summary`、`stderr_summary`、`artifact_paths`、`provider_name`、`duration_ms`、`retry_classification`
3. `review_result`
   - 关键字段：`status`、`requirements_covered`、`missing_evidence`、`risks`、`required_changes`、`confidence`
4. `memory_record`
   - 关键字段：`scope`、`category`、`source`、`dedupe_key`、`confidence`、`retention`、`archive_path`
5. `evolution_draft`
   - 关键字段：`source_sessions`、`problem_pattern`、`proposal_type`、`applicability`、`risk`、`rollback`、`approval_required`

## 10. 阶段路线
### Phase A：2.0 基线校正
先纠正所有“方向对，但 2.0 下不会真实生效”的设计。
输出物：
- 新版蓝图文档
- skill 原生发现路径迁移方案
- terrarium channel 语义清理方案
- 治理 plugin 的内置复用策略
- 能力路由与 package 分发策略

### Phase B：最小主工作流
只做能跑通主工作流的最短闭环：
- `root-privileged`
- `coordinator`
- `worker-base`
- `critic`
- `task-team-minimal`
目标：验证模板体系不是概念图，而是真的能在 2.0 下替代一部分重复造轮子。

### Phase C：记忆治理
加入 `curator`，把“任务完成后如何沉淀偏好和规范”标准化。
目标：把 session 历史转化为高价值、低噪声、分层明确的长期 memory。

### Phase D：治理插件
对接 2.0 内置 `permgate`、`budget`、`sandbox`，并补项目特有的 `audit-guard`。
目标：确保个性化能力增强不会突破权限、安全与成本边界。

### Phase E：可控演化
设计 `evolver` 与草案审批流，但默认不自动生效。
目标：先形成“提案系统”，再决定是否开放“自动应用”。

## 11. 任务追踪清单
说明：
- 每项任务都必须在本文件内原地更新状态。
- 完成时将 `状态` 改为 `已完成`，并勾选任务标题。
- 若任务被拆分，保留父任务并在“备注”中追加子项，不另起第二套追踪文档。
- 若任务在历史上完成过设计，但 2.0 下未真实生效，应标记为 `待重构`，而不是误记为 `已完成`。

### 任务组 A. 蓝图与边界
- [x] `T0` 编写模板体系蓝图文档
  - 状态：已完成
  - 解决问题：项目缺少可执行的个性化 creature 设计总图，容易边做边漂移
  - 适合模块：`docs`
  - 交付物：蓝图总文档
  - 完成标准：文档明确目标、模块边界、阶段路线、任务清单
  - 备注：后续所有任务以本文件为唯一追踪入口
- [x] `T1` 定义模块归属规则
  - 状态：已完成
  - 解决问题：不清楚哪些能力该放在 creature、plugin、skill、package、MCP、Studio
  - 适合模块：`docs`
  - 交付物：模块职责表、反模式清单
  - 完成标准：后续新增功能都能依据本规则判断落点
- [x] `T29` 完成 2.0 基线校正并重写蓝图
  - 状态：已完成
  - 解决问题：旧蓝图混用了 1.0 时代假设与 2.0 现实，继续沿用会误导后续实现
  - 适合模块：`docs`
  - 交付物：本文件的 2.0 校正版
  - 完成标准：明确 skill 路径、channel 语义、内置 plugin 复用与 2.0 新边界
  - 备注：旧版已备份到 `personalized-creature-blueprint.backup-pre-v2-rewrite.md`

### 任务组 B. Package 骨架与分发
- [x] `T2` 创建个性化模板 package 骨架
  - 状态：已完成
  - 解决问题：模板无法版本化、安装化、共享化
  - 适合模块：`package`
  - 交付物：`kohaku.yaml`、`creatures/`、`terrariums/`、工具模块骨架
  - 完成标准：能被 `kt` 识别为完整 package
  - 备注：已创建 `examples/test-kit/`
- [x] `T3` 设计目录与命名约定
  - 状态：已完成
  - 解决问题：后续模板扩展缺少统一布局，容易演变为示例堆叠
  - 适合模块：`package`
  - 交付物：目录规范、命名规范、模板继承规范
  - 完成标准：新增 creature / skill / plugin 时不需要重新讨论目录形态
  - 备注：规范文档见 `docs/zh-CN/dev/package-naming-conventions.md`
- [ ] `T35` 定义 package / marketplace 发布与版本治理策略
  - 状态：待开始
  - 解决问题：私有模板体系缺少可发布、可升级、可回滚的分发生命周期设计
  - 适合模块：`package` + `marketplace` + `docs`
  - 交付物：来源策略、版本策略、editable 开发策略、回滚策略
  - 完成标准：本地开发、私有发布、后续升级三条路径都被明确描述

### 任务组 C. 主工作流模板
- [x] `T4` 实现 `root-privileged` 模板
  - 状态：已完成
  - 解决问题：缺少通用入口、审批点和 graph 管理角色
  - 适合模块：`creature` + `terrarium`
  - 交付物：模板 config、system prompt、权限边界说明
  - 完成标准：能统一接用户任务、查询团队状态、触发审批
  - 备注：已新增 `examples/test-kit/creatures/root-privileged/`、`docs/zh-CN/dev/t4-root-privileged-validation.md` 与验证脚本；模板保持 control-plane 最小工具面，运行时优先对接 2.0 的 privileged `group_*` 工具
- [x] `T5` 实现 `coordinator` 模板
  - 状态：已完成
  - 解决问题：用户意图到执行任务之间缺少稳定的结构化 handoff
  - 适合模块：`creature` + `skill`
  - 交付物：模板 config、handoff 协议、必要子代理组合
  - 完成标准：输出稳定的 `task_card`，而不是松散自然语言
  - 备注：已新增 `examples/test-kit/creatures/coordinator/`、`docs/zh-CN/dev/t5-coordinator-validation.md` 与验证脚本；当前先将 handoff 契约固化在 creature 模板中，待 `T9` 再外提为独立 skill
- [x] `T6` 实现 `worker-base` 模板
  - 状态：已完成
  - 解决问题：执行型 creature 缺少统一骨架，具体 worker 难以派生
  - 适合模块：`creature` + `subagent`
  - 交付物：模板 config、可继承的 prompt、工具边界
  - 完成标准：能低成本派生出至少一个具体 worker
  - 备注：已新增 `examples/test-kit/creatures/worker-base/`、`docs/zh-CN/dev/t6-worker-base-validation.md` 与验证脚本；模板明确面向本地 8B-9B 级小模型做窄工具面与静默执行优化
- [x] `T7` 实现 `critic` 模板
  - 状态：已完成
  - 解决问题：反馈与验收缺少标准协议，难以形成高质量闭环
  - 适合模块：`creature` + `skill`
  - 交付物：review 协议、模板 config、输出格式
  - 完成标准：对 worker 产出进行结构化判定与打回
  - 备注：已新增 `examples/test-kit/creatures/critic/`、`docs/zh-CN/dev/t7-critic-validation.md` 与验证脚本；模板支持共享上下文与压缩上下文双模式，并把 review 结果压缩为可回注上游 agent 的结构化反馈
- [x] `T8` 实现 `task-team-minimal` terrarium
  - 状态：已完成
  - 解决问题：模板体系如果没有最小联调样板，就无法证明其真实可用
  - 适合模块：`terrarium`
  - 交付物：`root + coordinator + worker + critic` 最小团队
  - 完成标准：能跑通一条完整任务链
  - 备注：已新增 `examples/test-kit/terrariums/task-team-minimal/`、`docs/zh-CN/dev/t8-task-team-minimal-validation.md`、验证脚本与 demo 脚本；采用 `coordinator -> worker -> critic -> root` 的固定 `output_wiring`，并通过 recipe 级 controller 覆盖支持整队切到同一个兼容模型联调，不依赖 `type: queue/broadcast` 旧语义
- [ ] `T36` 建立长链路 turn barrier / idle barrier 稳定层
  - 状态：进行中
  - 解决问题：demo、harness 与 Studio 外挂脚本此前依赖弱信号判断“本轮结束”，导致长链路常被过早关闭或误判超时
  - 适合模块：`terrarium` + `service` + `examples`
  - 交付物：正式等待接口、增量输出读取能力、`task-team-minimal` 的 output log 配置示例
  - 完成标准：脚本不再通过消息数或文件时间戳判断 turn 完成，至少 `test-kit` 演示链路切到统一等待协议
  - 备注：当前已在 `LocalTerrariumService` 增加本地 turn 控制辅助，并接通 `task-team-minimal` 的 `output_log`
- [ ] `T37` 建立模块自描述与配置项自动写回机制
  - 状态：进行中
  - 解决问题：新增自定义模块后，agent 配置里没有同步出现可改入口，导致模块可复用但不可治理
  - 适合模块：`examples/test-kit` + `docs`
  - 交付物：模块默认配置声明、同步脚本、已落盘的示例 creature 配置项
  - 完成标准：`test-kit` 中新增具备 schema/defaults 的自定义模块后，可通过同步器自动把默认配置项写入对应 agent `config.yaml`
  - 备注：当前已为 `cli_invoke`、`provider_select`、`result_feedback`、`lab_report` 加入默认配置声明，并新增 `sync_test_kit_module_configs.py`

### 任务组 D. Skill 协议层与 2.0 发现路径
- [ ] `T9` 实现 `structured-handoff` skill
  - 状态：待开始
  - 解决问题：跨 creature 交接容易语义丢失
  - 适合模块：`skill`
  - 交付物：handoff 模板与使用规范
  - 完成标准：`coordinator` 和 `worker` 都使用同一交接协议
- [ ] `T10` 实现 `review-protocol` skill
  - 状态：待开始
  - 解决问题：`critic` 的反馈面不统一，难以积累高质量评审标准
  - 适合模块：`skill`
  - 交付物：review checklist 与输出协议
  - 完成标准：`critic` 输出可预测、可机器读取
- [ ] `T11` 实现 `memory-curation` skill
  - 状态：待开始
  - 解决问题：memory 整理策略缺少统一流程
  - 适合模块：`skill`
  - 交付物：memory 分类、升级、压缩、归档规范
  - 完成标准：`curator` 可按统一规则沉淀长期记忆
- [x] `T30` 迁移 CLI 创建类 skill 到 2.0 原生发现路径
  - 状态：已完成
  - 解决问题：当前 `.trae/skills/` 在 2.0 下不会被框架发现，历史设计实际上未生效
  - 适合模块：`.kt/skills` 或 package `skills:`
  - 交付物：迁移后的 `SKILL.md`、对应 manifest 或项目级路径
  - 完成标准：相关 skill 能被 2.0 原生发现与挂载
  - 备注：已将三项 CLI 创建类 skill 迁入 `examples/test-kit/skills/`，并在 `examples/test-kit/kohaku.yaml` 中通过 `skills:` 对外发布
- [x] `T31` 重构系统级可选 skill 挂载规则
  - 状态：已完成
  - 解决问题：当前可选 skill 接入规则依赖 `.trae/project-skill-library/`，未对接 2.0 真实启用机制
  - 适合模块：`creature` + `skill` + `docs`
  - 交付物：基于 creature `skills:` 配置的接入策略
  - 完成标准：可选 skill 的默认挂载、显式启用、无副作用移除都能在 2.0 下真实生效
  - 备注：已将策略索引迁入 `examples/test-kit/skill-policies/creature-creation/`，并让 `lab-runner` 用 `skills: [provider-aware-cli-builder]` 做真实 opt-in 示例

### 任务组 E. 记忆治理层
- [ ] `T12` 设计 memory schema
  - 状态：待开始
  - 解决问题：用户偏好、项目约束、工作区资产、一次性上下文混在一起，难以维护
  - 适合模块：`memory` + `docs`
  - 交付物：分层文件结构、字段建议、scope 规则
  - 完成标准：至少区分用户偏好、项目规则、工作区资产、任务归档、临时上下文
  - 备注：需与 2.0 的 identity / session 边界保持一致
- [ ] `T13` 实现 `curator` 模板
  - 状态：待开始
  - 解决问题：session 记录强，但缺少把历史转成长期资产的治理者
  - 适合模块：`creature` + `memory` + `subagent`
  - 交付物：模板 config、memory 读写流程、整理触发条件
  - 完成标准：任务结束后可稳定归档、压缩、去重
- [ ] `T14` 实现 `task-team-learning` terrarium
  - 状态：待开始
  - 解决问题：主链完成任务后，缺少低频学习闭环的集成样板
  - 适合模块：`terrarium`
  - 交付物：含 `curator` 的学习型团队
  - 完成标准：执行与沉淀两个链路彼此解耦
  - 备注：同样不得依赖旧版 channel `type` 语义

### 任务组 F. 策略与治理插件
- [ ] `T15` 对接 2.0 内置审批能力并封装 `approval-gate`
  - 状态：待开始
  - 解决问题：高风险动作与演化提案缺少统一审批机制
  - 适合模块：内置 `permgate` + 项目级 `plugin`
  - 交付物：审批策略、元数据约定、拒绝反馈机制
  - 完成标准：危险动作和新规则启用前都能被确认
  - 备注：不从零重复实现审批引擎，优先复用 2.0 内置能力
- [ ] `T16` 对接 2.0 内置预算能力并封装 `budget-policy`
  - 状态：待开始
  - 解决问题：多 agent 系统的 token、turn、tool 成本难控
  - 适合模块：内置 `budget` + 项目级 `plugin`
  - 交付物：按角色区分的预算策略与推荐配置
  - 完成标准：`root`、`worker`、`critic`、`curator` 可配置不同预算
  - 备注：不从零重写预算框架，优先做项目层策略封装
- [ ] `T17` 实现 `audit-guard` plugin
  - 状态：待开始
  - 解决问题：个性化与演化行为如果不可审计，后续会变成黑箱
  - 适合模块：`plugin`
  - 交付物：操作日志、草案来源、变更记录
  - 完成标准：任何关键变更都能追溯来源

### 任务组 G. 可控演化
- [ ] `T18` 设计 evolver 草案协议
  - 状态：待开始
  - 解决问题：系统进化缺少标准提案格式，无法纳入审批流
  - 适合模块：`skill` + `docs`
  - 交付物：skill / prompt / rule 草案格式
  - 完成标准：提案至少包含来源、适用范围、风险、回滚方式
- [ ] `T19` 实现 `evolver` 原型
  - 状态：待开始
  - 解决问题：反复纠正无法系统沉淀，个性化优化停留在人工修改
  - 适合模块：`creature`
  - 交付物：只生成草案的低频角色
  - 完成标准：能基于会话历史输出候选 skill / prompt patch，但不会自动生效

### 任务组 H. CLI 兼容与静默执行
- [x] `T20` 设计外部 CLI 兼容抽象层
  - 状态：已完成
  - 解决问题：`CLI-Anything` 与 `OpenCLI` 能力形态不同，缺少统一接入标准
  - 适合模块：`package` + `docs`
  - 交付物：provider 抽象、registry 约定、调用协议
  - 完成标准：两个外部 CLI 能被映射到同一套私有调用接口
  - 备注：设计文档见 `docs/zh-CN/dev/cli-compatibility-abstraction.md`
- [x] `T21` 实现 `CLI-Anything` 主兼容适配
  - 状态：已完成
  - 解决问题：私有 agent 生态缺少面向通用软件能力的主兼容标准
  - 适合模块：`package` + `worker-base`
  - 交付物：私有 registry 结构、安装/发现/调用封装
  - 完成标准：`CLI-Anything` registry 条目可被统一 capability 稳定发现、解析并分流
- [x] `T22` 实现 `OpenCLI` 次兼容适配
  - 状态：已完成
  - 解决问题：网页登录态与浏览器自动化场景需要专项 provider，但不应污染总抽象
  - 适合模块：`plugin` + `worker`
  - 交付物：provider 检测、调用封装、权限约束
  - 完成标准：`OpenCLI` 目标可被统一发现、解析并分流到专项 capability
- [x] `T23` 实现静默执行协议
  - 状态：已完成
  - 解决问题：执行层持续输出 token 会抬高成本并放大上下文污染
  - 适合模块：`worker-base` + `plugin`
  - 交付物：命令静默执行包装器、结果落盘格式、错误分级策略
  - 完成标准：正常执行时不输出过程 token，只保留结构化结果与证据
- [x] `T24` 实现编排阶段的 provider 选择机制
  - 状态：已完成
  - 解决问题：任务派发时如果不知道该选哪个 CLI 源，执行层会反复试错
  - 适合模块：`coordinator` + `skill`
  - 交付物：provider 选择字段、任务派发规则、优先级策略
  - 完成标准：`task_card` 能显式包含 `preferred_provider` 与 `artifact_expectation`
- [x] `T25` 实现结果反馈分析协议
  - 状态：已完成
  - 解决问题：如果结果分析没有统一协议，就会重新把执行细节大量喂回模型
  - 适合模块：`critic` + `curator` + `skill`
  - 交付物：效果分析模板、摘要字段、可复用反馈协议
  - 完成标准：执行完成后只基于产物摘要完成效果评估与记忆沉淀

### 任务组 I. CLI 创建 Skill 编排
- [x] `T26` 设计 `OpenCLI` 独立创建 skill
  - 状态：已完成
  - 解决问题：若只需要 `OpenCLI` 路线，用户应能单独使用浏览器 / adapter 定向的 CLI 创建能力
  - 适合模块：`skill`
  - 交付物：`OpenCLI` 自主选择并创建自定义 CLI 的 skill
  - 完成标准：能独立判断是否复用现有 OpenCLI adapter / external CLI，或创建新的 OpenCLI adapter
  - 备注：skill 已迁入 `examples/test-kit/skills/opencli-autonomous-builder/SKILL.md` 并通过 package manifest 发布
- [x] `T27` 设计双 provider 合并 skill
  - 状态：已完成
  - 解决问题：当用户同时启用 `CLI-Anything` 与 `OpenCLI` 时，需要一个统一入口做 provider 选择和创建路径分流
  - 适合模块：`skill`
  - 交付物：合并 skill、provider 选择规则、复用优先级说明
  - 完成标准：可在两个 provider 间做显式选择，并保留单独 skill 的独立可用性
  - 备注：skill 已迁入 `examples/test-kit/skills/provider-aware-cli-builder/SKILL.md` 并通过 package manifest 发布
- [x] `T28` 设计系统级可选 skill 的可移除接入规则
  - 状态：已完成
  - 解决问题：creature 默认接入系统级可选 skill 时，必须保留按用户需求增删的权利，不能固化为体系强依赖
  - 适合模块：`creature` + `skill` + `docs`
  - 交付物：可选 skill 接入约定、移除说明、默认启用条件
  - 完成标准：顶层 creature 可以默认挂载这些 skill，也可以无副作用移除
  - 备注：规则已落到 package 内策略目录，并通过 creature `skills:` 显式物化，不再依赖 `.trae/project-skill-library/`

### 任务组 J. 2.0 专项整合
- [x] `T32` 清理 terrarium channel `type` 语义并更新实验样板
  - 状态：已完成
  - 解决问题：当前 `lab-smoke` 仍保留 `type: queue/broadcast`，继续沿用会制造错误心智模型
  - 适合模块：`terrarium` + `examples`
  - 交付物：清理后的 terrarium 样板与说明文档
  - 完成标准：不再依赖 `type` 字段表达队列语义，改用 `listen` / `can_send`、DM channel、output wiring 等真实机制
  - 备注：已清理 `examples/test-kit/terrariums/lab-smoke/terrarium.yaml` 中的 `type` 字段，并同步更新 `examples/test-kit/README.md`
- [ ] `T33` 定义统一能力路由策略
  - 状态：待开始
  - 解决问题：当前设计过度集中于 CLI 路线，尚未把 built-in tools、MCP、CLI provider 放进同一选路框架
  - 适合模块：`docs` + `coordinator` + `worker-base`
  - 交付物：能力选择顺序、冲突处理规则、失败升级规则
  - 完成标准：`coordinator` 可以按统一策略选择 built-in / MCP / `CLI-Anything` / `OpenCLI`
- [ ] `T34` 将 `verify_t2x_*.py` 纳入回归保护
  - 状态：待开始
  - 解决问题：当前验证脚本能跑，但没有进入稳定回归链路，后续容易被无意破坏
  - 适合模块：`tests` + `scripts` + `CI`
  - 交付物：统一入口脚本或 CI 配置
  - 完成标准：至少能在本地或 CI 一键执行已有关键验证

## 12. 每阶段验证方式
### 文档与基线阶段
- 检查新版蓝图能解释“哪些旧设计可继承，哪些必须重构”。
- 检查 skill 路径、channel 语义、内置 plugin 复用策略是否明确。
- 检查 package / marketplace / MCP / identity 是否已进入蓝图主干，而不是停留在边角说明。

### 主工作流阶段
- 跑通最小 terrarium。
- 验证 `coordinator -> worker -> critic` 的结构化协议没有明显语义塌缩。
- 验证执行阶段默认不输出中间 token，仍能保证命令调用准确性。
- 验证主工作流不依赖已失效的 channel `type` 语义。

### 记忆治理阶段
- 验证 `curator` 不会把一次性任务上下文污染进长期 memory。
- 验证相同偏好能被合并，而不是不断追加重复文本。
- 验证 memory schema 能区分用户偏好、项目规则、工作区资产与临时上下文。

### 治理与演化阶段
- 验证审批插件能截住高风险动作。
- 验证预算策略确实复用了 2.0 内置能力，而不是重复造轮子。
- 验证 `evolver` 只产出草案，不直接污染正式模板。

### 兼容与分发阶段
- 验证 `CLI-Anything` 能作为主兼容标准被发现、安装、调用。
- 验证 `OpenCLI` 只在浏览器类任务中被选中，不扩散为总依赖。
- 验证 MCP、package、marketplace 能被纳入统一能力路由与分发逻辑。
- 验证失败时只回传最小必要错误上下文，而不是完整过程日志。

## 13. 当前状态
- 当前阶段：`Phase A`
- 当前重点：`T4-T8` 已落地，最小主链闭环已经建立
- 当前下一步：可继续推进 `T9-T11` 协议 skill 外提，或进入 `T12-T17` 的记忆与治理层
- 当前判断：入口控制面、任务编排层、执行骨架、结构化评审层与最小 terrarium 都已建立；下一轮重点应转向协议沉淀与后治理能力，而不是继续堆新角色

## 14. 更新规则
后续每完成一项，必须同步更新本文件：
1. 勾选对应任务。
2. 把 `状态` 改为 `已完成`。
3. 若实现路径与本蓝图不同，在任务备注中补一行“偏离原因”。
4. 若是历史设计完成但 2.0 下仍未真实生效，不得直接记为 `已完成`，应先标 `待重构`。
5. 若新增任务，放入对应阶段，不单独新建第二份 todo 文档。
