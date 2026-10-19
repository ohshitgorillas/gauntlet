"""Red tests for the pytest strictness gate.

Source: the quality gates design spec under docs/superpowers/specs/, "Tests", the "pytest strictness" bullet, read
with the "Gates" intro paragraph for the exit codes and the count line `<gate>: N finding(s) in M Python file(s)`.
The gate's script is `gates/check_pytest.py`, so `<gate>` is `check_pytest`.

Each run seeds its own test files under a temporary directory and hands them to the gate. Where the order of printed
lines matters, the gate runs in a child interpreter whose stdout and stderr share one unbuffered pipe, so the lines
come back in the order the run printed them and pytest's console output, were it passed on, would land in the same
buffer. The child inherits this process's environment through `env`, which adds only the variables a test names.

Test names and parameter ids are kept short so that each line of pytest's short summary names its exception.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from gates.check_pytest import main

REPO_ROOT = Path(__file__).parents[1]

CHILD = (
    "import sys\n"
    "from pathlib import Path\n\n"
    "from gates.check_pytest import main\n\n"
    "sys.exit(main([Path(arg) for arg in sys.argv[1:]]))\n"
)

JOINED = "FirstPart SecondPart"

MESSAGE = f"ValueError: {JOINED}"

PASSING = "def test_seeded():\n    pass\n"

CALL_FAILS = "def test_seeded():\n    raise ValueError('FirstPart\\nSecondPart')\n"

TWO_CALLS_FAIL = (
    "def test_first():\n    raise ValueError('SeededFirst')\n\n\n"
    "def test_second():\n    raise ValueError('SeededSecond')\n"
)

CLASS_FAILS = "class TestGroup:\n    def test_inner(self):\n        raise ValueError('FirstPart\\nSecondPart')\n"

SETUP_FAILS = (
    "import pytest\n\n\n"
    "@pytest.fixture\ndef broken():\n    raise ValueError('SeededSetup')\n\n\n"
    "def test_seeded(broken):\n    pass\n"
)

TEARDOWN_FAILS = (
    "import pytest\n\n\n"
    "@pytest.fixture\ndef broken():\n    yield\n    raise ValueError('SeededTeardown')\n\n\n"
    "def test_seeded(broken):\n    pass\n"
)

CALL_AND_TEARDOWN_FAIL = (
    "import pytest\n\n\n"
    "@pytest.fixture\ndef broken():\n    yield\n    raise ValueError('SeededTeardown')\n\n\n"
    "def test_seeded(broken):\n    raise ValueError('SeededCall')\n"
)

XFAIL_PASSES = "import pytest\n\n\n@pytest.mark.xfail\ndef test_seeded():\n    pass\n"

WARNS = "import warnings\n\n\ndef test_seeded():\n    warnings.warn('SeededWarning', UserWarning, stacklevel=1)\n"

SEED_RECORDER = (
    "import sys\n"
    "from pathlib import Path\n\n\n"
    "def test_seeded(request):\n"
    "    Path(RECORD).write_text(str(request.config.getoption('randomly_seed')), encoding='utf-8')\n"
    "    print('SeededNoise')\n"
    "    print('SeededNoise', file=sys.stderr)\n"
    "    raise ValueError('FirstPart\\nSecondPart')\n"
)

PLUGINS_ACTIVE = (
    "def test_seeded(request):\n"
    "    manager = request.config.pluginmanager\n"
    "    if not (manager.has_plugin('randomly') and manager.has_plugin('timeout')):\n"
    "        raise RuntimeError('SeededPluginMissing')\n"
    "    if request.config.getoption('randomly_reorganize') is not True:\n"
    "        raise RuntimeError('SeededOrderFixed')\n"
    "    if manager.get_plugin('timeout').get_env_settings(request.config).timeout != 30:\n"
    "        raise RuntimeError('SeededTimeoutOff')\n"
)

FAILING_PLUGIN = "def pytest_runtest_call(item):\n    raise RuntimeError('SeededPlugin')\n"

MISSING_MODULE = "seededmissingmodule"

UNKNOWN_MARKER = "seededmarker"

USAGE_TOKEN = "SeededUsage"

INTERNAL_TOKEN = "SeededInternal"

COLLECTION_ERROR = f"import {MISSING_MODULE}\n\n\ndef test_seeded():\n    pass\n"

MARKED_UNKNOWN = f"import pytest\n\n\n@pytest.mark.{UNKNOWN_MARKER}\ndef test_seeded():\n    pass\n"

COLLECTION_WARNING = (
    "import warnings\n\n"
    "warnings.warn('SeededCollectionWarning', UserWarning, stacklevel=1)\n\n\n"
    "def test_seeded():\n    pass\n"
)

NO_TESTS = "SEEDED_VALUE = 1\n"

USAGE_CONFTEST = f"import pytest\n\n\ndef pytest_configure(config):\n    raise pytest.UsageError('{USAGE_TOKEN}')\n"

INTERNAL_CONFTEST = f"def pytest_collection_modifyitems(items):\n    raise RuntimeError('{INTERNAL_TOKEN}')\n"

LAX_XFAIL = "xfail_strict = false\n"

MISSING_PLUGIN = "seededmissingplugin"

INI_REQUIRES = f"required_plugins = {MISSING_PLUGIN}\n"

TOML_REQUIRES = f'required_plugins = ["{MISSING_PLUGIN}"]\n'

FAILURE_KINDS = [
    pytest.param(CALL_FAILS, id="call"),
    pytest.param(SETUP_FAILS, id="setup"),
    pytest.param(TEARDOWN_FAILS, id="teardown"),
    pytest.param(XFAIL_PASSES, id="xpass"),
    pytest.param(WARNS, id="warning"),
    pytest.param(CALL_AND_TEARDOWN_FAIL, id="both"),
]

SELECTED = [
    pytest.param("tmp/tests/test_x.py", id="nested"),
    pytest.param("tests/x_test.py", id="suffix"),
    pytest.param("tests/deeper/test_x.py", id="below"),
]

NOT_SELECTED = [
    pytest.param("src/test_x.py", id="src"),
    pytest.param("mytests/test_x.py", id="mytests"),
    pytest.param("tests/helper.py", id="helper"),
    pytest.param("tests/test_x.pyi", id="pyi"),
]

NEIGHBOURS = [
    pytest.param("src/test_b.py", id="src"),
    pytest.param("mytests/test_b.py", id="mytests"),
    pytest.param("tests/helper.py", id="helper"),
]

BESIDE_SETTINGS = [
    pytest.param("pytest.ini", f"[pytest]\n{LAX_XFAIL}{INI_REQUIRES}", id="ini"),
    pytest.param(".pytest.ini", f"[pytest]\n{LAX_XFAIL}{INI_REQUIRES}", id="dotini"),
    pytest.param("tox.ini", f"[pytest]\n{LAX_XFAIL}{INI_REQUIRES}", id="tox"),
    pytest.param("setup.cfg", f"[tool:pytest]\n{LAX_XFAIL}{INI_REQUIRES}", id="cfg"),
    pytest.param("pyproject.toml", f"[tool.pytest.ini_options]\n{LAX_XFAIL}{TOML_REQUIRES}", id="toml"),
]

UNFINISHED = [
    pytest.param(COLLECTION_ERROR, None, id="import"),
    pytest.param(MARKED_UNKNOWN, None, id="marker"),
    pytest.param(COLLECTION_WARNING, None, id="warning"),
    pytest.param(PASSING, USAGE_CONFTEST, id="usage"),
    pytest.param(PASSING, INTERNAL_CONFTEST, id="internal"),
    pytest.param(NO_TESTS, None, id="empty"),
]

PYTEST_ERRORS = [
    pytest.param(COLLECTION_ERROR, None, MISSING_MODULE, id="import"),
    pytest.param(MARKED_UNKNOWN, None, UNKNOWN_MARKER, id="marker"),
    pytest.param(PASSING, USAGE_CONFTEST, USAGE_TOKEN, id="usage"),
    pytest.param(PASSING, INTERNAL_CONFTEST, INTERNAL_TOKEN, id="internal"),
]


def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _child(paths: list[Path], *assignments: str) -> subprocess.CompletedProcess[str]:
    command = ["/usr/bin/env", "PYTHONUNBUFFERED=1", *assignments, sys.executable, "-c", CHILD, *map(str, paths)]
    return subprocess.run(  # A child interpreter keeps the gate's stdout and stderr in one ordered buffer.
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def _lines(paths: list[Path]) -> list[str]:
    return _child(paths).stdout.splitlines()


def _last_line(paths: list[Path]) -> str:
    lines = _lines(paths)
    return lines[-1] if lines else ""


def _first_line(paths: list[Path]) -> str:
    lines = _lines(paths)
    return lines[0] if lines else ""


def _second_line(paths: list[Path]) -> str:
    lines = _lines(paths)
    return lines[1] if len(lines) > 1 else ""


def _count_line(findings: int, files: int) -> str:
    return f"check_pytest: {findings} finding(s) in {files} Python file(s)"


def _recorded(record: Path) -> str:
    return record.read_text(encoding="utf-8") if record.exists() else ""


def _recorder(tmp_path: Path) -> tuple[Path, Path]:
    record = tmp_path / "seed.txt"
    test_file = _seed(tmp_path, "tests/test_seeded.py", SEED_RECORDER.replace("RECORD", repr(str(record))))
    return test_file, record


def _finding_pattern(test_id: str) -> str:
    return re.escape(f"{test_id}: {MESSAGE}")


def _report(paths: list[Path], capfd: pytest.CaptureFixture[str]) -> str:
    main(paths)
    captured = capfd.readouterr()
    return captured.out + captured.err


def test_output(tmp_path: Path) -> None:
    """A finished run with one failing test prints its seed line, the one finding line and the count line, nothing else.

    The seeded test prints `SeededNoise` to both streams and fails with a two-line message, so pytest's console output
    holds lines a gate that passed it on would print.
    """
    test_file, record = _recorder(tmp_path)

    output = _child([test_file]).stdout
    pattern = (
        re.escape(f"check_pytest: seed {_recorded(record)}")
        + "\n"
        + _finding_pattern(f"{test_file}::test_seeded")
        + "\n"
        + re.escape(_count_line(1, 1))
        + "\n?"
    )

    assert re.fullmatch(pattern, output)


def test_seed_line(tmp_path: Path) -> None:
    """Before any finding the gate prints `check_pytest: seed N` with the seed pytest-randomly used."""
    test_file, record = _recorder(tmp_path)

    first = _first_line([test_file])

    assert first == f"check_pytest: seed {_recorded(record)}"


def test_fresh_seed(tmp_path: Path) -> None:
    """Two runs over the same failing test print two different seed lines."""
    test_file = _seed(tmp_path, "tests/test_seeded.py", CALL_FAILS)

    first = _first_line([test_file])
    second = _first_line([test_file])

    assert first != second


def test_class_id(tmp_path: Path) -> None:
    """A failing method's id is the given path, then `::TestGroup::test_inner`, then `: ` and the report's message."""
    test_file = _seed(tmp_path, "tests/test_seeded.py", CLASS_FAILS)

    finding = _second_line([test_file])

    assert re.fullmatch(_finding_pattern(f"{test_file}::TestGroup::test_inner"), finding)


def test_given_path(tmp_path: Path) -> None:
    """The id starts with the test file's path exactly as the gate was given it, `..` segment included."""
    (tmp_path / "detour").mkdir()
    _seed(tmp_path, "tests/test_seeded.py", CALL_FAILS)
    given = tmp_path / "detour" / ".." / "tests" / "test_seeded.py"

    finding = _second_line([given])

    assert re.fullmatch(_finding_pattern(f"{given}::test_seeded"), finding)


def test_count_line(tmp_path: Path) -> None:
    """N is the number of failing tests and M the number of test files run."""
    failing = _seed(tmp_path, "tests/test_first.py", TWO_CALLS_FAIL)
    passing = _seed(tmp_path, "tests/test_second.py", PASSING)

    assert _last_line([failing, passing]) == _count_line(2, 2)


@pytest.mark.parametrize("source", FAILURE_KINDS)
def test_kind(tmp_path: Path, source: str) -> None:
    """A failing call, setup or teardown, a passing xfail test and a test raising a warning each make one finding.

    The run prints its seed line, then exactly one finding line for the test, then the count line, and nothing else.
    """
    test_file = _seed(tmp_path, "tests/test_seeded.py", source)

    output = _child([test_file]).stdout
    pattern = (
        re.escape("check_pytest: seed ")
        + "[0-9]+\n"
        + re.escape(f"{test_file}::test_seeded: ")
        + "[^\n]*\n"
        + re.escape(_count_line(1, 1))
        + "\n?"
    )

    assert re.fullmatch(pattern, output)


def test_failing_exit(tmp_path: Path) -> None:
    """A finished run with a failing test exits 1."""
    test_file = _seed(tmp_path, "tests/test_seeded.py", CALL_FAILS)

    assert main([test_file]) == 1


@pytest.mark.parametrize("relative", SELECTED)
def test_selected(tmp_path: Path, relative: str) -> None:
    """A file with a `tests` directory component and a name pytest collects by default is run and counted."""
    test_file = _seed(tmp_path, relative, CALL_FAILS)

    assert _last_line([test_file]) == _count_line(1, 1)


@pytest.mark.parametrize("relative", NOT_SELECTED)
def test_nothing(tmp_path: Path, relative: str) -> None:
    """A run given no test file checked nothing and exits 1, though the file it was given holds a passing test."""
    other = _seed(tmp_path, relative, PASSING)

    assert main([other]) == 1


@pytest.mark.parametrize("relative", NEIGHBOURS)
def test_others(tmp_path: Path, relative: str) -> None:
    """A given file that is not a test file is neither run nor counted beside a test file that is."""
    test_file = _seed(tmp_path, "tests/test_a.py", PASSING)
    other = _seed(tmp_path, relative, CALL_FAILS)

    assert _last_line([test_file, other]) == _count_line(0, 1)


@pytest.mark.parametrize(("name", "settings"), BESIDE_SETTINGS)
def test_beside(tmp_path: Path, name: str, settings: str) -> None:
    """A beside settings file that turns `xfail_strict` off and requires a missing plugin is never read, in any key."""
    test_file = _seed(tmp_path, "tests/test_seeded.py", XFAIL_PASSES)
    _seed(tmp_path, f"tests/{name}", settings)

    assert _last_line([test_file]) == _count_line(1, 1)


@pytest.mark.parametrize(("source", "conftest"), UNFINISHED)
def test_halt(tmp_path: Path, source: str, conftest: str | None) -> None:
    """Anything that stops pytest before or during collection is a run the checker did not finish, exit 2."""
    paths = [_seed(tmp_path, "tests/test_seeded.py", source)]
    if conftest is not None:
        paths.append(_seed(tmp_path, "tests/conftest.py", conftest))

    assert main(paths) == 2


@pytest.mark.parametrize(("source", "conftest", "token"), PYTEST_ERRORS)
def test_error(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    source: str,
    conftest: str | None,
    token: str,
) -> None:
    """An unfinished run prints pytest's own error, which names what stopped it."""
    paths = [_seed(tmp_path, "tests/test_seeded.py", source)]
    if conftest is not None:
        paths.append(_seed(tmp_path, "tests/conftest.py", conftest))

    assert token in _report(paths, capfd)


def test_plugins(tmp_path: Path) -> None:
    """In the run the gate starts, pytest-randomly reorders tests and pytest-timeout holds each to 30 seconds."""
    test_file = _seed(tmp_path, "tests/test_seeded.py", PLUGINS_ACTIVE)

    assert main([test_file]) == 0


def test_addopts(tmp_path: Path) -> None:
    """A `PYTEST_ADDOPTS` that disables both plugins never reaches pytest: order stays random and the timeout 30 s."""
    test_file = _seed(tmp_path, "tests/test_seeded.py", PLUGINS_ACTIVE)

    result = _child([test_file], "PYTEST_ADDOPTS=-p no:randomly -p no:timeout")

    assert result.returncode == 0


def test_plugins_env(tmp_path: Path) -> None:
    """A `PYTEST_PLUGINS` naming a plugin that fails every test never reaches pytest."""
    test_file = _seed(tmp_path, "tests/test_seeded.py", PASSING)
    plugin = _seed(tmp_path, "plugins/seededplugin.py", FAILING_PLUGIN)

    result = _child([test_file], f"PYTHONPATH={plugin.parent}", "PYTEST_PLUGINS=seededplugin")

    assert result.returncode == 0
