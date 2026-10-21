"""Red tests for `Completed.output()`: the checker's whole console output, its stdout followed by its stderr.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process",
which gives `Completed(status, stdout, stderr, timed_out, outputs)` and `.output() = stdout + stderr`; the quality-gates
design spec's "Gates" bullet names a checker's whole output as "stdout and stderr". `stdout + stderr` is the two texts
joined as they are: stdout first, then stderr, nothing put between them and nothing taken from either.
"""

from gates.core.checker import Completed

OUT = "check: on stdout\nsecond stdout line\n"

ERR = "check: on stderr\nsecond stderr line\n"

PARTIAL = "stdout-without-newline"

REST = "stderr-after-it\n"

PADDED_OUT = "line\n\n"

PADDED_ERR = "\n  \n"


def _completed(stdout: str, stderr: str) -> Completed:
    """A finished checker run with exit 0 and no output files, holding the two streams given."""
    return Completed(status=0, stdout=stdout, stderr=stderr, timed_out=False, outputs={})


def test_output_stdout_then_stderr() -> None:
    """The whole output is the checker's stdout followed by its stderr."""
    assert _completed(OUT, ERR).output() == OUT + ERR


def test_output_puts_nothing_between() -> None:
    """A stdout that ends mid-line runs straight into the stderr: no separator is put between the two streams."""
    assert _completed(PARTIAL, REST).output() == PARTIAL + REST


def test_output_keeps_whitespace() -> None:
    """Blank lines and trailing whitespace in either stream are kept: neither stream nor the whole is stripped."""
    assert _completed(PADDED_OUT, PADDED_ERR).output() == PADDED_OUT + PADDED_ERR
