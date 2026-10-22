"""Red tests for `python_module`: the Command that runs a Python module with the given arguments, cwd and timeout.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process",
which gives `python_module(module, *arguments: str | Path, cwd: Path, timeout: float | None = None) -> Command` and a
Command's `argv: tuple[str, ...]`; decision 3, which names the command it stands for, `python -m mypy`; and section 2,
where check_mypy hands it `run.project.config`, a Path, among its string arguments. So the argv after the interpreter
is `-m`, the module, then each argument in order as a string, a Path as its own text; the Command's `cwd` is the
directory given and its `timeout` the timeout given, None when none is.

Which interpreter path stands first in argv the documents do not say, so no test pins it; the last test holds only that
`run` runs the module through it, reading a relative Path argument in the given directory.
"""

from pathlib import Path

from gates.core.checker import python_module, run

# The json.tool input, and its --compact rendering: separators "," and ":", then one line break.
DATA = '{"a": 1, "b": [1, 2]}'

COMPACT = '{"a":1,"b":[1,2]}\n'

CAP = 600.0


def test_argv_order(tmp_path: Path) -> None:
    """After the interpreter, argv is -m, the module, then each argument in order, a Path as its own text."""
    command = python_module(
        "mypy",
        "--config-file",
        Path("conf") / "pyproject.toml",
        "--no-error-summary",
        cwd=tmp_path,
    )

    assert command.argv[1:] == (
        "-m",
        "mypy",
        "--config-file",
        "conf/pyproject.toml",
        "--no-error-summary",
    )


def test_argv_no_arguments(tmp_path: Path) -> None:
    """With no arguments, argv after the interpreter is -m and the module, and nothing else."""
    assert python_module("pytest", cwd=tmp_path).argv[1:] == ("-m", "pytest")


def test_cwd(tmp_path: Path) -> None:
    """The Command's cwd is the directory given, as given."""
    place = tmp_path / "place"

    assert python_module("mypy", "--version", cwd=place).cwd == place


def test_timeout(tmp_path: Path) -> None:
    """The Command's timeout is the timeout given."""
    assert python_module("mutmut", "run", cwd=tmp_path, timeout=CAP).timeout == CAP


def test_no_timeout(tmp_path: Path) -> None:
    """With no timeout given, the Command runs in the directory given and has no timeout."""
    command = python_module("pytest", "-q", cwd=tmp_path)

    assert (command.cwd, command.timeout) == (tmp_path, None)


def test_runs_module(tmp_path: Path) -> None:
    """Run, the Command runs the module with its arguments in the directory given: json.tool reads a relative path."""
    (tmp_path / "data.json").write_text(DATA, encoding="utf-8")

    command = python_module("json.tool", "--compact", Path("data.json"), cwd=tmp_path)

    assert run(command).stdout == COMPACT
