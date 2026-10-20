"""Red tests for the line the host-safety wrapper runs its command by, per platform.

Source: the agents design spec under docs/superpowers/specs/, "Decisions", the bullet on heavy runs: "It runs that
command at niceness 19 and the host's lowest I/O priority, by the line one pure function gives, `wrapped(command,
platform, niceness)`, where `platform` is the host as `sys.platform` names it, `linux` or `darwin`, and `niceness` is
the caller's own and the wrapper passes its process's, read with `os.getpriority(os.PRIO_PROCESS, 0)`: on Linux
`ionice -c3 nice -n <k> -- <command>`, on macOS `taskpolicy -b nice -n <k> -- <command>`, where `k` is 19 − niceness,
since `nice -n` adds to a niceness rather than setting it, and a caller at 19 or above, macOS's ceiling being 20, gets
`nice -n 0`; the `--` ends `nice`'s options, so any command is run as given, one whose first word begins with `-`
included; each tool is found on `PATH`; on any other host `wrapped` gives None."

The function is pure, so the line is held whole: each tool is named bare, for `PATH` to find, and a tool named by a fixed
path breaks it. A platform is named here as Python names its host in `sys.platform`, `linux` for Linux and `darwin` for
macOS; the spec says only "on Linux" and "on macOS".
"""

import pytest

from gates import heavy

COMMAND = ["make", "check", "two words", "-n", "0", "--lock", "other"]

PLATFORMS = {
    "linux": False,
    "darwin": False,
    "win32": True,
    "cygwin": True,
    "freebsd14": True,
    "aix": True,
    "emscripten": True,
}

STEPS = [(0, "19"), (7, "12"), (19, "0")]


def test_platforms_without_line() -> None:
    """Linux and macOS each get a line; every other host gets None."""
    assert {platform: heavy.wrapped(COMMAND, platform, 0) is None for platform in PLATFORMS} == PLATFORMS


@pytest.mark.parametrize(("niceness", "step"), STEPS)
def test_darwin_line(niceness: int, step: str) -> None:
    """The macOS line is taskpolicy -b, then nice -n k, then --, then the command.

    Here k is 19 less the caller's niceness, floored at 0.
    """
    assert heavy.wrapped(COMMAND, "darwin", niceness) == ["taskpolicy", "-b", "nice", "-n", step, "--", *COMMAND]


@pytest.mark.parametrize(("niceness", "step"), STEPS)
def test_linux_line(niceness: int, step: str) -> None:
    """The Linux line is ionice -c3, then nice -n k, then --, then the command.

    Here k is 19 less the caller's niceness, floored at 0.
    """
    assert heavy.wrapped(COMMAND, "linux", niceness) == ["ionice", "-c3", "nice", "-n", step, "--", *COMMAND]
