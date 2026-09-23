#!/usr/bin/env python3
"""Gate: the kit, installed into a project that is not this one, survives a session.

    scripts/gates/consumer-smoke.py [--check]
    scripts/gates/consumer-smoke.py --self-test

Every other gate here runs the hooks against this checkout, where every
directory the kit expects is present and every path resolves. A consumer
installs the kit into a project that has none of that history: a fresh
repository, no `gauntlet/` directory, no red run, no approved block, nothing the
chain has ever written. Four shipped-green outages have been exactly that
difference, and none of them was a logic error.

So the kit is copied into a scratch project and driven through the events a
session actually fires, in the order it fires them, with the manifest deciding
which hooks run at each one:

    SessionStart -> UserPromptSubmit -> PreToolUse(Bash) -> PreToolUse(Write)
                 -> PostToolUse(Write) -> Stop

Four rules, read on every hook of every step:

  * **Nothing crashes.** A traceback is not a verdict, and on `Stop` it is a
    turn held open.
  * **What is printed is readable.** Anything on stdout parses as JSON, since
    that is the only thing the host reads a decision out of.
  * **A fresh project is not held.** The `Stop` gate exits 0 where the chain
    has never run. A consumer who installs the kit and writes no spec must not
    find the turn refused.
  * **The lane works there.** A main-agent write to the consumer's own tests
    directory comes back denied, in a project this repository has never seen.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

MANIFEST = ".claude-plugin/plugin.json"

#: what an install carries, and nothing else: the tests and the documents of
#: this repository are not part of what a consumer gets. `scripts` is, because
#: the manifest's MCP servers and the lane hooks run the scripts under it.
INSTALLED = ("hooks", "agents", "scripts", ".claude-plugin")

#: a hook that has not answered by now is stuck
TIMEOUT = 30

#: what a crash looks like on the way out
CRASH = "Traceback (most recent call last)"

#: the directories a fresh consumer project holds, and nothing the chain wrote
CONSUMER = ("tests", "src", "docs")


#: the write the source file of one step names
WRITTEN = {"file_path": "src/parser.py", "content": "x\n"}

STEPS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("SessionStart", {"source": "startup"}),
    ("UserPromptSubmit", {"prompt": "add a guard to the parser"}),
    ("PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "ls src"}}),
    ("PreToolUse", {"tool_name": "Write", "tool_input": WRITTEN}),
    ("PostToolUse", {"tool_name": "Write", "tool_input": WRITTEN}),
    ("Stop", {"stop_hook_active": False}),
)

#: the opening exchange a session has with one MCP server, one message per line
SERVER_STEPS: tuple[dict[str, Any], ...] = (
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
)

#: a grant an agent definition names, qualified by the plugin and server it reaches
GRANT_RE = re.compile(r"mcp__plugin_[\w-]+__[\w*-]+")


def lane_step(root: str) -> tuple[str, dict[str, Any]]:
    """The one step that must be refused: a main-agent write to the tests lane."""
    return (
        "PreToolUse",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": f"{root}/tests/test_parser.py", "content": "x\n"},
        },
    )


def project(base: Path) -> Path:
    """A fresh consumer checkout: a git directory, source, prose and tests."""
    root = base / "consumer"
    for name in CONSUMER:
        (root / name).mkdir(parents=True, exist_ok=True)
        (root / name / "kept.txt").write_text("kept\n", encoding="utf-8")
    (root / ".git").mkdir(exist_ok=True)
    return root


def install(base: Path, source: Path = ROOT) -> Path:
    """The kit as a consumer installs it, copied into its own directory."""
    kit = base / "kit"
    for name in INSTALLED:
        shutil.copytree(source / name, kit / name, dirs_exist_ok=True)
    return kit


def wired(kit: Path) -> dict[str, list[str]]:
    """Every wired command the installed manifest carries, event to commands."""
    try:
        data = json.loads((kit / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return {}
    return {
        event: [
            entry["command"]
            for group in listed
            for entry in group.get("hooks", [])
            if isinstance(entry, dict) and isinstance(entry.get("command"), str)
        ]
        for event, listed in hooks.items()
    }


def _argv(command: str, kit: Path, root: Path) -> list[str]:
    """One wired command as an argument list, as the host would fill it in."""
    filled = command.replace('"${CLAUDE_PLUGIN_ROOT}"', str(kit))
    filled = filled.replace("${CLAUDE_PLUGIN_ROOT}", str(kit))
    filled = filled.replace('"${CLAUDE_PROJECT_DIR}"', str(root))
    filled = filled.replace("${CLAUDE_PROJECT_DIR}", str(root))
    parts = filled.split()
    return [sys.executable if parts[0] == "python3" else parts[0], *parts[1:]]


def answer(
    command: str, event: str, payload: dict[str, Any], kit: Path, root: Path
) -> subprocess.CompletedProcess[str]:
    """What one installed hook does with one session-shaped payload."""
    whole = {
        "hook_event_name": event,
        "cwd": str(root),
        "session_id": "consumer-smoke",
        **payload,
    }
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    environment["CLAUDE_PLUGIN_ROOT"] = str(kit)
    environment["CLAUDE_PROJECT_DIR"] = str(root)
    try:
        return subprocess.run(
            _argv(command, kit, root),
            input=json.dumps(whole),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=[command], returncode=1, stdout="", stderr=f"did not answer in {TIMEOUT}s"
        )


def served(kit: Path) -> dict[str, list[str]]:
    """Every MCP server the installed manifest names, its key to its argv."""
    try:
        data = json.loads((kit / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    listed = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(listed, dict):
        return {}
    found: dict[str, list[str]] = {}
    for name, entry in listed.items():
        if not isinstance(entry, dict):
            continue
        command = entry.get("command")
        args = entry.get("args")
        if not isinstance(command, str) or not isinstance(args, list):
            continue
        words = [command, *(arg for arg in args if isinstance(arg, str))]
        found[name] = _argv(" ".join(words), kit, kit)
    return found


def granted(kit: Path) -> dict[str, set[str]]:
    """Every tool name a copied agent definition grants, keyed by the server it reaches.

    A wildcard grant (`__*`) names no one tool and is skipped, so the expected
    set comes from what an agent definition actually asks for, never from the
    server's own table -- the no-copy-assertions gate objects to that shape.
    """
    try:
        data = json.loads((kit / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    plugin = data.get("name") if isinstance(data, dict) else None
    if not isinstance(plugin, str):
        return {}
    prefix = f"mcp__plugin_{plugin}_"
    found: dict[str, set[str]] = {}
    for path in sorted((kit / "agents").glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for token in GRANT_RE.findall(text):
            if not token.startswith(prefix):
                continue
            server, sep, tool = token[len(prefix) :].partition("__")
            if sep and tool != "*":
                found.setdefault(server, set()).add(tool)
    return found


def speak(argv: list[str], kit: Path, root: Path) -> subprocess.CompletedProcess[str]:
    """Drive one installed MCP server through `initialize`, its ack, and `tools/list`."""
    stdin = "".join(json.dumps(step) + "\n" for step in SERVER_STEPS)
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    environment["CLAUDE_PLUGIN_ROOT"] = str(kit)
    environment["CLAUDE_PROJECT_DIR"] = str(root)
    try:
        return subprocess.run(
            argv,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=argv, returncode=1, stdout="", stderr=f"did not answer in {TIMEOUT}s"
        )


def denied(done: subprocess.CompletedProcess[str]) -> bool:
    """Did this hook refuse the call it was given?"""
    try:
        said = json.loads(done.stdout)
    except ValueError:
        return False
    specific = said.get("hookSpecificOutput") if isinstance(said, dict) else None
    if not isinstance(specific, dict):
        return False
    return specific.get("permissionDecision") == "deny"


def judge(
    said: list[tuple[str, str, subprocess.CompletedProcess[str]]],
    lane: list[subprocess.CompletedProcess[str]],
) -> list[str]:
    """Why the installed kit cannot stand in a fresh project, if it cannot."""
    problems = []
    for event, command, done in said:
        name = command.rsplit("/", 1)[-1]
        if CRASH in done.stdout or CRASH in done.stderr or "did not answer" in done.stderr:
            tail = (done.stderr or done.stdout).strip().splitlines()
            problems.append(f"{event}: {name} crashed, {(tail[-1] if tail else 'no output')!r}")
            continue
        if done.stdout.strip():
            try:
                json.loads(done.stdout)
            except ValueError:
                problems.append(
                    f"{event}: {name} printed something the host cannot read, "
                    f"{done.stdout.strip().splitlines()[0]!r}"
                )
        if event == "Stop" and done.returncode != 0:
            problems.append(
                f"Stop: {name} exited {done.returncode} in a project the chain never ran in. "
                "A consumer who installs the kit and writes no spec is held at every turn"
            )
    if not any(denied(done) for done in lane):
        problems.append(
            "a main-agent write to the consumer's own tests directory was allowed. "
            "The lane holds in this repository and nowhere else"
        )
    return problems


def judge_servers(
    said: list[tuple[str, list[str], subprocess.CompletedProcess[str]]],
    expected: dict[str, set[str]],
) -> list[str]:
    """Why an installed MCP server cannot answer a session's opening calls, if it cannot."""
    problems = []
    for name, _argv, done in said:
        if CRASH in done.stdout or CRASH in done.stderr or "did not answer" in done.stderr:
            tail = (done.stderr or done.stdout).strip().splitlines()
            problems.append(f"{name}: crashed, {(tail[-1] if tail else 'no output')!r}")
            continue
        listing = None
        for line in done.stdout.splitlines():
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if isinstance(message, dict) and message.get("id") == 2:
                listing = message
        if listing is None:
            problems.append(f"{name}: gave no answer to tools/list")
            continue
        result = listing.get("result") if isinstance(listing, dict) else None
        tools = result.get("tools") if isinstance(result, dict) else None
        if not isinstance(tools, list) or not tools:
            problems.append(f"{name}: tools/list answered with no tools")
            continue
        names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
        problems += [
            f"{name}: {tool} is granted and tools/list does not list it"
            for tool in sorted(expected.get(name, set()) - names)
        ]
    return problems


def readings(base: Path) -> list[str]:
    """Install the kit, drive one session through it, and score every answer."""
    kit = install(base)
    root = project(base)
    commands = wired(kit)
    said = [
        (event, command, answer(command, event, payload, kit, root))
        for event, payload in STEPS
        for command in commands.get(event, [])
    ]
    event, payload = lane_step(str(root))
    lane = [
        (event, command, answer(command, event, payload, kit, root))
        for command in commands.get(event, [])
    ]
    server_said = [(name, argv, speak(argv, kit, root)) for name, argv in served(kit).items()]
    return judge(said + lane, [done for _, _, done in lane]) + judge_servers(
        server_said, granted(kit)
    )


def check() -> int:
    """Copy the kit into a scratch project and run a session through it."""
    with tempfile.TemporaryDirectory(prefix="consumer-smoke-") as base:
        problems = readings(Path(base))
    with tempfile.TemporaryDirectory(prefix="consumer-smoke-count-") as base:
        server_count = len(served(install(Path(base))))

    for problem in problems:
        print(problem)
    print(f"{len(STEPS) + 1 + server_count * len(SERVER_STEPS)} step(s) through an installed kit")
    if problems:
        print(f"\n{len(problems)} problem(s). A consumer's project has none of this one's history.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from consumer_smoke_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
