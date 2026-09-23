"""Execution tests for the pair driver's MCP server, scripts/mcp/pair_server.py.

Each test drives the server as the host does: one JSON-RPC message per line on
stdin, one per line back on stdout. The fixture checkout carries the kit's
pair.sh and the server beside it, so each tool runs pair.sh against that
checkout exactly as a session's call would, and what it returns is compared with
pair.sh run directly on the same checkout.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.pair_fixture import (
    BLOCK_NEW,
    ENV,
    REVIEWER,
    SLUG,
    _repo,
    _worktree,
)

REPO = Path(__file__).resolve().parent.parent
MCP = REPO / "scripts" / "mcp"

#: a commit no fixture checkout holds, in the shape the server admits
ABSENT_REV = "0" * 40


@pytest.fixture
def repo(tmp_path):
    """A fixture checkout carrying pair.sh and the MCP servers beside it."""
    checkout = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    shutil.copytree(MCP, checkout / "scripts" / "mcp", ignore=shutil.ignore_patterns("__pycache__"))
    return checkout


def _env(repo):
    env = dict(ENV)
    env["HOME"] = str(repo)
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    return env


def _call(repo, name, arguments):
    """The `tools/call` result the server answers for one call, after `initialize`."""
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
        [sys.executable, str(repo / "scripts" / "mcp" / "pair_server.py")],
        cwd=repo,
        env=_env(repo),
        input="".join(json.dumps(message) + "\n" for message in messages),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    sys.stderr.write(done.stderr)
    replies = {reply["id"]: reply for reply in map(json.loads, done.stdout.splitlines())}
    return replies[2]["result"]


def _direct(repo, *words):
    """pair.sh run on the same checkout with no server between, as the server reports it."""
    done = subprocess.run(
        [str(repo / "scripts" / "pair.sh"), *words],
        cwd=repo,
        env=_env(repo),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    return {"exit": done.returncode, "stdout": done.stdout, "stderr": done.stderr}


def _run(result):
    return json.loads(result["content"][0]["text"])


@pytest.mark.parametrize(
    ("name", "arguments", "words"),
    [
        ("list", {}, ("list",)),
        ("review", {"slug": SLUG}, ("review", SLUG)),
        ("review_plan", {"slug": SLUG}, ("review", "plan", SLUG)),
        ("restore", {"slug": SLUG, "rev": ABSENT_REV}, ("restore", SLUG, ABSENT_REV)),
    ],
    ids=["list", "review", "review-plan", "restore-absent-rev"],
)
def test_a_tool_returns_what_pair_sh_prints_for_its_verb(repo, name, arguments, words):
    assert _run(_call(repo, name, arguments)) == _direct(repo, *words)


def test_a_failing_run_is_a_tool_error(repo):
    assert _call(repo, "restore", {"slug": SLUG, "rev": ABSENT_REV})["isError"] is True


def test_open_cuts_the_spec_worktree(repo):
    _call(repo, "open", {"slug": SLUG})
    assert _worktree(repo).is_dir()


def test_open_returns_the_open_contract_line(repo):
    assert _run(_call(repo, "open", {"slug": SLUG}))["stdout"] == (
        "OPEN .claude/worktrees/" + SLUG + "-spec\n"
    )


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("open", {"slug": "../" + SLUG}),
        ("open", {"slug": "-" + SLUG}),
        ("open", {"slug": SLUG, "rev": "HEAD"}),
        ("restore", {"slug": SLUG, "rev": "HEAD:lib/secret.py"}),
        ("restore", {"slug": SLUG}),
    ],
    ids=["slug-with-path", "slug-as-option", "undeclared-arg", "rev-with-path", "missing-rev"],
)
def test_an_argument_failing_its_type_is_refused_as_a_tool_error(repo, name, arguments):
    assert _call(repo, name, arguments)["isError"] is True


def test_a_refused_open_cuts_no_worktree(repo):
    _call(repo, "open", {"slug": SLUG, "rev": "HEAD"})
    assert not _worktree(repo).exists()


def test_server_lists_one_tool_per_pair_sh_verb(repo):
    done = subprocess.run(
        [sys.executable, str(repo / "scripts" / "mcp" / "pair_server.py")],
        cwd=repo,
        env=_env(repo),
        input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert [tool["name"] for tool in json.loads(done.stdout)["result"]["tools"]] == [
        "open",
        "respec",
        "red",
        "check",
        "merge",
        "abort",
        "close",
        "list",
        "review",
        "review_plan",
        "restore",
        "impl_checkout",
        "impl_merge",
    ]
