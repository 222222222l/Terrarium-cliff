from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLES = ["root-privileged", "coordinator", "worker-base", "critic", "curator"]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _plugin_by_name(config: dict, name: str) -> dict:
    for plugin in config.get("plugins", []):
        if isinstance(plugin, dict) and plugin.get("name") == name:
            return plugin
    raise AssertionError(f"Missing plugin: {name}")


def main() -> None:
    policy_path = ROOT / "governance-policies" / "budget-policy.yaml"
    docs_path = ROOT.parents[1] / "docs" / "zh-CN" / "dev" / "t16-budget-policy.md"
    assert policy_path.is_file(), policy_path
    assert docs_path.is_file(), docs_path

    policy = load_yaml(policy_path)
    assert policy.get("builtin_plugin", {}).get("name") == "budget"
    role_budgets = policy.get("role_budgets", {})
    assert set(ROLES).issubset(role_budgets), role_budgets

    seen_budgets = set()
    for role in ROLES:
        expected = role_budgets[role]
        config = load_yaml(ROOT / "creatures" / role / "config.yaml")
        budget = _plugin_by_name(config, "budget")
        options = budget.get("options", {})
        assert options.get("turn_budget") == expected.get("turn_budget"), role
        assert options.get("tool_call_budget") == expected.get("tool_call_budget"), role
        assert "walltime_budget" not in options, role
        seen_budgets.add(
            (
                tuple(options.get("turn_budget")),
                tuple(options.get("tool_call_budget")),
            )
        )

    assert len(seen_budgets) == len(ROLES), "role budgets should be distinct"

    for role in ["worker-base", "curator"]:
        config = load_yaml(ROOT / "creatures" / role / "config.yaml")
        _plugin_by_name(config, "permgate")

    rules = "\n".join(policy.get("budget_rules", []))
    assert "soft limits" in rules
    assert "hard limits" in rules
    fallback = policy.get("fallback_behavior", {})
    assert fallback.get("hard_wall")
    assert fallback.get("soft_alarm")

    print("T16 budget-policy verification passed")


if __name__ == "__main__":
    main()
