"""Red tests for `throttle_line`: the command prefix a heavy checker runs under, per platform and caller's niceness.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`def throttle_line(platform: str, niceness: int, path: str | None = None) -> list[str]  # heavy's line; GateError on a
host with none, or a tool not on `path` (None: os.environ's PATH)`, which replaces "heavy's `wrapped`, `missing` and
`status`". Heavy's line is the agents design spec's, under "Decisions", the bullet on heavy runs: "on Linux `ionice -c3
nice -n <k> -- <command>`, on macOS `nice -n <k> -- <command>`, with no `taskpolicy -b`, ..., where `k` is 19 − niceness,
since `nice -n` adds to a niceness rather than setting it, and a caller at 19 or above, macOS's ceiling being 20, gets
`nice -n 0`; the `--` ends `nice`'s options, so any command is run as given, ...; each tool is found on `PATH`; on any
other host `wrapped` gives None." and "On any other host, or where a tool of the line is not on `PATH`, the wrapper runs
nothing and exits 2". `throttle_line` takes no command, so its line is heavy's line up to and including the `--`, the
command being what a caller puts after it.

A platform is named as `sys.platform` names its host: `linux` for Linux, `darwin` for macOS. Each tool is named bare, for
`PATH` to find, so a tool named by a fixed path breaks the line.

A case that turns on what `PATH` holds hands `throttle_line` its `path`: one directory the test fills with stand-in `nice`
and `ionice` executables. The macOS line with no `path` given looks on the host's own `PATH` and relies on the host's own
`nice`, which POSIX requires on every host that has a `PATH`.
"""

from pathlib import Path

import pytest

from gates.core.checker import throttle_line
from gates.core.report import GateError

TOOL = "#!/bin/sh\nexit 0\n"

EXECUTABLE = 0o755

OTHER_HOSTS = ["win32", "cygwin", "freebsd14", "aix", "emscripten"]

STEPS = [(0, "19"), (7, "12"), (18, "1"), (19, "0"), (20, "0")]


def _tools(tmp_path: Path, tools: tuple[str, ...]) -> str:
    """Make one directory holding only the given stand-in tools, and return it as a PATH."""
    directory = tmp_path / "bin"
    directory.mkdir()
    for name in tools:
        tool = directory / name
        tool.write_text(TOOL, encoding="utf-8")
        tool.chmod(EXECUTABLE)
    return str(directory)


@pytest.mark.parametrize("platform", OTHER_HOSTS)
def test_other_host(tmp_path: Path, platform: str) -> None:
    """A host other than Linux and macOS has no throttle line, with nice and ionice both on the path: a GateError."""
    path = _tools(tmp_path, ("ionice", "nice"))

    with pytest.raises(GateError):
        throttle_line(platform, 0, path=path)


@pytest.mark.parametrize(("niceness", "step"), STEPS)
def test_darwin_line(niceness: int, step: str) -> None:
    """The macOS line is nice -n k, then --, with no taskpolicy -b; k is 19 less the niceness, floored at 0."""
    assert throttle_line("darwin", niceness) == ["nice", "-n", step, "--"]


@pytest.mark.parametrize(("niceness", "step"), STEPS)
def test_linux_line(tmp_path: Path, niceness: int, step: str) -> None:
    """With ionice and nice on the path, the Linux line is ionice -c3, then nice -n k, then --."""
    path = _tools(tmp_path, ("ionice", "nice"))

    assert throttle_line("linux", niceness, path=path) == ["ionice", "-c3", "nice", "-n", step, "--"]


def test_darwin_needs_no_ionice(tmp_path: Path) -> None:
    """On macOS only nice need be on the path: with ionice absent the macOS line still comes back."""
    path = _tools(tmp_path, ("nice",))

    assert throttle_line("darwin", 0, path=path) == ["nice", "-n", "19", "--"]


@pytest.mark.parametrize(
    ("platform", "tools"),
    [("linux", ("nice",)), ("linux", ("ionice",)), ("linux", ()), ("darwin", ("ionice",)), ("darwin", ())],
    ids=["linux-ionice", "linux-nice", "linux-both", "darwin-nice", "darwin-both"],
)
def test_absent(tmp_path: Path, platform: str, tools: tuple[str, ...]) -> None:
    """Where a tool the platform's line needs is not on the path, throttle_line raises a GateError."""
    path = _tools(tmp_path, tools)

    with pytest.raises(GateError):
        throttle_line(platform, 0, path=path)
