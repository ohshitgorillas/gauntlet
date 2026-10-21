"""Red tests for the gates core project: its Python files, its test files, its config and its git.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "project.py: the project, its config and
its files", and its decisions 1 and 9 to 13; the quality gates design spec, "Gates", intro, for the Python-file rule
and the files given twice, and "Tests", the pytest strictness bullet, for the one test-file definition.

A Python file "is a file whose name ends in `.py` or `.pyi`, or an extensionless file whose first line is a shebang
that names python; a `.pyw` file is not one". A file given twice, "under one spelling or under two that are the same
path once made absolute, as `a.py` and `./a.py`, is one file ... named as first given": `python_files` keeps one
Source for it, its first spelling as `given`, and `absolute` is `os.path.abspath` of it. Decision 9 says what a path
that names nothing, or an extensionless file that cannot be read, is.

A test file is "a file whose path as given has a `tests` directory component and whose name pytest collects by
default, `test_*.py` or `*_test.py`, and any `conftest.py` beside one". `non_test_files` is every other source. Both
keep the order the sources came in.

The project: `Project.current()` is the working directory, a GateError if it holds no pyproject.toml (decision 1);
`.config` is `root / "pyproject.toml"`; `.settings()` is read once per run, a GateError naming the file if it is
unreadable or not TOML; `.setting(*keys)` is the value at those keys or None (decision 10); `.config_text()` is the raw
text (decision 11); `.git(*arguments)` runs git in the root "without the GIT_ variables a hook exports" (decision 12).
`key_findings` gives "pyproject.toml: <keys>: <says>" for each rule whose key breaks it (decision 13).

`test_files` is called through its module, since pytest would collect the bare name as a test.

The test-shape gates forbid reading `os.environ`, so the variable the git tests know is pytest's own `PYTEST_VERSION`,
and a `GIT_` variable reaches git only through a child started with an environment the test builds from `environment`.
The repository a git test makes is made without the `GIT_` variables, so a hook running the suite cannot redirect it.
"""

import contextlib
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from gates.core.checker import environment
from gates.core import project as core
from gates.core.project import KeyRule, Project, Source, key_findings, non_test_files, python_files
from gates.core.report import Finding, GateError
from tests.support.fake import FakeRunner, completed

CONFIG = "pyproject.toml"

PIN = '[tool.pyright]\npythonVersion = "3.12"\n'


def _seed(path: Path, text: str = "value = 1\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _project(root: Path, text: str = PIN) -> Project:
    _seed(root / CONFIG, text)
    return Project(root)


def _source(given: str) -> Source:
    return Source(given=Path(given), absolute=Path(os.path.abspath(given)))


def _given(sources: list[Source]) -> list[str]:
    return [source.given.as_posix() for source in sources]


# python_files


@pytest.mark.parametrize("name", ["a.py", "a.pyi"])
def test_python_suffix(tmp_path: Path, name: str) -> None:
    """A file whose name ends in .py or .pyi is a Python file, whatever it holds."""
    path = _seed(tmp_path / name, "#!/bin/sh\n")

    assert python_files([path]) == [Source(given=path, absolute=path)]


@pytest.mark.parametrize("shebang", ["#!/usr/bin/env python3\n", "#!/usr/bin/python\n"])
def test_shebang(tmp_path: Path, shebang: str) -> None:
    """An extensionless file whose first line is a shebang naming python is a Python file."""
    path = _seed(tmp_path / "tool", shebang + "value = 1\n")

    assert python_files([path]) == [Source(given=path, absolute=path)]


@pytest.mark.parametrize(
    ("name", "text"),
    [
        pytest.param("a.pyw", "value = 1\n", id="pyw"),
        pytest.param("a.txt", "#!/usr/bin/env python3\n", id="other-suffix"),
        pytest.param("tool", "#!/bin/sh\n", id="shell-shebang"),
        pytest.param("tool", "value = 1\n#!/usr/bin/env python3\n", id="shebang-not-first"),
        pytest.param("tool", "", id="empty"),
    ],
)
def test_not_python(tmp_path: Path, name: str, text: str) -> None:
    """A .pyw file, a file with another suffix, and an extensionless file with no python shebang first are not."""
    assert python_files([_seed(tmp_path / name, text)]) == []


def test_directory(tmp_path: Path) -> None:
    """A directory is no Python file, whatever its name."""
    (tmp_path / "package.py").mkdir()

    assert python_files([tmp_path / "package.py"]) == []


@pytest.mark.parametrize("name", ["gone.py", "gone"])
def test_names_nothing(tmp_path: Path, name: str) -> None:
    """A path that names nothing is no Python file (decision 9)."""
    assert python_files([tmp_path / name, tmp_path / "missing" / name]) == []


def test_unreadable_extensionless(tmp_path: Path) -> None:
    """An extensionless file whose first line cannot be read is taken as a Python file (decision 9)."""
    path = _seed(tmp_path / "tool", "#!/bin/sh\n")
    path.chmod(0)

    assert python_files([path]) == [Source(given=path, absolute=path)]


def test_order(tmp_path: Path) -> None:
    """The Python files keep the order they were given in; the others are dropped from among them."""
    paths = [_seed(tmp_path / name) for name in ["b.py", "notes.txt", "a.pyi", "c.py"]]

    assert python_files(paths) == [Source(given=path, absolute=path) for path in [paths[0], paths[2], paths[3]]]


def test_twice(tmp_path: Path) -> None:
    """A file given twice under one spelling is one Source."""
    path = _seed(tmp_path / "a.py")

    assert python_files([path, path]) == [Source(given=path, absolute=path)]


def test_two_spellings(tmp_path: Path) -> None:
    """`a.py` and `./a.py` are one file, named as first given, its absolute path the working directory's a.py."""
    path = _seed(tmp_path / "a.py")
    with contextlib.chdir(tmp_path):
        sources = python_files([Path("./a.py"), path, Path("a.py")])

    assert sources == [Source(given=Path("./a.py"), absolute=path)]


def test_absolute_is_lexical(tmp_path: Path) -> None:
    """The absolute path is os.path.abspath of the path given: `..` is folded, the spelling kept in `given`."""
    path = _seed(tmp_path / "a.py")
    (tmp_path / "sub").mkdir()
    roundabout = tmp_path / "sub" / ".." / "a.py"

    assert python_files([roundabout, path]) == [Source(given=roundabout, absolute=path)]


# test_files and non_test_files


@pytest.mark.parametrize(
    "given",
    ["tests/test_x.py", "tests/x_test.py", "tmp/tests/test_x.py", "tests/unit/test_x.py", "/r/tests/test_x.py"],
)
def test_test_module(given: str) -> None:
    """A path as given with a `tests` directory component and a name pytest collects by default is a test file."""
    assert _given(core.test_files([_source(given)])) == [given]


@pytest.mark.parametrize(
    "given",
    ["test_x.py", "src/test_x.py", "tests/helper.py", "tests/test_x.pyi", "tests_a/test_x.py", "tests/testx.py"],
)
def test_not_test_module(given: str) -> None:
    """A path with no `tests` directory component, or a name pytest does not collect by default, is no test file."""
    assert core.test_files([_source(given)]) == []


def test_as_given() -> None:
    """The `tests` component is read from the path as given, never from the absolute path."""
    source = Source(given=Path("test_x.py"), absolute=Path("/r/tests/test_x.py"))

    assert core.test_files([source]) == []


def test_conftest_beside() -> None:
    """A conftest.py in the directory of a test module given is a test file."""
    sources = [_source("tests/conftest.py"), _source("tests/test_x.py")]

    assert _given(core.test_files(sources)) == ["tests/conftest.py", "tests/test_x.py"]


def test_conftest_beside_spelling() -> None:
    """A conftest.py beside a test module is one whatever spelling either is given under."""
    sources = [_source("./tests/conftest.py"), _source("tests/./test_x.py")]

    assert _given(core.test_files(sources)) == ["tests/conftest.py", "tests/test_x.py"]


@pytest.mark.parametrize(
    "sources",
    [
        pytest.param(["tests/conftest.py"], id="alone"),
        pytest.param(["tests/conftest.py", "tests/helper.py"], id="beside-helper"),
        pytest.param(["tests/conftest.py", "tests/unit/test_x.py"], id="parent"),
        pytest.param(["tests/unit/conftest.py", "tests/test_x.py"], id="child"),
    ],
)
def test_conftest_not_beside(sources: list[str]) -> None:
    """A conftest.py with no test module given in its own directory is no test file."""
    assert [source for source in _given(core.test_files([_source(given) for given in sources])) if "conftest" in source] == []


def test_test_order() -> None:
    """Test files keep the order the sources came in."""
    sources = [_source(given) for given in ["tests/test_b.py", "tests/conftest.py", "a.py", "tests/a_test.py"]]

    assert _given(core.test_files(sources)) == ["tests/test_b.py", "tests/conftest.py", "tests/a_test.py"]


def test_non_test_files() -> None:
    """Every source that is not a test file, in order; a conftest.py with no test module beside it among them."""
    sources = [_source(given) for given in ["b.py", "tests/test_x.py", "tests/unit/conftest.py", "tests/helper.py"]]

    assert _given(non_test_files(sources)) == ["b.py", "tests/unit/conftest.py", "tests/helper.py"]


# Project


def test_current(tmp_path: Path) -> None:
    """The current project is the working directory."""
    _seed(tmp_path / CONFIG, PIN)
    with contextlib.chdir(tmp_path):
        project = Project.current()

    assert project.root.resolve() == tmp_path.resolve()


def test_current_config_directory(tmp_path: Path) -> None:
    """A working directory whose pyproject.toml is a directory holds no pyproject.toml: a GateError naming the file."""
    (tmp_path / CONFIG).mkdir()
    with contextlib.chdir(tmp_path), pytest.raises(GateError) as raised:
        Project.current()

    assert CONFIG in raised.value.report


def test_current_missing_config(tmp_path: Path) -> None:
    """A working directory with no pyproject.toml at all is a GateError naming the file."""
    with contextlib.chdir(tmp_path), pytest.raises(GateError) as raised:
        Project.current()

    assert CONFIG in raised.value.report


def test_config(tmp_path: Path) -> None:
    """The config is the root's pyproject.toml."""
    assert Project(tmp_path).config == tmp_path / CONFIG


def test_settings(tmp_path: Path) -> None:
    """The settings are the pyproject.toml's tables."""
    assert _project(tmp_path, PIN + "[tool.mutmut]\npaths = [1]\n").settings() == {
        "tool": {"pyright": {"pythonVersion": "3.12"}, "mutmut": {"paths": [1]}}
    }


def test_settings_read_once(tmp_path: Path) -> None:
    """The settings are read once per run: a change to the file after the first read is not seen."""
    project = _project(tmp_path)
    first = project.settings()
    _seed(project.config, "[tool]\nother = 1\n")

    assert project.settings() == first


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("[tool\n", id="not-toml"),
        pytest.param("key = \n", id="no-value"),
    ],
)
def test_settings_not_toml(tmp_path: Path, text: str) -> None:
    """A pyproject.toml that is not TOML is a GateError naming the file."""
    project = _project(tmp_path, text)
    with pytest.raises(GateError) as raised:
        project.settings()

    assert str(project.config) in raised.value.report


def test_settings_not_utf8(tmp_path: Path) -> None:
    """A pyproject.toml that is not UTF-8 is not TOML: a GateError naming the file."""
    project = Project(tmp_path)
    project.config.write_bytes(b'name = "\xff"\n')
    with pytest.raises(GateError) as raised:
        project.settings()

    assert str(project.config) in raised.value.report


@pytest.mark.parametrize("make", ["missing", "directory"])
def test_settings_unreadable(tmp_path: Path, make: str) -> None:
    """A pyproject.toml that cannot be read is a GateError naming the file."""
    project = Project(tmp_path)
    if make == "directory":
        project.config.mkdir()
    with pytest.raises(GateError) as raised:
        project.settings()

    assert str(project.config) in raised.value.report


def test_setting(tmp_path: Path) -> None:
    """A setting is the value at its keys, table by table."""
    assert _project(tmp_path).setting("tool", "pyright", "pythonVersion") == "3.12"


def test_setting_table(tmp_path: Path) -> None:
    """A setting may be a whole table."""
    assert _project(tmp_path).setting("tool", "pyright") == {"pythonVersion": "3.12"}


@pytest.mark.parametrize(
    "keys",
    [
        pytest.param(("tool", "pyright", "strict"), id="last-missing"),
        pytest.param(("tool", "mutmut", "paths"), id="table-missing"),
        pytest.param(("project",), id="top-missing"),
        pytest.param(("tool", "pyright", "pythonVersion", "major"), id="under-a-value"),
    ],
)
def test_setting_absent(tmp_path: Path, keys: tuple[str, ...]) -> None:
    """A setting absent at any of its keys, or under a value that is no table, is None (decision 10)."""
    assert _project(tmp_path).setting(*keys) is None


def test_setting_unreadable(tmp_path: Path) -> None:
    """A setting of a pyproject.toml that cannot be read is a GateError naming the file."""
    project = Project(tmp_path)
    with pytest.raises(GateError) as raised:
        project.setting("tool")

    assert str(project.config) in raised.value.report


def test_config_text(tmp_path: Path) -> None:
    """The config text is the file's raw text, comments included."""
    text = '[tool.ruff.lint]\nignore = ["E501"]  # long lines are fine here\n'

    assert _project(tmp_path, text).config_text() == text


def test_config_text_read_once(tmp_path: Path) -> None:
    """The config text is the text the settings were read from, read once per run (decision 11)."""
    project = _project(tmp_path)
    project.settings()
    _seed(project.config, "# changed\n")

    assert project.config_text() == PIN


def test_config_text_unreadable(tmp_path: Path) -> None:
    """A config text that cannot be read is a GateError naming the file (decision 11)."""
    project = Project(tmp_path)
    with pytest.raises(GateError) as raised:
        project.config_text()

    assert str(project.config) in raised.value.report


# git


def test_git_command(tmp_path: Path) -> None:
    """git runs with the arguments given, in the root, and its Completed is returned as the runner gave it."""
    reply = completed(stdout="diff\n")
    runner = FakeRunner([reply])
    result = Project(tmp_path).git("diff", "HEAD", process=runner)
    command = runner.commands[0]

    assert (result, command.argv, command.cwd) == (reply, ("git", "diff", "HEAD"), tmp_path)


def test_git_environment(tmp_path: Path) -> None:
    """git gets this process's variables, less every GIT_ one (decision 12)."""
    runner = FakeRunner([completed()])
    Project(tmp_path).git("status", process=runner)
    env = runner.commands[0].env
    assert env is not None

    assert ([name for name in env if name.startswith("GIT_")], env.get("PYTEST_VERSION")) == ([], pytest.__version__)


def _init(root: Path) -> None:
    """Make the root a git repository, free of the GIT_ variables a hook running this suite exports."""
    env = {name: value for name, value in environment().items() if not name.startswith("GIT_")}
    subprocess.run(["git", "init", "--quiet", str(root)], env=env, check=True)


def test_git_runs(tmp_path: Path) -> None:
    """git runs for real by default, in the root."""
    _init(tmp_path)
    result = Project(tmp_path).git("rev-parse", "--show-toplevel")

    assert (result.status, Path(result.stdout.strip()).resolve()) == (0, tmp_path.resolve())


@pytest.mark.parametrize(
    "variables",
    [
        pytest.param({"GIT_DIR": "{elsewhere}", "GIT_WORK_TREE": "{elsewhere}"}, id="git-dir-and-work-tree"),
        pytest.param({"GIT_DIR": "{elsewhere}"}, id="git-dir"),
        pytest.param({"GIT_WORK_TREE": "{elsewhere}"}, id="work-tree"),
        pytest.param({"GIT_COMMON_DIR": "{elsewhere}"}, id="common-dir"),
        pytest.param({"GIT_OBJECT_DIRECTORY": "{elsewhere}"}, id="object-directory"),
        pytest.param({"GIT_CONFIG_COUNT": "1"}, id="config-count"),
        pytest.param({"GIT_CONFIG_PARAMETERS": "bogus"}, id="config-parameters"),
    ],
)
def test_git_ignores_hook_variables(tmp_path: Path, variables: dict[str, str]) -> None:
    """None of these GIT_ variables reaches a real git, each on its own: it still finds the root's own repository.

    Every variable here, reaching git, sends `rev-parse --show-toplevel` elsewhere or fails it (decision 12); that every
    GIT_ name is dropped, these and any other, is test_git_drops_every_git_variable's claim.
    """
    _init(tmp_path)
    program = (
        "import sys\nfrom pathlib import Path\nfrom gates.core.project import Project\n"
        "print(Project(Path(sys.argv[1])).git('rev-parse', '--show-toplevel').stdout, end='')\n"
    )
    elsewhere = tmp_path / "elsewhere"
    env = {**environment(), **{name: value.format(elsewhere=elsewhere) for name, value in variables.items()}}
    child = subprocess.run(
        [sys.executable, "-c", program, str(tmp_path)], env=env, capture_output=True, text=True, check=False
    )

    assert (child.returncode, Path(child.stdout.strip()).resolve()) == (0, tmp_path.resolve())


REPO_ROOT = Path(__file__).parents[1]

HOOK_VARIABLES = {
    "GIT_GAUNTLET_UNHEARD_OF": "made up",
    "GIT_INDEX_FILE": "/nonexistent/elsewhere",
    "GIT_NAMESPACE": "x",
    "GIT_CONFIG_KEY_0": "core.bare",
}

LOOKALIKES = {"GIT": "bare", "GITHUB_TOKEN": "kept"}


def test_git_drops_every_git_variable(tmp_path: Path) -> None:
    """Every variable whose name starts with GIT_ is dropped, a made-up one included, not a list of names (decision 12).

    A child starts with these GIT_ variables, calls `git` with a recording runner, and prints the GIT_ names it saw
    itself and those the runner was given. A runner given no environment at all would let git inherit every GIT_
    variable, so the child exits non-zero on it. The prefix is GIT_, not GIT: a name that merely begins GIT, as
    GITHUB_TOKEN, reaches the runner with its value, which the child prints last.
    """
    program = (
        "import sys\nfrom pathlib import Path\nfrom gates.core.checker import environment\n"
        "from gates.core.project import Project\nfrom tests.support.fake import FakeRunner, completed\n"
        "runner = FakeRunner([completed()])\nProject(Path(sys.argv[1])).git('status', process=runner)\n"
        "env = runner.commands[0].env\n"
        "if env is None:\n    sys.exit('git was given no environment, so it inherits every variable')\n"
        "print(' '.join(sorted(n for n in environment() if n.startswith('GIT_'))))\n"
        "print(' '.join(sorted(n for n in env if n.startswith('GIT_'))))\n"
        "print(' '.join(f'{n}={env[n]}' for n in sorted(env) if n.startswith('GIT') and not n.startswith('GIT_')))\n"
    )
    clean = {name: value for name, value in environment().items() if not name.startswith("GIT")}
    child = subprocess.run(
        [sys.executable, "-c", program, str(tmp_path)],
        env={**clean, **HOOK_VARIABLES, **LOOKALIKES},
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert (child.returncode, child.stdout.splitlines()) == (
        0,
        [" ".join(sorted(HOOK_VARIABLES)), "", "GIT=bare GITHUB_TOKEN=kept"],
    )


# key_findings


def _breaks_src(value: object) -> bool:
    return value == ["src"]


def _recorder(asked: list[object]) -> Callable[[object], bool]:
    def breaks(value: object) -> bool:
        asked.append(value)
        return True

    return breaks


MUTMUT = '[tool.mutmut]\npaths_to_mutate = ["src"]\ndo_not_mutate = []\n'


def test_key_finding(tmp_path: Path) -> None:
    """A key whose value breaks its rule is one Finding naming the file, the dotted keys and what the rule says."""
    rule = KeyRule(keys=("tool", "mutmut", "paths_to_mutate"), breaks=_breaks_src, says="narrows the mutated files")

    assert key_findings(_project(tmp_path, MUTMUT), [rule]) == [
        Finding("pyproject.toml: tool.mutmut.paths_to_mutate: narrows the mutated files")
    ]


def test_key_kept(tmp_path: Path) -> None:
    """A key whose value keeps its rule is no finding."""
    rule = KeyRule(keys=("tool", "mutmut", "do_not_mutate"), breaks=_breaks_src, says="ignores")

    assert key_findings(_project(tmp_path, MUTMUT), [rule]) == []


def test_key_absent(tmp_path: Path) -> None:
    """An absent key is no finding, and its rule is never asked (decision 13)."""
    asked: list[object] = []
    rules = [KeyRule(keys=("tool", "coverage", "run", "omit"), breaks=_recorder(asked), says="omits")]

    assert (key_findings(_project(tmp_path, MUTMUT), rules), asked) == ([], [])


def test_key_findings_order(tmp_path: Path) -> None:
    """Findings come in the order of the rules, one for each rule broken."""
    rules = [
        KeyRule(keys=("tool", "mutmut", "paths_to_mutate"), breaks=_breaks_src, says="second"),
        KeyRule(keys=("tool", "mutmut", "do_not_mutate"), breaks=lambda value: value == [], says="first"),
        KeyRule(keys=("tool", "mutmut", "do_not_mutate"), breaks=_breaks_src, says="kept"),
    ]

    assert key_findings(_project(tmp_path, MUTMUT), rules) == [
        Finding("pyproject.toml: tool.mutmut.paths_to_mutate: second"),
        Finding("pyproject.toml: tool.mutmut.do_not_mutate: first"),
    ]


def test_key_findings_unreadable(tmp_path: Path) -> None:
    """A pyproject.toml that cannot be read is a GateError naming the file."""
    project = Project(tmp_path)
    rule = KeyRule(keys=("tool",), breaks=_breaks_src, says="x")
    with pytest.raises(GateError) as raised:
        key_findings(project, [rule])

    assert str(project.config) in raised.value.report

