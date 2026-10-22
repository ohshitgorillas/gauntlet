# Copyright 2026 oh shit, gorillas!
"""Red tests for `tests/support/fake.py`: FakeRunner, a Runner that gives back canned replies, and `completed`, a reply builder.

Source: the gates core design spec under docs/superpowers/specs/, section 3, "Tests", the `fake.py` bullet:
"`FakeRunner(replies: Sequence[Completed])` returns canned replies in order and appends each Command to the public
`commands: list[Command]`; a call with no reply left raises AssertionError naming the Command's argv.
`completed(status=0, stdout="", stderr="", outputs={}, *, timed_out=False) -> Completed` builds a reply." Section 1,
"checker.py", gives `Completed(status, stdout, stderr, timed_out, outputs)` and `type Runner = Callable[[Command],
Completed]`.

How the AssertionError spells the argv the documents do not say, so each exhaustion test gives a one-word argv and
claims only that the word appears in the message. That `timed_out` is keyword-only is held by the signature itself and
is not claimed here: a call that passes it by position is a type error in the test, not a red test.
"""

import re
from pathlib import Path

import pytest

from gates.core.checker import Command, Completed, Runner
from tests.support.fake import FakeRunner, completed

CWD = Path("work")

FIRST = Command(argv=("lint", "a.py"), cwd=CWD)

SECOND = Command(
    argv=("types", "b.py"),
    cwd=CWD,
    env={"PATH": "/opt/checker/bin"},
    timeout=90.0,
    throttled=True,
    outputs={"record": Path("record.json")},
    capture=False,
    pass_fds=(7,),
)

LEFTOVER = "leftover-checker-4c1e"

OUTPUTS: dict[str, str | None] = {"junit": "<testsuites/>", "record": None}

LATE = Completed(
    status=4, stdout="third", stderr="late warning", timed_out=True, outputs=OUTPUTS
)


def _reply(status: int, stdout: str) -> Completed:
    return Completed(
        status=status, stdout=stdout, stderr="warned", timed_out=False, outputs={}
    )


def _fields(reply: Completed) -> tuple[int, str, str, bool, dict[str, str | None]]:
    return (
        reply.status,
        reply.stdout,
        reply.stderr,
        reply.timed_out,
        dict(reply.outputs),
    )


def test_in_order() -> None:
    """Each call gives back the next canned reply whole, every field as seeded, in the order the replies were given."""
    runner: Runner = FakeRunner([_reply(3, "first"), _reply(5, "second"), LATE])
    replies = [runner(FIRST), runner(SECOND), runner(FIRST)]
    assert [_fields(reply) for reply in replies] == [
        _fields(_reply(3, "first")),
        _fields(_reply(5, "second")),
        (4, "third", "late warning", True, OUTPUTS),
    ]


def test_commands() -> None:
    """Each call appends the Command it was called with, every field as given, to the public `commands` list."""
    runner = FakeRunner([_reply(0, "first"), _reply(1, "second")])
    runner(FIRST)
    runner(SECOND)
    assert runner.commands == [Command(argv=("lint", "a.py"), cwd=CWD), SECOND]


def test_no_replies() -> None:
    """A FakeRunner given no reply raises AssertionError naming the argv of the Command it was called with."""
    runner = FakeRunner([])
    with pytest.raises(AssertionError, match=re.escape(LEFTOVER)):
        runner(Command(argv=(LEFTOVER,), cwd=CWD))


def test_exhausted() -> None:
    """Once its replies are spent, the next call raises AssertionError naming that call's argv."""
    runner = FakeRunner([_reply(0, "first")])
    runner(FIRST)
    with pytest.raises(AssertionError, match=re.escape(LEFTOVER)):
        runner(Command(argv=(LEFTOVER,), cwd=CWD))


def test_defaults() -> None:
    """`completed()` is status 0, empty stdout and stderr, no outputs, not timed out."""
    expected = Completed(status=0, stdout="", stderr="", timed_out=False, outputs={})
    assert _fields(completed()) == _fields(expected)


def test_positional() -> None:
    """`completed` takes status, stdout, stderr and outputs by position, in that order, each set as given."""
    assert _fields(completed(3, "out", "err", OUTPUTS)) == (
        3,
        "out",
        "err",
        False,
        OUTPUTS,
    )


def test_timed_out() -> None:
    """`completed(timed_out=True)` gives a timed-out reply and keeps every other default."""
    assert _fields(completed(timed_out=True)) == (0, "", "", True, {})
