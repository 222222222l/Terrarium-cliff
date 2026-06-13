#!/usr/bin/env python
"""T41 application-layer startup smoke under sandboxed config writes.

This verifier intentionally runs the real ``kohakuterrarium`` CLI/module in a
subprocess while pointing ``KT_CONFIG_DIR`` at a regular file.  That simulates
managed sandboxes where the default user config home cannot be created.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_ROOT.parent
DEFAULT_REPO_ROOT = PACKAGE_ROOT.parent.parent


def _run_python(
    repo_root: Path, blocked_config: Path, args: list[str]
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["KT_CONFIG_DIR"] = str(blocked_config)
    env["PYTHONPATH"] = str(repo_root / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, *args],
        cwd=repo_root,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
        check=False,
    )


def _assert_success(label: str, result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode != 0:
        raise AssertionError(
            f"{label} failed with exit code {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def verify(repo_root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="t41-app-startup-") as tmp:
        blocked_config = Path(tmp) / "blocked-config"
        blocked_config.write_text("not a directory", encoding="utf-8")

        version = _run_python(
            repo_root, blocked_config, ["-m", "kohakuterrarium", "--version"]
        )
        _assert_success("kt --version", version)
        if "version:" not in version.stdout:
            raise AssertionError("kt --version did not print runtime version info")

        help_result = _run_python(
            repo_root, blocked_config, ["-m", "kohakuterrarium", "--help"]
        )
        _assert_success("kt --help", help_result)
        if "usage: kt" not in help_result.stdout:
            raise AssertionError("kt --help did not print CLI usage")

        worker_info = _run_python(
            repo_root,
            blocked_config,
            [
                "-m",
                "kohakuterrarium",
                "info",
                str(PACKAGE_ROOT / "creatures" / "worker-base"),
            ],
        )
        _assert_success("kt info worker-base", worker_info)
        if "Agent: worker-base" not in worker_info.stdout:
            raise AssertionError("kt info did not load worker-base")

        terrarium = _run_python(
            repo_root,
            blocked_config,
            [
                "-c",
                (
                    "from kohakuterrarium.terrarium.config import "
                    "load_terrarium_config; "
                    "cfg = load_terrarium_config("
                    f"{str(PACKAGE_ROOT / 'terrariums' / 'task-team-minimal')!r}"
                    "); "
                    "print(cfg.name); "
                    "print(','.join(c.name for c in cfg.creatures))"
                ),
            ],
        )
        _assert_success("load task-team-minimal", terrarium)
        if "task-team-minimal" not in terrarium.stdout:
            raise AssertionError("terrarium loader did not load task-team-minimal")

    return {
        "status": "PASS",
        "checks": {
            "version": True,
            "help": True,
            "worker_info": True,
            "terrarium_loader": True,
        },
        "sandbox_case": "KT_CONFIG_DIR points to a regular file",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Repository root. Defaults to this script's repository.",
    )
    args = parser.parse_args()

    try:
        result = verify(args.repo_root.resolve())
    except AssertionError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
