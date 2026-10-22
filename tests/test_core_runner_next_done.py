"""Red test for `check_with` handing `Run.next_done` to `run_all`.

Source: the no-wall-clock design spec under docs/superpowers/specs/, section "gates/core/runner.py: a test's wait on
`run_all`'s workers, carried explicitly", decision 10, and its step 17: `Run` has a `next_done` field beside `process`,
`first_done` by default, which `check_with` hands to `run_all` beside `run.process`; `run_all` makes every wait on its
workers, the wait for one to end included, through that `next_done`. The test's `next_done` notes how many workers each
call is handed and answers with `first_done`. The test's process holds its one call until that `next_done` is entered,
so the worker is still running when `run_all` waits on it.
"""

import threading
from collections.abc import Collection, Sequence
from concurrent.futures import Future
from pathlib import Path

from gates.core.checker import Command, Completed, first_done
from gates.core.project import Source
from gates.core.report import Line, Outcome
from gates.core.runner import Run, Scratch, check_with
from tests.support.fake import FakeRunner, completed
from tests.support.project import scaffold


class Quiet:
    """A checker with one batch per source, whose report is its exit status and which gives no line."""

    stopped: frozenset[int] = frozenset()

    def batches(self, run: Run) -> list[list[Source]]:
        return [[source] for source in run.sources]

    def command(self, run: Run, batch: Sequence[Source]) -> Command:
        return Command(argv=("echo", batch[0].given.name), cwd=run.project.root)

    def read(self, completed: Completed) -> int:
        return completed.status

    def expected_status(self, report: int) -> int:
        return 0

    def lines(
        self, report: int, batch: Sequence[Source], *, stopped: bool
    ) -> list[Line]:
        return []


class Held:
    """A Runner that holds each call until its entered event is set, then replies as a FakeRunner does."""

    def __init__(self, replies: Sequence[Completed], entered: threading.Event) -> None:
        self._fake = FakeRunner(replies)
        self.commands = self._fake.commands
        self._entered = entered

    def __call__(self, command: Command) -> Completed:
        self._entered.wait()
        return self._fake(command)


class Noting:
    """A next_done that notes how many workers each call is handed, sets entered, then answers with first_done."""

    def __init__(self, entered: threading.Event) -> None:
        self.noted: list[int] = []
        self._entered = entered

    def __call__(
        self, running: Collection[Future[Completed]]
    ) -> set[Future[Completed]]:
        self.noted.append(len(running))
        self._entered.set()
        return first_done(running)


def test_check_with_waits_through_run_next_done(tmp_path: Path) -> None:
    """With one batch, check_with's run_all waits for its one worker through the next_done the Run carries."""
    # Breaks when check_with calls run_all without run.next_done, so run_all waits through first_done and the
    # Run's next_done is never called.
    project = scaffold(tmp_path / "project", {"a.py": "value = 1\n"})
    sources = (Source(given=Path("a.py"), absolute=project.root / "a.py"),)
    entered = threading.Event()
    process = Held([completed()], entered)
    next_done = Noting(entered)
    run = Run(
        project=project,
        sources=sources,
        scratch=Scratch(tmp_path),
        process=process,
        next_done=next_done,
    )

    outcome = check_with(Quiet())(run)

    assert (next_done.noted, len(process.commands), outcome) == (
        [1],
        1,
        Outcome(lines=()),
    )
