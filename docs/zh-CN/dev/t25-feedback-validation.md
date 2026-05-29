---
title: T25 验证说明
summary: 结果反馈双通道协议的最小验证手册，只说明运行什么命令、看什么结果、判断什么指标。
tags:
  - dev
  - testing
  - feedback
  - protocol
---

# T25 验证说明

这份文档只说明 `T25` 怎么验证，不解释设计背景。

## 1. 最小验证命令

运行命令：

```bash
.\scripts\run-in-test-env.ps1 python .\examples\test-kit\scripts\verify_t25_feedback_protocol.py
```

看什么输出：

- JSON 中有 `"status": "PASS"`
- `json_case.call_status` 是 `success`
- `xml_case.agent_feedback_format` 是 `xml`
- `tool_case.output_preview` 里有“正在做什么”
- `registration_case.package_registered` 和 `registration_case.creature_registered` 都是 `true`

看什么指标：

- **双通道分离**：用户侧只看到简洁自然语言摘要，不混入路径和结构化字段
- **结构化落盘**：agent 侧反馈能写成 `json` 或 `xml` 文件，供后续 agent 按需读取
- **压缩优先**：结构化结果只保留短字段、关键发现、证据路径和裁剪后的原始结果摘要
- **实验台可用**：`result_feedback` 已经注册进 `test-kit` 包与 `lab-runner`

## 2. Agent 侧验证

运行命令：

```bash
.\scripts\run-in-test-env.ps1 kt run .\examples\test-kit\creatures\lab-runner
```

建议输入：

```text
请调用 result_feedback，tool_name=result_feedback，call_status=running，current_action=整理当前验证进度，next_action=把结构化结果交给后续 agent，achievements=["实验台已接入该工具"]，key_findings=["agent 侧结构化反馈会单独落盘"]。然后直接展示工具输出里的用户摘要，并说明 metadata 中应重点关注哪些字段。
```

看什么输出：

- 工具输出只展示用户摘要
- 用户摘要里有：
  - “工具 `result_feedback` 当前状态：执行中。”
  - “正在做什么：整理当前验证进度”
  - “将要做什么：把结构化结果交给后续 agent”
- agent 会补充说明 metadata 里至少有：
  - `schema_version`
  - `agent_feedback_path`
  - `user_feedback_path`
  - `agent_feedback_format`

看什么指标：

- **不黑箱**：用户能看到当前动作、下一步和已经达成的里程碑
- **不混通道**：结构化字段不直接塞进用户展示正文
- **可衔接后续 agent**：后续 agent 能从 metadata 与落盘文件继续分析，而不是复读完整执行日志

## 3. 通过标准

`T25` 验证通过，至少满足这三条：

1. 验证脚本返回 `PASS`
2. 用户摘要和结构化输出分离
3. `result_feedback` 已接入 `test-kit` 与 `lab-runner`
