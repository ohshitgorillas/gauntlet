"""Red tests for how many pytest processes the pytest gate runs at once.

Source: the quality gates design spec under docs/superpowers/specs/, "Tests", the "pytest strictness" bullet and its
first sub-bullet: the gate runs the test modules' processes in parallel, as many at once as there are test modules up to
floor(C / 2) and never fewer than one, where C counts the CPUs the gate's process may run on, read in the gate's own
process and never from a command: the CPUs its affinity allows where the host keeps an affinity, and the host's CPU
count elsewhere, as on macOS. The exit codes come from the "Gates" intro paragraph.

Two seeded test modules meet at a rendezvous: each marks its own file and waits up to ten seconds for the other's. Both
pass only when their processes run at once; run one after the other, the first one waits alone and fails.
"""

import os
import subprocess
import sys
from pathlib import Path

from gates.check_pytest import cpus, main, processes

REPO_ROOT = Path(__file__).parents[1]

NO_FINDING = 0
FINDINGS = 1

THREE_MODULES = 3
FIVE_MODULES = 5
TEN_MODULES = 10

ONE_CPU = 1
THREE_CPUS = 3
FOUR_CPUS = 4
SEVEN_CPUS = 7
EIGHT_CPUS = 8
SIXTEEN_CPUS = 16

ONE_PROCESS = 1
THREE_PROCESSES = 3
FOUR_PROCESSES = 4

SEEDED_COUNT = 1000

COUNTING_TOOLS = ("sysctl", "nproc", "getconf")

PASSING = "def test_seeded():\n    pass\n"

RENDEZVOUS = (
    "import pathlib\n"
    "import time\n\n"
    "MINE = pathlib.Path(MINE_PATH)\n"
    "OTHER = pathlib.Path(OTHER_PATH)\n\n\n"
    "def test_seeded():\n"
    "    MINE.touch()\n"
    "    for _ in range(200):\n"
    "        if OTHER.exists():\n"
    "            break\n"
    "        time.sleep(0.05)\n"
    "    assert OTHER.exists()\n"
)

CHILD = "from gates.check_pytest import cpus\n\nprint(cpus())\n"

def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _rendezvous(root: Path) -> list[Path]:
    left = repr(str(root / "left.mark"))
    right = repr(str(root / "right.mark"))
    return [
        _seed(root, "tests/test_left.py", RENDEZVOUS.replace("MINE_PATH", left).replace("OTHER_PATH", right)),
        _seed(root, "tests/test_right.py", RENDEZVOUS.replace("MINE_PATH", right).replace("OTHER_PATH", left)),
    ]


def _seeded_tools(root: Path) -> Path:
    for name in COUNTING_TOOLS:
        _seed(root, f"bin/{name}", f"#!/bin/sh\necho {SEEDED_COUNT}\n").chmod(0o755)
    return root / "bin"


def _host_cpus() -> int | None:
    if sys.platform == "linux":
        return len(os.sched_getaffinity(0))
    return os.cpu_count()


def test_fewer_modules() -> None:
    """Fewer test modules than half the CPUs run one process each, all at once."""
    assert processes(THREE_MODULES, SIXTEEN_CPUS) == THREE_PROCESSES


def test_half_cpus() -> None:
    """More test modules than half the CPUs run half the CPUs' worth of processes at once."""
    assert processes(TEN_MODULES, EIGHT_CPUS) == FOUR_PROCESSES


def test_odd_cpus() -> None:
    """Half of an odd CPU count is rounded down."""
    assert processes(TEN_MODULES, SEVEN_CPUS) == THREE_PROCESSES


def test_one_cpu() -> None:
    """One CPU, whose half rounds down to none, still runs one process."""
    assert processes(FIVE_MODULES, ONE_CPU) == ONE_PROCESS


def test_host_count() -> None:
    """The gate counts the CPUs its affinity allows where the host keeps one, and the host's CPU count elsewhere."""
    assert cpus() == _host_cpus()


def test_no_command(tmp_path: Path) -> None:
    """The count is read in the gate's own process: a counting command on the PATH is never what it reads."""
    child = subprocess.run(  # A child interpreter whose PATH holds only seeded counting commands.
        [sys.executable, "-c", CHILD],
        cwd=REPO_ROOT,
        env={"PATH": str(_seeded_tools(tmp_path))},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )

    assert child.stdout == f"{_host_cpus()}\n"


def test_one_cpu_runs(tmp_path: Path) -> None:
    """One CPU still runs the given test module, and a passing one finishes with no finding."""
    module = _seed(tmp_path, "tests/test_seeded.py", PASSING)

    assert main([module], read_cpus=lambda: ONE_CPU) == NO_FINDING


def test_parallel(tmp_path: Path) -> None:
    """Two test modules with room for two processes run at once, so the rendezvous is met and both pass."""
    assert main(_rendezvous(tmp_path), read_cpus=lambda: FOUR_CPUS) == NO_FINDING


def test_capped(tmp_path: Path) -> None:
    """Three CPUs leave room for one process, so the two modules run one after the other and the first waits alone."""
    assert main(_rendezvous(tmp_path), read_cpus=lambda: THREE_CPUS) == FINDINGS
