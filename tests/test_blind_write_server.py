"""Execution tests for the scrivener's writing server, scripts/mcp/blind_write_server.py.

Each test drives the server as the host does: one JSON-RPC message per line on
stdin, one per line back on stdout. The fixture checkout carries a copy of the
kit's blind.sh and both servers beside it, and a spec worktree opened by
pair.sh, so the `format` tool runs blind.sh under bwrap against that worktree
exactly as a scrivener's call would. The fix tools are ruff and black
themselves, reached through shims in the fixture's .venv, because what is
observed is the bytes they leave. The checkouts are built beside this file
rather than in the suite's temporary directory, because blind.sh runs under a
private /tmp.
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
FIXTURE_ROOT = Path(__file__).resolve().parent / ".blind-write-server-fixtures"

TARGET_NAME = "test_target.py"
TARGET_ARG = ".claude/worktrees/" + SLUG + "-spec/tests/" + TARGET_NAME

#: a missing space after a comma, which black repairs on its own
FIXABLE = "x = [1,2]\n"
#: the same file once black has spaced the list
FORMATTED = "x = [1, 2]\n"
#: an undefined name, which ruff reports and no fix tool repairs
UNREPAIRABLE = "y = undefined_name\n"


@pytest.fixture
def fixture_root(request):
    """An empty directory beside this file, removed again after the test."""
    root = FIXTURE_ROOT / request.node.name.replace("[", "-").replace("]", "")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _shim(path, module):
    """An executable at `path` that runs `module` under this interpreter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!/bin/sh\nexec "' + sys.executable + '" -m ' + module + ' "$@"\n')
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _opened(fixture_root, text):
    """A fixture checkout carrying blind.sh and the servers, its spec worktree open.

    The worktree's target file holds `text`. Returns the checkout and that file.
    """
    repo = _repo(fixture_root, BLOCK_NEW, REVIEWER)
    shutil.copy2(BLIND, repo / "scripts" / "blind.sh")
    shutil.copytree(MCP, repo / "scripts" / "mcp", ignore=shutil.ignore_patterns("__pycache__"))
    (repo / "tests" / TARGET_NAME).write_text("x = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "target")
    _pair(repo, "open", SLUG)
    for name in ("ruff", "black"):
        _shim(repo / ".venv" / "bin" / name, name)
    target = _worktree(repo) / "tests" / TARGET_NAME
    target.write_text(text)
    return repo, target


def _replies(repo, messages, env=None):
    """Every reply the server writes for `messages`, by id, under `env` if one is given."""
    if env is None:
        env = dict(ENV, HOME=str(repo), CLAUDE_PROJECT_DIR=str(repo))
    done = subprocess.run(
        [sys.executable, str(repo / "scripts" / "mcp" / "blind_write_server.py")],
        cwd=repo,
        env=env,
        input="".join(json.dumps(message) + "\n" for message in messages),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    sys.stderr.write(done.stderr)
    return {reply["id"]: reply for reply in map(json.loads, done.stdout.splitlines())}


def _call(repo, arguments, name="format"):
    """The `tools/call` reply the server writes for one call, after `initialize`."""
    return _replies(
        repo,
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        ],
    )[2]


def test_format_rewrites_the_worktree_file(fixture_root):
    repo, target = _opened(fixture_root, FIXABLE)
    _call(repo, {"path": TARGET_ARG})
    assert target.read_text() == FORMATTED


def test_format_of_a_file_it_repairs_answers_clean(fixture_root):
    repo, _target = _opened(fixture_root, FIXABLE)
    assert _call(repo, {"path": TARGET_ARG})["result"]["content"][0]["text"] == "clean\n"


def test_format_of_a_fault_no_fix_tool_repairs_is_not_a_tool_error(fixture_root):
    repo, _target = _opened(fixture_root, UNREPAIRABLE)
    assert _call(repo, {"path": TARGET_ARG})["result"]["isError"] is False


def test_format_of_a_fault_no_fix_tool_repairs_does_not_answer_clean(fixture_root):
    repo, _target = _opened(fixture_root, UNREPAIRABLE)
    assert _call(repo, {"path": TARGET_ARG})["result"]["content"][0]["text"] != "clean\n"


@pytest.mark.parametrize(
    "arguments",
    [
        {"path": "scripts/blind.sh"},
        {"path": "tests/../scripts/blind.sh"},
        {"path": TARGET_ARG, "slug": SLUG},
        {"path": 7},
    ],
    ids=["outside-tests", "dot-dot", "undeclared-arg", "not-a-string"],
)
def test_an_argument_failing_its_type_is_refused_as_a_tool_error(fixture_root, arguments):
    repo, _target = _opened(fixture_root, FIXABLE)
    assert _call(repo, arguments)["result"]["isError"] is True


def test_a_refused_argument_leaves_the_file_untouched(fixture_root):
    repo, target = _opened(fixture_root, FIXABLE)
    _call(repo, {"path": TARGET_ARG, "slug": SLUG})
    assert target.read_text() == FIXABLE


@pytest.mark.parametrize("name", ["test", "status", "show"])
def test_a_reading_tool_is_not_served(fixture_root, name):
    repo, _target = _opened(fixture_root, FIXABLE)
    assert "error" in _call(repo, {"path": TARGET_ARG}, name)


def test_tools_list_names_format_alone(fixture_root):
    repo, _target = _opened(fixture_root, FIXABLE)
    listed = _replies(repo, [{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])[1]
    assert [tool["name"] for tool in listed["result"]["tools"]] == ["format"]


#: a stand-in blind.sh that refuses with its own line carrying a byte that is not UTF-8
RAW_BLIND = "#!/bin/sh\nprintf 'blind.sh: b\\377\\n' >&2\nexit 2\n"
#: that line as the caller reads it
RAW_TEXT = "blind.sh: b\udcff"

FORMAT_CALL = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {"name": "format", "arguments": {"path": TARGET_ARG}},
}


def _format_then_ping(repo):
    """The replies to a `format` call from a missing checkout and a `ping` after it."""
    return _replies(
        repo,
        [FORMAT_CALL, {"jsonrpc": "2.0", "id": 3, "method": "ping"}],
        dict(ENV, HOME=str(repo), CLAUDE_PROJECT_DIR="/nonexistent"),
    )


def test_a_call_from_a_missing_checkout_leaves_the_server_answering(fixture_root):
    repo, _target = _opened(fixture_root, FIXABLE)
    assert _format_then_ping(repo)[3]["result"] == {}


def test_a_call_from_a_missing_checkout_is_a_tool_error(fixture_root):
    repo, _target = _opened(fixture_root, FIXABLE)
    assert _format_then_ping(repo)[2]["result"]["isError"] is True


def test_a_refusal_line_that_is_not_utf8_comes_back_byte_faithful(fixture_root):
    repo, _target = _opened(fixture_root, FIXABLE)
    blind = repo / "scripts" / "blind.sh"
    blind.write_text(RAW_BLIND)
    assert _call(repo, {"path": TARGET_ARG})["result"]["content"][0]["text"] == RAW_TEXT


def test_a_host_that_names_no_project_dir_is_served_from_the_checkout(fixture_root):
    repo, target = _opened(fixture_root, FIXABLE)
    _replies(repo, [FORMAT_CALL], dict(ENV, HOME=str(repo)))
    assert target.read_text() == FORMATTED
