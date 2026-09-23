#!/usr/bin/env python3
"""PreToolUse hook: the `blind-write` server answers the `scrivener` and nobody else.

Wired from `.claude-plugin/plugin.json` on a matcher that names the whole
server, `mcp__plugin_gauntlet_blind-write__.*`. An MCP server the manifest wires
is in front of every agent in the session, the main agent included, and an
agent definition's `tools:` line narrows that one agent and no other. So the
server's writing tool is held here, by caller: a call whose `agent_type` is not
`scrivener` is denied.

This is an allowlist of one, and it fails closed. An absent `agent_type` is the
main agent, and it is denied like any other caller rather than passed: the tool
writes into the tests lane, which is the `scrivener`'s alone, and a build that
stopped supplying the key for subagents would deny the `scrivener` its tool
rather than hand it to anyone else.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

import hook_payload  # noqa: E402
import hook_shape  # noqa: E402

#: every tool of the server, as the host names it for a plugin's server
SERVER = "mcp__plugin_gauntlet_blind-write__"

#: the tools this hook decides, so a malformed call of one is refused
GUARDS = (SERVER + "format",)

#: the callers the server answers
WRITERS = ("scrivener",)


def verdict(name: str, _tool_input: dict[str, Any], payload: dict[str, Any]) -> str | None:
    """Why this call is refused, or None to let it through."""
    if not name.startswith(SERVER):
        return None
    agent = hook_payload.agent_of(payload)
    if agent in WRITERS:
        return None
    caller = f"`{agent}`" if agent else "the main agent"
    return (
        f"{name} answers the `scrivener` and nobody else, and {caller} is not the "
        "`scrivener`. It writes a test file in the tests lane, which is the "
        "`scrivener`'s alone. (hooks/blind-write.py)"
    )


def main() -> None:
    hook_shape.hook_main(verdict, guards=GUARDS)


def _self_test() -> int:
    """Run the self-test, which lives beside this file in `blind_write_selftest.py`."""
    sys.modules.setdefault("blind-write", sys.modules[__name__])
    return int(importlib.import_module("blind_write_selftest").self_test())


if __name__ == "__main__":
    hook_shape.entry(_self_test, main)
