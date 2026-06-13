---
title: T38 阶段性可用性验证
summary: 将当前蓝图进度下的可用性验收固化为可重复、离线优先、可选实时 API 冒烟的阶段门禁。
---

# T38 阶段性可用性验证

`T38` 的目标不是继续增加新协议，而是在 `T11-T19`、`T33`、`T35` 完成后，把“当前功能是否还能作为一个可用阶段继续前进”变成稳定检查。

## 1. 验证边界

默认验证只做离线检查：

- 默认回归套件已经覆盖主链、记忆治理、审批、预算、审计、演化、静默执行、能力路由与发布治理。
- `TASK_TEAM_BASE_URL` / `TASK_TEAM_API_KEY` / `TASK_TEAM_MODEL` 能覆盖角色 LLM 默认配置。
- Windows 下角色 LLM 的 `curl.exe` 兜底会带 `--ssl-no-revoke`，降低证书吊销查询导致的误失败。
- `run_t8_role_direct.py` 保留 coordinator / critic / root 的真实 prompt 直连入口。
- `worker-base` 的 `edit` 与 `cli_invoke` 仍被 `permgate` 保护，因此完整工具链冒烟不应和纯模型连通性测试混在一起。

## 2. 默认执行

```bash
python .\examples\test-kit\scripts\verify_t38_phase_usability.py --repo-root .
```

通过后会输出 JSON：

```json
{
  "status": "PASS",
  "default_suite": {
    "count": 19
  },
  "live_smoke_entry": "examples/test-kit/scripts/run_t8_role_direct.py"
}
```

`T38` 已纳入默认离线回归：

```bash
python .\examples\test-kit\scripts\verify_regression_suite.py --json
```

## 3. 可选实时 API 冒烟

当需要验证某个临时或私有 OpenAI-compatible provider 时，只在当前 shell 注入环境变量，不写入仓库配置：

PowerShell:

```powershell
$env:TASK_TEAM_BASE_URL = "https://example-provider.test/v1"
$env:TASK_TEAM_API_KEY = "<temporary-key>"
$env:TASK_TEAM_MODEL = "gemini-3-flash-preview"
$env:T8_ROLE = "coordinator"
$env:T8_MAX_TOKENS = "3000"
$env:T8_USER_INPUT = "Smoke test only. Produce one minimal task_card for a no-op validation task. Do not call tools."
python .\examples\test-kit\scripts\run_t8_role_direct.py
```

Bash:

```bash
export TASK_TEAM_BASE_URL="https://example-provider.test/v1"
export TASK_TEAM_API_KEY="<temporary-key>"
export TASK_TEAM_MODEL="gemini-3-flash-preview"
export T8_ROLE="coordinator"
export T8_MAX_TOKENS="3000"
export T8_USER_INPUT="Smoke test only. Produce one minimal task_card for a no-op validation task. Do not call tools."
python ./examples/test-kit/scripts/run_t8_role_direct.py
```

验收标准：

- 命令返回 0。
- 输出包含完整 `task_card` fence。
- 不要求执行 `cli_invoke`。

## 4. 为什么不默认跑完整工具链冒烟

当前阶段已经启用了 `T15 approval-gate`：

- `worker-base` 的 `cli_invoke` 被 `permgate` 保护。
- 非交互脚本中强行跑完整 worker 链路，会把“provider 连通性”误测成“审批 UI / 审批超时策略”。
- 因此实时 provider 冒烟先走 `run_t8_role_direct.py`；完整工具链应作为单独人工验收或审批流测试执行。

## 5. 完成判定

`T38` 通过至少意味着：

1. 当前阶段的离线功能门禁仍然完整。
2. 实时 provider 冒烟有明确入口和环境变量约定。
3. 工具执行链路的审批边界被保留，没有为了测试便利绕过治理。
4. 后续进入 CLI / Studio / marketplace 实装前，有一个稳定的阶段验收基准。
