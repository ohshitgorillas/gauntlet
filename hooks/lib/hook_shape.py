"""The shape a lane hook is, and the shape its self-test is.

Five hooks here guard a directory that one named agent writes. They differ in
the lane, the agent and the prose of the refusal; everything around those three
was the same text in five files, which is the arrangement where one hook gets a
fix and four keep the defect. The dispatch from a tool call to the handler for
its kind, the entry point that reads a payload and prints a denial, the
sentence a write into a lane is refused with, and the whole policy of a lane
one named agent writes live here now.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from typing import Any

from hook_payload import (
    Payload,
    Verdict,
    agent_of,
    cwd_of,
    deny,
    misconfigured,
    payload_fault,
    undecidable,
)
from lane_config import DEFAULT_DIRS, dirs
from lane_declaration import config_fault
from lane_paths import bypassed

#: tools that write a file. `NotebookEdit` names its target `notebook_path`.
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")


def write_target(tool_input: dict[str, Any] | None) -> str:
    """The path a write tool names, or the empty string for no target."""
    tool_input = tool_input or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    return target if isinstance(target, str) else ""


def dispatch(
    name: str,
    tool_input: dict[str, Any],
    payload: Payload,
    *,
    on_write: Callable[[str, str, str], str | None],
    on_read: Callable[[dict[str, Any], str, str], str | None] | None = None,
    read_tools: tuple[str, ...] = (),
) -> str | None:
    """Route one tool call to the handler for its kind; None lets it through.

    `on_write(target, cwd, agent)` is called only for a write that names a
    target, since a write with no path denies nothing. `on_read(tool_input,
    cwd, agent)` sees the whole input, because a read names its target under
    three different keys. A `Bash` call has no handler: no hook reads a shell
    command, and a lane's shell half is held by the mount table.
    """
    cwd = cwd_of(payload)
    agent = agent_of(payload)
    if name in WRITE_TOOLS:
        target = write_target(tool_input)
        return on_write(target, cwd, agent) if target else None
    if on_read is not None and name in read_tools:
        return on_read(tool_input, cwd, agent)
    return None


def read_payload(guards: tuple[str, ...]) -> tuple[Payload | None, str | None]:
    """One payload from stdin as `(payload, refusal)`; exactly one is not None.

    Every way the payload can fail to be a call this hook can decide ends in a
    refusal, never in silence. The three the old entry point swallowed -- stdin
    that will not read, text that is not JSON, JSON that is not an object --
    are each a case where the hook has no idea what it was asked to decide, and
    no idea is not consent.
    """
    try:
        raw = sys.stdin.read()
    except OSError as exc:
        return None, undecidable(f"its payload could not be read from stdin ({exc})")
    try:
        data = json.loads(raw)
    except ValueError:
        return None, undecidable("its payload is not JSON")
    if not isinstance(data, dict):
        return None, undecidable("its payload is not a JSON object")
    if not isinstance(data.get("tool_name", ""), str):
        return None, undecidable("its payload carries tool_name as something other than a string")
    fault = payload_fault(data.get("tool_name", ""), data.get("tool_input"), data, guards)
    return (None, undecidable(fault)) if fault is not None else (data, None)


def hook_main(verdict: Verdict, *, guards: tuple[str, ...] = WRITE_TOOLS + ("Bash",)) -> None:
    """Read one payload from stdin and print a denial if `verdict` names one.

    `guards` is the set of tools this hook decides, and it is what makes a
    malformed payload refusable: a call of a tool outside the set is not this
    hook's to refuse however broken it is.

    A `verdict` that raises is a denial too. It is the same failure as a
    payload that will not parse -- the hook does not know whether the call is
    allowed -- and the same answer follows, with the exception named in it so
    the defect is visible rather than absorbed. `except Exception` is wide on
    purpose: what is caught is not a known-harmless class but every way this
    hook can fail, and none of them ends in the call being run.

    The switch is read here and nowhere else: a self-test calls `verdict`
    directly, so a bypass reachable from inside it would make every self-test
    pass vacuously under `GAUNTLET=off`.
    """
    if bypassed():
        return  # GAUNTLET=off: the owner's switch, read at the entry point only
    data, refusal = read_payload(guards)
    if refusal is not None or data is None:
        print(deny(refusal or undecidable("its payload named no call")))
        return
    fault = config_fault()
    if fault is not None:
        print(deny(misconfigured(fault)))
        return
    try:
        reason = verdict(data.get("tool_name", ""), data.get("tool_input") or {}, data)
    except Exception as exc:  # noqa: BLE001 -- see the docstring: a crash is a denial
        print(deny(undecidable(f"deciding it raised {type(exc).__name__}: {exc}")))
        return
    if reason is not None:
        print(deny(reason))


def answer_main(
    answer_of: Callable[[Payload], dict[str, Any] | None],
    *,
    guards: tuple[str, ...] = ("Bash",),
) -> None:
    """`hook_main` for a hook whose answer is not a denial.

    `bwrap-wrap.py` rewrites the command rather than refusing it, so its answer
    is a whole `hookSpecificOutput` object. Every failure path is the same as
    `hook_main`'s and ends the same way: a hook that cannot build the sandbox a
    command was going to run inside refuses the command, because the fallback
    it would otherwise take is running that command unsandboxed.
    """
    if bypassed():
        return  # GAUNTLET=off: the owner's switch, read at the entry point only
    data, refusal = read_payload(guards)
    if refusal is not None or data is None:
        print(deny(refusal or undecidable("its payload named no call")))
        return
    fault = config_fault()
    if fault is not None:
        print(deny(misconfigured(fault)))
        return
    try:
        answer = answer_of(data)
    except Exception as exc:  # noqa: BLE001 -- see `hook_main`: a crash is a denial
        print(deny(undecidable(f"answering it raised {type(exc).__name__}: {exc}")))
        return
    if answer is not None:
        print(json.dumps(answer))


def entry(self_test_fn: Callable[[], int], main_fn: Callable[[], None]) -> None:
    """The `__main__` of a hook with one gate mode and one wire mode."""
    sys.exit(self_test_fn()) if "--self-test" in sys.argv else main_fn()


# --- the shape a self-test is ------------------------------------------------


def denied(verdict: str | None) -> bool:
    """That a verdict refused the call: a refusal is its own reason."""
    return isinstance(verdict, str)


def allowed(verdict: str | None) -> bool:
    """That a verdict let the call through."""
    return verdict is None


def probe(
    verdict: Verdict,
    root: str,
    tool: str,
    key: str = "file_path",
    *,
    agent: str | None = None,
) -> Callable[..., str | None]:
    """A closure that calls `verdict` for one tool the way the wire does.

    `key` is the field that tool carries its target in. `agent` is the default
    `agent_type` the closure sends, overridden per call; `None` is the main
    agent, whose payload carries no such key at all.
    """

    def call(value: Any, who: str | None = agent) -> str | None:
        payload: Payload = {"cwd": root}
        if who is not None:
            payload["agent_type"] = who
        return verdict(tool, {key: value}, payload)

    return call


#: one of the three default directory names as a whole path segment, for
#: `rebased`. The bounds are not `\b`: a name is a segment when nothing joins it
#: on either side, and `\b` would take the `gauntlet` of `arbiter` and
#: rename the agent. A trailing `/` is left to the text, so `find tests -delete`
#: and `cd tests && rm t.py` -- a lane named with no slash at all -- respell too.
_DEFAULT_SEGMENT = re.compile(
    r"(?<![\w.-])(" + "|".join(sorted(set(DEFAULT_DIRS.values()))) + r")(?![\w.-])"
)


def respell(target: str) -> str:
    """One self-test path or command, at the configured directories.

    Exactly one pass, and never applied twice to the same string: the three
    names are disjoint from each other but a configured name may still contain
    a default one as a segment -- `gauntlet_dir` of `work/tests` is a legal set
    beside `tests_dir` -- and a second pass would rewrite what the first wrote.
    """
    by_default = dict(zip(DEFAULT_DIRS.values(), dirs().values(), strict=True))
    if all(default == configured for default, configured in by_default.items()):
        return target
    return _DEFAULT_SEGMENT.sub(lambda m: by_default[m.group(1)], target)


def rebased(one_probe: Callable[..., str | None]) -> Callable[..., str | None]:
    """A probe that respells the kit's default directories at the configured ones.

    Every self-test writes its paths at `tests/`, `docs/` and `gauntlet/`, which
    is what the kit ships and what the prose around each line says. Under a
    project that moved one of them those literals name nothing any hook guards,
    so the lines would pass by naming paths outside the lane and prove nothing.
    Rewriting the segment here means one set of lines holds at any base, and the
    lane each line is about is the lane the hook actually resolved.

    One pass, not three: with `tests_dir` at `docs` and `docs_dir` elsewhere,
    replacing one name after another would rewrite what the previous pass had
    just written. The names are disjoint, so a single alternation is exact.
    """

    def at_configured_dirs(target: str, *rest: Any) -> str | None:
        return one_probe(respell(target), *rest)

    return at_configured_dirs


def probes(
    verdict: Verdict, root: str = "/repo", *, agent: str | None = None
) -> tuple[Callable[..., str | None], Callable[..., str | None]]:
    """The `(write, bash)` pair every lane self-test drives its lane through."""
    return (
        rebased(probe(verdict, root, "Edit", agent=agent)),
        rebased(probe(verdict, root, "Bash", "command", agent=agent)),
    )


def report(lines: dict[str, bool]) -> int:
    """Print one PASS or FAIL per spec line; 0 if every line held."""
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1
