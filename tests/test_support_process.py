# Copyright 2026 oh shit, gorillas!
"""M2 Order step 5: literal product process replies, call history and exhaustion."""

from pathlib import Path
from types import MappingProxyType

import pytest

from gauntlet.core.errors import ProcessError
from gauntlet.seams.process import Command, Completed
from tests.support.process import FakeRunner, RepliesExhaustedError, completed

_FIRST = Command(("git", "status"), Path("/literal/repo"))
_SECOND = Command(("podman", "inspect", "role-7"), Path("/literal/job"), timeout=4.5)
_THIRD = Command(("podman", "rm", "proxy-7"), Path("/literal/job"), capture=False)
_ONE = Completed(
    0, "first out", "first err", timed_out=False, outputs=MappingProxyType({})
)
_TWO = Completed(125, "", "no such container", timed_out=True, outputs={"report": None})
_THREE = Completed(3, "third", "", timed_out=False, outputs={"result": "written text"})


# Reordering replies, copying or rebuilding a reply, or reusing one reply fails.
def test_runner_returns_seeded_replies_unchanged_in_call_order() -> None:
    """Each call returns the very next seeded literal, untouched."""
    runner = FakeRunner([_ONE, _TWO, _THREE])
    replies = (runner(_THIRD), runner(_FIRST), runner(_FIRST))
    assert (
        replies[0] is _ONE,
        replies[1] is _TWO,
        replies[2] is _THREE,
        replies,
    ) == (True, True, True, (_ONE, _TWO, _THREE))


# Returning a synthesized Completed for a seeded error, or raising a new error, fails.
def test_seeded_process_error_is_raised_for_its_call() -> None:
    """A seeded ProcessError is the reply for its own call; later replies follow."""
    error = ProcessError("podman secret create", 125, "literal failure")
    runner = FakeRunner([_ONE, error, _TWO])
    first = runner(_FIRST)
    with pytest.raises(ProcessError) as raised:
        runner(_SECOND)
    third = runner(_THIRD)
    assert (first is _ONE, raised.value is error, third is _TWO) == (True, True, True)


# Dropping, reordering or copying recorded Commands, or skipping an erroring call, fails.
def test_runner_retains_typed_call_history() -> None:
    """The runner's commands hold every Command received, in call order, as the same objects."""
    error = ProcessError("git worktree add", None, "start failed")
    runner = FakeRunner([_ONE, error, _TWO])
    runner(_SECOND)
    with pytest.raises(ProcessError):
        runner(_FIRST)
    runner(_SECOND)
    assert (
        runner.commands,
        [
            command is expected
            for command, expected in zip(
                runner.commands, (_SECOND, _FIRST, _SECOND), strict=True
            )
        ],
    ) == ([_SECOND, _FIRST, _SECOND], [True, True, True])


# Losing either constructor value, or making the error not an Exception, fails.
def test_exhaustion_error_keeps_collaborator_and_count() -> None:
    """RepliesExhaustedError carries its collaborator identity and attempted-call count."""
    error = RepliesExhaustedError("literal-collaborator", 4)
    assert (error.collaborator, error.count, isinstance(error, Exception)) == (
        "literal-collaborator",
        4,
        True,
    )


# Synthesizing a reply on exhaustion, or counting replies instead of attempted calls, fails.
def test_exhaustion_raises_with_attempted_call_count() -> None:
    """Calls past the seeded replies raise typed exhaustion counting every attempt."""
    runner = FakeRunner([_ONE, _TWO])
    runner(_FIRST)
    runner(_SECOND)
    with pytest.raises(RepliesExhaustedError) as first:
        runner(_THIRD)
    with pytest.raises(RepliesExhaustedError) as second:
        runner(_FIRST)
    assert (
        first.value.count,
        second.value.count,
        first.value.collaborator == second.value.collaborator,
        bool(first.value.collaborator),
    ) == (3, 4, True, True)


# An unseeded runner that returns anything or counts from zero fails.
def test_empty_runner_exhausts_on_first_call() -> None:
    """With no replies, the first call is the first attempted call."""
    runner = FakeRunner([])
    with pytest.raises(RepliesExhaustedError) as raised:
        runner(_FIRST)
    assert raised.value.count == 1


# Dropping, defaulting or swapping any supplied field fails.
def test_completed_carries_its_literal_fields() -> None:
    """completed() builds a Completed from exactly the supplied values."""
    outputs = {"report": "text", "missing": None}
    built = completed(7, "literal out", "literal err", timed_out=True, outputs=outputs)
    assert (built, built.outputs) == (
        Completed(7, "literal out", "literal err", timed_out=True, outputs=outputs),
        {"report": "text", "missing": None},
    )


# Non-zero, non-empty or timed-out defaults, or default outputs with entries, fail.
def test_completed_defaults_are_a_clean_success() -> None:
    """completed() with no arguments is status 0, empty streams, no timeout, no outputs."""
    built = completed()
    assert (
        built.status,
        built.stdout,
        built.stderr,
        built.timed_out,
        dict(built.outputs),
    ) == (
        0,
        "",
        "",
        False,
        {},
    )
