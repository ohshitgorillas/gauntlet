"""Reading a checker's JSON report, as the gates whose checker writes one do: the run that wrote no report the gate can read, and the guard on the report's shape."""

import json
import subprocess
import sys
from typing import TypeGuard

FINISHED = frozenset({0, 1})


class UnfinishedError(Exception):
    """The checker gave no verdict the gate can read: it exited `status` and wrote `output` to stdout, with no JSON report the gate can read in it."""

    def __init__(self, status: int, output: str) -> None:
        """Carry the checker's exit status and its whole stdout."""
        super().__init__(status, output)
        self.status = status
        self.output = output


def is_list(value: object) -> TypeGuard[list[object]]:
    """Tell whether `value` is a list; every element of a list is an `object`, so the narrowing claims nothing it did not check."""
    return isinstance(value, list)


def load(completed: subprocess.CompletedProcess[str]) -> object:
    """Read the JSON document the checker wrote to stdout in a run that finished, and raise `UnfinishedError` for a run that did not.

    The checker finished only when it exited 0 or 1 and wrote a JSON document to stdout. The
    exit status alone does not tell: `python -m <checker>` also exits 1 when the checker never
    starts, and then writes no report. Whether the document has the shape the gate reads is
    the gate's to check.
    """
    if completed.returncode not in FINISHED:
        raise UnfinishedError(completed.returncode, completed.stdout)
    try:
        parsed: object = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise UnfinishedError(completed.returncode, completed.stdout) from error
    return parsed


def print_unread(gate: str, checker: str, unread: UnfinishedError, files: int) -> None:
    """Print the whole output of a checker run that gave no verdict the gate can read, each line on a line of its own, then the gate's count line saying the checker could not finish and with what status."""
    sys.stdout.write("".join(f"{line}\n" for line in unread.output.splitlines()))
    sys.stdout.write(f"{gate}: {checker} exited {unread.status} and gave no report it could read on {files} Python file(s)\n")
