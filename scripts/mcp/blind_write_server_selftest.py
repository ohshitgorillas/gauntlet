"""The `--self-test` body of `blind_write_server.py`: one line per rule the server holds.

`python3 scripts/mcp/blind_write_server.py --self-test` runs it. Nothing runs
`bwrap` and nothing reads the checkout: the tests directory and `blind.sh` are
stood in for by functions that answer as the real ones do, and the rules are
read off what `handle` does with those answers.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import blind_server
import blind_write_server as server
import rpc

TESTS = "tests"
TREE_PATH = ".claude/worktrees/demo-spec/tests/test_x.py"


def _refused(arguments: dict[str, object]) -> bool:
    """Whether `check` refuses these arguments."""
    try:
        server.check(dict(arguments), TESTS)
    except blind_server.Refused:
        return True
    return False


def _answer(line: dict[str, Any]) -> dict[str, Any] | None:
    return rpc.answer(server.SERVER, json.dumps(line))


def _handled(
    returncode: int, stderr: str = "", arguments: dict[str, Any] | None = None
) -> tuple[rpc.Reply, list[list[str]]]:
    """What `handle` answers when `blind.sh` exits `returncode`, and the argv it was given."""
    seen: list[list[str]] = []

    #: the names are the signature `blind_server.run` has, which mypy holds it to
    def run(
        words: list[str], cwd: Path, timeout: int  # noqa: ARG001
    ) -> subprocess.CompletedProcess[str]:
        seen.append(words)
        return subprocess.CompletedProcess(words, returncode, "--- ruff\nleaked\n", stderr)

    saved: tuple[Callable[..., Any], Callable[..., Any]] = (
        blind_server.run,
        blind_server.tests_dir,
    )
    blind_server.run = run
    blind_server.tests_dir = lambda cwd: TESTS  # noqa: ARG005
    try:
        reply = server.handle("format", arguments or {"path": TREE_PATH}, Path("/"))
    finally:
        blind_server.run, blind_server.tests_dir = saved
    return reply, seen


def _rules() -> dict[str, bool]:
    listed = _answer({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) or {}
    reading = _answer(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "test"}}
    )
    clean, argv = _handled(0)
    unclean, _ = _handled(1)
    broken, _ = _handled(2, "blind.sh: no such test file: x\nTraceback: child noise\n")
    refused, unrun = _handled(0, arguments={"path": "hooks/lanes.py"})
    return {
        "a worktree test path is admitted": not _refused({"path": TREE_PATH}),
        "a path outside the tests directory is refused": _refused({"path": "hooks/lanes.py"}),
        "a path climbing out with .. is refused": _refused({"path": "tests/../hooks/lanes.py"}),
        "a path that is not a string is refused": _refused({"path": 7}),
        "an argument the tool does not declare is refused": _refused(
            {"path": TREE_PATH, "extra": "x"}
        ),
        "a refused path never reaches blind.sh": refused.error and unrun == [],
        "blind.sh is handed format and the one path": argv == [["format", TREE_PATH]],
        "exit 0 answers clean": clean == rpc.Reply(server.CLEAN),
        "exit 1 answers not clean, without the fix tools' output": unclean
        == rpc.Reply(server.UNCLEAN),
        "exit 2 answers blind.sh's own line and no child's": broken
        == rpc.Reply("blind.sh: no such test file: x", error=True),
        "tools/list names format alone": [
            tool["name"] for tool in listed.get("result", {}).get("tools", [])
        ]
        == ["format"],
        "a reading tool is not served here": bool(reading) and "error" in (reading or {}),
    }


def self_test() -> int:
    """Print one PASS or FAIL per rule; exit 1 if any failed."""
    rules = _rules()
    for name, held in rules.items():
        print(f"{'PASS' if held else 'FAIL'}  {name}")
    return 0 if all(rules.values()) else 1
