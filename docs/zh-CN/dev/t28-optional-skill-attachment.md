---
title: T28 可选 Skill 挂载规则
summary: 面向 creature 默认挂载 skill 的通用接入与可移除规则，适用于所有后续系统级可选 skill，而不只限于 CLI 类能力。
tags:
  - dev
  - skill
  - creature
  - policy
---

# T28 可选 Skill 挂载规则

本文档对应 `T28`，目标不是新增一个只服务 CLI skill 的特例，而是定义一套对所有“系统级可选 skill”通用的 creature 挂载规则。

## 1. 先回答原始问题

我们真正要解决的是三个问题：

1. **如何让新 creature 开箱即用**：默认创建出来就能正常跑，不因为缺少某个可选 skill 而报错。
2. **如何保留用户自由度**：用户可以在创建 creature 时增减默认挂载的 skill，而不是被体系强绑定。
3. **如何避免规则失真**：如果底层不支持“运行时按 creature 做细粒度挂载/卸载”，就不要伪装成已经支持。

因此，`T28` 的正确实现方式不是去发明新的核心协议，而是基于当前 KT 已有能力，定义一套稳定、低心智负担、可生成到 `config.yaml` 的约定。

## 2. 当前底层边界

当前仓库里，和 skill 挂载直接相关的事实有三条：

1. `AgentConfig.skills` 已经存在，表示 creature 对 **package-shipped skills** 的默认启用列表。
2. package skill 默认是 **关闭** 的，只有 creature 在 `skills:` 里显式列出时才默认启用。
3. project / user / creature 本地发现到的 skill 默认是 **开启** 的，它们更像“环境级能力”，不适合作为按 creature 精准控制默认挂载的唯一机制。

结论：

- **需要按 creature 默认挂载、并允许用户加减的 skill，应优先走 package skill 路线。**
- 项目级 skill 根可以作为环境级能力存在，但当前项目里的可选挂载规则已经迁到 package skill 路线，不再把 `.trae/skills/` 当成唯一的 per-creature 挂载机制。

## 3. 通用原则

任何系统级可选 skill，只要想进入“默认挂载候选集”，都必须满足下面五条：

1. **可移除**：移除后 creature 仍能启动，核心角色职责不崩。
2. **可降级**：移除后最多失去一个加速流程，不能失去唯一完成路径。
3. **可解释**：用户能看懂这个 skill 是干什么的、什么时候会被调用。
4. **可控范围**：skill 的职责边界清楚，不要把多个不相关流程打包成一个默认项。
5. **默认保守**：只有低风险、低耦合、对该角色普遍有益的 skill，才应该考虑默认挂载。

反过来说：

- 如果某能力是 creature 成功运行的硬前提，它就不应该被建模成“可选 skill”。
- 如果某 skill 只对少数场景有价值，它应该默认关闭，改成用户可选添加。

## 4. 挂载解析顺序

创建 creature 时，最终 `skills:` 列表按下面顺序解析：

1. `safe-default` 安全默认包
2. 角色默认 bundle
3. 用户额外选择的 bundle
4. 用户显式增加的 skill
5. 用户显式删除的 skill

同一轮创建里，**删除优先级高于增加**。  
也就是说，哪怕某 skill 在默认 bundle 里，只要用户明确删掉，就必须从最终 creature 配置里移除。

## 5. 为什么最终要落到 `skills:` 列表

因为当前 creature 继承规则里，`skills` 是普通 list，不是 identity list。

这意味着：

- 子 creature 不会对父 creature 的 `skills` 做按项增量 merge
- 子 creature 的 `skills:` 会整体替换父 creature 的 `skills:`
- 如果要彻底丢弃父级技能列表，可以用 `no_inherit: [skills]`

所以，`T28` 的推荐做法是：

- **在创建 creature 时就把解析完成后的最终 skill 集合直接写进 `config.yaml`**
- 不依赖“运行时再猜一次该挂哪些 skill”
- 不依赖“隐式增删 diff”

## 6. 默认挂载规则

### 6.1 什么 skill 可以进入默认包

一个 skill 只有同时满足下面条件，才可以进入默认包：

1. 对该角色是高频有益而不是低频特例
2. 不依赖隐藏上下文才能正确使用
3. 移除后 creature 仍可正常完成基础工作
4. 不会误导用户以为这是体系强依赖
5. 文档里明确写出 fallback 行为

### 6.2 默认包应该多大

默认包必须小。

推荐顺序：

1. 先有 `safe-default`
2. 再有角色默认 bundle
3. 少数明显有价值的领域 bundle 再单独可选

不要一开始就给所有 creature 挂一串“看起来很强”的 skill。  
默认项越多，错误心智模型越重，后续移除成本越高。

### 6.3 当前默认策略

当前项目的安全默认策略是：

- 新 creature 默认从 `safe-default` 开始
- `safe-default` 允许为空
- CLI 创建相关 skill 目前都属于 **可选 bundle**，而不是所有 creature 的全局默认项

这样做的原因很简单：

- 现在这些 skill 仍然是专项能力
- 它们并不适合对所有 creature 无差别默认挂载
- 空默认包不会导致 creature 出错，反而更符合“开箱即用但不越权”

## 7. 用户增加 / 删除规则

### 7.1 增加规则

用户增加一个可选 skill 时，创建流程应该做四件事：

1. 检查 skill 是否在项目级目录或 package skill 清单中登记
2. 检查该 skill 是否适用于当前 creature 角色
3. 检查是否与已选 skill 冲突
4. 把它写入最终 `skills:` 列表

### 7.2 删除规则

用户删除一个默认 skill 时，创建流程应该做三件事：

1. 从最终 `skills:` 列表去掉该 skill
2. 不再让 creature 的 prompt / README 声称自己带有这个 skill
3. 若该 skill 有 fallback 行为，给出一句简短说明

### 7.3 删除后的保证

删除任何“系统级可选 skill”后，必须保证：

1. creature 仍能启动
2. creature 基础职责仍成立
3. 只是少一个可选流程，而不是进入错误状态

## 8. 对后续所有系统级可选 Skill 的元信息要求

任何未来想进入这个体系的 skill，至少要登记这些字段：

- `skill_name`
- `category`
- `default_attach`
- `removable`
- `safe_for_default_bundle`
- `fallback_behavior`
- `supported_roles`
- `attach_scope`

这不是为了形式化，而是为了保证创建 creature 时能够稳定回答这几个问题：

- 默认挂不挂
- 谁可以挂
- 能不能删
- 删了会怎样

## 9. 推荐落地方式

当前项目当前落地为：

- package skill 目录：
  - `examples/test-kit/skills/`
- 通用策略文件：
  - `examples/test-kit/skill-policies/creature-creation/attachment-policy.yaml`
- 当前 skill 清单：
  - `examples/test-kit/skill-policies/creature-creation/catalog.yaml`

推荐以后都按这个流程落地：

1. 真实可调用 skill 放在 package `skills/` 标准发现路径
2. package 内策略目录只负责“选什么、怎么挂、能不能删”
3. 创建 creature 时按策略解算出最终 skill 集
4. 把最终结果写进 creature 的 `skills:` 列表

## 10. 示例

### 10.1 默认安全配置

```yaml
name: root
skills: []
```

说明：

- 这是最稳妥的开箱即用起点
- 没有任何系统级可选 skill 也不会报错

### 10.2 为创建型 root 挂载可选 skill

```yaml
name: root
skills:
  - provider-aware-cli-builder
```

说明：

- 这是一个“增加一个可选 skill”的例子
- creature 仍然不依赖它才能启动

### 10.3 子 creature 替换继承来的 skill 列表

```yaml
base_config: "@my-pack/creatures/root"
no_inherit: [skills]

skills:
  - structured-handoff
```

说明：

- 这里不是追加，而是显式替换
- 适合用户想从父模板里删除默认 skill 后重新指定最终列表

## 11. 决策总结

`T28` 的最终规则是：

1. 通用可选 skill 规则不只服务 CLI skill，而是服务全部后续系统级可选 skill
2. per-creature 可控默认挂载优先走 package skill + `skills:` 列表
3. 项目级 skill 目录负责选型与策略，不伪装成新的 runtime 发现根
4. 默认配置优先保证开箱即用和不出错，而不是追求默认挂很多能力
5. 所有可选 skill 都必须可移除、可降级、可解释
