#!/usr/bin/env python3
"""PreToolUse hook: `tests/` is the scrivener's lane, and only in its spec tree.

Wired session-wide from `.claude/settings.json`, so it binds the main agent
and every subagent, and again from the `hooks:` frontmatter of
`agents/scrivener.md`, where the same script confines that agent to
its own tree's `tests/`.

The rule it enforces: tests are written blind, from an approved spec block, by
the `scrivener`, in the spec worktree cut for the run. Every other hand on a
test file is the one the chain exists to keep off it: the agent that
implements the change editing a test until it passes.

Denied:

  * `Write`/`Edit`/`NotebookEdit` whose target is under `tests/` of any
    checkout, unless the caller's `agent_type` is `scrivener` AND the
    target is inside a `.claude/worktrees/*-spec` tree
  * for the `scrivener`, any `Write`/`Edit` outside its spec tree's `tests/`

Allowed: every write elsewhere.

`Bash` is not this hook's business. A shell that writes into `tests/` is
stopped by the mount table -- `bwrap-wrap.py` binds the lane directories
read-only inside every wrapped profile -- rather than by reading the command,
which is the question no string answers. The cost is the prose: a shell write
comes back as an errno, and the explanation below survives only for `Write`
and `Edit`, which is the tool an agent should be using.

One lane is a script's rather than the writer's. A strike motion block names
tests to remove; a single test is an `Edit` and the writer's, but a whole file
cannot be, because this hook denies every hand the shell it would take. So
`scripts/pair.sh red` removes the whole-file targets itself, from the committed
block. This hook does not see that removal and is not meant to: it governs what
an agent types, and the script is bounded by the block it reads from git.
`scripts/strike-diff.py` checks the result at merge, against that same block.

`agent_type` is present in the payload only for subagent calls; an absent key
is the main agent. If a build omits the key for subagents too, the writer is
over-denied, which is the safe direction: nothing leaks, and the denial names
this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shell_shapes as sh  # noqa: E402

WRITER = "scrivener"
#: `tests` unless the repo names another directory under the `tests_dir` key
#: of `blind-reads.json`; the lane hooks and the scripts read the same key
LANE = sh.tests_dir()

_LANE = (
    f"{LANE}/ is the scrivener's lane, written only in its spec tree from the "
    "committed spec block. A test whose behavior changed goes back through the "
    "spec: a re-approved line, a new `spec:` commit, a delta to the writer. A "
    "test whose assertion survives unchanged goes through "
    "`motion: rehome`, which quotes that assertion and names where it lands, its "
    "own file included. "
    "Either route, never by hand, never in the impl tree, never on the branch. "
    "(hooks/tests-lane.py)"
)
_WRITER_LANE = (
    f"Blind writer: you write under {LANE}/ of your own spec tree and nowhere else. "
    f"Not the source tree, not {sh.docs_dir()}/, not another worktree. (hooks/tests-lane.py)"
)


def _is_spec_tree(root: str) -> bool:
    path = Path(root)
    return path.name.endswith("-spec") and path.parent.name == "worktrees"


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


def _verdict(name: str, tool_input: sh.ToolInput, payload: sh.Payload) -> str | None:
    """Why this call is refused, or None to let it through."""
    return sh.dispatch(name, tool_input, payload, on_write=_write_verdict)


def main() -> None:
    sh.hook_main(_verdict, guards=sh.WRITE_TOOLS)


def self_test() -> int:
    """Pin the three spec lines of the test lane."""
    root = sh.checkout_root(str(Path(__file__).resolve().parent)) or "/repo"
    spec = str(Path(root) / ".claude" / "worktrees" / "x-spec")
    impl = str(Path(root) / ".claude" / "worktrees" / "x-impl")

    write, bash = sh.probes(_verdict, root)
    denied, allowed = sh.denied, sh.allowed
    lines = {
        "1 tests/ closed to all but the writer in a spec tree": all(
            (
                denied(write(f"{root}/tests/t.py")),
                denied(write(f"{impl}/tests/t.py")),
                denied(write(f"{spec}/tests/t.py")),
                denied(write(f"{impl}/tests/t.py", "cavecrew-builder")),
                allowed(write(f"{spec}/tests/t.py", WRITER)),
                denied(write(f"{impl}/tests/t.py", WRITER)),
                #: installed as a plugin the harness spells the name with its
                #: plugin in front of it, and that is the same agent
                allowed(write(f"{spec}/tests/t.py", f"gauntlet:{WRITER}")),
                denied(write(f"{impl}/tests/t.py", f"gauntlet:{WRITER}")),
            )
        ),
        "2 writer confined to its spec tree's tests/": all(
            (
                denied(write(f"{spec}/src/m.py", WRITER)),
                denied(write(f"{spec}/docs/testing.md", WRITER)),
                allowed(write(f"{spec}/tests/conftest.py", WRITER)),
            )
        ),
        #: the classifier is gone: the lane's shell half is the mount table,
        #: which binds this directory read-only inside every wrapped profile
        "3 a Bash call is not this lane's business, whatever it names": all(
            (
                allowed(bash("sed -i 's/a/b/' tests/t.py")),
                allowed(bash("rm tests/t.py")),
                allowed(bash("cd tests && rm t.py")),
                allowed(bash("find tests -name '*.py' -delete")),
                allowed(bash(".venv/bin/pytest tests/t.py -q")),
            )
        ),
        #: a hook decides a tool call, so its own crash is a denial -- and a
        #: payload it cannot read is a call it cannot decide, which is a refusal
        "every payload shape is answered, and an unreadable one is refused": (
            sh.survives_hostile_payloads(__file__, guards=sh.WRITE_TOOLS)
        ),
    }
    return sh.report(lines)


if __name__ == "__main__":
    sh.entry(self_test, main)
