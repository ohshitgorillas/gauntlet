"""Execution tests for the blind agents' MCP server, scripts/mcp/blind_server.py.

Each test drives the server as the host does: one JSON-RPC message per line on
stdin, one per line back on stdout. The fixture checkout carries a copy of the
kit's blind.sh and the server beside it, and a spec worktree opened by pair.sh,
so the `test` tool runs blind.sh under bwrap against that worktree exactly as a
scrivener's call would. The checkouts are built beside this file rather than in
the suite's temporary directory, because blind.sh runs under a private /tmp.
"""

import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.pair_fixture import (
    BLOCK_NEW,
    ENV,
    REVIEWER,
    SLUG,
    _git,
    _pair,
    _repo,
    _worktree,
)

REPO = Path(__file__).resolve().parent.parent
BLIND = REPO / "scripts" / "blind.sh"
MCP = REPO / "scripts" / "mcp"
FIXTURE_ROOT = Path(__file__).resolve().parent / ".blind-server-fixtures"

TARGET_NAME = "test_target.py"
TARGET_ARG = ".claude/worktrees/" + SLUG + "-spec/tests/" + TARGET_NAME

#: the implementation line a collection error runs through, which no report may carry
SECRET_LINE = 'SECRET_SOURCE_LINE = "the implementation"'
SECRET_MODULE = SECRET_LINE + '\nraise RuntimeError("module import failed")\n'
IMPORT_LINE = "from lib import secret"
IMPORTING_TEST = IMPORT_LINE + "\n\n\ndef test_target():\n    assert secret\n"
#: a parametrize id built from an implementation value, which no report may carry
ID_MARKER = "IMPLEMENTATION_ID_MARKER"
ID_MODULE = 'LEAKED = "' + ID_MARKER + '"\n'
PARAMETRIZED_TEST = (
    "import pytest\n\nfrom lib.secret import LEAKED\n\n\n"
    '@pytest.mark.parametrize("value", [LEAKED])\n'
    "def test_target(value):\n    assert value\n"
)
#: a collection-time exception whose message quotes the implementation, on two lines
EXCEPTION_MARKER = "IMPLEMENTATION_EXCEPTION_MARKER"
EXCEPTION_MODULE = (
    'raise RuntimeError("quoted ' + EXCEPTION_MARKER + "\\n" + EXCEPTION_MARKER + '")\n'
)
#: a node test name built from an implementation value, which no report may carry
NAME_MARKER = "IMPLEMENTATION_NAME_MARKER"
NODE_MODULE = 'module.exports = { LEAKED: "' + NAME_MARKER + '" };\n'
NODE_NAME = "test_target.cjs"
NODE_ARG = ".claude/worktrees/" + SLUG + "-spec/tests/" + NODE_NAME
NODE_TEST = (
    'const test = require("node:test");\n'
    'const { LEAKED } = require("../lib/secret.cjs");\n\n'
    "test(`names ${LEAKED}`, () => {});\n"
)
MIXED_TEST = "def test_one():\n    assert 1 == 1\n\n\ndef test_two():\n    assert 1 == 2\n"
#: pytest's summary order, failures before passes, one id per line
MIXED_VERDICTS = (
    "FAILED tests/" + TARGET_NAME + "::test_two\nPASSED tests/" + TARGET_NAME + "::test_one\n"
)


@pytest.fixture
def fixture_root(request):
    """An empty directory beside this file, removed again after the test."""
    root = FIXTURE_ROOT / request.node.name.replace("[", "-").replace("]", "")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _executable(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _opened(fixture_root):
    """A fixture checkout carrying blind.sh and the server, with its spec worktree open.

    Returns the checkout and its spec worktree. The lint tools are shims that
    always pass, so what a `test` call reports is the test run alone.
    """
    repo = _repo(fixture_root, BLOCK_NEW, REVIEWER)
    shutil.copy2(BLIND, repo / "scripts" / "blind.sh")
    shutil.copytree(MCP, repo / "scripts" / "mcp", ignore=shutil.ignore_patterns("__pycache__"))
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "tests" / TARGET_NAME).write_text(MIXED_TEST)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "target")
    _pair(repo, "open", SLUG)
    for name in ("ruff", "black"):
        _executable(repo / ".venv" / "bin" / name, "#!/bin/sh\nexit 0\n")
    return repo, _worktree(repo)


def _call(repo, name, arguments, shims=None):
    """The `tools/call` result the server answers for one call, after `initialize`."""
    env = dict(ENV)
    if shims is not None:
        env["PATH"] = str(shims) + ":" + env["PATH"]
    env["HOME"] = str(repo)
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    ]
    done = subprocess.run(
        [sys.executable, str(repo / "scripts" / "mcp" / "blind_server.py")],
        cwd=repo,
        env=env,
        input="".join(json.dumps(message) + "\n" for message in messages),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    sys.stderr.write(done.stderr)
    replies = {reply["id"]: reply for reply in map(json.loads, done.stdout.splitlines())}
    return replies[2]["result"]


def _test_report(fixture_root, test_text, module_text=SECRET_MODULE):
    """The text `test` returns for the worktree's target file written `test_text`."""
    repo, tree = _opened(fixture_root)
    (tree / "lib").mkdir()
    (tree / "lib" / "secret.py").write_text(module_text)
    (tree / "tests" / TARGET_NAME).write_text(test_text)
    return _call(repo, "test", {"path": TARGET_ARG})["content"][0]["text"]


def _node_report(fixture_root, test_text):
    """The text `test` returns for the worktree's node target written `test_text`.

    `npx` is a shim that always passes, so the eslint gate reaches no network.
    """
    repo, tree = _opened(fixture_root)
    (tree / "lib").mkdir()
    (tree / "lib" / "secret.cjs").write_text(NODE_MODULE)
    (tree / "tests" / NODE_NAME).write_text(test_text)
    _executable(repo / "shims" / "npx", "#!/bin/sh\nexit 0\n")
    return _call(repo, "test", {"path": NODE_ARG}, repo / "shims")["content"][0]["text"]


def test_test_report_is_one_verdict_line_per_test_id(fixture_root):
    assert _test_report(fixture_root, MIXED_TEST) == MIXED_VERDICTS


def test_test_report_of_a_collection_error_carries_no_implementation_line(fixture_root):
    assert SECRET_LINE not in _test_report(fixture_root, IMPORTING_TEST)


def test_test_report_of_a_collection_error_keeps_the_tests_frame(fixture_root):
    assert "    " + IMPORT_LINE in _test_report(fixture_root, IMPORTING_TEST)


def test_test_report_carries_no_source_text_in_a_parametrize_id(fixture_root):
    assert ID_MARKER not in _test_report(fixture_root, PARAMETRIZED_TEST, ID_MODULE)


def test_test_report_carries_no_source_text_in_a_collection_exception_line(fixture_root):
    assert EXCEPTION_MARKER not in _test_report(fixture_root, IMPORTING_TEST, EXCEPTION_MODULE)


def test_test_report_carries_no_source_text_in_a_node_test_name(fixture_root):
    assert NAME_MARKER not in _node_report(fixture_root, NODE_TEST)


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("test", {"path": "lib/secret.py"}),
        ("test", {"path": "tests/../lib/secret.py"}),
        ("show", {"commit": "HEAD:lib/secret.py", "slug": SLUG}),
        ("status", {"slug": "../" + SLUG}),
        ("status", {"slug": SLUG, "path": "tests/test_a.py"}),
    ],
    ids=["outside-tests", "dot-dot", "commit-with-path", "slug-with-path", "undeclared-arg"],
)
def test_an_argument_failing_its_type_is_refused_as_a_tool_error(fixture_root, name, arguments):
    repo, _tree = _opened(fixture_root)
    assert _call(repo, name, arguments)["isError"] is True


def test_show_returns_the_committed_block(fixture_root):
    repo, _tree = _opened(fixture_root)
    assert _call(repo, "show", {"commit": "HEAD", "slug": SLUG})["content"][0]["text"] == (
        BLOCK_NEW
    )


def test_server_answers_initialize_with_the_tools_capability(fixture_root):
    repo, _tree = _opened(fixture_root)
    env = dict(ENV, CLAUDE_PROJECT_DIR=str(repo))
    done = subprocess.run(
        [sys.executable, str(repo / "scripts" / "mcp" / "blind_server.py")],
        cwd=repo,
        env=env,
        input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert json.loads(done.stdout)["result"]["capabilities"] == {"tools": {}}
