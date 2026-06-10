from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class VerifyScript:
    task_id: str
    path: Path
    args: tuple[str, ...] = ()
    external_paths: tuple[Path, ...] = ()

    @property
    def is_external(self) -> bool:
        return bool(self.external_paths)


DEFAULT_SCRIPTS: tuple[VerifyScript, ...] = (
    VerifyScript("T4", SCRIPT_ROOT / "verify_t4_root_privileged.py"),
    VerifyScript("T5", SCRIPT_ROOT / "verify_t5_coordinator.py"),
    VerifyScript("T6", SCRIPT_ROOT / "verify_t6_worker_base.py"),
    VerifyScript("T7", SCRIPT_ROOT / "verify_t7_critic.py"),
    VerifyScript("T8", SCRIPT_ROOT / "verify_t8_task_team_minimal.py"),
    VerifyScript("T9-T10", SCRIPT_ROOT / "verify_t9_t10_protocol_skills.py"),
    VerifyScript(
        "T23",
        SCRIPT_ROOT / "verify_t23_silent_execution.py",
        ("--repo-root", str(PROJECT_ROOT)),
    ),
    VerifyScript(
        "T24",
        SCRIPT_ROOT / "verify_t24_provider_selection.py",
        ("--repo-root", str(PROJECT_ROOT)),
    ),
    VerifyScript(
        "T25",
        SCRIPT_ROOT / "verify_t25_feedback_protocol.py",
        ("--repo-root", str(PROJECT_ROOT)),
    ),
    VerifyScript("T30-T32", SCRIPT_ROOT / "verify_t30_t32_skill_packaging.py"),
)

EXTERNAL_SCRIPTS: tuple[VerifyScript, ...] = (
    VerifyScript(
        "T21",
        SCRIPT_ROOT / "verify_t21_cli_anything.py",
        ("--repo-root", str(PROJECT_ROOT)),
        (PROJECT_ROOT / "CLI-Anything" / "registry.json",),
    ),
    VerifyScript(
        "T22",
        SCRIPT_ROOT / "verify_t22_opencli.py",
        ("--repo-root", str(PROJECT_ROOT)),
        (
            PROJECT_ROOT / "OpenCLI" / "docs" / "adapters" / "index.md",
            PROJECT_ROOT / "OpenCLI" / "src" / "external-clis.yaml",
        ),
    ),
)


def _script_command(script: VerifyScript) -> list[str]:
    return [sys.executable, str(script.path), *script.args]


def _missing_external_paths(script: VerifyScript) -> list[str]:
    return [str(path) for path in script.external_paths if not path.exists()]


def _run_script(script: VerifyScript) -> dict:
    start = time.perf_counter()
    missing = _missing_external_paths(script)
    if missing:
        return {
            "task_id": script.task_id,
            "status": "SKIP",
            "script": str(script.path.relative_to(PROJECT_ROOT)),
            "duration_ms": 0,
            "reason": "missing external fixture",
            "missing": missing,
        }

    with tempfile.TemporaryDirectory(
        prefix=f"test-kit-{script.task_id.lower()}-"
    ) as config_dir:
        env = os.environ.copy()
        python_paths = [
            str(PROJECT_ROOT / "src"),
            str(PROJECT_ROOT / "examples" / "test-kit"),
        ]
        if env.get("PYTHONPATH"):
            python_paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(python_paths)
        env["KT_CONFIG_DIR"] = config_dir
        env["PYTHONIOENCODING"] = "utf-8"

        completed = subprocess.run(
            _script_command(script),
            cwd=PROJECT_ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    duration_ms = int((time.perf_counter() - start) * 1000)
    return {
        "task_id": script.task_id,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "script": str(script.path.relative_to(PROJECT_ROOT)),
        "duration_ms": duration_ms,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _selected_scripts(
    include_external: bool, only: set[str] | None
) -> list[VerifyScript]:
    scripts = list(DEFAULT_SCRIPTS)
    if include_external:
        scripts.extend(EXTERNAL_SCRIPTS)
    if only:
        scripts = [script for script in scripts if script.task_id in only]
    return scripts


def _build_summary(results: list[dict]) -> dict:
    failed = [item for item in results if item["status"] == "FAIL"]
    skipped = [item for item in results if item["status"] == "SKIP"]
    return {
        "status": "PASS" if not failed else "FAIL",
        "total": len(results),
        "passed": sum(1 for item in results if item["status"] == "PASS"),
        "failed": len(failed),
        "skipped": len(skipped),
        "results": results,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Run the stable test-kit verification suite."
    )
    parser.add_argument(
        "--include-external",
        action="store_true",
        help="Also run verifiers that require sibling CLI-Anything/OpenCLI checkout fixtures.",
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=[script.task_id for script in DEFAULT_SCRIPTS + EXTERNAL_SCRIPTS],
        help="Run only the selected task id. Can be passed multiple times.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List selected verifiers without running them.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON summary only.")
    args = parser.parse_args()

    scripts = _selected_scripts(args.include_external, set(args.only or []) or None)
    if args.list:
        for script in scripts:
            marker = "external" if script.is_external else "default"
            print(
                f"{script.task_id}\t{marker}\t{script.path.relative_to(PROJECT_ROOT)}"
            )
        return 0

    results = [_run_script(script) for script in scripts]
    summary = _build_summary(results)
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"status: {summary['status']}")
        print(
            f"total: {summary['total']} passed: {summary['passed']} "
            f"failed: {summary['failed']} skipped: {summary['skipped']}"
        )
        for item in results:
            print(f"- {item['task_id']}: {item['status']} ({item['duration_ms']} ms)")
            if item["status"] == "FAIL":
                if item.get("stdout"):
                    print(item["stdout"])
                if item.get("stderr"):
                    print(item["stderr"])
            elif item["status"] == "SKIP":
                print(f"  reason: {item['reason']}")

    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
