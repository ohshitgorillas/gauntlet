"""The project a gate runs in: its Python files, its test files, its one config file, and git in its root."""

import errno
import fnmatch
import os
import re
import stat
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard

from gates.core.checker import Command, Completed, Runner, environment, run
from gates.core.report import Finding, GateError

CONFIG = "pyproject.toml"

PYTHON_SUFFIXES = (".py", ".pyi")

PYTHON_SHEBANG = re.compile(rb"^#!.*python")

# The errors that say a path names nothing: it, or a directory on the way to it, does not exist.
NAMES_NOTHING = frozenset({errno.ENOENT, errno.ENOTDIR})

# The test-file rule's directory: a test file's path as given has a component of this name.
TESTS_DIRECTORY = "tests"

TEST_MODULE_PATTERNS = ("test_*.py", "*_test.py")

CONFTEST = "conftest.py"


@dataclass(frozen=True)
class Source:
    """A file a gate checks: `given` as the caller spelled it, `absolute` its os.path.abspath, the file's identity."""

    given: Path
    absolute: Path


def is_python_file(path: Path) -> bool:
    """Tell whether the path is a Python file: a name ending in .py or .pyi, or an extensionless python-shebang file.

    A path whose kind, or an extensionless one whose first line, cannot be read may be a Python file, and only reading
    it tells, so it is taken as one and its checker reports it unreadable. A path that names nothing is none. The
    path is stat'ed, not asked `Path.is_file()`, which reports False on any error and so cannot tell the two apart.
    """
    named = path.name.endswith(PYTHON_SUFFIXES)
    if not named and path.suffix:
        return False
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            return False
        if named:
            return True
        with path.open("rb") as source:
            first_line = source.readline()
    except OSError as error:
        return error.errno not in NAMES_NOTHING
    return PYTHON_SHEBANG.match(first_line) is not None


def python_files(paths: Sequence[Path]) -> list[Source]:
    """Return the Python files among the paths, in order; a file given twice is one Source, its first spelling kept."""
    sources: dict[str, Source] = {}
    for path in paths:
        absolute = os.path.abspath(path)
        if absolute not in sources and is_python_file(path):
            sources[absolute] = Source(given=path, absolute=Path(absolute))
    return list(sources.values())


def is_test_module(source: Source) -> bool:
    """Tell whether the path as given has a `tests` directory component and a name pytest collects by default."""
    given = source.given
    return TESTS_DIRECTORY in given.parent.parts and any(
        fnmatch.fnmatchcase(given.name, pattern) for pattern in TEST_MODULE_PATTERNS
    )


def test_files(sources: Sequence[Source]) -> list[Source]:
    """Return the test files among the sources, in order: each test module, and each conftest.py beside one."""
    beside = {source.absolute.parent for source in sources if is_test_module(source)}
    return [
        source
        for source in sources
        if is_test_module(source)
        or (source.given.name == CONFTEST and source.absolute.parent in beside)
    ]


def non_test_files(sources: Sequence[Source]) -> list[Source]:
    """Return the sources that are not test files, in order."""
    tests = test_files(sources)
    return [source for source in sources if source not in tests]


def is_table(value: object) -> TypeGuard[Mapping[str, object]]:
    """Tell whether a config value is a table, as TOML's tables are read: a dict keyed by str."""
    return isinstance(value, dict)


class Project:
    """The project in `root`, whose pyproject.toml holds every checker's settings, read once per Project."""

    root: Path

    def __init__(self, root: Path) -> None:
        """Take the project in the root; nothing is read until asked for."""
        self.root = root
        self._text: str | None = None
        self._settings: Mapping[str, object] | None = None

    @classmethod
    def current(cls) -> "Project":
        """Return the project in the working directory.

        Raises GateError when the working directory holds no pyproject.toml.
        """
        project = cls(Path.cwd())
        if not project.config.is_file():
            message = f"{project.config}: no {CONFIG} in the working directory"
            raise GateError(message)
        return project

    @property
    def config(self) -> Path:
        """The root's pyproject.toml, the one file that holds every checker's settings."""
        return self.root / CONFIG

    def config_text(self) -> str:
        """Return the config's raw text, read once per Project.

        Raises GateError naming the file when it cannot be read or is not UTF-8.
        """
        if self._text is None:
            try:
                self._text = self.config.read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError) as error:
                message = f"{self.config}: cannot read: {error}"
                raise GateError(message) from error
        return self._text

    def settings(self) -> Mapping[str, object]:
        """Return the config's tables, read once per Project.

        Raises GateError naming the file when it cannot be read or is not TOML.
        """
        if self._settings is None:
            text = self.config_text()
            try:
                settings: dict[str, object] = tomllib.loads(text)
            except tomllib.TOMLDecodeError as error:
                message = f"{self.config}: not TOML: {error}"
                raise GateError(message) from error
            self._settings = settings
        return self._settings

    def setting(self, *keys: str) -> object | None:
        """Return the value at the keys, table by table; None when a key is absent or a value on the way is no table."""
        value: object = self.settings()
        for key in keys:
            if not is_table(value) or key not in value:
                return None
            value = value[key]
        return value

    def git(self, *arguments: str, process: Runner = run) -> Completed:
        """Run git with the arguments in the root, without any GIT_ variable, as those a hook exports."""
        command = Command(
            argv=("git", *arguments),
            cwd=self.root,
            env=environment(drop_prefixes=("GIT_",)),
        )
        return process(command)


@dataclass(frozen=True)
class KeyRule:
    """A config key, the test its value breaks the rule by, and what a finding on it says."""

    keys: tuple[str, ...]
    breaks: Callable[[object], bool]
    says: str


def key_findings(project: Project, rules: Sequence[KeyRule]) -> list[Finding]:
    """Return one Finding per rule whose key is set and whose value breaks it, in the order of the rules."""
    findings: list[Finding] = []
    for rule in rules:
        value = project.setting(*rule.keys)
        if value is not None and rule.breaks(value):
            findings.append(Finding(f"{CONFIG}: {'.'.join(rule.keys)}: {rule.says}"))
    return findings
