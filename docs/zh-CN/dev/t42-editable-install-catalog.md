# T42 Editable 安装与 Catalog 可见性验证

## 背景

`T41` 修复了真实 `kt` 入口在受限配置目录下的启动阻断，但继续进行应用层测试后发现三个更细的遗漏：

1. package 安装目录仍可能绕过 `KT_CONFIG_DIR`，尝试写入真实用户目录。
2. `kt info @pkg/creatures/name` 与文档承诺不一致，未解析 package ref。
3. Studio catalog scanner 只识别 manifest 中显式 `path` 字段，未识别 `test-kit` 当前使用的 name-only creature / terrarium 声明。

这些问题不一定会被默认离线回归发现，但会直接影响业务开发前的本地 editable package 使用。

## 修改

- `packages.locations._packages_dir()` 默认改为 `config_dir() / "packages"`，同时保留测试和旧调用方 monkeypatch `PACKAGES_DIR` 的兼容入口。
- `kt info` 入口补齐 `@pkg/...` 解析，与 `kt run` 的 package ref 行为一致。
- Studio catalog scanner 支持 name-only manifest entry，默认映射为：
  - creature: `creatures/{name}`
  - terrarium: `terrariums/{name}`
- 新增 `verify_t42_editable_install_catalog.py`，把 editable install、package ref、catalog creature/terrarium 可见性串成应用层 smoke。

## 验证

PowerShell：

```powershell
.\.venv\Scripts\python.exe .\examples\test-kit\scripts\verify_t42_editable_install_catalog.py --repo-root .
```

Linux / macOS：

```bash
./.venv/bin/python ./examples/test-kit/scripts/verify_t42_editable_install_catalog.py --repo-root .
```

该脚本使用临时 `KT_CONFIG_DIR`，不会写入真实 `~/.kohakuterrarium/packages`。验证内容包括：

- `kt install <test-kit> -e --name test-kit`
- editable link 写入 `KT_CONFIG_DIR/packages`
- `kt list` 能看到 `test-kit`
- `kt info @test-kit/creatures/worker-base` 可解析
- catalog scanner 能看到 `worker-base` 与 `task-team-minimal`

## 默认回归策略

`T42` 与 `T41` 一样属于应用层 smoke，需要完整本地运行环境，因此暂不纳入默认离线回归。进入业务层开发、准备私有发布或排查 Studio catalog 可见性时应单独运行。
