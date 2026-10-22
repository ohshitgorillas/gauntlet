"""Red tests for how many pytest processes the pytest gate runs at once.

Source: the quality gates design spec under docs/superpowers/specs/, "Tests", the "pytest strictness" bullet and its
first sub-bullet: the gate runs the test modules' processes in parallel, as many at once as there are test modules up to
floor(C / 2) and never fewer than one, where C counts the CPUs the gate's process may run on, read in the gate's own
process and never from a command: the CPUs its affinity allows where the host keeps an affinity, and the host's CPU
count elsewhere, as on macOS. The exit codes come from the "Gates" intro paragraph.

The no-wall-clock design Order steps 42–43 measure concurrency through Scripted and its own next_done.
"""

from pathlib import Path

from gates.check_pytest import gate, main, read_budget
from gates.core.checker import Command
from gates.core.runner import run_gate
from tests.support.fake import completed
from tests.support.project import scaffold
from tests.support.scripted import Scripted, Step

NO_FINDING = 0

ONE_CPU = 1
THREE_CPUS = 3
FOUR_CPUS = 4
PASSING = "def test_seeded():\n    pass\n"


def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_one_cpu_runs(tmp_path: Path) -> None:
    """One CPU still runs the given test module, and a passing one finishes with no finding."""
    module = _seed(tmp_path, "tests/test_seeded.py", PASSING)

    assert main([module], read_cpus=lambda: ONE_CPU) == NO_FINDING


def _module(command: Command) -> str:
    return next(
        word for word in command.argv if word.endswith(".py") and "=" not in word
    )


def _pair(root: Path, cpus: int) -> tuple[int, int, int]:
    names = ["tests/test_left.py", "tests/test_right.py"]
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
    status = run_gate(
        gate(lambda: read_budget(lambda: cpus)),
        modules,
        project=project,
        process=process,
        next_done=process.next_done,
    )
    return status, process.peak, len(process.finished)


# Breaks if two available workers serialize two test modules.
def test_two_modules_overlap_with_four_cpus(tmp_path: Path) -> None:
    assert _pair(tmp_path, FOUR_CPUS) == (NO_FINDING, 2, 2)


# Breaks if three CPUs permit both test modules to overlap.
def test_two_modules_serialize_with_three_cpus(tmp_path: Path) -> None:
    assert _pair(tmp_path, THREE_CPUS) == (NO_FINDING, 1, 2)
