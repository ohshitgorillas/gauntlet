"""Red tests for the pytest gate's parallel test-module processes.

Source: the quality gates design spec under docs/superpowers/specs/, "Tests", the "pytest strictness" bullet and its
first sub-bullet: each test module runs in a pytest process of its own, the processes run in parallel, each module's lines print
together, in the order the modules were given, after the seed line and before the count line. The count line's shape comes from
the "Gates" intro paragraph; the gate's script is `gates/check_pytest.py`, so `<gate>` is `check_pytest`.

The gate runs in a child interpreter whose `PATH` starts with a directory holding a seeded `sysctl`, so C is the number
that script prints.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]

CHILD = (
    "import sys\n"
    "from pathlib import Path\n\n"
    "from gates.check_pytest import main\n\n"
    "sys.exit(main([Path(arg) for arg in sys.argv[1:]]))\n"
)

PREPEND_PATH = 'export PATH="$0:$PATH"; exec "$@"'

MISSING_MODULE = "seededmissingmodule"

FIRST_FAILS_LATE = (
    "import pathlib\n"
    "import time\n\n"
    "DONE = pathlib.Path(DONE_PATH)\n\n\n"
    "def test_seeded():\n"
    "    start = time.monotonic()\n"
    "    while not DONE.exists() and time.monotonic() < start + 10:\n"
    "        time.sleep(0.05)\n"
    "    seen = DONE.exists()\n"
    "    time.sleep(2)\n"
    "    raise ValueError('SeededZulu' if seen else 'SeededAlone')\n"
)

FIRST_BREAKS_LATE = (
    "import pathlib\n"
    "import time\n\n"
    "DONE = pathlib.Path(DONE_PATH)\n"
    "START = time.monotonic()\n"
    "while not DONE.exists() and time.monotonic() < START + 10:\n"
    "    time.sleep(0.05)\n"
    "time.sleep(2)\n"
    "if DONE.exists():\n"
    f"    import {MISSING_MODULE}\n\n\n"
    "def test_seeded():\n"
    "    pass\n"
)

SECOND_FAILS_EARLY = (
    "import pathlib\n\n"
    "DONE = pathlib.Path(DONE_PATH)\n\n\n"
    "def test_seeded():\n"
    "    DONE.touch()\n"
    "    raise ValueError('SeededAlpha')\n"
)

def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _sysctl(root: Path, script: str) -> Path:
    tool = _seed(root, "bin/sysctl", script)
    tool.chmod(0o755)
    return tool.parent


def _cpus(root: Path, count: int) -> Path:
    return _sysctl(root, f"#!/bin/sh\necho {count}\n")


def _child(paths: list[Path], tools: Path) -> subprocess.CompletedProcess[str]:
    command = [
        "/bin/sh",
        "-c",
        PREPEND_PATH,
        str(tools),
        "/usr/bin/env",
        "PYTHONUNBUFFERED=1",
        sys.executable,
        "-c",
        CHILD,
        *map(str, paths),
    ]
    return subprocess.run(  # A child interpreter finds the seeded sysctl first on its PATH.
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def _ordered(root: Path, first_source: str) -> tuple[Path, Path]:
    done = repr(str(root / "done"))
    first = _seed(root, "tests/test_zulu.py", first_source.replace("DONE_PATH", done))
    second = _seed(root, "tests/test_alpha.py", SECOND_FAILS_EARLY.replace("DONE_PATH", done))
    return first, second


def _position(lines: list[str], wanted: str) -> int:
    return lines.index(wanted) if wanted in lines else -1


def test_given_order(tmp_path: Path) -> None:
    """The module given first, which ends last, prints its finding first, between the seed line and the count line."""
    first, second = _ordered(tmp_path, FIRST_FAILS_LATE)

    output = _child([first, second], _cpus(tmp_path, 4)).stdout
    pattern = (
        re.escape("check_pytest: seed ")
        + "[0-9]+\n"
        + re.escape(f"{first}::test_seeded: ValueError: SeededZulu\n")
        + re.escape(f"{second}::test_seeded: ValueError: SeededAlpha\n")
        + re.escape("check_pytest: 2 finding(s) in 2 Python file(s)")
        + "\n?"
    )

    assert re.fullmatch(pattern, output)


def test_error_whole(tmp_path: Path) -> None:
    """pytest's error for the module given first, which ends last, prints whole before the other module's finding."""
    first, second = _ordered(tmp_path, FIRST_BREAKS_LATE)

    lines = _child([first, second], _cpus(tmp_path, 4)).stdout.splitlines()
    error_lines = [index for index, line in enumerate(lines) if MISSING_MODULE in line]
    finding = f"{second}::test_seeded: ValueError: SeededAlpha"
    finding_at = _position(lines, finding)

    assert (finding_at > max(error_lines, default=len(lines)), finding_at) == (True, len(lines) - 2)
