---
title: T23 验证说明
summary: 静默执行协议的最小验证手册，只说明运行什么命令、看什么结果、判断什么指标。
tags:
  - dev
  - testing
  - cli
  - execution
---

# T23 验证说明

这份文档只说明 `T23` 怎么验证，不解释设计背景。

## 1. 最小验证命令

运行命令：

```bash
python ./examples/test-kit/scripts/verify_t23_silent_execution.py
```

看什么输出：

- JSON 中有 `"status": "PASS"`
- `success_case.success` 是 `true`
- `process_error_case.error_kind` 是 `process_error`
- `artifact_missing_case.error_kind` 是 `artifact_missing`

看什么指标：

- **静默成功路径**：成功执行时只保留 `stdout_summary`，不把完整输出回传给模型
- **错误分级**：非零退出码与产物缺失被分成不同错误类型
- **证据落盘**：每次执行都生成 `stdout.log`、`stderr.log`、`events.jsonl`、`result.json`

## 2. Agent 侧验证

运行命令：

```bash
kt run ./examples/test-kit/creatures/lab-runner
```

建议输入：

```text
调用 cli_invoke，用 python 执行一条会写入 tmp/t23-agent.txt 的命令，provider_name 设为 cli-anything，capability 设为 service_cli_task，artifact_expectation 指向这个文件；完成后再用 lab_report 保存结果。
```

看什么输出：

- 返回结构化结果，而不是整段 stdout
- 输出中能看到：
  - `success=True`
  - `stdout_summary=...`
  - `raw_log_path=...`
  - `result_path=...`
- 最后出现 `Saved lab report to ...`

看什么指标：

- **执行层静默**：返回内容只有摘要和路径，没有整段执行日志
- **结果可审计**：日志和结构化记录都能在文件里找到

## 3. 通过标准

`T23` 验证通过，至少满足这三条：

1. 验证脚本返回 `PASS`
2. 成功执行时不回传完整 stdout
3. 失败执行时只升级为最小诊断，而不是回传整段过程输出
