"""Red tests for `environment`: a checker's environment, the running process's variables less those it is told to drop.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process",
which gives `environment(*, drop_prefixes: tuple[str, ...] = (), drop: frozenset[str] = frozenset()) -> dict[str, str]`
as the home that replaces `check_pytest.pytest_environment`; section 2, where the mutation gate hands its checker
`environment(drop_prefixes=("PYTEST_",))`; and the quality gates spec's pytest bullets, which hand pytest "an environment
without `PYTEST_ADDOPTS` and `PYTEST_PLUGINS`". So the result holds every variable of the running process, under its
own value, less every variable whose name starts with one of the prefixes and every variable whose name is in the drop
set; a drop name is a whole name, never a prefix, and a prefix is matched at the start of a name only.

The test-shape gates forbid a test to read or write `os.environ`, so the variables these tests know are the two pytest
documents itself setting in its own process while it runs ("Environment variables" in pytest's reference):
`PYTEST_VERSION`, whose value is `pytest.__version__`, and `PYTEST_CURRENT_TEST`, whose value during a test's call is
the test's node id, its file's path from the rootdir, "::" and its name, followed by " (call)". The second is set only while a test runs, so it also shows that `environment`
reads the process's variables when it is called.

Every other variable is known through a child process started with no env of its own, which inherits the running
process's variables, and the `env -0` it runs prints each as `name=value`, NUL-terminated (`-0` being common to the
BSD and GNU `env`). That child can see more than the process's variables: a library may set a variable in the C
environment alone, as GNU readline, which pytest imports, sets `LINES` and `COLUMNS`. So the child is held only to
hold every variable `environment` gives, under its own value, and what a drop leaves is held against `environment()`
with nothing dropped.
"""

import subprocess

import pytest

from gates.core.checker import environment

VERSION = "PYTEST_VERSION"

CURRENT = "PYTEST_CURRENT_TEST"


def test_value() -> None:
    """With nothing dropped, a variable of the running process is kept under its own value."""
    assert environment()[VERSION] == pytest.__version__


def test_called(request: pytest.FixtureRequest) -> None:
    """The variables are the process's at the call: PYTEST_CURRENT_TEST names this test's call."""
    module = request.path.relative_to(request.config.rootpath).as_posix()

    assert environment()[CURRENT] == f"{module}::{test_called.__name__} (call)"


def test_prefix() -> None:
    """A variable whose name starts with a given prefix is dropped; one whose name does not is kept as it is."""
    env = environment(drop_prefixes=("PYTEST_CURRENT",))

    assert (CURRENT in env, env.get(VERSION)) == (False, pytest.__version__)


def test_any() -> None:
    """Of several prefixes, a name that starts with any one of them is dropped, the first given included."""
    env = environment(drop_prefixes=("PYTEST_CURRENT", "GAUNTLET_NO_SUCH_"))

    assert (CURRENT in env, env.get(VERSION)) == (False, pytest.__version__)


def test_start() -> None:
    """A prefix matches at the start of a name only: one that holds it later, or ends with it, is kept; the last drops."""
    env = environment(drop_prefixes=("_TEST", "PYTEST_V"))

    assert (CURRENT in env, VERSION in env) == (True, False)


def test_drop() -> None:
    """A variable named in the drop set is dropped; one not named there is kept as it is."""
    env = environment(drop=frozenset({CURRENT}))

    assert (CURRENT in env, env.get(VERSION)) == (False, pytest.__version__)


def test_whole() -> None:
    """A drop name is a whole name, never a prefix: names that only start with one are kept."""
    env = environment(drop=frozenset({"PYTEST_", "PYTEST_VERSIO", "PYTEST_CURRENT"}))

    assert (CURRENT in env, VERSION in env) == (True, True)


def _inherited() -> dict[str, str]:
    """The running process's variables as a child it starts with no env of its own sees them, through POSIX env."""
    printed = subprocess.run(["env", "-0"], capture_output=True, check=True).stdout.decode()
    return dict(entry.split("=", 1) for entry in printed.split("\0") if entry)


def test_inherited() -> None:
    """Each variable given is one a child of the running process inherits, under the value that child sees."""
    inherited = _inherited()

    assert {name: inherited.get(name) for name in environment()} == environment()


def test_both() -> None:
    """Given both, exactly the prefixed and the named variables are dropped, and every other one is kept."""
    kept = {name: value for name, value in environment().items() if name not in {CURRENT, VERSION}}

    assert environment(drop_prefixes=("PYTEST_CUR",), drop=frozenset({VERSION})) == kept
