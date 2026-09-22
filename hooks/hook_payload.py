"""One hook payload, as a hook reads it and as a hook refuses it.

A guard reads three things out of a payload: which tool, what it names, and who
is running it. Each of them is whatever JSON carried, so each is decided at
runtime rather than trusted by its static shape -- and the answer to a call a
guard cannot evaluate is no, never silence.

`HOSTILE_PAYLOADS` is that rule as a check every hook runs against itself. It
is not a guess at what Claude Code sends: each shape there is one some hook
here has assumed away.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

#: one payload as a hook reads it: whatever JSON carried, decided at runtime by
#: `payload_fault` rather than trusted by its static shape
Payload = dict[str, Any]
#: the `tool_input` of one payload, on the same terms: a hook reads the keys it
#: needs through `write_target`, which answers for a missing key
ToolInput = dict[str, Any]
#: the three arguments every lane verdict takes, and the refusal or None it gives
Verdict = Callable[[str, ToolInput, Payload], str | None]


def deny(reason: str) -> str:
    """The PreToolUse deny payload, as a JSON string."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def cwd_of(payload: Payload | None) -> str:
    """The `cwd` a payload names, as a path, or this process's own.

    The field is whatever the payload carried, and a hook that hands a number
    to `os.path` raises, which denies the call.
    """
    cwd = (payload or {}).get("cwd")
    return cwd if isinstance(cwd, str) and cwd else str(Path.cwd())


def agent_of(payload: Payload | None) -> str:
    """Who is running this call, as a bare agent name, or `""` for the main agent.

    Installed as a plugin, the harness spells a subagent's `agent_type` with
    the plugin it came from in front of it -- `gauntlet:prosecutor`
    where a loose copy of the same kit sends `prosecutor`. Every hook
    here compares the name against a bare one, so the namespace has to come off
    before the comparison or the same agent matches nothing it should: a lane
    denies its own writer, and a blind agent's guard finds no subject and lets
    the call through unblinded.

    An agent name carries no `:`, so everything up to the last one is the
    namespace and the tail is the name. Which plugin the namespace names
    is not checked: a foreign plugin shipping an agent named `arbiter`
    is treated as this kit's, exactly as an unnamespaced agent of that name in
    the host project already is.
    """
    agent = (payload or {}).get("agent_type") or ""
    if not isinstance(agent, str):
        return ""
    return agent.rsplit(":", 1)[-1] if ":" in agent else agent


#: payloads a hook must answer without dying, each with the tool it names --
#: `None` for a payload that names nothing readable at all -- and whether the
#: fields a hook has to read are usable. Not a guess at what Claude Code sends:
#: each one is a shape some hook here has assumed away -- a missing field, a
#: field of the wrong type, a `cwd` naming a tree that was cut, a path that is
#: not a path. A hook that raises on any of them exits non-zero, and a non-zero
#: `PreToolUse` blocks the call; a hook that shrugs at one of the unusable ones
#: runs the call it was put there to decide.
HOSTILE_PAYLOADS = (
    ("", None, False),
    ("not json at all", None, False),
    ("null", None, False),
    ("[]", None, False),
    #: an object naming no tool names no call this hook guards
    ("{}", "", True),
    ('{"tool_name": "Bash"}', "Bash", False),
    ('{"tool_name": "Bash", "tool_input": null, "cwd": null}', "Bash", False),
    ('{"tool_name": "Bash", "tool_input": {"command": 17}, "cwd": 17}', "Bash", False),
    #: an empty command and an empty cwd are readable: the command runs nothing
    #: and the cwd falls back to this process's own, which is what `cwd_of` says
    ('{"tool_name": "Bash", "tool_input": {"command": ""}, "cwd": ""}', "Bash", True),
    ('{"tool_name": "Edit", "tool_input": {"file_path": null}}', "Edit", False),
    #: a NUL in a path is a string, so it is readable here and raises deeper in
    ('{"tool_name": "Edit", "tool_input": {"file_path": "\\u0000"}}', "Edit", True),
    (
        '{"tool_name": "Bash", "tool_input": {"command": "echo hi"},'
        ' "cwd": "/nonexistent-by-construction/deeper"}',
        "Bash",
        True,
    ),
    (
        '{"tool_name": "Bash", "tool_input": {"command": "echo hi"}, "cwd": "/etc/hostname"}',
        "Bash",
        True,
    ),
    (
        '{"tool_name": "Bash", "tool_input": {"command": "echo hi"},'
        ' "agent_type": 3, "cwd": "/"}',
        "Bash",
        False,
    ),
)

#: the field a call of this tool must carry as a string before a hook can
#: decide it. `Bash` carries the command; a write carries its target.
REQUIRED_FIELD = {
    "Write": "file_path",
    "Edit": "file_path",
    "NotebookEdit": "notebook_path",
    "Read": "file_path",
    "Bash": "command",
}

#: a field a call may omit, but may not carry as something other than a string
OPTIONAL_FIELD = {"Grep": "path", "Glob": "path"}


def payload_fault(name: str, tool_input: Any, payload: Any, guarded: tuple[str, ...]) -> str | None:
    """Why this hook cannot decide the call it was handed, or None to decide it.

    A guard reads three things: which tool, what it names, and who is running
    it. Where one of them is missing or is not the type it has to be, the hook
    has not been handed a call it can evaluate -- and the answer to a call a
    guard cannot evaluate is no, never silence. Coercing the field to a benign
    default instead (an absent command, an empty path, an anonymous agent) is
    the shape that lets exactly the malformed call through the gate.

    Only a call of a tool in `guarded` is faulted. Every other tool is somebody
    else's to decide, and a hook that refuses a call outside its own subject
    would deny half the session over a field it never reads.
    """
    if name not in guarded:
        return None
    for field in ("cwd", "agent_type"):
        value = (payload or {}).get(field)
        if value is not None and not isinstance(value, str):
            return f"the payload carries {field} as {type(value).__name__}, not a string"
    if not isinstance(tool_input, dict):
        return f"the {name} call carries no tool_input object"
    required = REQUIRED_FIELD.get(name)
    if required is not None:
        value = tool_input.get(required)
        if not isinstance(value, str):
            return f"the {name} call carries {required} as {type(value).__name__}, not a string"
        if not value and name != "Bash":
            return f"the {name} call carries an empty {required}"
    optional = OPTIONAL_FIELD.get(name)
    if optional is not None:
        value = tool_input.get(optional)
        if value is not None and not isinstance(value, str):
            return f"the {name} call carries {optional} as {type(value).__name__}, not a string"
    return None


def undecidable(why: str) -> str:
    """The refusal a hook gives for a call it could not decide.

    Names the hook, so the denial that reaches the agent says which gate spoke
    and what it could not read, rather than arriving as an unexplained no.
    """
    hook = Path(sys.argv[0]).name or "a gauntlet hook"
    return (
        f"{hook} could not decide this call, so it refuses it: {why}. A gate that "
        "cannot read the call it was handed does not let the call through -- the "
        "malformed payload is the one that most needs deciding. Reissue the call "
        f"with the field it is missing. (hooks/{hook})"
    )


def misconfigured(fault: str) -> str:
    """The refusal a hook gives while the project's declaration is a fault.

    A lane is a configured directory, so a hook whose config will not load
    does not know where any lane is. It refuses rather than deciding against
    the kit's defaults: defaults that are not the project's are a lane in the
    wrong place, and a lane in the wrong place guards nothing.
    """
    hook = Path(sys.argv[0]).name or "a gauntlet hook"
    return (
        f"{hook} refuses this call: {fault}. The lanes are configured "
        "directories, so a gate that cannot read the declaration does not know "
        "which directory it guards, and it will not fall back on the kit's "
        "defaults and guard the wrong one. Fix the file, or write one with "
        f"`python3 scripts/init.py`. (hooks/{hook})"
    )


def is_denial(answer: str) -> bool:
    """Whether a hook's stdout is a `PreToolUse` denial."""
    try:
        parsed = json.loads(answer)
    except ValueError:
        return False
    if not isinstance(parsed, dict):
        return False
    specific = parsed.get("hookSpecificOutput")
    return isinstance(specific, dict) and specific.get("permissionDecision") == "deny"


def survives_hostile_payloads(
    hook_path: str,
    *argv: str,
    guards: tuple[str, ...] = ("Write", "Edit", "NotebookEdit", "Bash"),
    refuses_undecidable: bool = True,
) -> bool:
    """That this hook answers every `HOSTILE_PAYLOADS` shape, and answers no.

    Two failures, not one. A hook decides a tool call, so its own crash is a
    denial of whatever it was deciding: it is run the way Claude Code runs it,
    one JSON object on stdin, and must exit 0 and write either nothing or a
    parsable answer, whatever it is handed. And a hook that stays alive by
    treating every payload it cannot read as an allow has moved the defect
    rather than fixed it, so each payload whose fields this hook needs and
    cannot read must come back a denial. `guards` is the set of tools this hook
    decides; a payload naming any other tool is not its call to refuse.

    `refuses_undecidable` is false for an entry point that decides no tool call
    -- a `Stop` gate reads no payload and has no permission to withhold -- and
    there the older contract is the whole contract: stay alive, answer parsably.

    `GAUNTLET` is cleared for the run. Under `GAUNTLET=off` a hook returns at
    its first line, and every payload would pass without touching the code the
    check exists to exercise.
    """
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    for payload, tool, usable in HOSTILE_PAYLOADS:
        done = subprocess.run(
            [sys.executable, hook_path, *argv],
            input=payload,
            capture_output=True,
            text=True,
            env=environment,
            timeout=60,
            check=False,
        )
        if done.returncode != 0:
            return False
        out = done.stdout.strip()
        if out:
            try:
                json.loads(out)
            except ValueError:
                return False
        if not refuses_undecidable:
            continue
        #: a payload naming no readable tool at all is undecidable for every
        #: hook; one naming a guarded tool is undecidable when its fields are not
        if (tool is None or (tool in guards and not usable)) and not is_denial(out):
            return False
    return True
