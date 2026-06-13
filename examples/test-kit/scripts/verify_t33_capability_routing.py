from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_provider_selection(repo_root: Path):
    module_path = (
        repo_root / "examples" / "test-kit" / "test_kit" / "provider_selection.py"
    )
    spec = importlib.util.spec_from_file_location(
        "test_kit.provider_selection", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to load provider_selection module from {module_path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify T33 unified capability routing."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root containing examples/test-kit/.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    module = load_provider_selection(repo_root)
    select_provider_for_task = module.select_provider_for_task

    docs_case = select_provider_for_task(
        {
            "task_kind": "docs_task",
            "preferred_provider": "none",
        },
        repo_root,
    )
    code_case = select_provider_for_task(
        {
            "task_kind": "codebase_edit_task",
        },
        repo_root,
    )
    mcp_case = select_provider_for_task(
        {
            "task_kind": "mcp_tool_task",
            "mcp_server_hint": "sqlite",
        },
        repo_root,
    )
    service_case = select_provider_for_task(
        {
            "task_kind": "service_cli_task",
            "artifact_expectation": ["tmp/service.json"],
        },
        repo_root,
    )
    browser_case = select_provider_for_task(
        {
            "task_kind": "browser_authenticated_task",
            "needs_browser_session": True,
        },
        repo_root,
    )
    overlap_case = select_provider_for_task(
        {
            "task_kind": "browser_public_task",
            "target_hint": "website",
        },
        repo_root,
    )

    check(
        docs_case["execution_surface"] == "built-in_tools",
        "docs should route to built-in tools",
    )
    check(
        docs_case["preferred_provider"] == "none",
        "docs should not require external provider",
    )
    check(
        "read" in docs_case["recommended_tools"],
        "docs route should recommend built-in read",
    )
    check(
        code_case["capability_route"] == "codebase_edit_task",
        "code route should preserve task kind",
    )
    check("edit" in code_case["recommended_tools"], "code route should allow edit")

    check(mcp_case["execution_surface"] == "mcp", "mcp task should route to MCP")
    check(
        mcp_case["preferred_provider"] == "none",
        "mcp should not require external provider",
    )
    check(
        mcp_case["capability_route"] == "sqlite",
        "mcp route should preserve server hint",
    )
    check(
        mcp_case["recommended_tools"] == ["mcp_list", "mcp_call"],
        "mcp route should use MCP meta-tools",
    )

    check(
        service_case["execution_surface"] == "external_cli",
        "service task should route externally",
    )
    check(
        service_case["preferred_provider"] == "cli-anything",
        "service task should prefer CLI-Anything",
    )
    check(
        service_case["capability_route"] == "service_cli_task",
        "service route should preserve capability",
    )

    check(
        browser_case["execution_surface"] == "external_cli",
        "browser auth should route externally",
    )
    check(
        browser_case["preferred_provider"] == "opencli",
        "browser auth should prefer OpenCLI",
    )
    check(
        browser_case["capability_route"] == "browser_authenticated_task",
        "browser auth route should preserve capability",
    )

    check(
        overlap_case["decision_status"] == "needs_user_choice",
        "public browser overlap should not guess",
    )
    check(
        overlap_case["execution_surface"] == "external_cli",
        "overlap still belongs to external CLI surface",
    )
    check(
        overlap_case["candidate_providers"] == ["cli-anything", "opencli"],
        "overlap should offer both external providers",
    )

    report = {
        "status": "PASS",
        "docs_case": {
            "execution_surface": docs_case["execution_surface"],
            "preferred_provider": docs_case["preferred_provider"],
            "recommended_tools": docs_case["recommended_tools"],
        },
        "mcp_case": {
            "execution_surface": mcp_case["execution_surface"],
            "capability_route": mcp_case["capability_route"],
            "recommended_tools": mcp_case["recommended_tools"],
        },
        "service_case": {
            "execution_surface": service_case["execution_surface"],
            "preferred_provider": service_case["preferred_provider"],
        },
        "browser_case": {
            "execution_surface": browser_case["execution_surface"],
            "preferred_provider": browser_case["preferred_provider"],
        },
        "overlap_case": {
            "decision_status": overlap_case["decision_status"],
            "candidate_providers": overlap_case["candidate_providers"],
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
