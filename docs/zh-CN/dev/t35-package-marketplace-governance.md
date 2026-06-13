---
title: T35 Package / Marketplace 发布治理
summary: 私有 package 从本地开发到私有发布再到 marketplace 候选的版本、来源与回滚策略。
tags:
  - dev
  - package
  - marketplace
  - governance
---

# T35 Package / Marketplace 发布治理

这份文档定义私有模板 package 的发布生命周期。目标不是替代 `kt install` 或 marketplace，而是在现有机制之上补齐“什么时候能发布、怎么升级、坏版本怎么回滚”的治理规则。

## 1. 当前边界

`examples/test-kit` 继续保持为实验包：

- 它可以被 `kt install ./examples/test-kit -e` 安装，用于本地快速迭代。
- 它可以承载 verifier、实验 skill、实验 terrarium 和策略草案。
- 它暂不作为公开 marketplace 包直接分发。

只有当实验资产满足发布门槛后，才应拆出或晋升为正式模板包。

## 2. 三条分发路径

### 2.1 本地开发

使用 editable 安装：

```bash
kt install ./examples/test-kit -e
```

适用场景：

- 开发 creature、tool、skill、policy。
- 验证蓝图任务。
- 调整 verifier 与文档。

发布门槛：

- `kohaku.yaml` 可解析。
- 当前任务对应 verifier 通过。
- 若改动进入默认能力面，默认回归套件通过。

回滚方式：

- 直接回退本地 patch 或切回上一工作分支。

### 2.2 私有发布

使用 git URL 或内部仓库：

```bash
kt install <private-git-url>
```

适用场景：

- 团队内部复用稳定模板。
- 给某个工作流提供可 pin 的版本基线。
- 在进入 marketplace 前做真实安装验证。

发布门槛：

- 默认离线回归套件通过。
- `kohaku.yaml` 的 `version` 与 git tag 一致。
- release notes 说明变更了哪些 creature、skill、tool、policy。
- 明确上一 known-good 版本。

回滚方式：

- 重新安装或 checkout 上一个已知良好的 tag。

### 2.3 Marketplace 候选

使用 marketplace spec：

```bash
kt install @test-kit
kt install @<source>/test-kit
```

适用场景：

- 已经稳定的模板包分发。
- 非 editable 消费者安装。
- 多 marketplace source 按顺序发现。

发布门槛：

- 已先满足私有发布门槛。
- marketplace entry 填齐 `repo`、`tags`、`author`、`license`、`framework`、`versions`。
- 最新未 pin 版本不可是 yanked。
- 坏版本通过 yanked 标记下架，而不是删除历史版本。

回滚方式：

- 将问题版本标记为 yanked。
- 通知用户 pin 到上一个 known-good tag。

## 3. 版本策略

- `0.x`：实验期，可调整模板、策略字段与目录，但必须写 release notes。
- `1.x`：稳定期，必须保留已文档化的安装、运行与引用路径。
- tag 使用 `vMAJOR.MINOR.PATCH`。
- marketplace entry 的 per-version `framework` 可以覆盖 package 级兼容范围。

## 4. `test-kit` 的落地状态

`test-kit` 当前在 `kohaku.yaml` 中声明：

- `distribution.lifecycle_stage: lab`
- `distribution.release_channel: experimental`
- `distribution.marketplace_eligible: false`
- `distribution.governance_policy: release-policy.yaml`

这意味着它现在是可安装、可验证、可演进的实验包，但不是默认公开分发包。

## 5. 验证命令

运行：

```bash
python .\examples\test-kit\scripts\verify_t35_package_governance.py
```

通过标准：

- `kohaku.yaml` 的 distribution 元数据存在且指向真实 policy 文件。
- `release-policy.yaml` 覆盖本地开发、私有发布、marketplace 候选三条路径。
- 每条路径都有发布门槛与回滚方式。
- marketplace entry contract 包含框架当前解析所需字段。
