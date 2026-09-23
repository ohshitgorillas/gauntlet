#!/usr/bin/env python3
"""The owner's off switch, in its two voices.

`GAUNTLET=off claude` starts a session with every hook in `SILENCED` and the
`Stop` gate silent: the lanes, the blind reads, the shell wrap, the blind-write
guard, the lane audit and the kit probe. The switch itself is `bypassed()` in `lane_paths.py`, read
at the top of each hook's `main()`; this file is what the switch says out loud.

One file rather than two, because both behaviours are the same one-line
question asked of the same variable, and splitting them would put two copies
of that question in the tree.

  * `--session-start`  silent when the gauntlet is on; a banner when it is off,
    naming the silenced hooks, the `Stop` gate, and the plain statement that
    nothing in `gauntlet/` is protected from any hand.
  * `--prompt`         silent when the gauntlet is on. When it is off, the
    standing notice that the chain is not running, on the session's first turn
    and every `EVERY`th turn after it. The never-propose rule is not spoken
    here. `gauntlet/CLAUDE.md` states it once in a file loaded once per session,
    and a per-turn copy is paid for again in every turn that follows it.
    The cadence is what holds that state in view thirty turns deep,
    past the point where the session-start banner has left the context window,
    and it is spaced because a line still in context is already doing its work.
    The turn is counted in a file under the system temporary directory, named
    for the session, so each session counts its own turns and the count lives
    where temporary files live. A payload carrying no readable `session_id`
    falls back to its `transcript_path`, and then to the id of the process that
    spawned the hook: each is stable across the turns of one session and
    distinct between two, which is all a count file's name has to be. Only a
    count that cannot be read or written speaks unconditionally -- a voice on
    every turn is paid for in every turn after it, so the fallback is a key and
    not a shrug.

No voice here reads a shell command. The switch belongs to the hand that
launches the session, and `CLAUDE.md` says so; no hook reads a command's text
to hold it there.

The `--self-test` sets the value it is testing explicitly for each case and
never reads the ambient variable to decide what to assert, so a developer
running it under `GAUNTLET=off` gets the same output as one running it with the
variable unset. That property is itself one of the lines it pins, and it is
`docs/testing.md` rule 16 being obeyed rather than bent.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

import lane_paths  # noqa: E402

VAR = "GAUNTLET"
OFF = "off"

#: how many turns apart the `--prompt` voice speaks. One is a voice on every
#: turn; a large number is a voice the session loses. Ten is a context window's
#: worth of turns, near enough.
EVERY = 10

#: the characters that survive into the name of a count file. A session id
#: arrives in a payload, so it is spelled into a flat name before it is a path.
_TAME = re.compile(r"[^A-Za-z0-9_-]")

#: every hook the switch silences, by the name a reader sees in the tree: each
#: one reads `bypassed()` at its entry point and says nothing when it is set
SILENCED = (
    "lanes.py",
    "no-impl-reads.py",
    "bwrap-wrap.py",
    "blind-write.py",
    "lane-audit.py",
    "kit-probe.py",
)

BANNER = (
    "GAUNTLET=off -- the chain is not running in this session.\n"
    "Silent: " + ", ".join(SILENCED) + ", and the `Stop` gate "
    "(`lanes.py --stop`), which no longer holds a turn open for an "
    "unruled red run.\n"
    "Nothing under `gauntlet/` is protected from any hand, this agent's "
    "included. A blind subagent spawned in this session is not blind: it can "
    "read the implementation and run any shell command.\n"
    "The chain is for work done under the chain. A session with the gauntlet "
    "off should not run it: an approved spec block written here was reviewed "
    "by an agent that could read the code, and it lands in a tracked file "
    "indistinguishable from one produced under the chain."
)

NOTICE = (
    "GAUNTLET=off is in force: " + ", ".join(SILENCED) + " and the `Stop` gate "
    "are silent this session -- the chain is not running. Any write into `gauntlet/` "
    "will be allowed whoever "
    "makes it, and no blind agent is blind. Artifacts produced here are not "
    "evidence of anything."
)


def off(value: str | None) -> bool:
    """Whether this value of the variable means off.

    Pure, and the switch's whole grammar: the exact value `off` after strip and
    lowercase. Unset, empty or misspelled leaves the gauntlet on, which is the
    safe direction. `lane_paths.bypassed()` is this predicate over `os.environ`; this
    one takes its value as an argument so the self-test never has to touch the
    ambient environment to assert on it.
    """
    return (value or "").strip().lower() == OFF


def session_start() -> None:
    if lane_paths.bypassed():
        print(BANNER)


def _stdin() -> str:
    """The payload on standard input, or an empty string where there is none.

    A hook that only speaks must not die reading its own input: a closed or
    absent stdin reads as no session, and `_speaks` answers that by speaking.
    """
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return ""
        return sys.stdin.read()
    except (OSError, ValueError):
        return ""


def _session(text: str) -> str:
    """The session id in a hook payload, tamed to a filename, or an empty string.

    Every shape that is not a JSON object with a string `session_id` reads as no
    session at all, which `_key` answers with a fallback name.
    """
    return _string_field(text, "session_id")


def _string_field(text: str, field: str) -> str:
    """One string field of a hook payload, tamed to a filename.

    Every shape that is not a JSON object with that field a string reads as an
    empty string.
    """
    try:
        payload = json.loads(text or "{}")
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    value = payload.get(field)
    if not isinstance(value, str):
        return ""
    return _TAME.sub("", value)[:64]


def _key(text: str) -> str:
    """The name this session's count file takes, and never an empty string.

    `session_id` where the payload carries one, its `transcript_path` where it
    does not, and the spawning process where it carries neither. A hook is a
    child of the session that runs it, so that id is stable across the turns of
    one session and distinct between two -- which is the whole of what the name
    has to be.
    """
    return _session(text) or _string_field(text, "transcript_path") or ("ppid-" + str(os.getppid()))


def _count_path(session: str) -> Path:
    return Path(tempfile.gettempdir()) / ("gauntlet-off." + session)


def _speaks(session: str, *, every: int = EVERY) -> bool:
    """Whether this turn is one the voice speaks on, and count the turn.

    True on the first turn of a session and every `every`th turn after it. A
    count file that cannot be read or written is True: a voice lost costs the
    rule it carries. The caller passes a name from `_key`, which is never empty,
    so an unnameable session no longer reads as a first turn on every turn.
    """
    if not session or every < 1:
        return True
    path = _count_path(session)
    try:
        seen = int(path.read_text())
    except (OSError, ValueError):
        seen = 0
    try:
        path.write_text(str(seen + 1))
    except OSError:
        return True
    return seen % every == 0


def prompt(stdin: str = "") -> None:
    if lane_paths.bypassed() and _speaks(_key(stdin)):
        print(NOTICE)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        import gauntlet_off_selftest

        sys.exit(gauntlet_off_selftest.self_test())
    if "--session-start" in sys.argv:
        session_start()
    elif "--prompt" in sys.argv:
        prompt(_stdin())
