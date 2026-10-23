# Copyright 2026 oh shit, gorillas!
"""The one test in `tests/` that waits on real time: `SystemClock` says time's up when no event comes within its cap.

Source: gates/core/clock.py and tests/support/clock.py: kept on its own, the one test in this file hands `SYSTEM.wait`
`threading.Event().wait` uncalled as its `Ready`, an event nothing sets, and a cap of a few hundredths of a second as
the `seconds` keyword, and checks that it says time's up; the whole test waits well under a tenth of a second. A
clock's `wait` is "True when the event came before `seconds` passed on this clock", so time's up is False. `SYSTEM` is
"a SystemClock; the default of every clock parameter in gates/", so the test goes through it, not a fresh one.

`SystemClock` hands that cap to the `Ready` as it is, so this test makes no timed wait of its own, and the one positive
number in this file is that `Clock`'s cap.
"""

import threading

from gates.core.clock import SYSTEM


def test_says_times_up_when_no_event_comes_within_its_cap() -> None:
    """Breaks when `SYSTEM.wait` says the event came (True) or anything but False, such as None, with no event set."""
    assert SYSTEM.wait(threading.Event().wait, seconds=0.03) is False
