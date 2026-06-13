---
title: T40 Package 安装就绪门禁
summary: 在 T35 发布治理之上，验证 test-kit 作为可安装 package 时 manifest 中声明的资源都能解析到真实文件。
---

# T40 Package 安装就绪门禁

`T35` 已定义 package / marketplace 的发布治理策略，但它主要回答“什么时候能发布、怎么回滚”。`T40` 补上更靠近实际安装的一层：`kohaku.yaml` 中声明的 creature、terrarium、skill、tool、plugin 是否都指向真实、相对、双端友好的 package 资源。

## 1. 验证范围

默认离线检查：

- `kohaku.yaml` 的 package 名称与 semver 版本格式。
- `distribution.governance_policy` 指向真实 `release-policy.yaml`。
- `creatures:` 中每个条目存在 `creatures/<name>/config.yaml`。
- `terrariums:` 中每个条目存在 `terrariums/<name>/terrarium.yaml`。
- `skills:` 中每个 `path` 是相对路径、使用 `/` 分隔、指向真实 `SKILL.md`。
- `tools:` 与 `plugins:` 中每个 `module` 能映射到 `examples/test-kit/test_kit/**/*.py`。
- `release-checklist.yaml` 声明 Windows / Linux 双端支持、默认回归、T39 双端门禁、release notes 字段和私有发布阻断项。

## 2. 为什么不直接运行 `kt install`

`T40` 是默认离线回归的一部分，不能依赖外部网络、真实用户 package cache 或当前机器全局安装状态。它只验证安装前最容易破坏的静态契约：manifest 是否自洽、引用是否落到真实文件、发布前 checklist 是否完整。

真实 `kt install ./examples/test-kit -e` 仍应作为人工验收或发布前 smoke 执行，但不放进默认离线回归。

## 3. 执行方式

PowerShell:

```powershell
python .\examples\test-kit\scripts\verify_t40_package_install_readiness.py --repo-root .
```

Bash:

```bash
python ./examples/test-kit/scripts/verify_t40_package_install_readiness.py --repo-root .
```

默认回归：

```bash
python ./examples/test-kit/scripts/verify_regression_suite.py --json
```

## 4. 通过标准

`T40` 通过至少意味着：

1. manifest 中公开的资源没有悬空引用。
2. skill 路径保持 package-relative，未写死 Windows 路径。
3. tool / plugin 模块路径能静态映射到真实 Python 文件。
4. 私有发布前必须跑默认回归与 T39 双端门禁。
5. release notes 至少包含变更面、验证结果、回滚目标和已知限制。
