#!/usr/bin/env python3
"""PreToolUse hook: the two blind agents that keep `Bash` get one command.

Wired session-wide from `.claude-plugin/plugin.json`, and gated on the caller, the
same shape `no-impl-reads.py` carries. A plugin-shipped agent definition runs
no `hooks:` frontmatter of its own, so frontmatter wiring reaches nothing once
the kit ships as a plugin.

`BLIND` is still the two agents it always was; what inverted is the caller
rule. A caller outside that pair returns `None` and is unjudged, so the main
agent's shell is judged by nothing this hook does -- identical to the
frontmatter wiring it replaces, which never saw a main-agent call either.

The `juror` and the `arbiter` have no `Bash` at all. The
`scrivener` and the `bailiff` still need one: a suite run
against the file they wrote, the working-tree check that proves their spec is
committed, and a `git show` of that spec. Those three are `scripts/blind.sh`,
and this hook is what makes them the only three.

The check is a whole-string anchored match, never a search. A hook that looks
for `scripts/blind.sh` anywhere in the command lets a second command appended
after it through, and that prints a file the same agent's `Read` is denied. So
the command text is matched end to end, and a second command appended, a
command in front, or an environment assignment in front all fail to match.

Each subcommand admits its own argument shape and nothing wider:

  * `test <path>`   a repo-relative path under `<tests dir>/`
  * `status <slug>`
  * `show <commit> <slug>`

The argument grammars are the other half of the same rule. A hook that takes
whatever word follows `show` as the slug admits a relative path walking out of
the lane, and one that takes whatever word sits in the commit position admits
an object name carrying its own `:path`. Either hands a blind agent an
approved plan, which is the read `no-impl-reads.py` denies it by every other
route.

The runner a `test` run uses is configuration, never an argument. It is
`pytest_command` or `node_command` from `blind-reads.json`, read by
`scripts/blind.sh` after this hook has decided, so a project that has to
deselect a marker or import a loader widens its own runner and widens nothing
here: the admitted shape is still `scripts/blind.sh test <path>` with one
argument, and a runner word typed after the path is a second argument and
denied. Typing the runner itself is denied too, by the same rule that denies
every other command: `.venv/bin/pytest <path>` is not a `scripts/blind.sh`
call. That is what keeps the blind agent's suite run the run the script
defines rather than one the agent composed.

A bare head is resolved here rather than typed. `scripts/blind.sh` names
nothing in a consumer's checkout -- the script ships in the plugin, beside this
file -- so a bare call passes this hook and then dies at exec with "no such
file or directory". The alternative was prose: every brief and every doc
spelling `${CLAUDE_PLUGIN_ROOT}/scripts/blind.sh` at each of the blind agents'
call sites, a prefix an agent has to carry through every command it types. So
the hook answers with `updatedInput` instead, the mechanism `bwrap-wrap.py`
takes, and spells the bare head at this file's own sibling: `Path(__file__)`
is inside the kit wherever the kit is installed, which is exactly the fact the
agent lacks. Only a bare head is rewritten, only for a caller in `BLIND`, and
only after the admitted-shape match has already decided the call -- the
resolution moves no boundary, because the shapes it runs behind are the same
three and a denied command is never resolved.

`agent_type` is present in the payload only for subagent calls, so an absent
key is the main agent and passes. That is the cost of session wiring, and it
is the opposite of what frontmatter wiring gave: the old rule denied on an
absent key, because a build that stopped supplying it cost the two blind
agents their one command rather than handing a full shell to a caller nobody
identified. Session-wide that guarantee is unavailable -- the main agent is
itself the caller with no key -- so a build that stopped supplying it would
hand the scrivener an unrestricted shell instead of denying it. Guarding by
caller identity cannot fail closed; guarding by wiring scope could, and does
not survive packaging. `no-impl-reads.py` pays the same price for the same
reason, and `${CLAUDE_PLUGIN_ROOT}/docs/approved-specs.md` states it once for both.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shell_shapes as sh  # noqa: E402

BLIND = ("scrivener", "bailiff")
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
#: the head, in the three spellings admitted. `scripts/blind.sh` bare is the
#: one an agent types; the absolute path and the `${CLAUDE_PLUGIN_ROOT}` the
#: runtime expands into one are admitted because a brief or a doc may still
#: carry them. A *relative* prefix is deliberately not admitted: the blind
#: writer may write under `<tests dir>/`, so `tests/scripts/blind.sh` would be
#: a shell of its own authoring.
_HEAD = r"(?:/[A-Za-z0-9_.@+:/-]*/|\$\{CLAUDE_PLUGIN_ROOT\}/)?" + re.escape(ENTRY)

ALLOWED = tuple(re.compile(rf"\s*{_HEAD}\s+{a}\s*\Z") for a in _ARGS)

_WHY = (
    "A blind agent's shell is one command: `scripts/blind.sh test <path>`, "
    "`scripts/blind.sh status <slug>` or `scripts/blind.sh show <commit> <slug>`. The whole "
    "command text has to be that call and nothing else -- no second command after it, no "
    "command or environment assignment in front of it -- and each argument has to be the "
    "shape its subcommand names. Everything else is denied by name, not by analysis. "
    "(hooks/blind-bash.py)"
)

def _allowed_command(command: str) -> bool:
    """Whether the whole command text is one `scripts/blind.sh` call we admit."""
    if ".." in command:
        return False
    return any(p.match(command) for p in ALLOWED)


def kit_entry() -> str:
    """This kit's own `scripts/blind.sh`, absolute.

    `hooks/` and `scripts/` are siblings in the plugin, so the entry is found
    from this file rather than from the checkout the command runs in -- which,
    for an installed plugin, holds no copy of the script at all.
    """
    return str(Path(__file__).resolve().parent.parent / ENTRY)


def _resolved(command: str) -> str | None:
    """The same command with a bare head spelled at this kit's own entry.

    None where the head is already absolute or `${CLAUDE_PLUGIN_ROOT}`: those
    name a script themselves and are left exactly as typed. The command has
    matched an admitted shape before this runs, so the head is the first word
    and a leading occurrence of the entry is that word.
    """
    head = command.lstrip()
    if not head.startswith(ENTRY):
        return None
    lead = command[: len(command) - len(head)]
    return lead + kit_entry() + head[len(ENTRY) :]


def _verdict(name: str, tool_input: sh.ToolInput, payload: sh.Payload) -> str | None:
    """Why this call is refused, or None to let it through."""
    if name != "Bash":
        return None
    #: wired session-wide, so every agent's shell arrives here. A caller
    #: outside `BLIND` is not this hook's subject and is let through unjudged,
    #: the main agent -- which carries no `agent_type` at all -- included
    if sh.agent_of(payload) not in BLIND:
        return None
    return None if _allowed_command(sh.command_of(tool_input)) else _WHY


def _answer(payload: sh.Payload) -> dict[str, Any] | None:
    """The hook's answer for this payload: a denial, a resolved head, or nothing.

    The denial is the whole of the rule and runs first. A call it lets through
    is resolved only for a caller in `BLIND`, so the main agent's shell is
    untouched here exactly as it is untouched by the verdict.
    """
    name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    reason = _verdict(name, tool_input, payload)
    if reason is not None:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    if name != "Bash" or sh.agent_of(payload) not in BLIND:
        return None
    resolved = _resolved(sh.command_of(tool_input))
    if resolved is None:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {"command": resolved},
        }
    }


def main() -> None:
    sh.answer_main(_answer)


def self_test() -> int:
    """Pin the four spec lines of the blind agents' one command."""
    shapes = "shell_shapes.py"
    hook = "no-impl-reads.py"
    here = "hooks/"
    wire = sh.tests_dir() + "/test_hook_wire.py"
    plan = sh.plans_lane() + "/bash-sandbox"

    bash = sh.rebased(sh.probe(_verdict, "/repo", "Bash", "command", agent="scrivener"))

    denied, allowed = sh.denied, sh.allowed

    def at_runner(words: list[str], target: str) -> bool:
        """With `words` configured as the runner, are its own words still denied?

        The runner is read by `scripts/blind.sh`, after this hook has decided,
        so a configured invocation is not a command this hook admits. Naming
        one here and asking again is what proves that.
        """
        saved = sh.runners
        #: a plain function where the module holds an `lru_cache` wrapper, which
        #: is the whole point of the swap: the stand-in answers without a cache
        sh.runners = lambda: {  # type: ignore[assignment]
            "pytest_command": words,
            "node_command": words,
        }
        try:
            typed = " ".join(words + [target])
            return denied(bash(typed)) and denied(bash(f"scripts/blind.sh test {typed}"))
        finally:
            sh.runners = saved

    entry = kit_entry()

    def _answered(command: str, who: str | None = "scrivener") -> dict[str, Any]:
        """What this hook hands back for one Bash call, as the wire sends it."""
        payload: sh.Payload = {"cwd": "/repo", "tool_name": "Bash"}
        payload["tool_input"] = {"command": sh.respell(command)}
        if who is not None:
            payload["agent_type"] = who
        answer = _answer(payload) or {}
        return answer.get("hookSpecificOutput") or {}

    def resolved(command: str, who: str | None = "scrivener") -> str | None:
        """The command text the hook rewrote this call to, or None for neither."""
        return (_answered(command, who).get("updatedInput") or {}).get("command")

    def answers_deny(command: str, who: str | None = "scrivener") -> bool:
        """That the answer is a denial, which is the only other answer there is."""
        return _answered(command, who).get("permissionDecision") == "deny"

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
        "1a the head is the entry, an absolute path to it, or the plugin root": all(
            (
                allowed(bash("/opt/gauntlet/scripts/blind.sh status demo")),
                allowed(bash("${CLAUDE_PLUGIN_ROOT}/scripts/blind.sh status demo")),
                allowed(bash(f"${{CLAUDE_PLUGIN_ROOT}}/scripts/blind.sh test {wire}")),
                #: a relative prefix is not a head: the blind writer can write
                #: under its own lane, so this would be a shell it authored
                denied(bash(f"{sh.tests_dir()}/scripts/blind.sh status demo")),
                denied(bash("../scripts/blind.sh status demo")),
                denied(bash("/opt/gauntlet/scripts/blind.sh.bak status demo")),
                denied(bash("/opt/g;x/scripts/blind.sh status demo")),
            )
        ),
        "1b a bare head is resolved to this kit's own copy, and nothing else is": all(
            (
                #: the spelling every agent definition and doc now carries,
                #: answered with the script's real path so it runs where the
                #: kit is installed rather than dying at exec
                resolved("scripts/blind.sh status demo") == f"{entry} status demo",
                resolved(f"scripts/blind.sh test {wire}") == f"{entry} test {wire}",
                resolved("  scripts/blind.sh show HEAD demo  ")
                == f"  {entry} show HEAD demo  ",
                #: the entry is beside this hook, so the answer names a file
                #: that is there
                Path(kit_entry()).is_file(),
                #: a head that already names a script is left as typed
                resolved("${CLAUDE_PLUGIN_ROOT}/scripts/blind.sh status demo") is None,
                resolved("/opt/gauntlet/scripts/blind.sh status demo") is None,
                #: a denied command is never resolved, the traversal head
                #: line 1a refuses included: the denial is the whole answer
                answers_deny(f"{sh.tests_dir()}/scripts/blind.sh status demo"),
                resolved(f"{sh.tests_dir()}/scripts/blind.sh status demo") is None,
                resolved(f"cat {here}{hook}") is None,
                #: and a caller this hook does not answer for keeps its own
                #: command text, resolution included
                resolved("scripts/blind.sh status demo", None) is None,
                resolved("scripts/blind.sh status demo", "prosecutor") is None,
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
        "3 the two blind agents are judged, and no other caller is": all(
            (
                #: the one command, for the pair this hook answers for
                allowed(bash("scripts/blind.sh status demo", "scrivener")),
                allowed(bash("scripts/blind.sh status demo", "bailiff")),
                denied(bash(f"cat {here}{hook}", "scrivener")),
                denied(bash(f"cat {here}{hook}", "bailiff")),
                #: the main agent carries no `agent_type`, and session wiring
                #: puts its every shell command here: it passes unjudged
                allowed(bash(f"cat {here}{hook}", None)),
                allowed(bash("", None)),
                #: an empty string is no name, and reads as the main agent
                allowed(bash(f"cat {here}{hook}", "")),
                #: and so does an agent this hook does not answer for, rather
                #: than losing a shell to a rule that is not about it
                allowed(bash(f"cat {here}{hook}", "juror")),
                allowed(bash(f"cat {here}{hook}", "arbiter")),
                allowed(bash(f"cat {here}{hook}", "prosecutor")),
                allowed(bash(f"cat {here}{hook}", "general-purpose")),
                #: installed as a plugin the harness spells the name with its
                #: plugin in front of it, and that is the same agent
                allowed(bash("scripts/blind.sh status demo", "gauntlet:scrivener")),
                allowed(bash("scripts/blind.sh status demo", "gauntlet:bailiff")),
                denied(bash(f"cat {here}{hook}", "gauntlet:scrivener")),
                denied(bash(f"cat {here}{hook}", "gauntlet:bailiff")),
                allowed(bash(f"cat {here}{hook}", "gauntlet:juror")),
            )
        ),
        "4 the runner is configuration, and no runner argument widens the one command": (
            all(
                (
                    #: the whole of what an agent may type: the path, and nothing
                    #: after it. The flags the suite runs with are the script's.
                    allowed(bash(f"scripts/blind.sh test {wire}")),
                    denied(bash(f"scripts/blind.sh test {wire} -q")),
                    denied(bash(f"scripts/blind.sh test {wire} -m 'not live and not e2e'")),
                    denied(bash(f"scripts/blind.sh test {wire} --import ./support/resolve.js")),
                    denied(bash(f"scripts/blind.sh test -m live {wire}")),
                    #: nor by naming a runner directly, configured or not
                    denied(bash(f".venv/bin/pytest {wire}")),
                    denied(bash(f"pytest -m 'not live and not e2e' {wire}")),
                    denied(bash(f"node --test {wire}")),
                    #: and a project whose configured runner carries those very
                    #: words admits no more: this hook never reads the runner
                    at_runner(["pytest", "-m", "not live and not e2e"], wire),
                    at_runner(["node", "--import", "./support/resolve.js", "--test"], wire),
                )
            )
        ),
        #: a hook decides a tool call, so its own crash is a denial -- and a
        #: payload it cannot read is a call it cannot decide, which is a refusal
        "every payload shape is answered, and an unreadable one is refused": (
            sh.survives_hostile_payloads(__file__, guards=("Bash",))
        ),
    }
    return sh.report(lines)


if __name__ == "__main__":
    sh.entry(self_test, main)
