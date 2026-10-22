"""Red tests for the pytest gate's cap on processes at once, and the CPU count it reads in its own process.

Source: the quality gates design spec under docs/superpowers/specs/, "Tests", the "pytest strictness" bullet, the
sub-bullet beginning "Each test module": the gate runs the test modules' processes in parallel, as many at once as there
are test modules up to floor(C / 2) and never fewer than one, where C counts the CPUs the gate's process may run on,
read in the gate's own process: the CPUs its affinity allows where the host keeps an affinity. The exit codes come from
the "Gates" intro paragraph.

The no-wall-clock design Order steps 37–41 measure concurrency through Scripted and its own next_done.
"""

import os
import sys
from pathlib import Path

from gates.check_pytest import gate, read_budget
from gates.core.checker import Command
from gates.core.runner import run_gate
from tests.support.fake import completed
from tests.support.project import scaffold
from tests.support.scripted import Scripted, Step

NO_FINDING = 0

NO_CPUS = 0
THREE_CPUS = 3
FOUR_CPUS = 4
SIX_CPUS = 6

PASSING = "def test_seeded():\n    pass\n"


def _module(command: Command) -> str:
    return next(
        word for word in command.argv if word.endswith(".py") and "=" not in word
    )


def _peak(root: Path, count: int, cpus: int | None) -> tuple[int, int, int]:
    names = [f"tests/test_module{index}.py" for index in range(count)]
    project = scaffold(root, dict.fromkeys(names, PASSING))
    modules = [project.root / name for name in names]
    steps = {
        str(module): Step(
            completed(
                outputs={
                    "junit": (
                        f'<testsuites><testsuite name="{module}" tests="1">'
                        f'<testcase classname="tests.{module.stem}" name="test_seeded"/>'
                        "</testsuite></testsuites>"
                    )
                }
            )
        )
        for module in modules
    }
    process = Scripted(steps, key=_module)
    selected = gate() if cpus is None else gate(lambda: read_budget(lambda: cpus))
    status = run_gate(
        selected, modules, project=project, process=process, next_done=process.next_done
    )
    return status, process.peak, len(process.finished)


# Breaks if the pytest gate runs fewer or more than two of three modules with four CPUs.
def test_four_cpus_overlap_exactly_two(tmp_path: Path) -> None:
    assert _peak(tmp_path, 3, FOUR_CPUS) == (NO_FINDING, 2, 3)


# Breaks if the CPU budget rounds three CPUs up to two workers.
def test_three_cpus_serialize_modules(tmp_path: Path) -> None:
    assert _peak(tmp_path, 2, THREE_CPUS) == (NO_FINDING, 1, 2)


# Breaks if six CPUs are capped below three concurrent workers.
def test_six_cpus_overlap_three_modules(tmp_path: Path) -> None:
    assert _peak(tmp_path, 3, SIX_CPUS) == (NO_FINDING, 3, 3)


# Breaks if zero CPUs prevents work or permits concurrent workers.
def test_zero_cpus_serialize_modules(tmp_path: Path) -> None:
    assert _peak(tmp_path, 2, NO_CPUS) == (NO_FINDING, 1, 2)


# Breaks if the default gate ignores process affinity or the host CPU count.
def test_default_cpu_count_controls_overlap(tmp_path: Path) -> None:
    if sys.platform == "linux":
        allowed = os.sched_getaffinity(0)
        os.sched_setaffinity(0, {min(allowed)})
        try:
            result = _peak(tmp_path, 2, None)
        finally:
            os.sched_setaffinity(0, allowed)

        assert result == (NO_FINDING, 1, 2)
    else:
        host = os.cpu_count()
        assert host is not None
        at_once = max(1, host // 2)
        assert _peak(tmp_path, at_once + 1, None) == (NO_FINDING, at_once, at_once + 1)
