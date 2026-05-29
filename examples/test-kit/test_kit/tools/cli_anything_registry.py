from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml

from kohakuterrarium.modules.tool.base import BaseTool, ExecutionMode, ToolResult


class CliAnythingRegistryTool(BaseTool):
    needs_context = True
    is_concurrency_safe = True

    @property
    def tool_name(self) -> str:
        return "cli_anything_registry"

    @property
    def description(self) -> str:
        return "Inspect and resolve CLI-Anything registry entries through the private provider mapping."

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["provider_summary", "search_registry", "resolve_cli"],
                    "description": "Operation to perform.",
                },
                "cli_name": {
                    "type": "string",
                    "description": "CLI name for resolve_cli.",
                },
                "query": {
                    "type": "string",
                    "description": "Keyword used by search_registry.",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter for search_registry.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "minimum": 1,
                    "maximum": 50,
                },
                "include_public": {
                    "type": "boolean",
                    "description": "Whether to include public_registry.json entries.",
                },
                "registry_path": {
                    "type": "string",
                    "description": "Optional override path for the official CLI-Anything registry.",
                },
                "public_registry_path": {
                    "type": "string",
                    "description": "Optional override path for the public CLI-Anything registry.",
                },
                "provider_spec_path": {
                    "type": "string",
                    "description": "Optional override path for providers/cli_anything.yaml.",
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
            repo_root / "examples" / "test-kit" / "providers" / "cli_anything.yaml",
        )
        official_registry_path = self._resolve_path(
            args.get("registry_path"),
            repo_root / "CLI-Anything" / "registry.json",
        )
        public_registry_path = self._resolve_path(
            args.get("public_registry_path"),
            repo_root / "CLI-Anything" / "public_registry.json",
        )
        include_public = bool(args.get("include_public", False))
        action = str(args.get("action", "")).strip()

        if not provider_spec_path.exists():
            return ToolResult(
                error=f"Provider spec not found: {provider_spec_path}",
                exit_code=1,
            )
        if not official_registry_path.exists():
            return ToolResult(
                error=f"CLI-Anything registry not found: {official_registry_path}",
                exit_code=1,
            )

        provider_spec = self._load_yaml(provider_spec_path)
        official_entries = self._load_registry_entries(official_registry_path, "official")
        public_entries: list[dict[str, Any]] = []
        if include_public and public_registry_path.exists():
            public_entries = self._load_registry_entries(public_registry_path, "public")

        entries = official_entries + public_entries

        match action:
            case "provider_summary":
                payload = self._provider_summary(
                    provider_spec,
                    official_entries,
                    public_entries,
                )
            case "search_registry":
                payload = self._search_registry(entries, provider_spec, args)
            case "resolve_cli":
                payload = self._resolve_cli(entries, provider_spec, args)
            case _:
                return ToolResult(error=f"Unsupported action: {action}", exit_code=1)

        return ToolResult(
            output=json.dumps(payload, indent=2, ensure_ascii=False),
            exit_code=0,
            metadata={"provider": "cli-anything"},
        )

    def _find_repo_root(self, start_dir: Path) -> Path:
        candidates = [start_dir.resolve(), *start_dir.resolve().parents]
        for candidate in candidates:
            if (candidate / "CLI-Anything" / "registry.json").exists():
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

    def _load_registry_entries(self, path: Path, source: str) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        clis = payload.get("clis") or []
        entries: list[dict[str, Any]] = []
        for item in clis:
            if isinstance(item, dict):
                enriched = dict(item)
                enriched["_registry_source"] = source
                entries.append(enriched)
        return entries

    def _provider_summary(
        self,
        provider_spec: dict[str, Any],
        official_entries: list[dict[str, Any]],
        public_entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        rules = provider_spec.get("capability_rules") or []
        overrides = provider_spec.get("entry_overrides") or []
        return {
            "provider_name": provider_spec.get("provider", {}).get("name"),
            "install_manager": provider_spec.get("provider", {}).get("install_manager"),
            "default_token_budget_mode": provider_spec.get("provider", {}).get(
                "default_token_budget_mode"
            ),
            "official_registry_count": len(official_entries),
            "public_registry_count": len(public_entries),
            "capability_rules": [
                {
                    "capability": rule.get("capability"),
                    "preferred": rule.get("preferred", True),
                    "categories": rule.get("categories") or [],
                }
                for rule in rules
            ],
            "entry_overrides": [
                {
                    "names": override.get("names") or [],
                    "capability": override.get("capability"),
                    "preferred": override.get("preferred", True),
                }
                for override in overrides
            ],
        }

    def _search_registry(
        self,
        entries: list[dict[str, Any]],
        provider_spec: dict[str, Any],
        args: dict[str, Any],
    ) -> dict[str, Any]:
        query = str(args.get("query", "")).strip().lower()
        category = str(args.get("category", "")).strip().lower()
        limit = int(args.get("limit", 10) or 10)

        filtered: list[dict[str, Any]] = []
        for entry in entries:
            entry_category = str(entry.get("category", "")).lower()
            haystack = " ".join(
                [
                    str(entry.get("name", "")),
                    str(entry.get("display_name", "")),
                    str(entry.get("description", "")),
                    entry_category,
                ]
            ).lower()
            if query and query not in haystack:
                continue
            if category and category != entry_category:
                continue
            filtered.append(entry)

        filtered = filtered[:limit]
        return {
            "count": len(filtered),
            "results": [
                self._format_resolution(entry, provider_spec) for entry in filtered
            ],
        }

    def _resolve_cli(
        self,
        entries: list[dict[str, Any]],
        provider_spec: dict[str, Any],
        args: dict[str, Any],
    ) -> dict[str, Any]:
        cli_name = str(args.get("cli_name", "")).strip().lower()
        if not cli_name:
            raise ValueError("cli_name is required for resolve_cli")

        for entry in entries:
            if str(entry.get("name", "")).strip().lower() == cli_name:
                return self._format_resolution(entry, provider_spec)

        raise ValueError(f"CLI not found in registry: {cli_name}")

    def _format_resolution(
        self,
        entry: dict[str, Any],
        provider_spec: dict[str, Any],
    ) -> dict[str, Any]:
        capability_info = self._classify_entry(entry, provider_spec)
        entry_point = entry.get("entry_point")
        detect_cmd = entry.get("detect_cmd") or entry_point
        return {
            "provider_name": provider_spec.get("provider", {}).get("name"),
            "cli_name": entry.get("name"),
            "display_name": entry.get("display_name"),
            "capability": capability_info["capability"],
            "preferred": capability_info["preferred"],
            "selection_reason": capability_info["reason"],
            "category": entry.get("category"),
            "install_cmd": entry.get("install_cmd"),
            "entry_point": entry_point,
            "detect_cmd": detect_cmd,
            "installed": bool(detect_cmd and shutil.which(str(detect_cmd))),
            "skill_md": entry.get("skill_md"),
            "registry_source": entry.get("_registry_source"),
            "requires": entry.get("requires"),
        }

    def _classify_entry(
        self,
        entry: dict[str, Any],
        provider_spec: dict[str, Any],
    ) -> dict[str, Any]:
        name = str(entry.get("name", "")).strip().lower()
        category = str(entry.get("category", "")).strip().lower()

        for override in provider_spec.get("entry_overrides") or []:
            names = [str(item).strip().lower() for item in (override.get("names") or [])]
            if name in names:
                return {
                    "capability": override.get("capability"),
                    "preferred": bool(override.get("preferred", True)),
                    "reason": f"name override:{name}",
                }

        for rule in provider_spec.get("capability_rules") or []:
            categories = [
                str(item).strip().lower() for item in (rule.get("categories") or [])
            ]
            if category in categories:
                return {
                    "capability": rule.get("capability"),
                    "preferred": bool(rule.get("preferred", True)),
                    "reason": f"category rule:{category}",
                }

        return {
            "capability": "unmapped",
            "preferred": False,
            "reason": f"unmapped category:{category or 'unknown'}",
        }

    def get_full_documentation(self, tool_format: str = "native") -> str:
        return (
            "# cli_anything_registry\n\n"
            "Inspect and resolve CLI-Anything registry entries using the private provider mapping.\n\n"
            "## Actions\n"
            "- `provider_summary`: show provider rules and registry counts\n"
            "- `search_registry`: search the registry and return mapped results\n"
            "- `resolve_cli`: resolve a single CLI to private capability metadata\n"
        )
