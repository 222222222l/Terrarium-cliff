from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _plugin_by_name(config: dict, name: str) -> dict:
    for plugin in config.get("plugins", []):
        if isinstance(plugin, dict) and plugin.get("name") == name:
            return plugin
    raise AssertionError(f"Missing plugin: {name}")


def main() -> None:
    policy_path = ROOT / "governance-policies" / "approval-gate.yaml"
    docs_path = ROOT.parents[1] / "docs" / "zh-CN" / "dev" / "t15-approval-gate.md"
    assert policy_path.is_file(), policy_path
    assert docs_path.is_file(), docs_path

    policy = load_yaml(policy_path)
    assert policy.get("builtin_plugin", {}).get("name") == "permgate"
    assert policy.get("status") == "active-policy"

    protected = {
        item["id"]: item
        for item in policy.get("protected_action_classes", [])
        if isinstance(item, dict)
    }
    assert {"workspace-write", "external-execution", "rule-activation"}.issubset(
        protected
    )
    assert set(protected["workspace-write"]["gated_tools"]) == {"write", "edit"}
    assert protected["external-execution"]["gated_tools"] == ["cli_invoke"]

    metadata_fields = set(
        policy.get("metadata_contract", {}).get("required_fields", [])
    )
    for field in [
        "action_kind",
        "risk_level",
        "source_ref",
        "approval_reason",
        "rollback_plan",
    ]:
        assert field in metadata_fields, field

    denial = policy.get("denial_feedback", {})
    assert denial.get("status") == "blocked"
    for field in ["blocked_by", "action_kind", "reason", "next_safe_step"]:
        assert field in denial.get("required_fields", []), field

    worker = load_yaml(ROOT / "creatures" / "worker-base" / "config.yaml")
    curator = load_yaml(ROOT / "creatures" / "curator" / "config.yaml")
    worker_permgate = _plugin_by_name(worker, "permgate")
    curator_permgate = _plugin_by_name(curator, "permgate")
    assert set(worker_permgate.get("options", {}).get("gated_tools", [])) == {
        "edit",
        "cli_invoke",
    }
    assert set(curator_permgate.get("options", {}).get("gated_tools", [])) == {
        "write",
        "edit",
    }
    assert worker_permgate.get("options", {}).get("surface") == "modal"
    assert curator_permgate.get("options", {}).get("surface") == "modal"

    print("T15 approval-gate verification passed")


if __name__ == "__main__":
    main()
