---
title: Package 目录与命名约定
summary: 面向私有 agent package 的 creature、skill、plugin 目录命名和模板规范，优先追求泛用性与简洁性。
tags:
  - dev
  - package
  - naming
  - conventions
---

# Package 目录与命名约定

这份文档对应 `T3`，目标是给后续的私有 package 一个统一、简洁、可扩展的布局标准。

原则只有四条：

1. **先能看懂，再谈扩展**：目录一眼能知道放什么。
2. **角色名短，职责名准**：名字优先表达用途，不堆修饰词。
3. **结构稳定，内部可演化**：后续增删模块时不需要改整体布局。
4. **默认最小模板**：每类模块只保留真正必要的骨架。

## 1. 总体布局

推荐 package 根目录固定为：

```text
my-pack/
  kohaku.yaml
  README.md
  creatures/
  skills/
  prompts/
  terrariums/
  my_pack/
    __init__.py
    plugins/
    tools/
```

说明：

- `creatures/` 放可直接运行或继承的 creature
- `skills/` 放流程知识与操作规范
- `prompts/` 放可复用提示词碎片
- `terrariums/` 放多角色编排
- `my_pack/plugins/` 放 Python plugin 模块
- `my_pack/tools/` 放 Python 工具模块

不建议：

- 在根目录散落多个平级脚本目录
- 把 `skill`、`prompt`、`plugin` 混在同一层
- 用 `misc`、`temp`、`new` 这类无语义目录名

## 2. `creature` 目录规范

### 2.1 命名规则

目录名统一使用 `kebab-case`。

推荐格式：

- 通用角色：`root`, `coordinator`, `worker-base`, `critic`, `curator`
- 领域角色：`swe-worker`, `research-worker`, `docs-worker`, `web-worker`
- 测试角色：`lab-runner`, `root-test`, `worker-test`, `critic-test`

命名原则：

- **角色优先**：先写角色，再写领域
- **一个名字只表达一个主职责**
- **避免无信息后缀**：如 `agent`, `creature`, `module`

例如：

- 好：`swe-worker`
- 好：`review-critic`
- 差：`general-agent-v2`
- 差：`test-creature-final`

### 2.2 目录结构

每个 creature 目录推荐最小结构：

```text
creatures/
  worker-base/
    config.yaml
    prompts/
      system.md
```

按需增加：

```text
creatures/
  worker-base/
    config.yaml
    prompts/
      system.md
      context.md
    memory/
      rules.md
      preferences.md
```

### 2.3 最小模板

```yaml
name: worker-base
base_config: "@my-pack/creatures/root"

system_prompt_file: prompts/system.md

tools:
  - read
  - write
  - bash

subagents:
  - plan
  - critic
```

### 2.4 设计约束

- 一个 creature 目录只表达一个稳定角色
- `config.yaml` 是唯一入口文件
- `prompts/system.md` 是默认必备文件
- 只有当该角色真的需要记忆时，才添加 `memory/`
- 领域差异优先通过继承产生，不要复制整份 config

## 3. `skill` 目录规范

### 3.1 命名规则

目录名统一使用 `kebab-case`。

推荐格式：

- 动作型：`structured-handoff`, `review-protocol`, `memory-curation`
- 约束型：`safe-editing`, `silent-execution`, `artifact-review`
- 领域型：`swe-patch-review`, `browser-task-routing`

命名原则：

- skill 名称优先表达“可复用流程”而不是“某次任务”
- 用动词短语或职责短语
- 不使用 `skill-1`, `new-skill`, `misc-flow`

### 3.2 目录结构

每个 skill 目录最小结构：

```text
skills/
  structured-handoff/
    SKILL.md
```

默认不增加额外层级，除非确实需要示例或附件。

### 3.3 最小模板

```markdown
# structured-handoff

## Purpose
Provide a stable handoff format between coordinator and worker.

## Use When
- A task needs to be delegated
- The next role needs explicit inputs and done criteria

## Output Contract
- task_id
- goal
- constraints
- deliverable
- done_definition
```

### 3.4 设计约束

- 一个 skill 只定义一个流程或协议
- `SKILL.md` 是唯一必备文件
- skill 不承载 Python 逻辑
- skill 不重复写大段项目背景
- skill 优先给出：
  - 什么时候用
  - 输出什么
  - 成功标准是什么

## 4. `plugin` 目录规范

### 4.1 命名规则

Python 文件名统一使用 `snake_case`。

推荐格式：

- 守卫类：`approval_gate.py`, `audit_guard.py`, `sandbox_guard.py`
- 策略类：`budget_policy.py`, `routing_policy.py`
- 记录类：`response_logger.py`, `tool_timer.py`

类名使用 `PascalCase`，并与文件语义一致：

- `approval_gate.py` -> `ApprovalGatePlugin`
- `budget_policy.py` -> `BudgetPolicyPlugin`

### 4.2 目录结构

推荐结构：

```text
my_pack/
  plugins/
    approval_gate.py
    budget_policy.py
    audit_guard.py
```

如果某个 plugin 明显更复杂，再升级为目录：

```text
my_pack/
  plugins/
    cli_provider_registry/
      __init__.py
      plugin.py
      helpers.py
```

### 4.3 最小模板

```python
from kohakuterrarium.modules.plugin.base import BasePlugin


class ApprovalGatePlugin(BasePlugin):
    name = "approval_gate"
    priority = 50
```

### 4.4 设计约束

- 简单 plugin 优先单文件
- 只有复杂 plugin 才升级为包目录
- plugin 名称表达横切策略，不表达业务 persona
- 不把 role 逻辑塞进 plugin
- plugin 只处理：
  - 审批
  - 预算
  - 审计
  - 拦截
  - 运行时服务

## 5. 推荐命名对照

### `creature`

- `root`
- `coordinator`
- `worker-base`
- `critic`
- `curator`
- `swe-worker`
- `research-worker`
- `lab-runner`

### `skill`

- `structured-handoff`
- `review-protocol`
- `memory-curation`
- `silent-execution`
- `artifact-review`

### `plugin`

- `approval_gate`
- `budget_policy`
- `audit_guard`
- `cli_execution_policy`
- `cli_provider_registry`

## 6. 模板继承规范

优先按这条链继承：

```text
root
  -> coordinator
  -> worker-base
      -> swe-worker
      -> research-worker
      -> docs-worker
  -> critic
  -> curator
```

规则：

- 通用角色做 base
- 领域角色从通用角色派生
- 测试角色可以直接继承通用角色，也可以独立极简配置
- 不从测试角色反向派生正式角色

## 7. 对 `test-kit` 的落地建议

当前 `test-kit` 已经符合这套约定的基本方向：

- `creatures/lab-runner/`
- `terrariums/lab-smoke/`
- `test_kit/tools/lab_report.py`

后续如果继续扩展：

- 新测试 creature 继续用 `kebab-case`
- 新 tool / plugin 保持 Python 命名约定
- 新 skill 统一放到 `skills/<skill-name>/SKILL.md`

## 8. 决策总结

`T3` 的最终规范是：

1. creature 目录名用 `kebab-case`
2. skill 目录名用 `kebab-case`
3. plugin 文件名用 `snake_case`，类名用 `PascalCase`
4. creature 最小模板是 `config.yaml + prompts/system.md`
5. skill 最小模板是 `SKILL.md`
6. plugin 最小模板是单文件 Python 模块
7. 复杂功能优先通过继承扩展，不优先复制目录
