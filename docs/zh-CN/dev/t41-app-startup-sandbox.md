# T41 应用层启动与沙箱写入兼容验证

## 背景

`T40` 已经证明 `examples/test-kit` 的 manifest、release checklist 与路径引用在离线层面自洽，但这还不能证明真实 `kt` 应用入口能在受限环境里启动。

本轮应用层 smoke 发现：当默认用户配置目录不可写时，框架 import 阶段会初始化日志系统，并尝试写入 `~/.kohakuterrarium/logs`。在沙箱只允许工作区写入的情况下，这会让 `kt --version`、`kt --help` 这类基础入口直接失败。

## 修改

- 日志初始化优先使用正常 `KT_CONFIG_DIR/logs`。
- 如果默认配置目录不可创建或不可写，自动降级到系统临时目录下的 `kohakuterrarium/logs`。
- 如果临时目录也不可写，降级为 `NullHandler`，保证 CLI 启动不因日志文件失败而中断。
- 新增 `current_log_file()`，便于测试确认当前文件日志实际落点。

## 验证

该验证需要可运行本地源码的 Python 环境，例如项目 `.venv`：

```powershell
.\.venv\Scripts\python.exe .\examples\test-kit\scripts\verify_t41_app_startup_sandbox.py --repo-root .
```

Linux / macOS：

```bash
./.venv/bin/python ./examples/test-kit/scripts/verify_t41_app_startup_sandbox.py --repo-root .
```

验证内容：

- `python -m kohakuterrarium --version` 可启动。
- `python -m kohakuterrarium --help` 可启动。
- `kt info` 能读取 `worker-base` creature。
- `load_terrarium_config()` 能读取 `task-team-minimal` terrarium。
- 上述检查都在 `KT_CONFIG_DIR` 指向普通文件的受限场景下执行。

## 默认回归策略

`T41` 暂不进入 `verify_regression_suite.py` 默认离线套件，因为它需要完整本地应用依赖环境。默认套件继续保持轻量、离线、无全局环境假设；应用层 smoke 作为阶段验收或发布前检查单独运行。
