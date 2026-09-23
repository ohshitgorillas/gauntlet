#!/usr/bin/env python3
"""The `--self-test` body of `hooks-wired.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays a set of rules
and a sweep, and `python3 scripts/gates/hookgates/hooks-wired.py --self-test` runs it.

Each case writes a real wiring file -- real JSON, real scripts beside it -- into
a throwaway directory, changes into it so the paths reaching the gate are
repo-relative the way a real run passes them, and reads back the pair the gate
offers a caller: the exit code, and what lands on stdout.

The last case is the live tree. A gate that holds every invented case and fails
the repository it ships in has told nobody anything, and this one is cheap:
the wiring is three small files.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType
from typing import Any

GATE_PATH = Path(__file__).resolve().parent / "hooks-wired.py"

#: A wired script as the gate wants one: it compiles, and it offers the flag.
GOOD = (
    "#!/usr/bin/env python3\n\n\ndef main():\n    return 0\n\n\n"
    'if __name__ == "__main__":\n    if "--self-test" in []:\n        pass\n    main()\n'
)

#: The same script with no `--self-test` anywhere in it.
NO_SELF_TEST = "#!/usr/bin/env python3\n\n\ndef main():\n    return 0\n"

#: A script that does not compile.
BROKEN = "#!/usr/bin/env python3\n\ndef main(:\n    return 0\n"

WIRING = ".claude-plugin/plugin.json"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location("hooks_wired_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _manifest(event: str, entries: list[dict[str, Any]], matcher: str | None = None) -> str:
    """Render a plugin manifest wiring one group of entries under one event."""
    group: dict[str, Any] = {"hooks": entries}
    if matcher is not None:
        group["matcher"] = matcher
    return json.dumps({"hooks": {event: [group]}}, indent=2)


def _servers_manifest(paths: list[str]) -> str:
    """Render a plugin manifest wiring one MCP server per path, under the plugin root."""
    servers = {
        f"server{index}": {
            "command": "python3",
            "args": [f"${{CLAUDE_PLUGIN_ROOT}}/{path}"],
        }
        for index, path in enumerate(paths)
    }
    return json.dumps({"mcpServers": servers}, indent=2)


def _entry(path: str) -> dict[str, Any]:
    """One `type: command` entry naming a script the way the manifest spells one."""
    return {"type": "command", "command": f'python3 "${{CLAUDE_PLUGIN_ROOT}}"/{path}'}


def _run(text: str, scripts: dict[str, str]) -> tuple[int, str]:
    """Write one wiring and its scripts into a throwaway tree, and check it there."""
    with tempfile.TemporaryDirectory() as root:
        wiring = Path(root) / WIRING
        wiring.parent.mkdir(parents=True)
        wiring.write_text(text, encoding="utf-8")
        for name, source in scripts.items():
            path = Path(root) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
        here = Path.cwd()
        os.chdir(root)
        try:
            printed = io.StringIO()
            with redirect_stdout(printed):
                status = GATE.check((WIRING,))
            return status, printed.getvalue()
        finally:
            os.chdir(here)


def _live() -> bool:
    """The wiring this repository ships and keeps, audited where it sits."""
    here = Path.cwd()
    os.chdir(Path(GATE_PATH).resolve().parents[3])
    try:
        return bool(GATE.audit() == [])
    finally:
        os.chdir(here)


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    good = _run(_manifest("PreToolUse", [_entry("hooks/one.py")], "Bash"), {"hooks/one.py": GOOD})
    missing = _run(_manifest("PreToolUse", [_entry("hooks/gone.py")]), {})
    broken = _run(_manifest("Stop", [_entry("hooks/two.py")]), {"hooks/two.py": BROKEN})
    silent = _run(_manifest("Stop", [_entry("hooks/two.py")]), {"hooks/two.py": NO_SELF_TEST})
    event = _run(_manifest("PreToolUze", [_entry("hooks/one.py")]), {"hooks/one.py": GOOD})
    matcher = _run(
        _manifest("PreToolUse", [_entry("hooks/one.py")], "Bash("), {"hooks/one.py": GOOD}
    )
    kind = _run(_manifest("Stop", [{"type": "prompt", "command": "x"}]), {})
    empty = _run(_manifest("Stop", [{"type": "command", "command": "  "}]), {})
    unparsed = _run("{not json", {})
    absent = _run(_manifest("Stop", []), {})
    foreign = _run(
        _manifest("Stop", [{"type": "command", "command": "python3 /opt/x/hook.py"}]), {}
    )
    missing_server = _run(_servers_manifest(["scripts/mcp/gone.py"]), {})
    broken_server = _run(_servers_manifest(["scripts/mcp/two.py"]), {"scripts/mcp/two.py": BROKEN})
    silent_server = _run(
        _servers_manifest(["scripts/mcp/two.py"]), {"scripts/mcp/two.py": NO_SELF_TEST}
    )
    sound_server = _run(_servers_manifest(["scripts/mcp/one.py"]), {"scripts/mcp/one.py": GOOD})
    return {
        "a wiring whose every entry can fire passes": good == (0, ""),
        "a command naming no file fails, and the path is named": (
            missing[0] == 1 and "hooks/gone.py" in missing[1] and "is not a file" in missing[1]
        ),
        "a wired script that does not compile fails": (
            broken[0] == 1 and "does not compile" in broken[1]
        ),
        "a wired script offering no --self-test fails": (
            silent[0] == 1 and "offers no --self-test" in silent[1]
        ),
        "an event key no dispatcher reads fails": (
            event[0] == 1 and "PreToolUze" in event[1] and "no hook event" in event[1]
        ),
        "a matcher that is no regex fails": (
            matcher[0] == 1 and "no regex" in matcher[1] and "Bash(" in matcher[1]
        ),
        "an entry that is not type 'command' fails": (
            kind[0] == 1 and "not type 'command'" in kind[1]
        ),
        "an entry carrying no command fails": empty[0] == 1 and "no command" in empty[1],
        "a wiring that is not JSON fails": unparsed[0] == 1 and "not JSON" in unparsed[1],
        "a wiring with no entries passes": absent == (0, ""),
        "a command naming no repository path is left alone": foreign == (0, ""),
        "a wired MCP server naming no file fails, and the path is named": (
            missing_server[0] == 1
            and "scripts/mcp/gone.py" in missing_server[1]
            and "is not a file" in missing_server[1]
        ),
        "a wired MCP server that does not compile fails": (
            broken_server[0] == 1 and "does not compile" in broken_server[1]
        ),
        "a wired MCP server offering no --self-test fails": (
            silent_server[0] == 1 and "offers no --self-test" in silent_server[1]
        ),
        "a wired MCP server that can fire passes": sound_server == (0, ""),
        "the wiring this repository ships and keeps is clean": _live(),
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
