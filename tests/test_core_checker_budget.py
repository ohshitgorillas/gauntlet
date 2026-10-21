"""Red test for `cpu_budget`: the cap on mutation and backstop workers, half the CPUs this process may run on.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`def cpu_budget(cpus: int | None = None) -> int  # floor(cpus / 2), the mutation and backstop cap; None: the CPUs this
process may run on`. The quality gates
spec's Tests section sets the same cap, "at most floor(`nproc` / 2) workers, where `nproc` counts the CPUs the gate's
process may run on", binds the backstop to it, and says what those CPUs are: "the CPUs its affinity allows where the
host keeps an affinity, and the host's CPU count elsewhere, as on macOS".

`cpu_budget` takes an optional `cpus` argument, and with `None` it counts the CPUs this process may run on, so the test
calls it with no argument and reads the CPUs this process may run on as that sentence defines them, in
this same process: the affinity set on Linux, which keeps one, and the host's CPU count elsewhere, as on macOS.
"""

import os
import sys

from gates.core.checker import cpu_budget


def test_cpu_budget_is_half_the_cpus_this_process_may_run_on_rounded_down() -> None:
    """cpu_budget gives floor(C / 2), C being the CPUs this process's affinity allows, or the host's count without one."""
    if sys.platform == "linux":
        cpus = len(os.sched_getaffinity(0))
    else:
        cpus = os.cpu_count()
    assert cpus is not None

    assert cpu_budget() == cpus // 2
