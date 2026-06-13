---
title: T39 Linux / Windows 双端兼容收口
summary: 将 test-kit 的 HTTP fetch、角色 LLM 冒烟、验证脚本和后续任务原则从 Windows 假设收口到 Linux / Windows 双端可用。
---

# T39 Linux / Windows 双端兼容收口

`T39` 的目标是把当前蓝图从“主要在 Windows 上验证过”推进到“后续任务默认考虑 Linux / Windows 双端”。这不是重写核心框架；核心框架已经有多处 POSIX / Windows 分支。真正需要收口的是 `examples/test-kit` 中的 demo、prompt、验证脚本和 curl 兜底。

## 1. 已确认不受影响

- creature / terrarium / skill / memory schema / governance policy 都使用 YAML、Markdown 和 Python `pathlib`，没有平台绑定。
- `permgate`、`budget`、`audit_guard`、memory curation、evolver 草案协议本身不依赖 Windows。
- 默认离线回归主要是静态结构验证和纯 Python 调用，适合进入 Linux CI。
- 核心服务的 PTY、daemon lifecycle、进程终止路径已经有 Windows / POSIX 分支。

## 2. 已修正的兼容问题

### `cli_runtime`

此前 `cli_invoke` 的 `url` 路径固定转换成：

```json
["curl.exe", "https://example.test"]
```

这在 Linux 上会直接触发 `provider_unavailable`。现在改为：

- Windows: `curl.exe`
- Linux / macOS: `curl`

同时，`command_text` 中用户或模型写出的 `curl` / `curl.exe` 会被规范化成当前平台的正确二进制。

### `role_llm`

角色 LLM 的 urllib 失败后会 fallback 到 curl。现在：

- Windows 使用 `curl.exe --ssl-no-revoke`
- Linux / macOS 使用 `curl`
- 如果 curl 不存在，会返回明确的 `curl executable not found` 错误，而不是隐藏成不透明 subprocess 异常。

### prompt / demo / docs

- worker prompt 不再要求 `curl.exe`，改为“平台 curl binary”。
- T8 worker shortest demo 接受 `curl` 与 `curl.exe`，只检查 URL 与结果语义。
- T38 实时 API 冒烟文档同时提供 PowerShell 和 Bash 示例。

## 3. 验证方式

```bash
python ./examples/test-kit/scripts/verify_t39_linux_windows_compatibility.py --repo-root .
```

该验证不需要真实 Linux 主机。它会用 monkeypatch 模拟：

- `os.name == "nt"` 时，`cli_runtime` 和 `role_llm` 使用 `curl.exe`
- `os.name == "posix"` 时，`cli_runtime` 和 `role_llm` 使用 `curl`
- Windows-only `--ssl-no-revoke` 不进入 POSIX 命令
- T38 文档同时包含 PowerShell / Bash 示例
- worker demo 不再只接受 `curl.exe`

`T39` 已纳入默认离线回归：

```bash
python ./examples/test-kit/scripts/verify_regression_suite.py --json
```

## 4. 后续默认原则

从 `T39` 之后，蓝图后续任务默认遵守：

1. 文档命令同时给出 PowerShell 与 Bash，除非任务明确只面向单端。
2. Python 实现不得把 `curl.exe`、`cmd.exe`、PowerShell、Windows 盘符路径作为通用默认。
3. 示例路径优先使用相对路径或 POSIX 风格路径；只有 Windows 专项说明才写 `E:\...` 或反斜杠路径。
4. 验证脚本检查行为语义，不检查单一平台的二进制名。
5. 外部 provider、浏览器会话、桌面自动化必须声明平台前置条件和缺失时的降级结果。
6. 默认离线回归不得依赖网络、真实浏览器、真实 sibling checkout 或 OS 专属工具。
