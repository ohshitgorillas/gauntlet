"""Red tests for the pytest gate's cap on processes at once, and the CPU count it reads in its own process.

Source: the quality gates design spec under docs/superpowers/specs/, "Tests", the "pytest strictness" bullet, the
sub-bullet beginning "Each test module": the gate runs the test modules' processes in parallel, as many at once as there
are test modules up to floor(C / 2) and never fewer than one, where C counts the CPUs the gate's process may run on,
read in the gate's own process: the CPUs its affinity allows where the host keeps an affinity. The exit codes come from
the "Gates" intro paragraph.

Seeded test modules meet at a rendezvous: each marks its own file, never removed, and waits up to ten seconds for every
other module's mark. A module passes only when every other module has run before it or runs beside it, so the modules
given first fail when the gate holds back a module they wait for.
"""

import os
from pathlib import Path

from gates.check_pytest import main

NO_FINDING = 0
FINDINGS = 1

NO_CPUS = 0
THREE_CPUS = 3
FOUR_CPUS = 4
SIX_CPUS = 6

PASSING = "def test_seeded():\n    pass\n"

RENDEZVOUS = (
    "import pathlib\n"
    "import time\n\n"
    "MINE = pathlib.Path(MINE_PATH)\n"
    "OTHERS = [pathlib.Path(path) for path in OTHER_PATHS]\n\n\n"
    "def missing():\n"
    "    return [str(other) for other in OTHERS if not other.exists()]\n\n\n"
    "def test_seeded():\n"
    "    MINE.touch()\n"
    "    for _ in range(200):\n"
    "        if not missing():\n"
    "            break\n"
    "        time.sleep(0.05)\n"
    "    assert missing() == []\n"
)


def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _rendezvous(root: Path, names: list[str]) -> list[Path]:
    """One test module per name, in the order given, each waiting for the marks of all the others."""
    marks = {name: str(root / f"{name}.mark") for name in names}
    modules: list[Path] = []
    for name in names:
        others = [marks[other] for other in names if other != name]
        source = RENDEZVOUS.replace("MINE_PATH", repr(marks[name])).replace("OTHER_PATHS", repr(others))
        modules.append(_seed(root, f"tests/test_{name}.py", source))
    return modules


def test_four_cpus_hold_back_a_third_module(tmp_path: Path) -> None:
    """Four CPUs leave room for two processes, no fewer and no more.

    Two at once: of three modules, a pair that waits for each other only meets beside a third that waits for none, which
    fails when the gate runs the three one at a time. No more: three modules that each wait for all the others fail, as
    the third waits and the first two wait for it alone.
    """
    pair = [*_rendezvous(tmp_path / "two", ["alpha", "bravo"]), _seed(tmp_path / "two", "tests/test_charlie.py", PASSING)]
    trio = _rendezvous(tmp_path / "three", ["alpha", "bravo", "charlie"])

    assert (main(pair, read_cpus=lambda: FOUR_CPUS), main(trio, read_cpus=lambda: FOUR_CPUS)) == (NO_FINDING, FINDINGS)


def test_three_cpus_run_one_at_a_time(tmp_path: Path) -> None:
    """Three CPUs are floor(3 / 2), one process, not two by rounding up: of two modules the first waits for the second alone."""
    modules = _rendezvous(tmp_path, ["left", "right"])

    assert main(modules, read_cpus=lambda: THREE_CPUS) == FINDINGS


def test_six_cpus_run_three_modules_at_once(tmp_path: Path) -> None:
    """Six CPUs leave room for three processes, so three modules all run at once and every rendezvous is met."""
    modules = _rendezvous(tmp_path, ["alpha", "bravo", "charlie"])

    assert main(modules, read_cpus=lambda: SIX_CPUS) == NO_FINDING


def test_no_cpus_still_run_one_at_a_time(tmp_path: Path) -> None:
    """A count of no CPUs is floor(0 / 2), raised to one process: both modules still run, one after the other."""
    modules = _rendezvous(tmp_path, ["left", "right"])

    assert main(modules, read_cpus=lambda: NO_CPUS) == FINDINGS


def test_affinity_of_one_cpu_runs_one_at_a_time(tmp_path: Path) -> None:
    """With no reader given, C is the CPUs this process's affinity allows: pinned to one, the two modules run in turn."""
    modules = _rendezvous(tmp_path, ["left", "right"])
    allowed = os.sched_getaffinity(0)
    os.sched_setaffinity(0, {min(allowed)})
    try:
        status = main(modules)
    finally:
        os.sched_setaffinity(0, allowed)

    assert status == FINDINGS
