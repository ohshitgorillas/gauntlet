#!/usr/bin/env python3
"""PreToolUse hook: the two blind agents that keep `Bash` get one command.

Wire it from the `hooks:` frontmatter of `.claude/agents/gauntlet-scrivener.md`
and `.claude/agents/gauntlet-bailiff.md`, and from nowhere else. It denies
every caller it does not recognise, so a session-wide wiring would deny the
main agent's shell outright.

The `gauntlet-juror` and the `gauntlet-arbiter` have no `Bash` at all. The
`gauntlet-scrivener` and the `gauntlet-bailiff` still need one: a suite run
against the file they wrote, the working-tree check that proves their spec is
committed, and a `git show` of that spec. Those three are `scripts/blind.sh`,
and this hook is what makes them the only three.

The check is a whole-string anchored match, never a search. A hook that looks
for `scripts/blind.sh` anywhere in the command lets a second command appended
after it through, and that prints a file the same agent's `Read` is denied. So
the command text is matched end to end, and a second command appended, a
command in front, or an environment assignment in front all fail to match.

Each subcommand admits its own argument shape and nothing wider:

  * `test <path>`   a repo-relative path under `tests/`
  * `status <slug>`
  * `show <commit> <slug>`

The argument grammars are the other half of the same rule. A hook that takes
whatever word follows `show` as the slug admits a relative path walking out of
the lane, and one that takes whatever word sits in the commit position admits
an object name carrying its own `:path`. Either hands a blind agent an
approved plan, which is the read `no-impl-reads.py` denies it by every other
route.

`agent_type` is present in the payload only for subagent calls. An absent key
is denied, the same direction the other lanes fail: a build that stops
supplying the key costs the two blind agents their one command, and does not
hand a full shell to a caller nobody identified.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shell_shapes as sh  # noqa: E402

BLIND = ("gauntlet-scrivener", "gauntlet-bailiff")
ENTRY = "scripts/blind.sh"

#: a slug names a file inside a lane directory, so it is one path segment and
#: carries no traversal: `..` and `/` are what the denial exists to refuse
SLUG = sh.SLUG
#: `HEAD`, or an abbreviated-to-full object name. A `:` is what turns a commit
#: argument into a path argument, and no shape here admits one
COMMIT = r"(?:HEAD|[0-9a-fA-F]{7,40})"
#: repo-relative, under the test directory, no traversal. The classifier reads
#: the same shape for the same entry, so it has one definition and lives there;
#: what refuses traversal here is `_allowed_command` on the raw command text,
#: and what refuses it there is normalization, which is why both still run
TESTPATH = sh.TESTPATH

_ARGS = (
    rf"test\s+{TESTPATH}",
    rf"status\s+{SLUG}",
    rf"show\s+{COMMIT}\s+{SLUG}",
)
ALLOWED = tuple(re.compile(rf"\s*{re.escape(ENTRY)}\s+{a}\s*\Z") for a in _ARGS)

_WHY = (
    "A blind agent's shell is one command: `scripts/blind.sh test <path>`, "
    "`scripts/blind.sh status <slug>` or `scripts/blind.sh show <commit> <slug>`. The whole "
    "command text has to be that call and nothing else -- no second command after it, no "
    "command or environment assignment in front of it -- and each argument has to be the "
    "shape its subcommand names. Everything else is denied by name, not by analysis. "
    "(hooks/blind-bash.py)"
)
_CALLER = (
    "This hook did not recognise the caller. It is wired from the gauntlet-scrivener and "
    "gauntlet-bailiff frontmatter and answers for those two agents alone; a payload naming "
    "another agent, or naming none, is denied rather than let through. " + _WHY
)


def _allowed_command(command: str) -> bool:
    """Whether the whole command text is one `scripts/blind.sh` call we admit."""
    if ".." in command:
        return False
    return any(p.match(command) for p in ALLOWED)


def _verdict(name: str, tool_input: dict, payload: dict) -> str | None:
    """Why this call is refused, or None to let it through."""
    if name != "Bash":
        return None
    if (payload.get("agent_type") or "") not in BLIND:
        return _CALLER
    return None if _allowed_command(tool_input.get("command", "")) else _WHY


def main() -> None:
    if sh.bypassed():
        return  # GAUNTLET=off: the owner's switch, read at the entry point only
    try:
        data = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        return  # never block on our own failure
    reason = _verdict(data.get("tool_name", ""), data.get("tool_input") or {}, data)
    if reason is not None:
        print(sh.deny(reason))


def self_test() -> int:
    """Pin the three spec lines of the blind agents' one command."""
    shapes = "shell_shapes.py"
    hook = "no-impl-reads.py"
    here = ".claude/hooks/"
    wire = "tests/test_hook_wire.py"
    plan = "gauntlet/plans/approved/bash-sandbox"

    def bash(cmd: str, agent: str | None = "gauntlet-scrivener") -> str | None:
        payload = {"cwd": "/repo"}
        if agent is not None:
            payload["agent_type"] = agent
        return _verdict("Bash", {"command": cmd}, payload)

    denied, allowed = (lambda v: isinstance(v, str)), (lambda v: v is None)
    lines = {
        "1 the whole command text is one scripts/blind.sh call, or it is denied": all(
            (
                allowed(bash("scripts/blind.sh status demo")),
                denied(bash(f"scripts/blind.sh status demo; cat {here}{shapes}")),
                denied(bash(f"scripts/blind.sh status demo && cat {here}{hook}")),
                denied(bash(f"cat {here}{shapes}; scripts/blind.sh status demo")),
                denied(bash("PYTHONPATH=. scripts/blind.sh status demo")),
                denied(bash("echo $(scripts/blind.sh status demo)")),
                denied(bash(f"cat {here}{hook}")),
                denied(bash("")),
            )
        ),
        "2 each subcommand admits only its own argument shape": all(
            (
                allowed(bash(f"scripts/blind.sh test {wire}")),
                allowed(bash(f"scripts/blind.sh test .claude/worktrees/demo-spec/{wire}")),
                denied(bash(f"scripts/blind.sh test .claude/worktrees/demo-spec/{here}{hook}")),
                denied(bash(f"scripts/blind.sh test {here}{hook}")),
                denied(bash(f"scripts/blind.sh test tests/../{here}{hook}")),
                denied(bash("scripts/blind.sh test")),
                allowed(bash("scripts/blind.sh status demo")),
                denied(bash("scripts/blind.sh status demo extra")),
                denied(bash("scripts/blind.sh status")),
                allowed(bash("scripts/blind.sh show 5494faa demo")),
                allowed(bash("scripts/blind.sh show HEAD demo")),
                denied(bash("scripts/blind.sh show 5494faa ../plans/bash-sandbox")),
                denied(bash(f"scripts/blind.sh show HEAD:{plan} demo")),
                denied(bash("scripts/blind.sh show 5494faa demo extra")),
                denied(bash("scripts/blind.sh show demo")),
                #: the subcommand name alone is not a pass: the arguments decide
                denied(bash(f"scripts/blind.sh status {wire} extra")),
                denied(bash("scripts/blind.sh merge demo")),
                denied(bash("scripts/blind.sh")),
            )
        ),
        "3 the caller key fails closed": all(
            (
                allowed(bash("scripts/blind.sh status demo", "gauntlet-scrivener")),
                allowed(bash("scripts/blind.sh status demo", "gauntlet-bailiff")),
                denied(bash("scripts/blind.sh status demo", None)),
                denied(bash("scripts/blind.sh status demo", "")),
                denied(bash("scripts/blind.sh status demo", "gauntlet-juror")),
                denied(bash("scripts/blind.sh status demo", "gauntlet-arbiter")),
                #: an unprefixed same-named agent in the host project is not this one
                denied(bash("scripts/blind.sh status demo", "scrivener")),
            )
        ),
        #: a hook decides a tool call, so its own crash is a denial
        "no payload shape makes this hook block the call it is deciding": (
            sh.survives_hostile_payloads(__file__)
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test()) if "--self-test" in sys.argv else sh.never_block(main)
