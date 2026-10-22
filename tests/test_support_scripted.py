# Copyright 2026 oh shit, gorillas!
"""The event paced Runner specified by the no-wall-clock design's Scripted stubs."""

import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import override

import pytest

from gates.core.checker import Command, Completed, run_all
from tests.support.fake import completed
from tests.support.scripted import ReleasedError, Scripted, Step, last_argument


def _command(tmp_path: Path, name: str) -> Command:
    return Command(argv=(name, "last"), cwd=tmp_path)


class NotedCalls(list[str]):
    """Expose the event that the Runner has recorded a call."""

    def __init__(self) -> None:
        """Initialize the seeded state."""
        super().__init__()
        self.entered = threading.Event()

    @override
    def append(self, name: str) -> None:
        super().append(name)
        self.entered.set()


# Returning the first argv word instead would choose a different step.
def test_last_argument(tmp_path: Path) -> None:
    """Verify last argument."""
    assert last_argument(_command(tmp_path, "first")) == "last"


# Reconstructing the reply would lose its identity.
def test_reply_identity_and_records(tmp_path: Path) -> None:
    """Verify reply identity and records."""
    reply = completed()
    process = Scripted({"last": Step(reply)})

    result = run_all(
        process, [_command(tmp_path, "first")], 1, next_done=process.next_done
    )

    assert result[0] is reply
    assert (process.called, process.finished, process.peak) == (["last"], ["last"], 1)


# Ignoring a supplied key would fail to find this first-argument step.
def test_custom_key(tmp_path: Path) -> None:
    """Verify custom key."""
    reply = completed(1, "chosen\n")
    process = Scripted({"first": Step(reply)}, key=lambda command: command.argv[0])

    result = run_all(
        process, [_command(tmp_path, "first")], 1, next_done=process.next_done
    )

    assert result == [reply]
    assert process.called == ["first"]


# Releasing each call as it starts would permit a peak below the whole batch.
def test_all_started_calls_overlap(tmp_path: Path) -> None:
    """Verify all started calls overlap."""
    names = ("a", "b", "c", "d")
    process = Scripted(
        {name: Step(completed()) for name in names}, key=lambda command: command.argv[0]
    )

    result = run_all(
        process,
        [_command(tmp_path, name) for name in names],
        4,
        next_done=process.next_done,
    )

    assert (len(result), process.peak) == (4, 4)
    assert sorted(process.called) == list(names)
    assert sorted(process.finished) == list(names)


# Dropping an after dependency would allow a to finish before b or c.
def test_after_waits_for_every_named_call(tmp_path: Path) -> None:
    """Verify after waits for every named call."""
    replies = [completed(0, name) for name in "abc"]
    process = Scripted(
        {
            "a": Step(replies[0], after=("c", "b")),
            "b": Step(replies[1], after=("b-go",)),
            "c": Step(replies[2], after=("c-go",)),
            "b-go": Step(completed()),
            "c-go": Step(completed()),
        },
        key=lambda command: command.argv[0],
    )
    sentinel: Future[Completed] = Future()
    sentinel.set_result(completed())
    with ThreadPoolExecutor(max_workers=5) as pool:
        a, b, c = [pool.submit(process, _command(tmp_path, name)) for name in "abc"]
        try:
            process.next_done([a, b, c, sentinel])
            process.waiting["a"].wait()
            process.waiting["a"].clear()

            c_go = pool.submit(process, _command(tmp_path, "c-go"))
            process.next_done([a, b, c, c_go, sentinel])
            c.result()
            process.waiting["a"].wait()
            assert "a" not in process.finished

            b_go = pool.submit(process, _command(tmp_path, "b-go"))
            process.next_done([a, b, c, c_go, b_go, sentinel])
            result = [a.result(), b.result(), c.result()]
        finally:
            process.close()

    assert result == replies
    assert [name for name in process.finished if name in ("a", "b", "c")] == [
        "c",
        "b",
        "a",
    ]


# Treating an exception as a return value would leave this future successful.
def test_exception_is_raised_and_finishes(tmp_path: Path) -> None:
    """Verify exception is raised and finishes."""
    error = ValueError("reply")
    process = Scripted({"last": Step(error)})

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(process, _command(tmp_path, "first"))
            try:
                done = process.next_done([future])
                assert done == {future}
                assert future.exception() is error
            finally:
                process.close()
    finally:
        process.close()

    assert process.finished == ["last"]


# Closing only existing calls would let a later call wait forever.
def test_close_rejects_later_calls(tmp_path: Path) -> None:
    """Verify close rejects later calls."""
    process = Scripted({"last": Step(completed())})
    process.close()
    process.close()

    with pytest.raises(ReleasedError) as caught:
        process(_command(tmp_path, "first"))

    assert caught.value.name == "last"
    assert (process.called, process.finished, process.peak) == ([], [], 0)


# Failing to wake held calls on close would leave the worker blocked.
def test_close_releases_held_call(tmp_path: Path) -> None:
    """Verify close releases held call."""
    calls = NotedCalls()
    process = Scripted({"last": Step(completed())})
    process.called = calls
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(process, _command(tmp_path, "first"))
        try:
            calls.entered.wait()
        finally:
            process.close()
        with pytest.raises(ReleasedError) as caught:
            future.result()

    assert caught.value.name == "last"


# Delegating a closed helper's next_done to its barrier would wait on a nonexistent call.
def test_closed_next_done_only_waits_for_futures() -> None:
    """Verify closed next done only waits for futures."""
    process = Scripted({})
    process.close()
    future: Future[Completed] = Future()
    future.set_result(completed())

    assert process.next_done([future]) == {future}


# Counting finished futures as unstarted calls would leave this wait blocked.
def test_next_done_accepts_already_done_future() -> None:
    """Verify next done accepts already done future."""
    process = Scripted({})
    future: Future[Completed] = Future()
    future.set_result(completed())

    try:
        assert process.next_done([future]) == {future}
    finally:
        process.close()


class RegisteredFuture(Future[Completed]):
    """Expose the event that a worker wait has registered this future."""

    def __init__(self, error: BaseException | None = None) -> None:
        """Initialize the seeded state."""
        super().__init__()
        self.registered = threading.Event()
        self.error = error

    @override
    def add_done_callback(self, fn: Callable[[Future[Completed]], object]) -> None:
        if self.error is not None:
            raise self.error
        super().add_done_callback(fn)
        self.registered.set()


# Failing to notify next_done on close would leave its barrier blocked.
def test_close_releases_blocked_next_done() -> None:
    """Verify close releases blocked next done."""
    process = Scripted({})
    future = RegisteredFuture()
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiter = pool.submit(process.next_done, [future])
        try:
            future.registered.wait()
        finally:
            process.close()
        with pytest.raises(ReleasedError) as caught:
            waiter.result()

    assert caught.value.name == "next_done"


# Swallowing a worker-wait exception or leaving workers held would violate cleanup.
def test_wait_exception_closes_before_reraising(tmp_path: Path) -> None:
    """Verify wait exception closes before reraising."""
    error = KeyboardInterrupt("worker wait")
    calls = NotedCalls()
    process = Scripted({"last": Step(completed(), after=("never",))})
    process.called = calls
    interrupted = RegisteredFuture(error)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(process, _command(tmp_path, "first"))
        try:
            calls.entered.wait()
            with pytest.raises(KeyboardInterrupt) as caught:
                process.next_done([future, interrupted])
            assert caught.value is error
            with pytest.raises(ReleasedError) as released:
                future.result()
            assert released.value.name == "last"
        finally:
            process.close()

    with pytest.raises(ReleasedError):
        process(_command(tmp_path, "first"))
