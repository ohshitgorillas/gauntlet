"""Red tests for `cpu_budget(cpus)`: half of the given CPU count, rounded down, the cap on mutation and backstop workers.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`def cpu_budget(cpus: int | None = None) -> int  # floor(cpus / 2), the mutation and backstop cap; None: the CPUs this
process may run on (its affinity where the host keeps one, else the host's count), so a test sets the count in-process`.
The quality gates spec's Tests section gives the same cap, "at most floor(`nproc` / 2) workers", and says a cap of 0
cannot start a run, so a count of 0 or 1 gives 0 and is never lifted to 1.

A count given is used as given, whatever the host has. Without one, the CPUs are the affinity's where the host keeps one,
which a test narrows in-process with `os.sched_setaffinity` on Linux, and the host's count elsewhere, as on macOS.
"""

import os
import sys

import pytest

from gates.core.checker import cpu_budget

NARROWED = 3


@pytest.mark.parametrize(
    ("cpus", "budget"),
    [
        (0, 0),
        (1, 0),
        (2, 1),
        (3, 1),
        (4, 2),
        (5, 2),
        (6, 3),
        (7, 3),
        (64, 32),
        (65, 32),
    ],
)
def test_given_count_is_halved_and_rounded_down(cpus: int, budget: int) -> None:
    """A CPU count given gives floor(count / 2): an odd count rounds down, and 0 and 1 give 0, whatever the host has."""
    assert cpu_budget(cpus) == budget


def test_no_count_follows_the_affinity_where_the_host_keeps_one() -> None:
    """Without a count the budget halves the CPUs the process's affinity allows, or the host's count without one."""
    if sys.platform == "linux":
        original = os.sched_getaffinity(0)
        narrowed = set(sorted(original)[:NARROWED])
        os.sched_setaffinity(0, narrowed)
        try:
            budget = cpu_budget()
        finally:
            os.sched_setaffinity(0, original)
        expected = len(narrowed) // 2
    else:
        host = os.cpu_count()
        assert host is not None
        budget = cpu_budget()
        expected = host // 2

    assert budget == expected
