# Copyright 2026 oh shit, gorillas!
"""Red tests for `SystemClock.wait` handing its `Ready` the seconds it is given and returning the `Ready`'s answer.

Source: gates/core/clock.py:
`SystemClock` is "real time, the only real time in gates/: hands `seconds` to ready as they are", and "Every other
behaviour of `SystemClock`, the `seconds` it hands `ready` and the answer it returns, is proven in
`tests/test_core_clock.py` through a `Ready` the test hands in, with no real time". A `Ready` is "the
caller's own wait on an event, for up to the seconds given (None: without end); True when the event came", and a
clock's `wait` is "True when the event came before `seconds` passed on this clock; None: no cap".

So the `Ready` each test hands in waits on nothing: it keeps what it is handed and gives a set answer. `SystemClock.wait`
hands it the seconds it was given, once and as they are, a number or None, and returns the one answer it gives. Every
cap is handed as the `seconds` keyword, the form the spec reads as a `Clock`'s cap.
"""

from gates.core.clock import SystemClock


class _Kept:
    """A `Ready` that waits on nothing: it keeps each `seconds` it is handed and gives `answer`."""

    def __init__(self, *, answer: bool) -> None:
        self.answer = answer
        self.handed: list[float | None] = []

    def __call__(self, seconds: float | None) -> bool:
        self.handed.append(seconds)
        return self.answer


def test_hands_ready_a_positive_cap_as_given() -> None:
    """Breaks when `wait` hands `ready` anything but the cap it was given (0, None, a share of it) or hands it twice."""
    ready = _Kept(answer=True)
    SystemClock().wait(ready, seconds=2.5)
    assert ready.handed == [2.5]


def test_hands_ready_each_cap_it_is_given() -> None:
    """Breaks when `wait` hands `ready` a cap of its own, or the first cap it was ever given, in place of this call's."""
    clock = SystemClock()
    ready = _Kept(answer=True)
    clock.wait(ready, seconds=0.25)
    clock.wait(ready, seconds=7.0)
    assert ready.handed == [0.25, 7.0]


def test_hands_ready_a_zero_cap_as_given() -> None:
    """Breaks when `wait` reads a zero cap as no cap and hands `ready` None, or hands it anything else."""
    ready = _Kept(answer=False)
    SystemClock().wait(ready, seconds=0.0)
    assert ready.handed == [0.0]


def test_hands_ready_none_when_given_no_cap() -> None:
    """Breaks when `wait` turns no cap into a number of its own, such as 0 or a default cap, before handing it on."""
    ready = _Kept(answer=True)
    SystemClock().wait(ready, seconds=None)
    assert ready.handed == [None]


def test_returns_true_when_ready_answers_true() -> None:
    """Breaks when `wait` returns False or anything but the `Ready`'s True, such as None, whatever `ready` answers."""
    ready = _Kept(answer=True)
    assert SystemClock().wait(ready, seconds=2.5) is True


def test_returns_false_when_ready_answers_false() -> None:
    """Breaks when `wait` returns True or anything but the `Ready`'s False, such as None, whatever `ready` answers."""
    ready = _Kept(answer=False)
    assert SystemClock().wait(ready, seconds=2.5) is False


def test_returns_false_when_ready_answers_false_with_no_cap() -> None:
    """Breaks when `wait` with no cap returns True without asking `ready`, reading no cap as an event that must come."""
    ready = _Kept(answer=False)
    assert SystemClock().wait(ready, seconds=None) is False
