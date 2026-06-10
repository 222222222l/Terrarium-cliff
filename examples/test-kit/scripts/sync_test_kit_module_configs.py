from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEST_KIT_ROOT = PROJECT_ROOT / "examples" / "test-kit"
CREATURES_DIR = TEST_KIT_ROOT / "creatures"
KT_HOME = PROJECT_ROOT / ".tmp-kt-home"


def _prepare_runtime_home() -> None:
    os.environ.setdefault("KT_CONFIG_DIR", str(KT_HOME))
    (KT_HOME / "logs").mkdir(parents=True, exist_ok=True)


def _load_tool_class(config_path: Path, tool_entry: dict[str, Any]) -> type[Any] | None:
    module_path = str(tool_entry.get("module", "") or "").strip()
    class_name = str(tool_entry.get("class", "") or "").strip()
    if not module_path or not class_name:
        return None
    full_module_path = (config_path.parent / module_path).resolve()
    if not full_module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(
        f"test_kit_sync_{full_module_path.stem}",
        full_module_path,
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, class_name, None)
    return cls if isinstance(cls, type) else None


def _default_options_for_tool(tool_cls: type[Any]) -> dict[str, Any]:
    default_options = getattr(tool_cls, "default_options", None)
    if callable(default_options):
        result = default_options()
        if isinstance(result, dict):
            return dict(result)
    option_schema = getattr(tool_cls, "option_schema", None)
    if callable(option_schema):
        schema = option_schema() or {}
        if isinstance(schema, dict):
            return {
                key: value.get("default")
                for key, value in schema.items()
                if isinstance(value, dict) and "default" in value
            }
    return {}


def _sync_config_file(config_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    tools = payload.get("tools") or []
    changed_tools: list[str] = []
    changed = False

    for tool_entry in tools:
        if not isinstance(tool_entry, dict):
            continue
        if str(tool_entry.get("type", "builtin")) != "custom":
            continue
        tool_cls = _load_tool_class(config_path, tool_entry)
        if tool_cls is None:
            continue
        defaults = _default_options_for_tool(tool_cls)
        if not defaults:
            continue
        tool_changed = False
        for key, value in defaults.items():
            if key not in tool_entry:
                tool_entry[key] = value
                tool_changed = True
                changed = True
        if tool_changed:
            changed_tools.append(str(tool_entry.get("name", tool_entry.get("class", "custom-tool"))))

    if changed:
        config_path.write_text(
            yaml.safe_dump(payload, allow_unicode=False, sort_keys=False),
            encoding="utf-8",
        )
    return {
        "config_path": str(config_path),
        "changed": changed,
        "changed_tools": changed_tools,
    }


def main() -> None:
    _prepare_runtime_home()
    config_paths = sorted(CREATURES_DIR.glob("*/config.yaml"))
    summary = [_sync_config_file(path) for path in config_paths]
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
