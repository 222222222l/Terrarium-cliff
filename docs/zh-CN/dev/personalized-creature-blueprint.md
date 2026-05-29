---
title: 个性化 Creature 蓝图
summary: 面向个性化 creature 模板生态的开发蓝图、模块边界、任务拆解与持续追踪清单。
tags:
  - dev
  - creature
  - roadmap
  - personalization
---
# 个性化 Creature 模板体系开发蓝图
本文档是后续开发的唯一追踪入口，目标是在 `KohakuTerrarium` 现有 runtime 之上，补出一层高度通用、可复用、可治理、可演化的 creature 模板生态。
## 1. 目标
本蓝图要解决的不是“再做几个 agent 配置”，而是以下四个项目级问题：
1. **模板生态薄弱**：框架能力强，但缺少可直接复用的高质量 creature 模板与 package 骨架。
2. **个性化沉淀不足**：会话、memory、compaction 已有基础，但缺少稳定的“用户偏好 / 项目规则 / 操作习惯”治理层。
3. **演化闭环缺失**：尚无“从历史会话中提取规则 -> 生成 skill 草案 -> 审批 -> 生效 -> 回滚”的标准路径。
4. **多 agent 成本高**：角色拆分后容易出现通信膨胀、语义漂移和维护成本上升，缺少一套低耦合的模块边界。
## 2. 设计原则
1. **先补能力层，再补角色数量**：优先沉淀可复用模板、协议和治理机制，而不是堆更多常驻 creature。
2. **主工作流最小化**：高频主链只保留 `root -> coordinator -> worker -> critic` 这条最短路径。
3. **学习与执行解耦**：`curator` 和 `evolver` 不进入每次任务的主链路，优先做后台或低频触发角色。
4. **跨切面问题不用 creature 承担**：预算、审批、安全、审计优先用 plugin，而不是单独做“守门员 creature”。
5. **模板必须可打包发布**：第一阶段的产物不是单个示例目录，而是一套可复用 package 骨架。
6. **所有演化都要可控**：任何自动生成的 skill、prompt、memory 规则都必须可审计、可禁用、可回滚。
7. **执行层默认静默**：能只用命令行完成的步骤就只走命令行，不向模型持续回传执行细节。
8. **只在必要节点消耗 token**：默认只在“任务编排与派发”和“执行完成后的效果反馈分析”两个阶段输出 token。
9. **准确性优先于可见性**：执行过程可以不输出，但必须保留结构化结果、退出码、错误摘要和可审计日志。
## 3. 推荐模板体系
第一阶段采用 `4+1+1` 模型：
- `root-privileged`：用户入口、权限审批、graph 管理、最终汇报
- `coordinator`：需求拆解、任务派发、结构化 handoff
- `worker-base`：执行骨架，再派生出具体工作型 worker
- `critic`：反馈、验收、驳回、补证据
- `curator`：记忆治理、归档、压缩、去重
- `evolver`：从历史中提出 skill / prompt / rule 草案，默认离线或低频触发
## 4. 模块归属规则
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
## 5. CLI 兼容与 Token 压缩策略
### 5.1 兼容总原则
- 以 `CLI-Anything` 作为主兼容标准，因为它更适合充当“私有 agent 工具市场”的统一抽象层。
- 以 `OpenCLI` 作为次兼容对象，主要服务网页登录态、浏览器自动化、社媒与 Electron 操作场景。
- `KohakuTerrarium` 内部不直接模仿两个项目的全部运行时，而是只兼容其最有价值的抽象：`registry`、安装协议、命令调用协议、结果回收协议。
- 所有外部 CLI 都必须先进入私有 package 的受控目录，再由模板 creature 间接调用，避免把宿主环境暴露给所有角色。

### 5.2 Token 压缩原则
- **命令优先**：能通过单条或少量命令确定性完成的动作，不交给 LLM 逐步推理。
- **执行静默**：worker 在执行命令时默认不持续输出中间 token，不逐步解释每个动作。
- **结构化回收**：命令执行结果优先写入 JSON、Markdown 报告或退出码，再由上层选择是否摘要给模型。
- **两段式用 token**：只有 `coordinator` 的任务编排与 `critic` / `curator` 的结果分析阶段允许系统性消耗 token。
- **错误例外**：当命令失败且无法仅凭退出码、stderr 摘要定位问题时，才允许把最小必要上下文回传给模型。
- **证据保留**：即使不回传过程 token，也要保留命令、参数摘要、输出文件路径、时间戳和状态，供审计与复盘使用。

### 5.3 两个外部 CLI 的分工
#### `CLI-Anything`
- 定位：主兼容标准、私有 registry 的参考模型、私有 CLI harness 的安装与发现入口。
- 适合承载：
  - 私有工具注册表
  - 私有 CLI harness 元数据
  - worker 可调用的本地专业工具
  - 与 `creature package` 配套的 skill / install metadata
- 在本项目中的推荐落点：
  - `package`：保存私有 registry、安装描述、封装后的 CLI harness
  - `worker-base`：提供统一的命令调用入口
  - `plugin`：控制是否允许安装、升级、调用某个 harness

#### `OpenCLI`
- 定位：浏览器与网页登录态专项 provider，不作为整个私有生态的总标准。
- 适合承载：
  - 网站操作
  - 浏览器页面抓取
  - 登录态任务
  - Electron / Web 平台自动化
- 在本项目中的推荐落点：
  - `worker` 派生角色：如 `web-worker`、`social-worker`
  - `plugin`：provider 可用性检测、浏览器会话守卫、权限控制
  - `skill`：把常用站点命令封装成任务模板，而不是把全量命令暴露给上层

### 5.4 统一调用协议
私有 agent 生态对两个外部 CLI 都统一走同一套协议：

1. `root` 或 `coordinator` 只负责选择能力源，不直接执行高噪声命令。
2. `worker-base` 根据任务类型选择 `CLI-Anything` harness 或 `OpenCLI` provider。
3. 执行阶段只运行命令，并将结果写入结构化产物：
   - `exit_code`
   - `stdout_summary`
   - `stderr_summary`
   - `artifact_paths`
   - `provider_name`
   - `duration_ms`
4. 若命令成功，默认不把完整过程回传给模型，只把产物路径和最小摘要交给后续节点。
5. 若命令失败，先走规则化重试和错误归类，再决定是否交给模型做最小化诊断。
6. `critic` 和 `curator` 只读取结果摘要与产物，不回放整个执行过程。

### 5.5 模块改造建议
- `root-privileged`
  - 增加能力：选择兼容源、审批高风险 CLI 调用、控制安装与升级。
- `coordinator`
  - 增加能力：为任务标注 `preferred_provider`、`token_budget_mode`、`artifact_expectation`。
- `worker-base`
  - 增加能力：统一命令执行包装器、静默执行策略、结果产物落盘。
- `critic`
  - 增加能力：只基于产物和摘要做效果评估，不读取冗长执行日志。
- `curator`
  - 增加能力：把高价值 CLI 使用模式沉淀成 skill、规则或 provider 选择偏好。

### 5.6 不做的事
- 不把 `OpenCLI` 或 `CLI-Anything` 的原生命令全集直接暴露给所有 creature。
- 不让 worker 在正常执行时边做边解释。
- 不把 stdout 原文长流直接喂回模型。
- 不把“浏览器专项 provider”误当成整个私有 agent 生态的唯一标准。
## 6. 第一阶段范围
### 必做
- 一套 package 骨架
- 五个模板 creature：`root-privileged`、`coordinator`、`worker-base`、`critic`、`curator`
- 一个最小 terrarium：`task-team-minimal`
- 一个学习型 terrarium：`task-team-learning`
- 三类通用 skill：`structured-handoff`、`review-protocol`、`memory-curation`
- 三类治理 plugin：`approval-gate`、`budget-policy`、`audit-guard`
### 延后
- `evolver` 独立常驻 creature
- 自动安装新 skill
- marketplace / catalog 推荐系统
- 多种行业模板同时铺开
## 7. 总体开发步骤
### Phase 0：定义骨架与标准
先确定模板边界和协议，不急于写复杂实现。
输出物：
- package 目录骨架
- 五类 creature 的职责说明
- handoff / critic / memory schema 三套协议
- 文档化的完成定义
### Phase 1：先做最小主链
只做能跑通主工作流的最短闭环：
- `root-privileged`
- `coordinator`
- `worker-base`
- `critic`
- `task-team-minimal`
目标：验证模板体系不是概念图，而是真的能替代一部分重复造轮子。
### Phase 2：补记忆治理
加入 `curator`，把“任务完成后如何沉淀偏好和规范”标准化。
目标：把 session 历史转化为高价值、低噪声的长期 memory。
### Phase 3：补策略治理
补 `approval-gate`、`budget-policy`、`audit-guard`。
目标：确保个性化能力增强不会突破权限、安全与成本边界。
### Phase 4：补可控演化
设计 `evolver` 与草案审批流，但默认不自动生效。
目标：先形成“提案系统”，再决定是否开放“自动应用”。
## 8. 模板设计蓝图
### 7.1 `root-privileged`
要解决的问题：
- 用户只有一个总入口，不应直接与所有 creature 混聊
- 团队需要一个统一审批点和编排点
- graph 变更与策略批准不能分散在 worker 中
适合使用：
- `creature`
- `terrarium` privileged `group_*` tools
- `plugin` 审批与审计
不适合使用：
- 长时间执行具体任务
- 直接承担记忆整理或产出大量内容
### 7.2 `coordinator`
要解决的问题：
- 用户需求常常模糊，不能直接丢给 worker
- 多 agent 语义漂移主要发生在任务转述阶段
适合使用：
- `creature`
- `skill`：`structured-handoff`
- 必要时用 `plan` / `explore` 子代理
核心输出协议建议：
- `task_id`
- `goal`
- `constraints`
- `inputs`
- `deliverable`
- `evidence_needed`
- `done_definition`
- `open_questions`
### 7.3 `worker-base`
要解决的问题：
- 当前生态缺少真正可派生的执行模板
- 不同领域 worker 容易从零复制 prompt 和工具配置
适合使用：
- `creature`
- `subagent` 进行垂直协作
- `package` 派生多个具体 worker 变体
派生方向：
- `swe-worker`
- `research-worker`
- `docs-worker`
- `ops-worker`
### 7.4 `critic`
要解决的问题：
- 反馈行为容易退化为自然语言闲聊，没有标准验收面
- 多 agent 系统最缺的是高质量否决与补证据机制
适合使用：
- `creature`
- `skill`：`review-protocol`
- `output_wiring` 作为固定验收环节
核心输出协议建议：
- `status`: `pass` / `fail` / `revise`
- `requirements_covered`
- `missing_evidence`
- `risks`
- `required_changes`
- `confidence`
### 7.5 `curator`
要解决的问题：
- 现有 session / memory / compact 能记录历史，但缺少整理策略
- 长期 memory 容易堆成文件垃圾场
适合使用：
- `creature`
- `memory_read` / `memory_write` 子代理
- `session memory` 检索
- `compact` 与自定义 memory schema
职责拆解：
- 提取短期高价值事实
- 合并重复偏好
- 把项目约束与一次性上下文分层
- 压缩中长期 memory
- 维护归档索引
### 7.6 `evolver`
要解决的问题：
- 反复纠正的行为无法自然沉淀成模板资产
- 个性化优化缺少“从观察到提案”的标准角色
适合使用：
- `creature`
- `skill`
- `plugin` 审批守卫
- `package` 写入草案区
第一阶段限制：
- 只生成草案
- 不直接覆盖现有 prompt
- 不直接安装 skill
- 必须交由 `root` 或用户审批
## 9. 任务追踪清单
说明：
- 每项任务都必须在本文件内原地更新状态。
- 完成时将 `状态` 从 `待开始` 改为 `已完成`，并勾选任务标题。
- 若任务被拆分，保留父任务并在“备注”中追加子项，不另起第二套追踪文档。
### 任务组 A. 蓝图与边界
- [x] `T0` 编写模板体系蓝图文档
  - 状态：已完成
  - 解决问题：项目缺少可执行的个性化 creature 设计总图，容易边做边漂移
  - 适合模块：`docs` 文档层
  - 交付物：本文件
  - 完成标准：文档明确目标、模块边界、阶段路线、任务清单
  - 备注：后续所有任务以本文件为唯一追踪入口
- [x] `T1` 定义模块归属规则
  - 状态：已完成
  - 解决问题：不清楚哪些能力该放在 creature、plugin、skill、package
  - 适合模块：`docs` + 后续 `package` 规范
  - 交付物：模块职责表、反模式清单
  - 完成标准：后续新增功能都能依据本规则判断落点
### 任务组 B. Package 骨架
- [x] `T2` 创建个性化模板 package 骨架
  - 状态：已完成
  - 解决问题：模板无法版本化、安装化、共享化
  - 适合模块：`package`
  - 交付物：`kohaku.yaml`、`creatures/`、`terrariums/`、`skills/`、`plugins/`
  - 完成标准：能被 `kt` 识别为完整 package
  - 备注：已创建 `examples/test-kit/`，包含 `lab-runner`、`lab-smoke`、`lab_report` 与配套文档
- [x] `T3` 设计目录与命名约定
  - 状态：已完成
  - 解决问题：后续模板扩展缺少统一布局，容易演变为示例堆叠
  - 适合模块：`package`
  - 交付物：目录规范、命名规范、模板继承规范
  - 完成标准：新增 creature / skill / plugin 时不需要重新讨论目录形态
  - 备注：规范文档见 `docs/zh-CN/dev/package-naming-conventions.md`
### 任务组 C. 主工作流模板
- [ ] `T4` 实现 `root-privileged` 模板
  - 状态：待开始
  - 解决问题：缺少通用入口、审批点和 graph 管理角色
  - 适合模块：`creature` + `terrarium`
  - 交付物：模板 config、system prompt、权限边界说明
  - 完成标准：能统一接用户任务、查询团队状态、触发审批
- [ ] `T5` 实现 `coordinator` 模板
  - 状态：待开始
  - 解决问题：用户意图到执行任务之间缺少稳定的结构化 handoff
  - 适合模块：`creature` + `skill`
  - 交付物：模板 config、handoff 协议、必要子代理组合
  - 完成标准：输出稳定的 task card，而不是松散自然语言
- [ ] `T6` 实现 `worker-base` 模板
  - 状态：待开始
  - 解决问题：执行型 creature 缺少统一骨架，具体 worker 难以派生
  - 适合模块：`creature` + `subagent`
  - 交付物：模板 config、可继承的 prompt、工具边界
  - 完成标准：能低成本派生出至少一个具体 worker
- [ ] `T7` 实现 `critic` 模板
  - 状态：待开始
  - 解决问题：反馈与验收缺少标准协议，难以形成高质量闭环
  - 适合模块：`creature` + `skill`
  - 交付物：review 协议、模板 config、输出格式
  - 完成标准：对 worker 产出进行结构化判定与打回
- [ ] `T8` 实现 `task-team-minimal` terrarium
  - 状态：待开始
  - 解决问题：模板体系如果没有最小联调样板，就无法证明其真实可用
  - 适合模块：`terrarium`
  - 交付物：`root + coordinator + worker + critic` 最小团队
  - 完成标准：能跑通一条完整任务链
### 任务组 D. Skill 协议层
- [ ] `T9` 实现 `structured-handoff` skill
  - 状态：待开始
  - 解决问题：跨 creature 交接容易语义丢失
  - 适合模块：`skill`
  - 交付物：handoff 模板与使用规范
  - 完成标准：coordinator 和 worker 都使用同一交接协议
- [ ] `T10` 实现 `review-protocol` skill
  - 状态：待开始
  - 解决问题：critic 的反馈面不统一，难以积累高质量评审标准
  - 适合模块：`skill`
  - 交付物：review checklist 与输出协议
  - 完成标准：critic 输出可预测、可机器读取
- [ ] `T11` 实现 `memory-curation` skill
  - 状态：待开始
  - 解决问题：memory 整理策略缺少统一流程
  - 适合模块：`skill`
  - 交付物：memory 分类、升级、压缩、归档规范
  - 完成标准：curator 可按统一规则沉淀长期记忆
### 任务组 E. 记忆治理层
- [ ] `T12` 设计 memory schema
  - 状态：待开始
  - 解决问题：用户偏好、项目约束、一次性上下文混在一起，难以维护
  - 适合模块：`memory`
  - 交付物：文件分层与字段建议
  - 完成标准：至少区分用户偏好、项目规则、任务归档、临时上下文
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
### 任务组 F. 策略与治理插件
- [ ] `T15` 实现 `approval-gate` plugin
  - 状态：待开始
  - 解决问题：高风险动作与演化提案缺少统一审批机制
  - 适合模块：`plugin`
  - 交付物：审批拦截、审批元数据、拒绝反馈机制
  - 完成标准：危险动作和新规则启用前都能被确认
- [ ] `T16` 实现 `budget-policy` plugin
  - 状态：待开始
  - 解决问题：多 agent 系统的 token、turn、tool 成本难控
  - 适合模块：`plugin`
  - 交付物：按角色区分的预算策略
  - 完成标准：root、worker、critic、curator 可配置不同预算
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
  - 完成标准：`CLI-Anything` registry 条目可被私有 provider 规则稳定发现、解析并分流到统一 capability
  - 备注：已新增 `examples/test-kit/registry/registry.yaml`、`examples/test-kit/providers/cli_anything.yaml`、`cli_anything_registry` 工具与 `docs/zh-CN/dev/t21-cli-anything-validation.md`

- [x] `T22` 实现 `OpenCLI` 次兼容适配
  - 状态：已完成
  - 解决问题：网页登录态与浏览器自动化场景需要专项 provider，但不应污染总抽象
  - 适合模块：`plugin` + `worker`
  - 交付物：provider 检测、调用封装、权限约束
  - 完成标准：`OpenCLI` 的浏览器、公共接口、桌面适配器与外部 CLI 目标可被统一发现、解析并分流到专项 capability
  - 备注：已新增 `examples/test-kit/providers/opencli.yaml`、`opencli_registry` 工具与 `docs/zh-CN/dev/t22-opencli-validation.md`

- [x] `T23` 实现静默执行协议
  - 状态：已完成
  - 解决问题：执行层持续输出 token 会抬高成本并放大上下文污染
  - 适合模块：`worker-base` + `plugin`
  - 交付物：命令静默执行包装器、结果落盘格式、错误分级策略
  - 完成标准：正常执行时不输出过程 token，只保留结构化结果与证据
  - 备注：已新增 `examples/test-kit/test_kit/cli_runtime.py`、`cli_invoke` 工具与 `docs/zh-CN/dev/t23-silent-execution-validation.md`

- [x] `T24` 实现编排阶段的 provider 选择机制
  - 状态：已完成
  - 解决问题：任务派发时如果不知道该选哪个 CLI 源，执行层会反复试错
  - 适合模块：`coordinator` + `skill`
  - 交付物：provider 选择字段、任务派发规则、优先级策略
  - 完成标准：task card 能显式包含 `preferred_provider` 与 `artifact_expectation`
  - 备注：已新增 `provider_select` 工具与 `docs/zh-CN/dev/t24-provider-selection-validation.md`；当 `CLI-Anything` 与 `OpenCLI` 在浏览器公共能力上重叠且信息不足时，选择权显式交还用户

- [x] `T25` 实现结果反馈分析协议
  - 状态：已完成
  - 解决问题：如果结果分析没有统一协议，就会重新把执行细节大量喂回模型
  - 适合模块：`critic` + `curator` + `skill`
  - 交付物：效果分析模板、摘要字段、可复用反馈协议
  - 完成标准：执行完成后只基于产物摘要完成效果评估与记忆沉淀
  - 备注：已新增 `examples/test-kit/test_kit/feedback_protocol.py`、`result_feedback` 工具、`examples/test-kit/scripts/verify_t25_feedback_protocol.py` 与 `docs/zh-CN/dev/t25-feedback-validation.md`；协议将用户可见摘要与 agent 侧结构化反馈分离，默认 `json`、可选 `xml`
### 任务组 I. CLI 创建 Skill 编排
- [x] `T26` 设计 `OpenCLI` 独立创建 skill
  - 状态：已完成
  - 解决问题：若只需要 `OpenCLI` 路线，用户应能单独使用浏览器 / adapter 定向的 CLI 创建能力，而不是被迫依赖 `CLI-Anything`
  - 适合模块：`skill`
  - 交付物：`OpenCLI` 自主选择并创建自定义 CLI 的 skill
  - 完成标准：能独立判断是否复用现有 OpenCLI adapter / external CLI，或创建新的 OpenCLI adapter
  - 备注：已新增 `.trae/skills/opencli-autonomous-builder/SKILL.md`，明确 `browser_authenticated_task`、`browser_public_task`、`desktop_app_task` 与 `external_cli_passthrough` 的适用边界，并要求优先复用现有 OpenCLI adapter / external CLI
- [x] `T27` 设计双 provider 合并 skill
  - 状态：已完成
  - 解决问题：当用户同时启用 `CLI-Anything` 与 `OpenCLI` 时，需要一个统一入口做 provider 选择和创建路径分流
  - 适合模块：`skill`
  - 交付物：合并 skill、provider 选择规则、复用优先级说明
  - 完成标准：可在两个 provider 间做显式选择，并保留单独 skill 的独立可用性
  - 备注：已新增 `.trae/skills/provider-aware-cli-builder/SKILL.md`，统一读取本仓库 provider 选择规则并在能力重叠时显式要求用户选择；同时新增 `.trae/project-skill-library/creature-creation/` 作为项目级 creature 可选 skill 目录，避免把项目级选型内容混入通用 `autonomous-cli-builder`
- [x] `T28` 设计系统级可选 skill 的可移除接入规则
  - 状态：已完成
  - 解决问题：creature 默认接入系统级可选 skill 时，必须保留按用户需求增删的权利，不能固化为体系强依赖
  - 适合模块：`creature` + `docs`
  - 交付物：可选 skill 接入约定、移除说明、默认启用条件
  - 完成标准：顶层 creature 可以默认挂载这些 skill，也可以无副作用移除
  - 备注：已新增 `docs/zh-CN/dev/t28-optional-skill-attachment.md` 与 `.trae/project-skill-library/creature-creation/attachment-policy.yaml`；规则已扩展为适用于所有后续系统级可选 skill，而不只限于 CLI 创建 skill
## 10. 每阶段验证方式
### 文档与模板阶段
- 检查模板边界是否能解释“为什么这个能力该放这里”
- 检查 package 骨架是否支持后续增量扩展
- 检查 CLI 兼容层是否能解释“为什么主兼容是 `CLI-Anything`，为什么 `OpenCLI` 只做专项 provider”
### 主工作流阶段
- 跑通最小 terrarium
- 验证 `coordinator -> worker -> critic` 的结构化协议没有明显语义塌缩
- 验证执行阶段默认不输出中间 token，仍能保证命令调用准确性
### 记忆治理阶段
- 验证 `curator` 不会把一次性任务上下文污染进长期 memory
- 验证相同偏好能被合并，而不是不断追加重复文本
### 治理与演化阶段
- 验证审批插件能截住高风险动作
- 验证 evolver 只产出草案，不直接污染正式模板
### CLI 兼容阶段
- 验证 `CLI-Anything` 能作为主兼容标准被发现、安装、调用
- 验证 `OpenCLI` 只在浏览器类任务中被选中，不扩散为总依赖
- 验证失败时只回传最小必要错误上下文，而不是完整过程日志
## 11. 当前状态
- 当前阶段：`Phase 0`
- 当前重点：CLI 创建类 skill 的三层结构与通用挂载规则已完成，下一步需要把这些规则真正落实到后续 creature 模板实现中
- 当前下一步：回到主模板阶段，按需推进 `T4-T8` 或后续落地任务
## 12. 更新规则
后续每完成一项，必须同步更新本文件：
1. 勾选对应任务
2. 把 `状态` 改为 `已完成`
3. 若实现路径与原蓝图不同，在任务备注中补一行“偏离原因”
4. 若新增任务，放入对应阶段，不单独新建第二份 todo 文档
