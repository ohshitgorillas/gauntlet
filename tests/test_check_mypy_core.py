"""Red tests for the mypy gate on the gates core: a mypy that exits nonzero with nothing to show is unfinished.

Source: the gates core design spec under docs/superpowers/specs/, "Why", item (a), section 1, runner.py, the paragraph
"A stopped batch always ends unfinished", decision 21, and report.py's `render` and `output_lines`; the quality gates
design spec, "Gates", the sub-bullet on when a checker finished.

mypy exits 1 with one or more errors and 0 with none, so an exit 1 with no record is not the 0 an empty report calls
for: the run is one the checker did not finish, it prints the checker's whole output, then the count line, and exits 2.
A stop (mypy's 2) with no record ends unfinished the same way. An exit 0 with no record is a finished, clean run.

Each per-file mypy run is preceded by the run's one warm of the cache, which must exit 0, print nothing and leave a
file; the runner below leaves one in every empty directory of the scratch root before it hands back its reply.
"""

from collections.abc import Sequence
from pathlib import Path

from gates.check_mypy import GATE
from gates.core.checker import Command, Completed
from gates.core.runner import run_gate
from tests.support.capture import captured
from tests.support.fake import FakeRunner, completed
from tests.support.project import scaffold

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

COUNT_NONE = "check_mypy: 0 finding(s) in 1 Python file(s)\n"

REFUSAL = "/opt/python/lib/python3.12/site-packages is in the MYPYPATH. Please remove it.\n"

SEE_ALSO = "See https://mypy.readthedocs.io/en/stable/running_mypy.html#how-mypy-handles-imports for more info\n"

USAGE = "usage: mypy [-h] [-v] [-V] [more options; see below]\n"

USAGE_ERROR = "mypy: error: unrecognized arguments: --bogus\n"

# The warm run's reply: exit 0 and nothing printed.
WARM = completed(0)


class CacheLeavingRunner:
    """A Runner that leaves a file in each empty directory under the scratch root, then gives the next canned reply."""

    def __init__(self, scratch: Path, replies: Sequence[Completed]) -> None:
        self.scratch = scratch
        self.replies = FakeRunner(replies)

    def __call__(self, command: Command) -> Completed:
        for directory in list(self.scratch.rglob("*")):
            if directory.is_dir() and not any(directory.iterdir()):
                (directory / "cache.json").write_text("{}\n", encoding="utf-8")
        return self.replies(command)


def _run(tmp_path: Path, reply: Completed) -> tuple[int, list[str]]:
    """Run the gate over one clean file of a scaffolded project: the warm, then one mypy run answered by `reply`."""
    project = scaffold(tmp_path / "project", {"clean.py": CLEAN})
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    runner = CacheLeavingRunner(scratch, [WARM, reply])
    output = captured(
        lambda: run_gate(
            GATE,
            [project.root / "clean.py"],
            project=project,
            process=runner,
            scratch_root=scratch,
        )
    )
    return output.result, output.merged


def test_exit_one_with_no_record_prints_the_whole_output(tmp_path: Path) -> None:
    """mypy's refusal, exit 1 with no record on stdout, is no finish: its whole output, then the count line, exit 2."""
    status, lines = _run(tmp_path, completed(1, "", REFUSAL + SEE_ALSO))

    assert (status, lines) == (2, [REFUSAL, SEE_ALSO, COUNT_NONE])


def test_exit_one_with_no_output_at_all_is_unfinished(tmp_path: Path) -> None:
    """An exit 1 with nothing on stdout or stderr is no finish either: the count line alone, exit 2."""
    status, lines = _run(tmp_path, completed(1))

    assert (status, lines) == (2, [COUNT_NONE])


def test_a_stop_with_no_record_prints_the_whole_output(tmp_path: Path) -> None:
    """A stop, mypy's exit 2, with no record always ends unfinished: its whole output, then the count line, exit 2."""
    status, lines = _run(tmp_path, completed(2, "", USAGE + USAGE_ERROR))

    assert (status, lines) == (2, [USAGE, USAGE_ERROR, COUNT_NONE])


def test_exit_zero_with_no_record_is_a_clean_finish(tmp_path: Path) -> None:
    """An exit 0 with no record is the status an empty report calls for: the count line alone, exit 0."""
    status, lines = _run(tmp_path, completed(0))

    assert (status, lines) == (0, [COUNT_NONE])
