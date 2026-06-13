---
title: T33 验证说明
summary: 统一能力路由策略的最小验证手册，覆盖 built-in tools、MCP、CLI-Anything、OpenCLI 与重叠回退。
tags:
  - dev
  - testing
  - routing
  - capability
---

# T33 验证说明

这份文档只说明 `T33` 怎么验证，不展开设计背景。

## 1. 最小验证命令

运行命令：

```bash
python .\examples\test-kit\scripts\verify_t33_capability_routing.py
```

看什么输出：

- JSON 中有 `"status": "PASS"`
- `docs_case.execution_surface` 是 `built-in_tools`
- `mcp_case.execution_surface` 是 `mcp`
- `service_case.preferred_provider` 是 `cli-anything`
- `browser_case.preferred_provider` 是 `opencli`
- `overlap_case.decision_status` 是 `needs_user_choice`

## 2. 回归套件验证

`T33` 已进入默认离线回归套件：

```bash
python .\examples\test-kit\scripts\verify_regression_suite.py
```

通过标准：

1. 默认套件返回 `PASS`
2. `T33` 在套件结果中返回 `PASS`
3. 不需要 `CLI-Anything` 或 `OpenCLI` sibling checkout

## 3. 判断指标

- **内建优先**：docs、codebase edit、analysis 任务不强行选择外部 CLI provider。
- **MCP 正名**：MCP 任务进入 `execution_surface: mcp`，并推荐 `mcp_list` / `mcp_call`。
- **外部 CLI 清晰**：service/local 任务落到 `CLI-Anything`，浏览器登录态/桌面任务落到 `OpenCLI`。
- **重叠不猜测**：公共浏览器任务仍返回 `needs_user_choice`，保留用户选择权。
