---
title: test-kit 参考说明
summary: test-kit 的设计目的、适用边界、组件替换方式与使用策略说明。
tags:
  - dev
  - testing
  - creature
  - package
---

# test-kit 参考说明

这份文档不负责告诉你“具体执行什么命令”，而是说明 `test-kit` 为什么这样设计，以及什么时候该怎么用。

如果你想直接执行测试，请看：

- [test-kit-usage.md](file:///e:/KohakuTerrarium/docs/zh-CN/dev/test-kit-usage.md)

## 1. 为什么分成两层

`test-kit` 分成：

- `lab-runner`
- `lab-smoke`

原因不是为了复杂，而是因为要测的问题本来就分两类：

- 单体问题：一个 creature、tool、plugin、skill 是否正常
- 编排问题：多角色路由、反馈闭环是否正常

把这两类问题硬塞进一个配置，只会让测试成本上升、定位难度变高。

## 2. `lab-runner` 的定位

`lab-runner` 是默认实验台，优先用于：

- package 工具测试
- plugin 测试
- skill 测试
- prompt 测试
- creature 行为测试
- 静默执行测试
- 未来的 `CLI-Anything` / `OpenCLI` 兼容接入测试

它的核心价值是：

- 启动快
- 变量少
- 容易复现
- 适合做“最小验证”

## 3. `lab-smoke` 的定位

`lab-smoke` 不是日常默认入口，只在需要验证这些问题时使用：

- root 编排
- worker 执行
- critic 反馈
- channel 路由
- 最小闭环

它的目标不是完整业务模拟，而是最小冒烟验证。

## 4. 为什么保留 `lab_report`

`lab_report` 的目的只有一个：把测试结果从对话里分离出来，形成独立可复盘记录。

这样做的好处：

- 不用反复翻聊天记录找结论
- 可以对比多次实验结果
- 后续做 provider 兼容、静默执行、反馈分析时都有统一产物

## 5. 如何替换组件

### 替换工具

编辑目标 creature 的 `tools:`：

- 增加 builtin tool
- 移除 builtin tool
- 替换 custom tool
- 后续改成 package tool

建议一次只改一个工具变量。

### 替换 plugin

给 `lab-runner` 或 `lab-smoke` 对应 creature 增加 `plugins:`。

建议一次只测一个 plugin，否则很难判断问题来源。

### 替换 prompt

最快方式是复制目标 creature 目录，只改 `prompts/system.md`。

### 替换 provider 兼容层

后续 `T21-T25` 实现后，优先把 provider 适配接进 `lab-runner`，不要另起一套新测试 creature。

## 6. 推荐使用策略

建议始终按这个顺序：

1. 先在 `lab-runner` 做单体测试
2. 单体通过后，再决定是否需要 `lab-smoke`
3. 测试结束后，一律生成 `lab_report`

如果是 CLI 兼容类功能：

1. 先测命令能否静默执行
2. 再测结果摘要是否足够
3. 最后才测 terrarium 路由

## 7. 适合在这里验证的后续任务

- `CLI-Anything` 主兼容适配
- `OpenCLI` 次兼容适配
- 静默执行协议
- provider 路由选择
- 结果反馈分析协议
