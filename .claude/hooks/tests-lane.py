#!/usr/bin/env python3
"""PreToolUse hook: `tests/` is the gauntlet-testsmith's lane, and only in its spec tree.

Wired session-wide from `.claude/settings.json`, so it binds the main agent
and every subagent, and again from the `hooks:` frontmatter of
`.claude/agents/gauntlet-testsmith.md`, where the same script confines that agent to
its own tree's `tests/`.

The rule it enforces: tests are written blind, from an approved spec block, by
the `gauntlet-testsmith`, in the spec worktree cut for the run. Every other hand on a
test file is the one the chain exists to keep off it: the agent that
implements the change editing a test until it passes.

Denied:

  * `Write`/`Edit`/`NotebookEdit` whose target is under `tests/` of any
    checkout, unless the caller's `agent_type` is `gauntlet-testsmith` AND the
    target is inside a `.claude/worktrees/*-spec` tree
  * for the `gauntlet-testsmith`, any `Write`/`Edit` outside its spec tree's `tests/`
  * a `Bash` command that writes and that names a `tests/` path, except a
    restore from a named git object (`git restore --source <rev>` or
    `git checkout <rev> --` onto the path), which copies a commit and types
    nothing

Allowed: every read-only command naming `tests/` (`pytest`, `cat`, `sed -n`,
`grep`), and every write elsewhere.

One lane is a script's rather than the writer's. An excision spec block names
tests to remove; a single test is an `Edit` and the writer's, but a whole file
cannot be, because this hook denies every hand the shell it would take. So
`scripts/pair.sh red` removes the whole-file targets itself, from the committed
block. This hook does not see that removal and is not meant to: it governs what
an agent types, and the script is bounded by the block it reads from git.
`scripts/excision-diff.py` checks the result at merge, against that same block.

`agent_type` is present in the payload only for subagent calls; an absent key
is the main agent. If a build omits the key for subagents too, the writer is
over-denied, which is the safe direction: nothing leaks, and the denial names
this file.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shell_shapes as sh  # noqa: E402

WRITER = "gauntlet-testsmith"
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")
LANE = "tests"
BASH_TESTS = sh.lane_pattern(LANE)

_LANE = (
    "tests/ is the gauntlet-testsmith's lane, written only in its spec tree from the "
    "committed spec block. A test that must change goes back through the spec: "
    "a re-approved line, a new `spec:` commit, a delta to the writer. Never by "
    "hand, never in the impl tree, never on the branch. (hooks/tests-lane.py)"
)
_WRITER_LANE = (
    "Blind writer: you write under tests/ of your own spec tree and nowhere else. "
    "Not the source tree, not docs/, not another worktree. (hooks/tests-lane.py)"
)
_BASH = (
    "A shell write naming a tests/ path is denied: " + _LANE + " Restoring a test "
    "from a git object is the one shell shape that passes: "
    "`git restore --source <rev> -- tests/<file>`."
)


def _is_spec_tree(root: str) -> bool:
    parent, name = os.path.split(root)
    return name.endswith("-spec") and os.path.basename(parent) == "worktrees"


def _write_verdict(target: str, cwd: str, agent: str) -> str | None:
    root, rel = sh.split_root(target, cwd)
    #: outside any checkout there is no root to name, but the lane still holds:
    #: a `tests/` segment in the path is the lane, before `git init` and after
    in_tests = (
        sh.under(rel, LANE)
        if rel is not None and not rel.startswith("..")
        else sh.path_in_lane(target, cwd, LANE)
    )
    if agent == WRITER:
        return None if in_tests and root is not None and _is_spec_tree(root) else _WRITER_LANE
    return _LANE if in_tests else None


def _bash_verdict(command: str) -> str | None:
    return _BASH if sh.lane_write_in(command, BASH_TESTS) else None


def _verdict(name: str, tool_input: dict, payload: dict) -> str | None:
    """Why this call is refused, or None to let it through."""
    cwd = payload.get("cwd") or os.getcwd()
    agent = payload.get("agent_type") or ""
    if name in WRITE_TOOLS:
        target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        return _write_verdict(target, cwd, agent) if target else None
    if name == "Bash":
        return _bash_verdict(tool_input.get("command", ""))
    return None


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        return  # never block on our own failure
    reason = _verdict(data.get("tool_name", ""), data.get("tool_input") or {}, data)
    if reason is not None:
        print(sh.deny(reason))


def self_test() -> int:
    """Pin the three spec lines of the test lane."""
    root = sh.checkout_root(os.path.dirname(os.path.abspath(__file__))) or "/repo"
    spec = os.path.join(root, ".claude", "worktrees", "x-spec")
    impl = os.path.join(root, ".claude", "worktrees", "x-impl")

    def write(path: str, agent: str | None = None) -> str | None:
        payload = {"cwd": root}
        if agent:
            payload["agent_type"] = agent
        return _verdict("Edit", {"file_path": path}, payload)

    def bash(cmd: str) -> str | None:
        return _verdict("Bash", {"command": cmd}, {"cwd": root})

    denied, allowed = (lambda v: isinstance(v, str)), (lambda v: v is None)
    lines = {
        "1 tests/ closed to all but the writer in a spec tree": all(
            (
                denied(write(f"{root}/tests/t.py")),
                denied(write(f"{impl}/tests/t.py")),
                denied(write(f"{spec}/tests/t.py")),
                denied(write(f"{impl}/tests/t.py", "cavecrew-builder")),
                #: an unprefixed same-named agent in the host project is not this one
                denied(write(f"{spec}/tests/t.py", "testsmith")),
                allowed(write(f"{spec}/tests/t.py", WRITER)),
                denied(write(f"{impl}/tests/t.py", WRITER)),
            )
        ),
        "2 writer confined to its spec tree's tests/": all(
            (
                denied(write(f"{spec}/src/m.py", WRITER)),
                denied(write(f"{spec}/docs/testing.md", WRITER)),
                allowed(write(f"{spec}/tests/conftest.py", WRITER)),
            )
        ),
        "3 shell writes naming tests/ denied, reads and object restores pass": all(
            (
                denied(bash("sed -i 's/a/b/' tests/t.py")),
                denied(bash("echo x > tests/t.py")),
                denied(bash("rm tests/t.py")),
                allowed(bash(".venv/bin/pytest tests/t.py -q")),
                allowed(bash("cat tests/t.py")),
                allowed(bash("grep -rn 'def test_' tests/")),
                allowed(bash("git restore --source abc1234 -- tests/t.py")),
                allowed(bash("git checkout abc1234 -- tests/t.py")),
                allowed(bash("git commit -m 'test: pins tests/t.py'")),
            )
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test()) if "--self-test" in sys.argv else main()
