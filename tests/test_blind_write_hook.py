"""Execution tests for hooks/blind-write.py, run as the host runs it.

Each test hands the hook one PreToolUse payload on stdin and reads what it
prints: a denial, or nothing, which lets the call through. The payloads name
the server's tool as the host names it for a plugin's server, and differ only
in who is calling.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "hooks" / "blind-write.py"
FORMAT = "mcp__plugin_gauntlet_blind-write__format"


def _decision(tool, agent=None):
    """The permission decision the hook prints for one call, or None for silence."""
    payload = {
        "tool_name": tool,
        "tool_input": {"path": "tests/test_x.py"},
        "cwd": str(REPO),
    }
    if agent is not None:
        payload["agent_type"] = agent
    env = dict(os.environ)
    env.pop("GAUNTLET", None)
    env["CLAUDE_PROJECT_DIR"] = str(REPO)
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=60,
    )
    if not done.stdout.strip():
        return None
    return json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"]


@pytest.mark.parametrize("agent", ["scrivener", "gauntlet:scrivener"])
def test_the_scrivener_is_let_through(agent):
    assert _decision(FORMAT, agent) is None


@pytest.mark.parametrize(
    "agent",
    [None, "", "bailiff", "gauntlet:bailiff", "juror", "arbiter", "general-purpose"],
    ids=["main-agent", "empty", "bailiff", "namespaced-bailiff", "juror", "arbiter", "outsider"],
)
def test_every_other_caller_is_denied(agent):
    assert _decision(FORMAT, agent) == "deny"


def test_a_tool_outside_the_server_is_not_decided():
    assert _decision("mcp__plugin_gauntlet_blind__test", "bailiff") is None
