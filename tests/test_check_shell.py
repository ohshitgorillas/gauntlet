# Copyright 2026 oh shit, gorillas!
"""Red tests for the gate that blocks shell-command parsing in Gauntlet's own code.

Source: docs/superpowers/specs/m1-core-records-design.md, "`gates/check_shell.py`", first paragraph after the stubs:
"A prohibited AST use is an import or from-import of shlex, bashlex, bashparser, bashparserlib or shellparse, their
submodules included; an importlib.import_module or __import__ call with one of those literal module names; or
shell=True passed to subprocess execution. Resolve aliases of importlib, __import__, subprocess and their directly
imported names in the module's imports. [...] A shadowed or dynamically computed target is not falsely claimed to be
resolved." The second paragraph: "Configuration command strings travel verbatim [...] Tests exercise every prohibited
syntax and alias form, safe opaque storage/forwarding, shadowing [...]". docs/design.md §1, "No shell command is ever
parsed", names this gate as the one exception.

Findings apply to gauntlet/ code, so every seeded file sits under `gauntlet/`. The quality-gates design's Gates
section requires exit 1 for findings and exit 0 for clean runs; the comparisons also retain the clean-run contrast.
"""

from pathlib import Path

import pytest

from gates.check_shell import main
from tests.support.project import scaffold

CLEAN = "VALUE = 1\n"


def _status(root: Path, source: str, name: str) -> int:
    """Seed the file in a project tree carrying the repository's own pyproject.toml, so the gate runs under its settings."""
    scaffold(root, {f"gauntlet/{name}": source})
    return main([Path("gauntlet") / name])


def _differs_from_clean(
    root: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> bool:
    """Run from the seeded root, so `gauntlet/` is a top-level folder of the inputs."""
    monkeypatch.chdir(root)
    status = _status(root, source, "seeded.py")
    clean = _status(root, CLEAN, "clean.py")
    return status != clean and status == 1 and clean == 0


def _matches_clean(root: Path, monkeypatch: pytest.MonkeyPatch, source: str) -> bool:
    """Run from the seeded root, so `gauntlet/` is a top-level folder of the inputs."""
    monkeypatch.chdir(root)
    status = _status(root, source, "seeded.py")
    clean = _status(root, CLEAN, "clean.py")
    return status == clean and status == 0 and clean == 0


PROHIBITED_SYNTAX = [
    pytest.param("import shlex\n", id="import-shlex"),
    pytest.param("import bashlex\n", id="import-bashlex"),
    pytest.param("import bashparser\n", id="import-bashparser"),
    pytest.param("import bashparserlib\n", id="import-bashparserlib"),
    pytest.param("import shellparse\n", id="import-shellparse"),
    pytest.param("import os, shlex\n", id="import-second-of-two"),
    pytest.param("from shlex import split\n", id="from-shlex"),
    pytest.param("from bashlex import parse\n", id="from-bashlex"),
    pytest.param("from bashparser import parse\n", id="from-bashparser"),
    pytest.param("from bashparserlib import parse\n", id="from-bashparserlib"),
    pytest.param("from shellparse import parse\n", id="from-shellparse"),
    pytest.param("import bashlex.parser\n", id="import-submodule"),
    pytest.param("import shellparse.tokens.words\n", id="import-deep-submodule"),
    pytest.param("from bashlex.parser import parse\n", id="from-submodule"),
    pytest.param(
        "def load() -> None:\n    import shlex\n\n    print(shlex)\n",
        id="import-inside-function",
    ),
    pytest.param(
        'import importlib\n\nmodule = importlib.import_module("shlex")\n',
        id="import-module-shlex",
    ),
    pytest.param(
        'import importlib\n\nmodule = importlib.import_module("bashparserlib")\n',
        id="import-module-bashparserlib",
    ),
    pytest.param('module = __import__("shlex")\n', id="dunder-import-shlex"),
    pytest.param('module = __import__("bashparser")\n', id="dunder-import-bashparser"),
    pytest.param(
        'import subprocess\n\nsubprocess.run("make check", shell=True)\n',
        id="run-shell-true",
    ),
    pytest.param(
        'import subprocess\n\nsubprocess.Popen("make check", shell=True)\n',
        id="popen-shell-true",
    ),
    pytest.param(
        'import subprocess\n\nsubprocess.call("make check", shell=True)\n',
        id="call-shell-true",
    ),
    pytest.param(
        'import subprocess\n\nsubprocess.check_call("make check", shell=True)\n',
        id="check-call-shell-true",
    ),
    pytest.param(
        'import subprocess\n\nsubprocess.check_output("make check", shell=True)\n',
        id="check-output-shell-true",
    ),
    pytest.param(
        'import subprocess\n\nsubprocess.run("make check", check=True, shell=True, text=True)\n',
        id="shell-true-among-keywords",
    ),
]


@pytest.mark.parametrize("source", PROHIBITED_SYNTAX)
def test_prohibited_syntax_is_a_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """Each import, from-import, literal dynamic import and shell=True call the design lists is a prohibited AST use."""
    assert _differs_from_clean(tmp_path, monkeypatch, source)


PROHIBITED_ALIASES = [
    pytest.param("import shlex as words\n", id="import-as"),
    pytest.param("import bashlex.parser as grammar\n", id="import-submodule-as"),
    pytest.param("from shlex import split as cut\n", id="from-import-as"),
    pytest.param(
        'import importlib as loader\n\nmodule = loader.import_module("shlex")\n',
        id="importlib-as",
    ),
    pytest.param(
        'from importlib import import_module\n\nmodule = import_module("bashlex")\n',
        id="from-importlib-import-module",
    ),
    pytest.param(
        'from importlib import import_module as load\n\nmodule = load("shellparse")\n',
        id="from-importlib-import-module-as",
    ),
    pytest.param(
        'from builtins import __import__ as load\n\nmodule = load("shlex")\n',
        id="dunder-import-as",
    ),
    pytest.param(
        'import subprocess as sp\n\nsp.run("make check", shell=True)\n',
        id="subprocess-as",
    ),
    pytest.param(
        'from subprocess import run\n\nrun("make check", shell=True)\n',
        id="from-subprocess-run",
    ),
    pytest.param(
        'from subprocess import Popen as Process\n\nProcess("make check", shell=True)\n',
        id="from-subprocess-popen-as",
    ),
    pytest.param(
        'from subprocess import check_output as grab\n\ngrab("make check", shell=True)\n',
        id="from-subprocess-check-output-as",
    ),
]


@pytest.mark.parametrize("source", PROHIBITED_ALIASES)
def test_aliased_prohibited_use_is_a_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """An alias of importlib, __import__, subprocess or a name imported directly from them is resolved through the module's imports."""
    assert _differs_from_clean(tmp_path, monkeypatch, source)


SAFE_SOURCES = [
    pytest.param(
        'COMMAND = "pytest {ids} | tee log.txt"\n', id="stored-command-string"
    ),
    pytest.param(
        'TEXT = "import shlex"\nOTHER = "shell=True"\nTHIRD = \'__import__("shlex")\'\n',
        id="prohibited-text-in-strings",
    ),
    pytest.param(
        "def forward(command: str) -> str:\n    return command\n",
        id="forwarded-command",
    ),
    pytest.param(
        'import subprocess\n\nsubprocess.run(["make", "check"], check=True)\n',
        id="argument-list-run",
    ),
    pytest.param(
        'import subprocess\n\nsubprocess.run("make check", shell=False)\n',
        id="shell-false",
    ),
    pytest.param(
        "import subprocess\n\n\ndef launch(command: list[str]) -> None:\n"
        "    subprocess.run(command, check=True)\n",
        id="forwarded-argument-list",
    ),
    pytest.param(
        'import importlib\n\nmodule = importlib.import_module("json")\n',
        id="import-module-other-name",
    ),
    pytest.param('module = __import__("json")\n', id="dunder-import-other-name"),
    pytest.param("import shlexer\n", id="name-extending-shlex"),
    pytest.param("import shellparser\n", id="name-extending-shellparse"),
    pytest.param("from bashlexer import parse\n", id="from-name-extending-bashlex"),
    pytest.param("import json.shlex\n", id="shlex-as-a-submodule-of-another"),
    pytest.param(
        "class Runner:\n    def run(self, command: str, shell: bool) -> str:\n"
        "        return command\n\n\n"
        'Runner().run("make check", shell=True)\n',
        id="shell-true-on-own-method",
    ),
    pytest.param(
        "def run(command: str, shell: bool) -> str:\n    return command\n\n\n"
        'run("make check", shell=True)\n',
        id="shell-true-on-own-function",
    ),
]


@pytest.mark.parametrize("source", SAFE_SOURCES)
def test_safe_source_ends_as_a_clean_file_does(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """Opaque command storage and forwarding, other module names and shell=True on non-subprocess calls are not prohibited uses."""
    assert _matches_clean(tmp_path, monkeypatch, source)


SHADOWED_OR_COMPUTED = [
    pytest.param(
        "from subprocess import run\n\n\n"
        "def run(command: str, shell: bool) -> str:\n    return command\n\n\n"
        'run("make check", shell=True)\n',
        id="imported-run-redefined",
    ),
    pytest.param(
        'from subprocess import run\n\nrun = print\nrun("make check", shell=True)\n',
        id="imported-run-reassigned",
    ),
    pytest.param(
        "import subprocess\n\n\n"
        "def launch(subprocess: object) -> None:\n"
        '    subprocess.run("make check", shell=True)\n',
        id="module-shadowed-by-parameter",
    ),
    pytest.param(
        "from importlib import import_module\n\n\n"
        "def import_module(name: str) -> str:\n    return name\n\n\n"
        'module = import_module("shlex")\n',
        id="import-module-redefined",
    ),
    pytest.param(
        "def __import__(name: str) -> str:\n    return name\n\n\n"
        'module = __import__("shlex")\n',
        id="dunder-import-redefined",
    ),
    pytest.param(
        'import importlib\n\nNAME = "shlex"\nmodule = importlib.import_module(NAME)\n',
        id="import-module-name-in-variable",
    ),
    pytest.param(
        'import importlib\n\nmodule = importlib.import_module("sh" + "lex")\n',
        id="import-module-name-concatenated",
    ),
    pytest.param(
        'NAME = "bashlex"\nmodule = __import__(NAME)\n',
        id="dunder-import-name-in-variable",
    ),
    pytest.param(
        'import subprocess\n\nOPTIONS = {"shell": True}\nsubprocess.run("make check", **OPTIONS)\n',
        id="shell-in-unpacked-mapping",
    ),
]


@pytest.mark.parametrize("source", SHADOWED_OR_COMPUTED)
def test_shadowed_or_computed_target_is_not_claimed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """A name rebound after its import, or a module name or keyword computed at run time, is not claimed as resolved."""
    assert _matches_clean(tmp_path, monkeypatch, source)
