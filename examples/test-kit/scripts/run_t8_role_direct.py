from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ROLE_PROMPTS = {
    "coordinator": [
        PROJECT_ROOT / "examples" / "test-kit" / "creatures" / "coordinator" / "prompts" / "system.md",
        PROJECT_ROOT / "examples" / "test-kit" / "terrariums" / "task-team-minimal" / "prompts" / "coordinator.md",
    ],
    "critic": [
        PROJECT_ROOT / "examples" / "test-kit" / "creatures" / "critic" / "prompts" / "system.md",
        PROJECT_ROOT / "examples" / "test-kit" / "terrariums" / "task-team-minimal" / "prompts" / "critic.md",
    ],
    "root": [
        PROJECT_ROOT / "examples" / "test-kit" / "creatures" / "root-privileged" / "prompts" / "system.md",
        PROJECT_ROOT / "examples" / "test-kit" / "terrariums" / "task-team-minimal" / "prompts" / "root.md",
    ],
}


def _load_call_role_llm():
    try:
        from test_kit.role_llm import call_role_llm  # type: ignore

        return call_role_llm
    except Exception:
        module_path = PROJECT_ROOT / "examples" / "test-kit" / "test_kit" / "role_llm.py"
        module_name = "test_kit.role_llm"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load role_llm helper from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module.call_role_llm


CALL_ROLE_LLM = _load_call_role_llm()


def _load_prompt(role: str) -> str:
    prompt = "\n\n".join(path.read_text(encoding="utf-8") for path in ROLE_PROMPTS[role])
    if role == "root":
        prompt += (
            "\n\nDirect harness override:\n"
            "- Do not call, simulate, or mention group_status, group_send, or tool traces.\n"
            "- Do not output tool logs.\n"
            "- Only produce a concise user-facing final answer."
        )
    return prompt


def main() -> None:
    role = (os.environ.get("T8_ROLE", "coordinator").strip() or "coordinator").lower()
    output_path = os.environ.get("T8_OUTPUT_PATH", "").strip()
    user_input_path = os.environ.get("T8_USER_INPUT_PATH", "").strip()
    user_input = os.environ.get("T8_USER_INPUT", "")
    max_tokens = int(os.environ.get("T8_MAX_TOKENS", "900") or "900")

    if role not in ROLE_PROMPTS:
        raise ValueError(f"unsupported role: {role}")
    if user_input_path:
        user_input = Path(user_input_path).read_text(encoding="utf-8")
    if not user_input.strip():
        raise ValueError("T8_USER_INPUT or T8_USER_INPUT_PATH is required")

    text = CALL_ROLE_LLM(_load_prompt(role), user_input, max_tokens=max_tokens)
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
