from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUITE_SCRIPT = (
    PROJECT_ROOT / "examples" / "test-kit" / "scripts" / "verify_regression_suite.py"
)


def test_verify_regression_suite_lists_default_tasks():
    completed = subprocess.run(
        [sys.executable, str(SUITE_SCRIPT), "--list"],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )

    listed = [line.split("\t", 1)[0] for line in completed.stdout.splitlines()]

    assert listed == [
        "T4",
        "T5",
        "T6",
        "T7",
        "T8",
        "T9-T10",
        "T23",
        "T24",
        "T25",
        "T30-T32",
    ]


def test_verify_regression_suite_default_run_passes():
    completed = subprocess.run(
        [sys.executable, str(SUITE_SCRIPT), "--json"],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    summary = json.loads(completed.stdout)

    assert summary["status"] == "PASS"
    assert summary["failed"] == 0
    assert summary["skipped"] == 0
    assert summary["passed"] == 10
