#!/usr/bin/env python3
"""PostToolUse audit: the file a write changed is one the lane table admitted.

The lane hook decides a write before it happens, from the path the call names.
The mount table `bwrap-wrap.py` builds cannot be wrong about a path -- the
kernel resolves it -- but `lanes.py` compares one, and a comparison can be. A
target reaches it as a spelling: a symlink, a relative path, a `..` walk, a
name whose parent does not exist yet. `lane_paths.real_path` collapses those
onto one name, and this hook is the check on that collapse.

It runs after the tool, reads the path the harness reports as changed, and
asks `lanes._verdict` about that path. An admitted write into a lane is a
divergence between what the gate decided and what landed, and it prints one
loud named line naming the tool, the hand and the file.

It never blocks. Nothing it can say un-writes the file, and a gate that fires
here would be firing after the fact. What it buys is time: a path-identity bug
becomes a line in the next run rather than a quiet hole found weeks later,
when the lane it opened has been open the whole time.

The `GAUNTLET=off` switch silences it, like every other hook here. With the
lanes not enforcing, every write into a lane is admitted by design, and an
audit that reported each one would be reporting the switch.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

lanes = importlib.import_module("lanes")
import hook_payload  # noqa: E402
import hook_shape  # noqa: E402
import lane_paths  # noqa: E402

#: the tools this hook audits, and the field each carries its target in
TARGET_FIELD = {"Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path"}

#: where the harness reports the file it actually touched. Read before the
#: tool input, which is what the gate already saw: the point of the audit is
#: the file on disk, not the request that asked for it.
RESPONSE_KEYS = ("filePath", "file_path", "notebook_path")


def changed_path(payload: hook_payload.Payload) -> str:
    """The file the harness says this call changed, or the target it named."""
    response = payload.get("tool_response")
    if isinstance(response, dict):
        for key in RESPONSE_KEYS:
            value = response.get(key)
            if isinstance(value, str) and value:
                return value
    tool_input = payload.get("tool_input")
    return hook_shape.write_target(tool_input if isinstance(tool_input, dict) else {})


def divergence(payload: hook_payload.Payload) -> str | None:
    """The loud line this write earns, or None when the gate and the disk agree."""
    name = payload.get("tool_name")
    field = TARGET_FIELD.get(name) if isinstance(name, str) else None
    if field is None:
        return None
    target = changed_path(payload)
    if not target:
        return None
    refusal = lanes._verdict(name, {field: target}, payload)  # noqa: SLF001
    if refusal is None:
        return None
    agent = hook_payload.agent_of(payload) or "the main agent"
    real = lane_paths.real_path(target, hook_payload.cwd_of(payload))
    return (
        "GAUNTLET LANE AUDIT: a write the lane table refuses reached the disk.\n"
        f"  tool: {name}\n"
        f"  hand: {agent}\n"
        f"  named: {target}\n"
        f"  landed: {real}\n"
        f"  the table's refusal for that file: {refusal}\n"
        "  The gate admitted this call and the table refuses the file it changed, so the "
        "two disagree about one path. That is a path-identity defect in "
        "hooks/lane_paths.py -- not a policy call and not something to write around. "
        "(hooks/lane-audit.py)"
    )


def answer(payload: hook_payload.Payload) -> dict[str, Any]:
    """The hook's stdout for one divergence: the same line to the user and the agent."""
    line = divergence(payload)
    if line is None:
        return {}
    return {
        "systemMessage": line,
        "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": line},
    }


def main() -> None:
    """Read one payload, print the line if there is one, and exit 0 regardless.

    Every failure is swallowed into silence here, which is the opposite of what
    a `PreToolUse` gate owes and is right for this one: it withholds no
    permission, so there is nothing for it to refuse, and a crash that took the
    turn down would be this hook breaking the session it exists to watch.
    """
    if lane_paths.bypassed():
        return
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            return
        out = answer(payload)
    except Exception:  # noqa: BLE001 -- see the docstring: an audit never blocks
        return
    if out:
        print(out["systemMessage"], file=sys.stderr)
        print(json.dumps(out))


def self_test() -> int:  # noqa: PLR0915
    """Pin what this hook prints, what it stays quiet about, and that it never blocks."""
    lane = lanes.SPECS
    root = "/repo"

    def run(payload: dict[str, Any]) -> tuple[int, str, str]:
        environment = dict(os.environ)
        environment.pop("GAUNTLET", None)
        done = subprocess.run(
            [sys.executable, __file__],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=environment,
            timeout=60,
            check=False,
        )
        return done.returncode, done.stdout, done.stderr

    def call(named: str, landed: str | None = None, tool: str = "Edit") -> dict[str, Any]:
        field = TARGET_FIELD[tool]
        payload: dict[str, Any] = {
            "tool_name": tool,
            "tool_input": {field: named},
            "cwd": root,
        }
        if landed is not None:
            payload["tool_response"] = {"filePath": landed}
        return payload

    def loud(payload: dict[str, Any]) -> bool:
        status, out, err = run(payload)
        return status == 0 and "GAUNTLET LANE AUDIT" in err and "GAUNTLET LANE AUDIT" in out

    def quiet(payload: dict[str, Any]) -> bool:
        status, out, err = run(payload)
        return status == 0 and out.strip() == "" and err.strip() == ""

    in_lane = f"{root}/{lane}/demo.txt"
    outside = f"{root}/src/demo.py"

    lines = {
        #: the whole point: the gate let this through and the table refuses the
        #: file it changed, so the two disagree and the disagreement is printed
        "a write into a lane that reached the disk is announced": loud(call(in_lane)),
        "a write outside every lane says nothing": quiet(call(outside)),
        #: the audited path is the harness's, not the call's. A gate bug is
        #: exactly the case where those two differ
        "the file the harness reports is the file audited": (
            loud(call(outside, landed=in_lane)) and quiet(call(in_lane, landed=outside))
        ),
        "a notebook write is audited at its own field": loud(
            call(f"{root}/{lane}/demo.ipynb", tool="NotebookEdit")
        ),
        "a tool this hook does not audit is not its business": quiet(
            {"tool_name": "Read", "tool_input": {"file_path": in_lane}, "cwd": root}
        ),
        #: it reports, it never decides. A `PostToolUse` hook that answered with
        #: a permission decision would be a gate firing after the write it was
        #: supposedly holding, and this one has no answer but a line
        "it never blocks: no payload makes it deny or exit non-zero": all(
            run(payload)[0] == 0 and "permissionDecision" not in run(payload)[1]
            for payload in (
                call(in_lane),
                call(outside),
                {"tool_name": "Edit"},
                {"tool_name": "Edit", "tool_input": {"file_path": 7}},
                {},
            )
        )
        and hook_payload.survives_hostile_payloads(__file__, guards=(), refuses_undecidable=False),
        #: the switch is the owner's and it silences this hook with the rest
        "GAUNTLET=off silences it": (
            subprocess.run(
                [sys.executable, __file__],
                input=json.dumps(call(in_lane)),
                capture_output=True,
                text=True,
                env={**os.environ, "GAUNTLET": "off"},
                timeout=60,
                check=False,
            ).stdout.strip()
            == ""
        ),
    }
    return hook_shape.report(lines)


if __name__ == "__main__":
    hook_shape.entry(self_test, main)
