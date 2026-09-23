#!/usr/bin/env python3
"""The `--self-test` body of `kit-probe.py`: one line per rule the hook holds.

Each case writes a real kit into a throwaway directory -- a real manifest, real
hook files beside it -- and reads back what the probe would say about it. The
bug this shape catches is a probe that reads a path the manifest does not spell
the way the test spells it, and no assertion over an invented list can see that.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

PROBE_PATH = Path(__file__).resolve().parent / "kit-probe.py"

MANIFEST = ".claude-plugin/plugin.json"


def _load_probe() -> ModuleType:
    """Import the probe by path, since its name is hyphenated."""
    if str(PROBE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(PROBE_PATH.parent))
    spec = importlib.util.spec_from_file_location("kit_probe_under_test", PROBE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {PROBE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROBE = _load_probe()


def _manifest(paths: list[str], servers: dict[str, Any] | None = None) -> str:
    """Render a manifest wiring one command per path under one event, and `servers`."""
    entries: list[dict[str, Any]] = [
        {"type": "command", "command": f'python3 "${{CLAUDE_PLUGIN_ROOT}}"/{path}'}
        for path in paths
    ]
    data: dict[str, Any] = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": entries}]}}
    if servers is not None:
        data["mcpServers"] = servers
    return json.dumps(data, indent=2)


def _server(path: str) -> dict[str, Any]:
    """One stdio server entry running a script under the plugin root."""
    return {"command": "python3", "args": [f"${{CLAUDE_PLUGIN_ROOT}}/{path}"]}


def _served(servers: dict[str, Any], present: list[str]) -> str:
    """What the probe announces about a kit whose hook is whole, for these servers."""
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        _kit(
            root, ["hooks/one.py"], ["hooks/one.py", *present], _manifest(["hooks/one.py"], servers)
        )
        return str(PROBE.announce(PROBE.missing(str(root)), *PROBE.servers(str(root))))


def _kit(root: Path, wired: list[str], present: list[str], text: str | None = None) -> None:
    """Write one kit: a manifest wiring `wired`, and the files in `present`."""
    manifest = root / MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(_manifest(wired) if text is None else text, encoding="utf-8")
    for path in present:
        here = root / path
        here.parent.mkdir(parents=True, exist_ok=True)
        here.write_text("", encoding="utf-8")


def _said(wired: list[str], present: list[str], text: str | None = None) -> str:
    """What the probe announces about one kit, built and read in a throwaway tree."""
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        _kit(root, wired, present, text)
        return str(PROBE.announce(PROBE.missing(str(root))))


def _rules() -> dict[str, bool]:
    """One entry per rule the probe exists to hold, name to whether it held."""
    gone = _said(["hooks/one.py", "hooks/two.py"], ["hooks/one.py"])
    both = _said(["hooks/one.py", "hooks/two.py"], [])
    broken = _said([], [], text="{not json")
    server = "scripts/mcp/one_server.py"
    whole = [server, *PROBE.SERVER_DEPS]
    absent = _served({"one": _server(server)}, [])
    missing_dep = _served({"one": _server(server)}, [server])
    crooked = _served({"crooked": "not an object", "one": _server(server)}, whole)
    return {
        "a whole kit says nothing at all": _said(["hooks/one.py"], ["hooks/one.py"]) == "",
        "a kit missing one hook names it, and not the hook that is there": (
            "hooks/two.py" in gone and "hooks/one.py" not in gone
        ),
        "a kit missing two hooks names both, and counts them": (
            "hooks/one.py" in both and "hooks/two.py" in both and "2 wired hook(s)" in both
        ),
        "an announcement says the lanes are open": "open for this session" in gone,
        "a manifest that is not JSON announces nothing": broken == "",
        "a kit with no manifest at all announces nothing": (
            PROBE.announce(PROBE.missing("/nowhere-at-all")) == ""
        ),
        "the kit root is the host's when it names one, else where the file sits": (
            Path(PROBE.kit_root()).is_dir()
        ),
        "the kit this hook ships in is whole": PROBE.missing(PROBE.kit_root()) == [],
        "a kit missing an MCP server's script names the server and its path": (
            f"one ({server})" in absent and "MCP server" in absent
        ),
        "a kit missing a server's shared dependency names it, its script present": (
            "scripts/mcp/rpc.py" in missing_dep and "MCP server" in missing_dep
        ),
        "a kit whose MCP servers are all there says nothing at all": (
            _served({"one": _server(server)}, whole) == ""
        ),
        "a malformed MCP server entry is named by its key, without a crash": (
            "crooked" in crooked and "one (" not in crooked
        ),
    }


def run() -> int:
    """One PASS or FAIL per rule the probe exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(run())
