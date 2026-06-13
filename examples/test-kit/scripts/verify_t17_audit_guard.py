from __future__ import annotations

import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _plugin_by_name(config: dict, name: str) -> dict:
    for plugin in config.get("plugins", []):
        if isinstance(plugin, dict) and plugin.get("name") == name:
            return plugin
    raise AssertionError(f"Missing plugin: {name}")


def _load_audit_guard_source() -> tuple[ast.Module, str]:
    module_path = ROOT / "test_kit" / "plugins" / "audit_guard.py"
    source = module_path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(module_path)), source


def _class_def(tree: ast.Module, name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"Missing class: {name}")


def main() -> None:
    manifest = load_yaml(ROOT / "kohaku.yaml")
    plugins = {
        entry["name"]: entry
        for entry in manifest.get("plugins", [])
        if isinstance(entry, dict)
    }
    assert "audit_guard" in plugins, sorted(plugins)
    assert plugins["audit_guard"]["module"] == "test_kit.plugins.audit_guard"
    assert plugins["audit_guard"]["class"] == "AuditGuardPlugin"

    tree, source = _load_audit_guard_source()
    plugin_cls = _class_def(tree, "AuditGuardPlugin")
    base_names = {
        base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
        for base in plugin_cls.bases
    }
    assert "BasePlugin" in base_names
    method_names = {
        node.name
        for node in plugin_cls.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert "option_schema" in method_names
    assert "post_tool_execute" in method_names
    assert "audit_path" in source
    assert "tracked_tools" in source
    assert "audit-guard.v1" in source

    policy_path = ROOT / "governance-policies" / "audit-guard.yaml"
    docs_path = PROJECT_ROOT / "docs" / "zh-CN" / "dev" / "t17-audit-guard.md"
    assert policy_path.is_file(), policy_path
    assert docs_path.is_file(), docs_path
    policy = load_yaml(policy_path)
    assert policy.get("plugin", {}).get("name") == "audit_guard"
    tracked = {
        item["id"]: item
        for item in policy.get("tracked_action_classes", [])
        if isinstance(item, dict)
    }
    assert {"workspace-write", "external-execution", "evolution-draft"}.issubset(
        tracked
    )

    worker = load_yaml(ROOT / "creatures" / "worker-base" / "config.yaml")
    curator = load_yaml(ROOT / "creatures" / "curator" / "config.yaml")
    worker_audit = _plugin_by_name(worker, "audit_guard")
    curator_audit = _plugin_by_name(curator, "audit_guard")
    assert set(worker_audit.get("tracked_tools", [])) == {"edit", "cli_invoke"}
    assert set(curator_audit.get("tracked_tools", [])) == {"write", "edit"}
    assert worker_audit.get("audit_path") == ".kohaku/audit/audit-guard.jsonl"
    assert curator_audit.get("audit_path") == ".kohaku/audit/audit-guard.jsonl"

    print("T17 audit-guard verification passed")


if __name__ == "__main__":
    main()
