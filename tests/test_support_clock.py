# Copyright 2026 oh shit, gorillas!
"""Tests for the test-support virtual clock.

Source: tests/support/clock.py: `VirtualClock` is a Clock whose time moves only as the test sets it; `now` is the virtual
seconds passed, from 0; `passes` is the seconds that pass in a wait whose event has not come at its poll, None for time
standing still; `after` blocks, with no timeout, until the event the test proves against has come, None for nothing to
wait for. `wait` calls `ready(0)` first; when that is False and `passes` reaches `seconds`, it calls `after()`, then
`ready(0)` again, and when that is still False, moves `now` by `seconds` and returns False; otherwise it returns
`ready(None)`. It never hands a Ready a positive number. A still `VirtualClock()` never lets a cap pass, so a wait on it
ends on its event alone; `VirtualClock(passes=p)` with `p` at or past the cap lets the cap pass at once, in virtual
time, when the event has not come at the clock's first poll, and `after` holds that moment back until an event of the
test's own has come. `Clock.wait` (the `gates/core/clock.py` module) is True when the event came before `seconds`
passed on the clock, and None for `seconds` is no cap.
"""

from collections import deque
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import pytest

from tests.support.clock import VirtualClock

if TYPE_CHECKING:
    from gates.core.clock import Clock


class _Event:
    """A Ready that answers each call from its script in order and records the seconds it was handed."""

    def __init__(
        self, answers: Sequence[bool], log: list[tuple[str, float | None]] | None = None
    ) -> None:
        self.handed: list[float | None] = []
        self._answers = deque(answers)
        self._log = log

    def __call__(self, seconds: float | None) -> bool:
        self.handed.append(seconds)
        if self._log is not None:
            self._log.append(("ready", seconds))
        if not self._answers:
            message = f"the Ready was called past its script, with {seconds!r}"
            raise AssertionError(message)
        return self._answers.popleft()


@pytest.mark.parametrize(
    "clock",
    [
        pytest.param(VirtualClock(), id="still"),
        pytest.param(VirtualClock(passes=7.0), id="passes set"),
    ],
)
def test_a_new_clock_has_passed_no_time(clock: VirtualClock) -> None:
    """Verify a new clock has passed no time."""
    assert clock.now == 0


@pytest.mark.parametrize(
    ("passes", "seconds"),
    [
        pytest.param(None, 5.0, id="still, a cap"),
        pytest.param(None, None, id="still, no cap"),
        pytest.param(2.0, 5.0, id="passes below the cap"),
        pytest.param(5.0, 5.0, id="passes at the cap"),
        pytest.param(9.0, 5.0, id="passes past the cap"),
        pytest.param(2.0, None, id="passes set, no cap"),
    ],
)
def test_an_event_come_at_the_poll_ends_the_wait_true_with_no_time_passed(
    passes: float | None, seconds: float | None
) -> None:
    """Verify an event come at the poll ends the wait true with no time passed."""
    clock = VirtualClock(passes=passes)
    ready = _Event([True])

    came = clock.wait(ready, seconds)

    assert (came, ready.handed, clock.now) == (True, [0], 0)


@pytest.mark.parametrize(
    ("passes", "seconds"),
    [
        pytest.param(3.0, 3.0, id="passes at the cap"),
        pytest.param(10.0, 3.0, id="passes past the cap"),
        pytest.param(0.0, 0.0, id="a zero cap and zero passing"),
    ],
)
def test_passes_at_or_past_the_cap_lets_the_cap_pass_at_once_when_the_event_has_not_come(
    passes: float, seconds: float
) -> None:
    """Verify passes at or past the cap lets the cap pass at once when the event has not come."""
    clock = VirtualClock(passes=passes)
    ready = _Event([False, False])

    came = clock.wait(ready, seconds)

    assert (came, ready.handed, clock.now) == (False, [0, 0], seconds)


@pytest.mark.parametrize(
    ("passes", "seconds"),
    [
        pytest.param(3.0, 3.0, id="passes at the cap"),
        pytest.param(10.0, 3.0, id="passes past the cap"),
    ],
)
def test_after_runs_between_the_first_poll_and_a_second_and_before_the_cap_passes(
    passes: float, seconds: float
) -> None:
    """Verify after runs between the first poll and a second and before the cap passes."""
    log: list[tuple[str, float | None]] = []
    ready = _Event([False, False], log)
    clock = VirtualClock(passes=passes, after=lambda: log.append(("after", clock.now)))

    came = clock.wait(ready, seconds)

    assert (came, log, clock.now) == (
        False,
        [("ready", 0), ("after", 0), ("ready", 0)],
        seconds,
    )


@pytest.mark.parametrize(
    "after",
    [
        pytest.param(None, id="nothing to wait for"),
        pytest.param(lambda: b"seen\n", id="an after"),
    ],
)
def test_an_event_come_at_the_second_poll_ends_the_wait_true_with_no_time_passed(
    after: Callable[[], object] | None,
) -> None:
    """Verify an event come at the second poll ends the wait true with no time passed."""
    clock = VirtualClock(passes=5.0, after=after)
    ready = _Event([False, True])

    came = clock.wait(ready, 5.0)

    assert (came, ready.handed, clock.now) == (True, [0, 0], 0)


@pytest.mark.parametrize(
    ("passes", "seconds", "answers", "handed"),
    [
        pytest.param(5.0, 5.0, [True], [0], id="the event at the first poll"),
        pytest.param(None, 5.0, [False, True], [0, None], id="still"),
        pytest.param(2.0, 5.0, [False, True], [0, None], id="passes short of the cap"),
        pytest.param(2.0, None, [False, True], [0, None], id="no cap"),
    ],
)
def test_after_is_not_called_when_the_cap_is_not_about_to_pass(
    passes: float | None,
    seconds: float | None,
    answers: list[bool],
    handed: list[float | None],
) -> None:
    """Verify after is not called when the cap is not about to pass."""
    calls: list[str] = []
    clock = VirtualClock(passes=passes, after=lambda: calls.append("after"))
    ready = _Event(answers)

    clock.wait(ready, seconds)

    assert (calls, ready.handed) == ([], handed)


@pytest.mark.parametrize(
    "seconds",
    [
        pytest.param(0.0, id="a zero cap"),
        pytest.param(5.0, id="a positive cap"),
        pytest.param(None, id="no cap"),
    ],
)
@pytest.mark.parametrize("answer", [True, False])
def test_a_still_clock_never_lets_a_cap_pass_and_ends_the_wait_on_the_event_alone(
    seconds: float | None, *, answer: bool
) -> None:
    """Verify a still clock never lets a cap pass and ends the wait on the event alone."""
    clock = VirtualClock()
    ready = _Event([False, answer])

    came = clock.wait(ready, seconds)

    assert (came, ready.handed, clock.now) == (answer, [0, None], 0)


@pytest.mark.parametrize(
    ("passes", "seconds"),
    [
        pytest.param(2.0, 5.0, id="passes below the cap"),
        pytest.param(2.0, None, id="no cap"),
    ],
)
@pytest.mark.parametrize("answer", [True, False])
def test_passes_short_of_the_cap_passes_its_seconds_and_ends_the_wait_on_the_event(
    passes: float, seconds: float | None, *, answer: bool
) -> None:
    """Verify passes short of the cap passes its seconds and ends the wait on the event."""
    clock = VirtualClock(passes=passes)
    ready = _Event([False, answer])

    came = clock.wait(ready, seconds)

    assert (came, ready.handed, clock.now) == (answer, [0, None], passes)


def test_time_moves_only_by_the_caps_that_pass_and_what_the_test_sets() -> None:
    """Verify time moves only by the caps that pass and what the test sets."""
    clock = VirtualClock(passes=4.0)

    first = clock.wait(_Event([False, False]), 3.0)
    after_first = clock.now
    clock.now = 10.0
    second = clock.wait(_Event([False, False]), 4.0)
    after_second = clock.now
    third = clock.wait(_Event([True]), 1.0)

    assert (first, after_first, second, after_second, third, clock.now) == (
        False,
        3.0,
        False,
        14.0,
        True,
        14.0,
    )


@pytest.mark.parametrize(
    ("passes", "answers"),
    [
        pytest.param(None, [True], id="still, the event at the poll"),
        pytest.param(None, [False, True], id="still, the event later"),
        pytest.param(1.0, [True], id="passes set, the event at the poll"),
        pytest.param(1.0, [False, True], id="passes below the cap, the event later"),
        pytest.param(30.0, [False, False], id="passes past the cap"),
    ],
)
def test_a_virtual_clock_is_a_clock_that_hands_its_ready_no_positive_number(
    passes: float | None, answers: list[bool]
) -> None:
    """Verify a virtual clock is a clock that hands its ready no positive number."""
    clock: Clock = VirtualClock(passes=passes)
    ready = _Event(answers)

    clock.wait(ready, 20.0)

    assert [
        seconds for seconds in ready.handed if seconds is not None and seconds > 0
    ] == []
