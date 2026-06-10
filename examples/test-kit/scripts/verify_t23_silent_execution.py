from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def load_cli_runtime(repo_root: Path):
    module_path = repo_root / "examples" / "test-kit" / "test_kit" / "cli_runtime.py"
    spec = importlib.util.spec_from_file_location("test_kit.cli_runtime", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load cli_runtime module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_success_case(repo_root: Path, execute_cli_invocation) -> dict:
    artifact_rel = "tmp/t23-success.txt"
    artifact_path = repo_root / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    if artifact_path.exists():
        artifact_path.unlink()

    code = (
        "from pathlib import Path; "
        f'path = Path(r"{artifact_path}"); '
        'path.write_text("done\\n", encoding="utf-8"); '
        'print("silent success")'
    )
    return execute_cli_invocation(
        {
            "provider_name": "cli-anything",
            "capability": "service_cli_task",
            "task_id": "t23-success",
            "command": [sys.executable, "-c", code],
            "artifact_expectation": [artifact_rel],
            "token_budget_mode": "silent",
        },
        repo_root,
    )


def run_process_error_case(repo_root: Path, execute_cli_invocation) -> dict:
    code = 'import sys; sys.stderr.write("boom\\n"); raise SystemExit(3)'
    return execute_cli_invocation(
        {
            "provider_name": "opencli",
            "capability": "browser_authenticated_task",
            "task_id": "t23-process-error",
            "command": [sys.executable, "-c", code],
            "token_budget_mode": "silent",
        },
        repo_root,
    )


def run_missing_artifact_case(repo_root: Path, execute_cli_invocation) -> dict:
    artifact_rel = "tmp/t23-missing.txt"
    artifact_path = repo_root / artifact_rel
    if artifact_path.exists():
        artifact_path.unlink()

    code = 'print("artifact missing case")'
    return execute_cli_invocation(
        {
            "provider_name": "cli-anything",
            "capability": "local_software_task",
            "task_id": "t23-artifact-missing",
            "command": [sys.executable, "-c", code],
            "artifact_expectation": [artifact_rel],
            "token_budget_mode": "silent",
        },
        repo_root,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify T23 silent execution protocol.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root containing examples/test-kit/.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    cli_runtime = load_cli_runtime(repo_root)
    execute_cli_invocation = cli_runtime.execute_cli_invocation
    success_record = run_success_case(repo_root, execute_cli_invocation)
    error_record = run_process_error_case(repo_root, execute_cli_invocation)
    missing_record = run_missing_artifact_case(repo_root, execute_cli_invocation)

    check(success_record["success"] is True, "success case should succeed")
    check(success_record["exit_code"] == 0, "success case exit code should be 0")
    check(success_record["artifact_paths"], "success case should record artifact path")
    check(success_record["stdout_summary"] == "silent success", "success summary should be compact")
    check(success_record["diagnostic_excerpt"] == "", "success case should not upgrade to diagnostics")

    check(error_record["success"] is False, "process error case should fail")
    check(error_record["error_kind"] == "process_error", "process error should be classified")
    check(error_record["retryable"] is True, "process error should be retryable")
    check("boom" in error_record["diagnostic_excerpt"], "process error should expose minimal diagnostic")

    check(missing_record["success"] is False, "missing artifact case should fail")
    check(missing_record["error_kind"] == "artifact_missing", "missing artifact should be classified")
    check(missing_record["retryable"] is False, "missing artifact should not be retryable by default")
    check("missing artifacts:" in missing_record["diagnostic_excerpt"], "missing artifact should expose artifact hint")

    for record in (success_record, error_record, missing_record):
        for key in ("raw_log_path", "stdout_path", "stderr_path", "result_path"):
            check(Path(record[key]).exists(), f"{key} should exist for {record['provider_name']}")

    report = {
        "status": "PASS",
        "success_case": {
            "success": success_record["success"],
            "stdout_summary": success_record["stdout_summary"],
            "artifact_count": len(success_record["artifact_paths"]),
        },
        "process_error_case": {
            "success": error_record["success"],
            "error_kind": error_record["error_kind"],
            "diagnostic_excerpt": error_record["diagnostic_excerpt"],
        },
        "artifact_missing_case": {
            "success": missing_record["success"],
            "error_kind": missing_record["error_kind"],
            "diagnostic_excerpt": missing_record["diagnostic_excerpt"],
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
