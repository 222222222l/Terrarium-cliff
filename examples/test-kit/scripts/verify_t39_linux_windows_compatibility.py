from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_name} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify T39 Linux/Windows compatibility gates."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root containing examples/test-kit/.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    test_kit_root = repo_root / "examples" / "test-kit"
    script_root = test_kit_root / "scripts"

    cli_runtime = load_module(
        test_kit_root / "test_kit" / "cli_runtime.py",
        "test_kit.cli_runtime_t39",
    )
    role_llm = load_module(
        test_kit_root / "test_kit" / "role_llm.py",
        "test_kit.role_llm_t39",
    )

    original_cli_os_name = cli_runtime.os.name
    original_role_os_name = role_llm.os.name
    try:
        cli_runtime.os.name = "nt"
        role_llm.os.name = "nt"
        windows_cli_command = cli_runtime._normalize_command(
            {"url": "https://example.test"}
        )
        windows_role_command = role_llm._build_curl_command(
            "https://example.test/v1/chat/completions",
            "redacted-key",
            "C:\\temp\\payload.json",
        )

        cli_runtime.os.name = "posix"
        role_llm.os.name = "posix"
        posix_cli_command = cli_runtime._normalize_command(
            {"url": "https://example.test"}
        )
        posix_command_text = cli_runtime._normalize_command(
            {"command_text": "curl.exe https://example.test"}
        )
        posix_role_command = role_llm._build_curl_command(
            "https://example.test/v1/chat/completions",
            "redacted-key",
            "/tmp/payload.json",
        )
    finally:
        cli_runtime.os.name = original_cli_os_name
        role_llm.os.name = original_role_os_name

    check(windows_cli_command[0] == "curl.exe", "Windows url fetch should use curl.exe")
    check(
        windows_role_command[0] == "curl.exe",
        "Windows role fallback should use curl.exe",
    )
    check(
        "--ssl-no-revoke" in windows_role_command,
        "Windows role fallback should include --ssl-no-revoke",
    )
    check(posix_cli_command[0] == "curl", "POSIX url fetch should use curl")
    check(
        posix_command_text[0] == "curl",
        "POSIX command_text should normalize curl.exe to curl",
    )
    check(posix_role_command[0] == "curl", "POSIX role fallback should use curl")
    check(
        "--ssl-no-revoke" not in posix_role_command,
        "POSIX role fallback should not include Windows curl flags",
    )

    worker_prompt = (
        test_kit_root / "terrariums" / "task-team-minimal" / "prompts" / "worker.md"
    ).read_text(encoding="utf-8")
    check(
        "platform curl binary" in worker_prompt,
        "worker prompt should be platform-aware",
    )
    check("Linux/macOS" in worker_prompt, "worker prompt should mention POSIX curl")

    t38_doc = (
        repo_root / "docs" / "zh-CN" / "dev" / "t38-phase-usability-validation.md"
    ).read_text(encoding="utf-8")
    check("```powershell" in t38_doc, "T38 doc should keep PowerShell example")
    check("```bash" in t38_doc, "T38 doc should add Bash example")

    shortest_demo = (script_root / "run_t8_worker_shortest_demo.py").read_text(
        encoding="utf-8"
    )
    check(
        '["curl"]' in shortest_demo and '["curl.exe"]' in shortest_demo,
        "worker shortest demo should accept both curl binaries",
    )

    docs_path = (
        repo_root / "docs" / "zh-CN" / "dev" / "t39-linux-windows-compatibility.md"
    )
    check(docs_path.is_file(), "T39 compatibility doc is missing")

    report = {
        "status": "PASS",
        "cli_runtime": {
            "windows_url_command": windows_cli_command,
            "posix_url_command": posix_cli_command,
            "posix_command_text": posix_command_text,
        },
        "role_llm": {
            "windows_binary": windows_role_command[0],
            "windows_ssl_no_revoke": "--ssl-no-revoke" in windows_role_command,
            "posix_binary": posix_role_command[0],
        },
        "docs": {
            "t38_has_powershell": True,
            "t38_has_bash": True,
            "t39_doc": str(docs_path.relative_to(repo_root)),
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
