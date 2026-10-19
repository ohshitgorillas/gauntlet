"""Red test for the Python version the test suite runs on.

Source: the quality gates design spec under docs/superpowers/specs/, "Types",
the last sentence of the first bullet: `python_version = "3.12"`,
`requires-python = ">=3.12"`, ruff `target-version = "py312"`. The spec pins
Python 3.12, so the interpreter the tests run under is 3.12.
"""

import sys

PINNED = (3, 12)


def test_runs_on_pinned_python() -> None:
    """The interpreter running the suite is the pinned Python, 3.12."""
    running = (sys.version_info.major, sys.version_info.minor)
    assert running == PINNED
