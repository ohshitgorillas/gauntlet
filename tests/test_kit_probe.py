"""Execution tests for hooks/kit-probe.py, run as the host runs it at SessionStart.

Each test writes a real kit into a throwaway directory -- a real manifest and
real files beside it -- points `CLAUDE_PLUGIN_ROOT` at it, runs the hook and
reads what it prints. The server names and script paths are this file's own.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "hooks" / "kit-probe.py"
MANIFEST = ".claude-plugin/plugin.json"
HOOK_PATH = "hooks/one.py"
SERVER_PATH = "scripts/mcp/one_server.py"


def _server(path):
    """One stdio server entry as the manifest spells it, under the plugin root."""
    return {"command": "python3", "args": ["${CLAUDE_PLUGIN_ROOT}/" + path]}


def _said(tmp_path, servers, present):
    """What the probe prints at SessionStart for one kit: stdout and stderr, stripped."""
    manifest = {
        "mcpServers": servers,
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f'python3 "${{CLAUDE_PLUGIN_ROOT}}"/{HOOK_PATH}',
                        }
                    ]
                }
            ]
        },
    }
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    for path in [HOOK_PATH, *present]:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text("", encoding="utf-8")
    env = dict(os.environ)
    env.pop("GAUNTLET", None)
    env["CLAUDE_PLUGIN_ROOT"] = str(tmp_path)
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=60,
    )
    return done.stdout.strip(), done.stderr.strip()


def test_a_missing_server_file_is_named_by_its_key(tmp_path):
    said, _ = _said(tmp_path, {"one": _server(SERVER_PATH)}, present=[])
    assert "one (" in said


def test_a_missing_server_file_is_named_with_its_manifest_path(tmp_path):
    said, _ = _said(tmp_path, {"one": _server(SERVER_PATH)}, present=[])
    assert SERVER_PATH in said


def test_a_kit_whose_servers_are_all_there_prints_nothing(tmp_path):
    said, _ = _said(tmp_path, {"one": _server(SERVER_PATH)}, present=[SERVER_PATH])
    assert said == ""


def test_a_malformed_server_entry_is_named_by_its_key(tmp_path):
    said, _ = _said(
        tmp_path, {"crooked": "not an object", "one": _server(SERVER_PATH)}, present=[SERVER_PATH]
    )
    assert "crooked" in said


def test_a_malformed_server_entry_does_not_crash_the_probe(tmp_path):
    _, err = _said(
        tmp_path, {"crooked": "not an object", "one": _server(SERVER_PATH)}, present=[SERVER_PATH]
    )
    assert err == ""
