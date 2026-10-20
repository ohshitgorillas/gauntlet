"""Red tests for the pytest gate's temp space: one temp directory per run under the scratch root it is handed, one pytest temp directory per test module inside it, deleted on every exit path, a failure to make or delete it reported.

Source: the quality gates design spec under docs/superpowers/specs/, "Tests", the "pytest strictness" bullet. "Each run of the pytest gate makes one temp directory of its own under the run's scratch root, before its seed line. The scratch root is the `scratch_root` argument of the gate's `main`, used as given". "Each test module's pytest process takes a path of its own inside the run's temp directory as pytest's `--basetemp`, which no other process shares". "The run's temp directory and all it holds are deleted on every exit path: every return and every exception, `KeyboardInterrupt` included, a run that did not finish among them. After a run the scratch root holds exactly what it held before, every other entry in it untouched". "A run temp directory the gate cannot make, a missing scratch root included, prints one error line naming the path and the OS error, then the count line with N 0 and M the test files given, and exits 2." "A deletion that fails ... is temp space the gate cannot delete and is never passed over: after the seed line and every module's lines, the gate prints one error line naming the path and the OS error, then the count line with N the findings it read, and exits 2, whatever the modules found." Placement is judged only by the scratch root the test hands the run, seen from inside a seeded test module through pytest's public `tmp_path_factory.getbasetemp()`. The seed line's shape is `<gate>: seed N`; the count line's shape and the empty run come from the "Gates" intro; a finding's shape from the JUnit sub-bullet. The gate's script is `gates/check_pytest.py`, so `<gate>` is `check_pytest`.

The documents do not spell the OS error's text, so an error line is held to what names the path and the error: the scratch root's path, which every path under it begins with, and `os.strerror` of the errno the operating system gives for the failure seeded. The run's temp directory is made undeletable by a seeded test module that takes write permission off the scratch root, which lies outside the temp space the gate owns.

A recording module lists the scratch root in its test body and again as its pytest process exits, after pytest has written its JUnit report. An interrupted run is looked at where `main` leaves, its exception still alive, once the interrupting module's pytest process has ended, and again after the child interpreter has exited.
"""

import errno
import fcntl
import itertools
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from gates.check_pytest import main
from tests.support.capture import captured

REPO_ROOT = Path(__file__).parents[1]

GATE = "check_pytest"

UNFINISHED = 2

ONE_RUN_DIRECTORY = 1
TWO_MODULES = 2

READ_ONLY = 0o500
WRITABLE = 0o700

SEED_LINE = re.compile(rf"{GATE}: seed \d+")

SEED = "<seed line>"
ERROR = "<error line naming the path and the OS error>"

COUNT_NO_FINDING = f"{GATE}: 0 finding(s) in 2 Python file(s)"
COUNT_ONE_FINDING = f"{GATE}: 1 finding(s) in 2 Python file(s)"

PRESEEDED = {
    "keep.txt": "kept",
    "tmpkeep/inner.txt": "inner",
    "pytest-of-seed/inner.txt": "pytest",
}

PASSING = "def test_seeded():\n    pass\n"

FAILS = "def test_seeded():\n    raise ValueError('SeededFailure')\n"

BROKEN = "import seededmissingmodule\n\n\ndef test_seeded():\n    pass\n"

LIBRARY = "def double(value):\n    return value * 2\n"

RECORDING = (
    "import atexit\n"
    "import os\n"
    "import pathlib\n\n"
    "RECORD = pathlib.Path(RECORD_PATH)\n"
    "SCRATCH = pathlib.Path(SCRATCH_PATH)\n\n\n"
    "def record(base, entries):\n"
    "    seen = sorted({*entries, *os.listdir(SCRATCH)})\n"
    "    RECORD.write_text('\\n'.join([base, *seen]), encoding='utf-8')\n\n\n"
    "def test_seeded(tmp_path_factory, tmp_path):\n"
    "    (tmp_path / 'left.txt').write_text('left', encoding='utf-8')\n"
    "    atexit.register(record, str(tmp_path_factory.getbasetemp()), os.listdir(SCRATCH))\n"
)

LEAVES = "def test_seeded(tmp_path):\n    (tmp_path / 'left.txt').write_text('left', encoding='utf-8')\n"

LEAVES_FAILING = LEAVES + "    raise ValueError('SeededFailure')\n"

INTERRUPTING = (
    "import fcntl\n"
    "import os\n"
    "import pathlib\n"
    "import signal\n\n"
    "RECORD = pathlib.Path(RECORD_PATH)\n"
    "SCRATCH = pathlib.Path(SCRATCH_PATH)\n"
    "PID = pathlib.Path(PID_PATH)\n"
    "LOCK = os.open(LOCK_PATH, os.O_WRONLY)\n"
    "fcntl.flock(LOCK, fcntl.LOCK_EX)\n\n\n"
    "def test_seeded(tmp_path):\n"
    "    (tmp_path / 'left.txt').write_text('left', encoding='utf-8')\n"
    "    RECORD.write_text('\\n'.join(sorted(os.listdir(SCRATCH))), encoding='utf-8')\n"
    "    os.kill(int(PID.read_text(encoding='utf-8')), signal.SIGINT)\n"
)

LOCKING = (
    "import pathlib\n\n"
    "SCRATCH = pathlib.Path(SCRATCH_PATH)\n\n\n"
    "def test_seeded():\n"
    f"    SCRATCH.chmod({READ_ONLY:#o})\n"
)

CHILD = (
    "import os\n"
    "import sys\n"
    "from pathlib import Path\n\n"
    f"from {main.__module__} import {main.__name__}\n\n\n"
    "def hold():\n"
    "    os.write(int(sys.argv[2]), b'.')\n"
    "    os.read(int(sys.argv[3]), 1)\n\n\n"
    "Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8')\n"
    "try:\n"
    f"    code = {main.__name__}([Path(arg) for arg in sys.argv[5:]], scratch_root=Path(sys.argv[4]))\n"
    "except BaseException:\n"
    "    hold()\n"
    "    raise\n"
    "hold()\n"
    "sys.exit(code)\n"
)

ENDINGS = [
    pytest.param(LEAVES, id="pass"),
    pytest.param(LEAVES_FAILING, id="find"),
    pytest.param(BROKEN, id="unfin"),
]

UNMADE = [
    pytest.param("absent", errno.ENOENT, id="absent"),
    pytest.param("file", errno.ENOTDIR, id="file"),
    pytest.param("locked", errno.EACCES, id="locked"),
]

COMPANIONS = [
    pytest.param(PASSING, False, id="pass"),
    pytest.param(FAILS, True, id="find"),
]


def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _scratch(root: Path) -> Path:
    """A scratch root that already holds a file and two directories, one named as a temp directory might be."""
    scratch = root / "scratch"
    for relative, text in PRESEEDED.items():
        _seed(scratch, relative, text)
    return scratch


def _snapshot(root: Path) -> dict[str, bytes]:
    """Every entry under the root by relative path, a directory with a trailing slash, a file with its bytes."""
    return {
        path.relative_to(root).as_posix() + ("/" if path.is_dir() else ""): b"" if path.is_dir() else path.read_bytes()
        for path in root.rglob("*")
    }


def _fill(
    source: str, scratch: Path, record: Path | None = None, pid: Path | None = None, lock: Path | None = None
) -> str:
    filled = source.replace("SCRATCH_PATH", repr(str(scratch)))
    for marker, path in (("RECORD_PATH", record), ("PID_PATH", pid), ("LOCK_PATH", lock)):
        if path is not None:
            filled = filled.replace(marker, repr(str(path)))
    return filled


def _record_lines(record: Path) -> list[str]:
    return record.read_text(encoding="utf-8").splitlines() if record.exists() else []


def _recording_run(root: Path) -> tuple[Path, list[list[str]]]:
    """Run the gate over two recording modules with a scratch root of the test's own; return the root and each module's record."""
    scratch = _scratch(root)
    records = [root / "records" / "alpha.txt", root / "records" / "zulu.txt"]
    records[0].parent.mkdir()
    modules = [
        _seed(root, f"tree/tests/test_{record.stem}.py", _fill(RECORDING, scratch, record)) for record in records
    ]
    main(modules, scratch_root=scratch)
    return scratch, [_record_lines(record) for record in records]


def _base(lines: list[str]) -> Path | None:
    return Path(lines[0]).resolve() if lines else None


def _top(base: Path | None, scratch: Path) -> str:
    """The entry of the scratch root the module's pytest temp directory lies in, or nothing when it lies outside."""
    if base is None or not base.is_relative_to(scratch.resolve()):
        return ""
    return base.relative_to(scratch.resolve()).parts[0]


def _new(entries: list[str]) -> list[str]:
    preseeded = {relative.split("/")[0] for relative in PRESEEDED}
    return [entry for entry in entries if entry not in preseeded]


def _nested(bases: list[Path | None]) -> int:
    """How many ordered pairs of the modules' pytest temp directories have one inside the other."""
    return sum(
        1
        for inner, outer in itertools.permutations(bases, 2)
        if inner is not None and outer is not None and inner.is_relative_to(outer)
    )


def test_inside(tmp_path: Path) -> None:
    """Each test module's pytest temp directory lies inside the scratch root the run is handed."""
    scratch, records = _recording_run(tmp_path)

    assert [_top(_base(lines), scratch) != "" for lines in records] == [True, True]


def test_one_per_run(tmp_path: Path) -> None:
    """While the modules run, each module's JUnit report written included, the scratch root holds one new entry, and both modules' pytest temp directories lie in it."""
    scratch, records = _recording_run(tmp_path)

    seen = sorted({entry for lines in records for entry in _new(lines[1:])})
    tops = sorted({_top(_base(lines), scratch) for lines in records})

    assert (len(seen), seen == tops) == (ONE_RUN_DIRECTORY, True)


def test_own_basetemp(tmp_path: Path) -> None:
    """Each module's pytest temp directory is its own, inside the scratch root: none shared, none inside another's."""
    scratch, records = _recording_run(tmp_path)

    bases = [_base(lines) for lines in records]
    inside = [_top(base, scratch) != "" for base in bases]

    assert (len(set(bases)), _nested(bases), inside) == (TWO_MODULES, 0, [True, True])


@pytest.mark.parametrize("companion", ENDINGS)
def test_deleted(tmp_path: Path, companion: str) -> None:
    """A run that passes, finds or does not finish made its temp directory under the scratch root and leaves the root as it was."""
    scratch = _scratch(tmp_path)
    before = _snapshot(scratch)
    record = tmp_path / "record.txt"
    paths = [
        _seed(tmp_path, "tree/tests/test_recording.py", _fill(RECORDING, scratch, record)),
        _seed(tmp_path, "tree/tests/test_companion.py", companion),
    ]

    main(paths, scratch_root=scratch)

    during = _new(_record_lines(record)[1:])
    assert (len(during), _snapshot(scratch) == before) == (ONE_RUN_DIRECTORY, True)


def _await_release(lock: Path) -> None:
    """Return once no process holds the lock, which the interrupting module's pytest process holds from its import until it exits."""
    descriptor = os.open(lock, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
    finally:
        os.close(descriptor)


def _interrupted_run(root: Path, scratch: Path) -> tuple[list[str], dict[str, bytes], dict[str, bytes]]:
    """Run the gate in a child interpreter the seeded module sends SIGINT to; return the module's record, the scratch root where `main` left, and the scratch root after the child exited.

    The child holds where `main` leaves, its exception still alive, until the parent has seen the scratch root there, once the module's pytest process has ended.
    """
    record = root / "record.txt"
    pid = root / "gate.pid"
    lock = _seed(root, "gate.lock", "")
    module = _seed(root, "tree/tests/test_interrupting.py", _fill(INTERRUPTING, scratch, record, pid, lock))
    left_read, left_write = os.pipe()
    hold_read, hold_write = os.pipe()
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, str(pid), str(left_write), str(hold_read), str(scratch), str(module)],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        pass_fds=(left_write, hold_read),
    )
    os.close(left_write)
    os.close(hold_read)
    try:
        os.read(left_read, 1)
        _await_release(lock)
        where_left = _snapshot(scratch)
    finally:
        os.close(hold_write)
        os.close(left_read)
        child.wait()
    return _record_lines(record), where_left, _snapshot(scratch)


def test_interrupt(tmp_path: Path) -> None:
    """A KeyboardInterrupt that reaches the gate while a module runs leaves the scratch root as it was before the run, as `main` leaves and after."""
    scratch = _scratch(tmp_path)
    before = _snapshot(scratch)

    record, where_left, after = _interrupted_run(tmp_path, scratch)

    assert (len(_new(record)), where_left == before, after == before) == (ONE_RUN_DIRECTORY, True, True)


def _shape(line: str, scratch: Path, error: str) -> str:
    """A printed line, with the seed line and an error line naming a path under the scratch root and the OS error each put as its kind."""
    if SEED_LINE.fullmatch(line) is not None:
        return SEED
    if str(scratch) in line and error in line:
        return ERROR
    return line


def _unmade_scratch(root: Path, kind: str) -> Path:
    scratch = root / "scratch"
    if kind == "file":
        _seed(root, "scratch", "not a directory\n")
    if kind == "locked":
        scratch.mkdir()
        scratch.chmod(READ_ONLY)
    return scratch


def _restore(scratch: Path) -> None:
    if scratch.is_dir():
        scratch.chmod(WRITABLE)


@pytest.mark.parametrize(("kind", "code"), UNMADE)
def test_unmade(tmp_path: Path, kind: str, code: int) -> None:
    """A run temp directory the gate cannot make prints one error line naming the path and the OS error, then the count line, and exits 2."""
    paths = [
        _seed(tmp_path, "tree/tests/test_one.py", PASSING),
        _seed(tmp_path, "tree/tests/test_two.py", PASSING),
        _seed(tmp_path, "tree/lib.py", LIBRARY),
    ]
    scratch = _unmade_scratch(tmp_path, kind)
    try:
        output = captured(lambda: main(paths, scratch_root=scratch))
    finally:
        _restore(scratch)
    shapes = [_shape(line.rstrip("\n"), scratch, os.strerror(code)) for line in output.lines]

    assert (output.result, shapes) == (UNFINISHED, [ERROR, COUNT_NO_FINDING])


@pytest.mark.parametrize(("companion", "finds"), COMPANIONS)
def test_undeleted(tmp_path: Path, companion: str, *, finds: bool) -> None:
    """A run temp directory the gate cannot delete prints one error line after every module's lines, then the count line, and exits 2."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    locker = _seed(tmp_path, "tree/tests/test_locker.py", _fill(LOCKING, scratch))
    other = _seed(tmp_path, "tree/tests/test_other.py", companion)
    try:
        output = captured(lambda: main([locker, other], scratch_root=scratch))
    finally:
        _restore(scratch)
    shapes = [_shape(line.rstrip("\n"), scratch, os.strerror(errno.EACCES)) for line in output.lines]
    finding = f"{other}::test_seeded: ValueError: SeededFailure"
    expected = [SEED, finding, ERROR, COUNT_ONE_FINDING] if finds else [SEED, ERROR, COUNT_NO_FINDING]

    assert (output.result, shapes) == (UNFINISHED, expected)
