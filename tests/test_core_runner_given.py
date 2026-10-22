# Copyright 2026 oh shit, gorillas!
"""Red tests for `Run.given`: every Python file given, test files included, which `run_gate` fills and selects from.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "runner.py: one gate run, from start to
exit", and its decision 28. `Run.given` carries every Python file given, test files included, as `python_files`
returns them: in the order given, a file given twice once, its first spelling kept. `run_gate` selects `sources` from
it, so M and the empty run are unchanged; those two stay held in `test_core_runner.py`.
"""

from pathlib import Path

from gates.core.project import Source, non_test_files
from gates.core.report import Outcome
from gates.core.runner import Gate, Run, run_gate
from tests.support.capture import captured
from tests.support.fake import FakeRunner
from tests.support.project import scaffold

NAME = "check_example"


class Seen:
    """A gate check that keeps every Run it is called with and gives an empty Outcome."""

    def __init__(self) -> None:
        """Initialize the seeded state."""
        self.runs: list[Run] = []

    def __call__(self, run: Run) -> Outcome:
        """Return the reply for the supplied call."""
        self.runs.append(run)
        return Outcome()


def test_given_every_python_file(tmp_path: Path) -> None:
    """The run's given holds every Python file given, test files included, once each as first spelled; its sources are.

    those the gate selects from it.
    """
    project = scaffold(
        tmp_path / "project",
        {
            "a.py": "value = 1\n",
            "b.py": "value = 1\n",
            "a.txt": "text\n",
            "tests/test_a.py": "value = 1\n",
        },
    )
    first = project.root / "b.py"
    text = project.root / "a.txt"
    test = project.root / "tests" / "test_a.py"
    other = project.root / "a.py"
    again = project.root / "tests" / ".." / "b.py"
    seen = Seen()
    gate = Gate(name=NAME, check=seen, select=non_test_files, selects="non-test file")
    root = tmp_path / "scratch"
    root.mkdir()

    captured(
        lambda: run_gate(
            gate,
            [first, text, test, other, again],
            project=project,
            process=FakeRunner([]),
            scratch_root=root,
        )
    )

    assert (seen.runs[0].given, seen.runs[0].sources) == (
        (
            Source(given=first, absolute=first),
            Source(given=test, absolute=test),
            Source(given=other, absolute=other),
        ),
        (Source(given=first, absolute=first), Source(given=other, absolute=other)),
    )
