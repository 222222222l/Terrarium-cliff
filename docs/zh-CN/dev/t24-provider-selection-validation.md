---
title: T24 验证说明
summary: Provider 选择机制的最小验证手册，只说明运行什么命令、看什么结果、判断什么指标。
tags:
  - dev
  - testing
  - provider
  - routing
---

# T24 验证说明

这份文档只说明 `T24` 怎么验证，不解释设计背景。

## 1. 最小验证命令

运行命令：

```bash
.\scripts\run-in-test-env.ps1 python .\examples\test-kit\scripts\verify_t24_provider_selection.py
```

看什么输出：

- JSON 中有 `"status": "PASS"`
- `service_case.preferred_provider` 是 `cli-anything`
- `browser_session_case.preferred_provider` 是 `opencli`
- `overlap_case.decision_status` 是 `needs_user_choice`
- `explicit_case.preferred_provider` 是 `opencli`

看什么指标：

- **自动选择**：明确的软件 / 服务任务自动落到 `CLI-Anything`
- **专项选择**：需要登录态或实时浏览器会话的任务自动落到 `OpenCLI`
- **重叠回退**：浏览器公共场景无法判断更优 provider 时，不擅自猜测，而是交还用户
- **显式优先级**：用户或 task card 已明确指定 provider 时，必须尊重

## 2. Agent 侧验证

运行命令：

```bash
.\scripts\run-in-test-env.ps1 kt run .\examples\test-kit\creatures\lab-runner
```

建议输入：

```text
先调用 provider_select 判断一个 browser_public_task 且 target_hint=website 的任务该选哪个 provider；如果结果是 needs_user_choice，就把候选 provider 和原因列出来；然后再调用 provider_select 判断一个 service_cli_task，并输出最终 preferred_provider。
```

看什么输出：

- 第一段结果里：
  - `decision_status` 是 `needs_user_choice`
  - `candidate_providers` 同时包含 `cli-anything` 和 `opencli`
- 第二段结果里：
  - `decision_status` 是 `selected`
  - `preferred_provider` 是 `cli-anything`

看什么指标：

- **用户主权**：重叠能力不会被模型静默拍板
- **编排稳定性**：明确任务不再把试错压力留给执行层

## 3. 通过标准

`T24` 验证通过，至少满足这三条：

1. 验证脚本返回 `PASS`
2. 重叠能力返回 `needs_user_choice`
3. 明确任务返回单一 `preferred_provider`
