---
title: T22 验证说明
summary: OpenCLI 次兼容适配的最小验证手册，只说明运行什么命令、看什么结果、判断什么指标。
tags:
  - dev
  - testing
  - opencli
  - package
---

# T22 验证说明

这份文档只说明 `T22` 怎么验证，不解释设计背景。

## 1. 最小验证命令

运行命令：

```bash
python ./examples/test-kit/scripts/verify_t22_opencli.py
```

看什么输出：

- `status: PASS`
- `browser_count` 大于 `0`
- `public_api_count` 大于 `0`
- `desktop_count` 大于 `0`
- `external_count` 大于 `0`
- `unmapped_count: 0`
- `preferred_external_count: 0`

看什么指标：

- **覆盖完整性**：浏览器、公共接口、桌面适配器、外部 CLI 四类目标都被覆盖
- **专项 provider 约束**：外部 passthrough CLI 没有被错误提升为首选执行能力

## 2. Agent 侧验证

运行命令：

```bash
kt run ./examples/test-kit/creatures/lab-runner
```

建议输入：

```text
调用 opencli_registry，先执行 provider_summary，再解析 twitter、cursor 和 gh 这三个目标，最后用 lab_report 保存结果。
```

看什么输出：

- 能返回 `provider_summary`
- `twitter` 被解析为 `browser_authenticated_task`
- `cursor` 被解析为 `desktop_app_task`
- `gh` 被解析为 `external_cli_passthrough`
- `gh` 不应被标成首选 provider
- 最后出现 `Saved lab report to ...`

看什么指标：

- **专项能力分流**：浏览器类、桌面类、外部 CLI 类目标被正确区分
- **优先级正确性**：`OpenCLI` 不会因为能 passthrough 外部命令就覆盖主兼容 provider
- **测试归档**：最终能生成报告文件

## 3. 通过标准

`T22` 验证通过，至少满足这三条：

1. 验证脚本返回 `PASS`
2. `external_cli_passthrough` 目标不被标记为首选
3. `lab-runner` 能读到并使用 `opencli_registry`
