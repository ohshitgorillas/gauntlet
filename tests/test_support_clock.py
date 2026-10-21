"""Tests for the test-support virtual clock.

Source: the no-wall-clock design spec under docs/superpowers/specs/, the `tests/support/clock.py` module, decision 6:
`VirtualClock` is a Clock whose time moves only as the test sets it; `now` is the virtual seconds passed, from 0;
`passes` is the seconds that pass in a wait whose event has not come at its poll, None for time standing still; `wait`
calls `ready(0)` first, and when that is False and `passes` reaches `seconds`, moves `now` by `seconds` and returns False,
and otherwise returns `ready(None)`. It never hands a Ready a positive number. A still `VirtualClock()` never lets a cap
pass, so a wait on it ends on its event alone; `VirtualClock(passes=p)` with `p` at or past the cap lets the cap pass at
once, in virtual time, when the event has not come at the clock's one poll. `Clock.wait` (the `gates/core/clock.py`
module) is True when the event came before `seconds` passed on the clock, and None for `seconds` is no cap.
"""

from collections import deque
from collections.abc import Sequence

import pytest

from gates.core.clock import Clock
from tests.support.clock import VirtualClock


class _Event:
    """A Ready that answers each call from its script in order and records the seconds it was handed."""

    def __init__(self, answers: Sequence[bool]) -> None:
        self.handed: list[float | None] = []
        self._answers = deque(answers)

    def __call__(self, seconds: float | None) -> bool:
        self.handed.append(seconds)
        if not self._answers:
            raise AssertionError(f"the Ready was called past its script, with {seconds!r}")
        return self._answers.popleft()


@pytest.mark.parametrize(
    "clock",
    [
        pytest.param(VirtualClock(), id="still"),
        pytest.param(VirtualClock(passes=7.0), id="passes set"),
    ],
)
def test_a_new_clock_has_passed_no_time(clock: VirtualClock) -> None:
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
    clock = VirtualClock(passes=passes)
    ready = _Event([False])

    came = clock.wait(ready, seconds)

    assert (came, ready.handed, clock.now) == (False, [0], seconds)


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
    seconds: float | None, answer: bool
) -> None:
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
    passes: float, seconds: float | None, answer: bool
) -> None:
    clock = VirtualClock(passes=passes)
    ready = _Event([False, answer])

    came = clock.wait(ready, seconds)

    assert (came, ready.handed, clock.now) == (answer, [0, None], passes)


def test_time_moves_only_by_the_caps_that_pass_and_what_the_test_sets() -> None:
    clock = VirtualClock(passes=4.0)

    first = clock.wait(_Event([False]), 3.0)
    after_first = clock.now
    clock.now = 10.0
    second = clock.wait(_Event([False]), 4.0)
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
        pytest.param(30.0, [False], id="passes past the cap"),
    ],
)
def test_a_virtual_clock_is_a_clock_that_hands_its_ready_no_positive_number(
    passes: float | None, answers: list[bool]
) -> None:
    clock: Clock = VirtualClock(passes=passes)
    ready = _Event(answers)

    clock.wait(ready, 20.0)

    assert [seconds for seconds in ready.handed if seconds is not None and seconds > 0] == []
