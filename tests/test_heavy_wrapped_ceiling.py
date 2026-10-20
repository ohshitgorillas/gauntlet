"""Red tests for the line the host-safety wrapper gives a caller already at niceness 19 or above.

Source: the agents design spec under docs/superpowers/specs/, "Decisions", the bullet on heavy runs: the wrapper runs
its command "by the line one pure function gives, `wrapped(command, platform, niceness)`, where `platform` is the host
as `sys.platform` names it, `linux` or `darwin`, and `niceness` is the caller's own [...]: on Linux `ionice -c3 nice -n
<k> -- <command>`, on macOS `nice -n <k> -- <command>`, with no `taskpolicy -b`, [...] where `k` is 19 − niceness,
since `nice -n` adds to a niceness rather than setting it, and a caller at 19 or above, macOS's ceiling being 20, gets
`nice -n 0`".

A caller at 20 is the one where 19 − niceness goes below 0, so it is held on both hosts beside the caller at 19.
"""

import pytest

from gates import heavy

COMMAND = ["make", "check-tests", "FILES=tests/test_a.py tests/test_b.py"]

CASES = [
    ("darwin", 19, ["nice", "-n", "0", "--", *COMMAND]),
    ("darwin", 20, ["nice", "-n", "0", "--", *COMMAND]),
    ("linux", 19, ["ionice", "-c3", "nice", "-n", "0", "--", *COMMAND]),
    ("linux", 20, ["ionice", "-c3", "nice", "-n", "0", "--", *COMMAND]),
]


@pytest.mark.parametrize(("platform", "niceness", "line"), CASES)
def test_caller_at_ceiling_gets_nice_zero(platform: str, niceness: int, line: list[str]) -> None:
    """A caller at niceness 19 or above is run by its host's line with nice -n 0, never a negative step."""
    assert heavy.wrapped(COMMAND, platform, niceness) == line
