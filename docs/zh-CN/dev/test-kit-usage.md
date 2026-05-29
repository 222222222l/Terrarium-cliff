---
title: test-kit 使用说明
summary: 面向实际执行的 test-kit 快速测试手册，只说明运行什么命令、看什么结果、判断什么指标。
tags:
  - dev
  - testing
  - creature
  - package
---

# test-kit 使用说明

这份文档只做一件事：告诉你用 `test-kit` 做测试时，应该运行什么命令、看什么输出、判断什么指标。

如果你需要看“为什么这样设计、什么时候切换组件、为什么区分 `lab-runner` 和 `lab-smoke`”，请看：

- [test-kit-reference.md](file:///e:/KohakuTerrarium/docs/zh-CN/dev/test-kit-reference.md)

## 1. 先看结论

- 单体测试：用 `lab-runner`
- 多角色路由冒烟：用 `lab-smoke`
- 每次测试结束：调用 `lab_report`

## 2. 最常用命令

### 2.1 直接运行单体测试

```bash
kt run ./examples/test-kit/creatures/lab-runner
```

看什么输出：

- 成功进入交互提示，例如 `Lab>`
- agent 能正常响应你的测试任务
- 测试结束后出现 `Saved lab report to ...`

看什么指标：

- 启动指标：是否能进入交互状态
- 执行指标：是否完成最小检查
- 归档指标：是否生成 `.kohaku/lab-reports/*.md`

### 2.2 直接运行多角色冒烟

```bash
kt terrarium run ./examples/test-kit/terrariums/lab-smoke --seed "执行一次最小冒烟测试，并确认路由和反馈链路都工作。"
```

看什么输出：

- root 是否接收 seed 任务
- worker 是否开始执行
- critic 是否给出 `PASS` / `FAIL` / `MISSING EVIDENCE`
- 最终是否出现结果汇总或报告保存信息

看什么指标：

- 路由指标：任务是否从 root 到 worker，再到 critic
- 反馈指标：critic 的反馈是否回来
- 结果指标：是否形成最终结果，而不是卡在中间角色

### 2.3 以 package 形式安装后运行

```bash
kt install ./examples/test-kit -e
kt run @test-kit/creatures/lab-runner
kt terrarium run @test-kit/terrariums/lab-smoke --seed "测试 test-kit 是否可用"
```

看什么输出：

- `kt install` 成功结束
- `@test-kit/...` 路径能被识别
- creature 和 terrarium 都能启动

看什么指标：

- 安装指标：无 manifest 解析错误
- 解析指标：`@test-kit/creatures/lab-runner` 可运行
- 复用指标：后续可直接基于 `@test-kit/...` 做测试

## 3. 建议的第一条测试输入

### 3.1 给 `lab-runner`

```text
检查当前 creature 配置里有哪些工具和子代理，执行一个最小安全检查，并用 lab_report 保存结果。
```

合格结果看什么：

- 能正确列出工具和子代理
- 至少完成一个安全检查
- 最后调用 `lab_report`

### 3.2 给 `lab-smoke`

```text
执行一次最小冒烟测试，并确认 root、worker、critic 三个角色都参与过。
```

合格结果看什么：

- 三个角色都出现过有效工作
- critic 给出明确判断
- 最终有汇总结果

## 4. 各类测试怎么跑

### 4.1 测一个 tool

运行命令：

```bash
kt run ./examples/test-kit/creatures/lab-runner
```

建议输入：

```text
只测试 <tool-name> 是否能完成一次最小安全调用，结论用 lab_report 保存。
```

主要看：

- 这个 tool 是否真的被调用
- 返回结果是否符合预期
- 是否写出报告

### 4.2 测一个 plugin

运行命令：

```bash
kt run ./examples/test-kit/creatures/lab-runner
```

主要看：

- plugin 是否生效
- 是否拦截、改写或放行了预期行为
- 是否引入额外噪声或副作用

### 4.3 测一个 prompt

运行命令：

```bash
kt run ./examples/test-kit/creatures/lab-runner
```

主要看：

- 输出风格是否变化
- 是否更稳定执行测试任务
- 是否没有额外跑偏

### 4.4 测 terrarium 路由

运行命令：

```bash
kt terrarium run ./examples/test-kit/terrariums/lab-smoke --seed "测试最小路由和反馈链路。"
```

主要看：

- root 是否正确派发
- worker 是否执行
- critic 是否反馈
- 流程是否闭环

## 5. `lab_report` 怎么判断是否正常

报告目录：

```text
.kohaku/lab-reports/
```

正常结果：

- 目录里出现新的 `.md` 文件
- 文件内至少包含：
  - `status`
  - `summary`
  - `generated_at`

如果没有生成报告，优先判断：

- 本次测试是否真的调用了 `lab_report`
- 是否有路径权限或执行中断问题

## 6. 最重要的判断指标

以后你做任何测试，优先只看这 5 个指标：

1. 能不能启动
2. 目标组件有没有真的加载
3. 最小测试有没有真的执行
4. 输出是否足够判断成败
5. 是否生成了可复盘报告

## 7. 推荐测试顺序

以后新增任何能力，按这个顺序跑：

1. 先跑 `lab-runner`
2. 单体通过后，再跑 `lab-smoke`
3. 最后看 `.kohaku/lab-reports/` 里的结果文件
