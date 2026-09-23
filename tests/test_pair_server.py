"""Execution tests for the pair driver's MCP server, scripts/mcp/pair_server.py.

Each test drives the server as the host does: one JSON-RPC message per line on
stdin, one per line back on stdout. The fixture checkout carries the kit's
pair.sh and the server beside it, so each tool runs pair.sh against that
checkout exactly as a session's call would, and what it returns is compared with
pair.sh run directly on the same checkout.
"""

import importlib.util
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
    _repo,
    _worktree,
)

REPO = Path(__file__).resolve().parent.parent
MCP = REPO / "scripts" / "mcp"

#: a commit no fixture checkout holds, in the shape the server admits
ABSENT_REV = "0" * 40

#: a stand-in pair.sh that prints a CRLF and a byte that is not UTF-8 on both streams
RAW_PAIR = "#!/bin/sh\nprintf 'a\\r\\nb\\377'\nprintf 'a\\r\\nb\\377' >&2\n"
#: what the stand-in printed, as the caller reads it
RAW_TEXT = "a\r\nb\udcff"
#: a slug `pair.sh` admits that a lowercase-only shape would refuse
WIDE_SLUG = "Demo_1.x"


def _rpc():
    """The server's JSON-RPC module, loaded from its file, as the servers load it."""
    spec = importlib.util.spec_from_file_location("mcp_rpc", MCP / "rpc.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rpc = _rpc()


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
        check=False,
        timeout=300,
    )
    return {
        "exit": done.returncode,
        "stdout": rpc.text(done.stdout),
        "stderr": rpc.text(done.stderr),
    }


def _run(result):
    return json.loads(result["content"][0]["text"])


def _session(repo, messages, env):
    """Every reply the server writes for `messages` under `env`, by id."""
    done = subprocess.run(
        [sys.executable, str(repo / "scripts" / "mcp" / "pair_server.py")],
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


LIST_CALL = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list"}}


def _list_then_ping(repo):
    """The replies to a `list` call from a missing checkout and a `ping` after it."""
    return _session(
        repo,
        [LIST_CALL, {"jsonrpc": "2.0", "id": 3, "method": "ping"}],
        dict(_env(repo), CLAUDE_PROJECT_DIR="/nonexistent"),
    )


def test_a_call_from_a_missing_checkout_leaves_the_server_answering(repo):
    assert _list_then_ping(repo)[3]["result"] == {}


def test_a_call_from_a_missing_checkout_is_a_tool_error(repo):
    assert _list_then_ping(repo)[2]["result"]["isError"] is True


def test_pair_sh_streams_come_back_byte_faithful(repo):
    pair = repo / "scripts" / "pair.sh"
    pair.write_text(RAW_PAIR)
    pair.chmod(pair.stat().st_mode | stat.S_IXUSR)
    assert _run(_call(repo, "list", {})) == {"exit": 0, "stdout": RAW_TEXT, "stderr": RAW_TEXT}


def test_a_host_that_names_no_project_dir_is_served_from_the_checkout(repo):
    env = _env(repo)
    del env["CLAUDE_PROJECT_DIR"]
    replies = _session(repo, [LIST_CALL], env)
    assert _run(replies[2]["result"]) == _direct(repo, "list")


@pytest.mark.parametrize(
    ("name", "arguments", "words"),
    [
        ("list", {}, ("list",)),
        ("review", {"slug": SLUG}, ("review", SLUG)),
        ("review", {"slug": WIDE_SLUG}, ("review", WIDE_SLUG)),
        ("review_plan", {"slug": SLUG}, ("review", "plan", SLUG)),
        ("restore", {"slug": SLUG, "rev": ABSENT_REV}, ("restore", SLUG, ABSENT_REV)),
    ],
    ids=["list", "review", "review-wide-slug", "review-plan", "restore-absent-rev"],
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
        ("review", {"slug": "plan"}),
    ],
    ids=[
        "slug-with-path",
        "slug-as-option",
        "undeclared-arg",
        "rev-with-path",
        "missing-rev",
        "review-slug-plan",
    ],
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
