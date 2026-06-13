from argparse import Namespace
import importlib
from pathlib import Path

cli_mod = importlib.import_module("kohakuterrarium.cli")


def test_info_dispatch_resolves_package_ref(monkeypatch):
    calls: list[str] = []
    resolved = Path("resolved") / "creatures" / "worker-base"

    monkeypatch.setattr(cli_mod, "resolve_package_path", lambda ref: resolved)
    monkeypatch.setattr(
        cli_mod, "show_agent_info_cli", lambda path: calls.append(path) or 0
    )

    rc = cli_mod.COMMANDS["info"](
        Namespace(agent_path="@test-kit/creatures/worker-base")
    )

    assert rc == 0
    assert calls == [str(resolved)]


def test_info_dispatch_keeps_plain_path(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        cli_mod, "show_agent_info_cli", lambda path: calls.append(path) or 0
    )

    rc = cli_mod.COMMANDS["info"](Namespace(agent_path="./creatures/worker-base"))

    assert rc == 0
    assert calls == ["./creatures/worker-base"]
