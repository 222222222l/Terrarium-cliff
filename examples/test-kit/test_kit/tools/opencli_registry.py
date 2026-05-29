from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import yaml

from kohakuterrarium.modules.tool.base import BaseTool, ExecutionMode, ToolResult


class OpenCliRegistryTool(BaseTool):
    needs_context = True
    is_concurrency_safe = True

    @property
    def tool_name(self) -> str:
        return "opencli_registry"

    @property
    def description(self) -> str:
        return "Inspect and resolve OpenCLI adapters and external CLIs through the private provider mapping."

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["provider_summary", "list_targets", "resolve_target"],
                    "description": "Operation to perform.",
                },
                "target_name": {
                    "type": "string",
                    "description": "Site, app, or external CLI name for resolve_target.",
                },
                "target_type": {
                    "type": "string",
                    "enum": ["browser", "public_api", "desktop", "external"],
                    "description": "Optional target family filter.",
                },
                "query": {
                    "type": "string",
                    "description": "Keyword used by list_targets.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum number of results to return.",
                },
                "provider_spec_path": {
                    "type": "string",
                    "description": "Optional override path for providers/opencli.yaml.",
                },
                "adapters_index_path": {
                    "type": "string",
                    "description": "Optional override path for docs/adapters/index.md.",
                },
                "external_clis_path": {
                    "type": "string",
                    "description": "Optional override path for src/external-clis.yaml.",
                },
            },
            "required": ["action"],
        }

    async def _execute(self, args: dict[str, Any], **kwargs: Any) -> ToolResult:
        context = kwargs.get("context")
        start_dir = context.working_dir if context else Path.cwd()
        repo_root = self._find_repo_root(start_dir)

        provider_spec_path = self._resolve_path(
            args.get("provider_spec_path"),
            repo_root / "examples" / "test-kit" / "providers" / "opencli.yaml",
        )
        adapters_index_path = self._resolve_path(
            args.get("adapters_index_path"),
            repo_root / "OpenCLI" / "docs" / "adapters" / "index.md",
        )
        external_clis_path = self._resolve_path(
            args.get("external_clis_path"),
            repo_root / "OpenCLI" / "src" / "external-clis.yaml",
        )

        if not provider_spec_path.exists():
            return ToolResult(error=f"Provider spec not found: {provider_spec_path}", exit_code=1)
        if not adapters_index_path.exists():
            return ToolResult(error=f"Adapters index not found: {adapters_index_path}", exit_code=1)
        if not external_clis_path.exists():
            return ToolResult(error=f"External CLI registry not found: {external_clis_path}", exit_code=1)

        provider_spec = self._load_yaml(provider_spec_path)
        adapters = self._load_adapters(adapters_index_path)
        external_clis = self._load_external_clis(external_clis_path)
        action = str(args.get("action", "")).strip()

        match action:
            case "provider_summary":
                payload = self._provider_summary(provider_spec, adapters, external_clis)
            case "list_targets":
                payload = self._list_targets(provider_spec, adapters, external_clis, args)
            case "resolve_target":
                payload = self._resolve_target(provider_spec, adapters, external_clis, args)
            case _:
                return ToolResult(error=f"Unsupported action: {action}", exit_code=1)

        return ToolResult(
            output=json.dumps(payload, indent=2, ensure_ascii=False),
            exit_code=0,
            metadata={"provider": "opencli"},
        )

    def _find_repo_root(self, start_dir: Path) -> Path:
        candidates = [start_dir.resolve(), *start_dir.resolve().parents]
        for candidate in candidates:
            if (candidate / "OpenCLI" / "README.md").exists():
                return candidate
        return start_dir.resolve()

    def _resolve_path(self, raw_path: Any, default_path: Path) -> Path:
        if raw_path:
            return Path(str(raw_path)).expanduser().resolve()
        return default_path.resolve()

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Expected YAML object in {path}")
        return data

    def _load_external_clis(self, path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or []
        if not isinstance(data, list):
            raise ValueError(f"Expected YAML list in {path}")
        result: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                enriched = dict(item)
                enriched["_source_type"] = "external"
                result.append(enriched)
        return result

    def _load_adapters(self, path: Path) -> list[dict[str, Any]]:
        lines = path.read_text(encoding="utf-8").splitlines()
        section: str | None = None
        results: list[dict[str, Any]] = []

        for raw_line in lines:
            line = raw_line.rstrip()
            if line.startswith("## "):
                section = line.removeprefix("## ").strip()
                continue
            if not section or not line.startswith("| **["):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 3:
                continue
            name_match = re.search(r"\*\*\[(.+?)\]\(", cells[0])
            if not name_match:
                continue
            name = name_match.group(1).strip()
            description = ""
            commands_cell = cells[1]
            mode = cells[2]
            target_type = "browser" if section == "Browser Adapters" else "public_api"
            if section == "Desktop Adapters":
                target_type = "desktop"
                description = commands_cell
                commands_cell = cells[2]
                mode = "Desktop"
            commands = re.findall(r"`([^`]+)`", commands_cell)
            results.append(
                {
                    "name": name.lower(),
                    "display_name": name,
                    "section": section,
                    "target_type": target_type,
                    "commands": commands,
                    "mode": mode,
                    "description": description,
                    "_source_type": "adapter",
                }
            )
        return results

    def _provider_summary(
        self,
        provider_spec: dict[str, Any],
        adapters: list[dict[str, Any]],
        external_clis: list[dict[str, Any]],
    ) -> dict[str, Any]:
        counts = {
            "browser": len([item for item in adapters if item["target_type"] == "browser"]),
            "public_api": len([item for item in adapters if item["target_type"] == "public_api"]),
            "desktop": len([item for item in adapters if item["target_type"] == "desktop"]),
            "external": len(external_clis),
        }
        return {
            "provider_name": provider_spec.get("provider", {}).get("name"),
            "entry_point": provider_spec.get("provider", {}).get("entry_point"),
            "installed": bool(shutil.which(str(provider_spec.get("provider", {}).get("entry_point", "opencli")))),
            "default_token_budget_mode": provider_spec.get("provider", {}).get("default_token_budget_mode"),
            "target_counts": counts,
            "capability_rules": provider_spec.get("capability_rules") or [],
            "constraints": provider_spec.get("constraints") or [],
        }

    def _list_targets(
        self,
        provider_spec: dict[str, Any],
        adapters: list[dict[str, Any]],
        external_clis: list[dict[str, Any]],
        args: dict[str, Any],
    ) -> dict[str, Any]:
        query = str(args.get("query", "")).strip().lower()
        target_type = str(args.get("target_type", "")).strip().lower()
        limit = int(args.get("limit", 20) or 20)

        all_targets = adapters + external_clis
        filtered: list[dict[str, Any]] = []
        for item in all_targets:
            item_type = str(item.get("target_type", item.get("_source_type", ""))).lower()
            haystack = " ".join(
                [
                    str(item.get("name", "")),
                    str(item.get("display_name", "")),
                    str(item.get("description", "")),
                    " ".join(item.get("commands") or []),
                    item_type,
                ]
            ).lower()
            if query and query not in haystack:
                continue
            if target_type and target_type != item_type:
                continue
            filtered.append(item)

        filtered = filtered[:limit]
        return {
            "count": len(filtered),
            "results": [self._format_resolution(item, provider_spec) for item in filtered],
        }

    def _resolve_target(
        self,
        provider_spec: dict[str, Any],
        adapters: list[dict[str, Any]],
        external_clis: list[dict[str, Any]],
        args: dict[str, Any],
    ) -> dict[str, Any]:
        target_name = str(args.get("target_name", "")).strip().lower()
        target_type = str(args.get("target_type", "")).strip().lower()
        if not target_name:
            raise ValueError("target_name is required for resolve_target")

        for item in adapters + external_clis:
            item_name = str(item.get("name", "")).strip().lower()
            item_type = str(item.get("target_type", item.get("_source_type", ""))).lower()
            if item_name != target_name:
                continue
            if target_type and item_type != target_type:
                continue
            return self._format_resolution(item, provider_spec)

        raise ValueError(f"OpenCLI target not found: {target_name}")

    def _format_resolution(self, item: dict[str, Any], provider_spec: dict[str, Any]) -> dict[str, Any]:
        classification = self._classify_entry(item, provider_spec)
        target_type = str(item.get("target_type", item.get("_source_type", ""))).lower()
        entry_point = "opencli"
        installed = bool(shutil.which(entry_point))
        detect_cmd = entry_point
        if target_type == "external":
            detect_cmd = str(item.get("binary") or entry_point)
        return {
            "provider_name": provider_spec.get("provider", {}).get("name"),
            "target_name": item.get("name"),
            "display_name": item.get("display_name", item.get("name")),
            "target_type": target_type,
            "capability": classification["capability"],
            "preferred": classification["preferred"],
            "selection_reason": classification["reason"],
            "requires_browser_session": classification["requires_browser_session"],
            "entry_point": entry_point,
            "detect_cmd": detect_cmd,
            "installed": installed,
            "commands": item.get("commands") or [],
            "mode": item.get("mode"),
            "description": item.get("description"),
            "homepage": item.get("homepage"),
            "binary": item.get("binary"),
            "install_hint": self._extract_install_hint(item),
        }

    def _extract_install_hint(self, item: dict[str, Any]) -> str | None:
        install = item.get("install")
        if isinstance(install, dict):
            for key in ("default", "windows", "mac", "linux"):
                value = install.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return None

    def _classify_entry(self, item: dict[str, Any], provider_spec: dict[str, Any]) -> dict[str, Any]:
        name = str(item.get("name", "")).strip().lower()
        section = str(item.get("section", "")).strip()
        mode = str(item.get("mode", "")).strip()
        source_type = item.get("_source_type")

        for override in provider_spec.get("entry_overrides") or []:
            names = [str(v).strip().lower() for v in (override.get("names") or [])]
            if name in names:
                return {
                    "capability": override.get("capability"),
                    "preferred": bool(override.get("preferred", True)),
                    "requires_browser_session": True,
                    "reason": f"name override:{name}",
                }

        for rule in provider_spec.get("capability_rules") or []:
            if source_type == "external" and rule.get("source") == "external-clis":
                return {
                    "capability": rule.get("capability"),
                    "preferred": bool(rule.get("preferred", True)),
                    "requires_browser_session": bool(rule.get("requires_browser_session", False)),
                    "reason": "source rule:external-clis",
                }
            if section and rule.get("section") == section:
                mode_contains = rule.get("mode_contains") or []
                if mode_contains and not any(token in mode for token in mode_contains):
                    continue
                return {
                    "capability": rule.get("capability"),
                    "preferred": bool(rule.get("preferred", True)),
                    "requires_browser_session": bool(rule.get("requires_browser_session", False)),
                    "reason": f"section rule:{section}",
                }

        return {
            "capability": "unmapped",
            "preferred": False,
            "requires_browser_session": False,
            "reason": "unmapped",
        }

    def get_full_documentation(self, tool_format: str = "native") -> str:
        return (
            "# opencli_registry\n\n"
            "Inspect and resolve OpenCLI adapters, desktop apps, and external CLIs using the private provider mapping.\n\n"
            "## Actions\n"
            "- `provider_summary`: show provider rules and target counts\n"
            "- `list_targets`: search the OpenCLI targets\n"
            "- `resolve_target`: resolve a single target to private capability metadata\n"
        )
