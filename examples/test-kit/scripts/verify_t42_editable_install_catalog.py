#!/usr/bin/env python
"""T42 editable install and catalog visibility smoke.

This verifier exercises the real application path after ``kt install -e``:
package storage must honor ``KT_CONFIG_DIR``, package refs must resolve, and
Studio catalog scanners must surface name-only manifest creature/terrarium
entries.
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
    repo_root: Path, kt_home: Path, args: list[str]
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["KT_CONFIG_DIR"] = str(kt_home)
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
    with tempfile.TemporaryDirectory(prefix="t42-editable-install-") as tmp:
        kt_home = Path(tmp) / "kt-home"

        install = _run_python(
            repo_root,
            kt_home,
            [
                "-m",
                "kohakuterrarium",
                "install",
                str(PACKAGE_ROOT),
                "-e",
                "--name",
                "test-kit",
            ],
        )
        _assert_success("kt install -e test-kit", install)
        if "Installed: test-kit (editable)" not in install.stdout:
            raise AssertionError("editable install did not report test-kit")

        link_file = kt_home / "packages" / "test-kit.link"
        if not link_file.exists():
            raise AssertionError("editable install did not write under KT_CONFIG_DIR")

        listing = _run_python(repo_root, kt_home, ["-m", "kohakuterrarium", "list"])
        _assert_success("kt list", listing)
        if "test-kit v0.1.0 (editable)" not in listing.stdout:
            raise AssertionError("kt list did not show editable test-kit")

        info = _run_python(
            repo_root,
            kt_home,
            [
                "-m",
                "kohakuterrarium",
                "info",
                "@test-kit/creatures/worker-base",
            ],
        )
        _assert_success("kt info @test-kit/creatures/worker-base", info)
        if "Agent: worker-base" not in info.stdout:
            raise AssertionError("kt info did not resolve package creature ref")

        catalog_code = (
            "from kohakuterrarium.studio.catalog.packages_scan import "
            "scan_creatures_in_dirs, scan_terrariums_in_dirs; "
            "print(','.join(sorted(x['name'] for x in scan_creatures_in_dirs([])))); "
            "print(','.join(sorted(x['name'] for x in scan_terrariums_in_dirs([]))))"
        )
        catalog = _run_python(repo_root, kt_home, ["-c", catalog_code])
        _assert_success("catalog scan", catalog)
        if "worker-base" not in catalog.stdout:
            raise AssertionError("catalog did not show worker-base")
        if "task-team-minimal" not in catalog.stdout:
            raise AssertionError("catalog did not show task-team-minimal")

    return {
        "status": "PASS",
        "checks": {
            "editable_install": True,
            "kt_config_dir_packages": True,
            "package_ref_info": True,
            "catalog_creatures": True,
            "catalog_terrariums": True,
        },
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
