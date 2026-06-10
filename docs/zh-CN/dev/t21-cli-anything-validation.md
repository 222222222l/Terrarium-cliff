---
title: T21 验证说明
summary: CLI-Anything 主兼容适配的最小验证手册，只说明运行什么命令、看什么结果、判断什么指标。
tags:
  - dev
  - testing
  - cli-anything
  - package
---

# T21 验证说明

这份文档只说明 `T21` 怎么验证，不解释设计背景。

## 1. 最小验证命令

运行命令：

```bash
python ./examples/test-kit/scripts/verify_t21_cli_anything.py
```

看什么输出：

- `status: PASS`
- `provider: cli-anything`
- `mapped_entries` 等于 `total_entries`
- `unmapped_entries: 0`
- `browser_nonpreferred_entries` 大于 `0`

看什么指标：

- **映射完整性**：所有官方 registry 条目都被映射到私有 capability
- **浏览器降级规则**：浏览器类 harness 没有被误判成默认首选能力

## 2. 包含公共 registry 的扩展验证

运行命令：

```bash
python ./examples/test-kit/scripts/verify_t21_cli_anything.py --include-public
```

看什么输出：

- 依然是 `status: PASS`
- `total_entries` 明显大于只跑官方 registry 时的数量

看什么指标：

- **兼容范围**：官方与公共 registry 条目都能被同一套规则覆盖

## 3. Agent 侧验证

运行命令：

```bash
kt run ./examples/test-kit/creatures/lab-runner
```

建议输入：

```text
调用 cli_anything_registry，先执行 provider_summary，再解析 libreoffice 和 browser 这两个条目，最后用 lab_report 保存结果。
```

看什么输出：

- 能返回 `provider_summary`
- `libreoffice` 被解析为 `local_software_task`
- `browser` 被解析为 `browser_cli_task`
- 最后出现 `Saved lab report to ...`

看什么指标：

- **provider 可见性**：agent 能读取私有 provider 规则
- **能力解析正确性**：软件类与浏览器类条目被正确分流
- **测试归档**：最终能生成报告文件

## 4. 通过标准

`T21` 验证通过，至少满足这三条：

1. 验证脚本返回 `PASS`
2. `browser` 不被当成默认首选执行能力
3. `lab-runner` 能读到并使用 `cli_anything_registry`
