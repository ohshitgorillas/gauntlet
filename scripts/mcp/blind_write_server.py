#!/usr/bin/env python3
"""The `scrivener`'s one writing tool, served over MCP: `format`.

    python3 scripts/mcp/blind_write_server.py              serve on stdin and stdout
    python3 scripts/mcp/blind_write_server.py --self-test

`format path` runs `scripts/blind.sh format` as an argv list, with no shell
between them, and `blind.sh` rewrites that one test file with the fix tools of
its extension under `bwrap`, the lane bound writable and nothing else. The path
is checked by `blind_server.check_path`, the function the `test` tool's path
goes through, so the two servers cannot part on which files a blind agent names.

It is a server of its own, apart from `blind`, because it writes. A server's
tools reach every agent that admits its wildcard, and the `bailiff` admits
`blind`. Served alone, the writing tool sits behind one `PreToolUse` matcher
that names the whole server, and `hooks/blind-write.py` denies every caller but
the `scrivener`.

What comes back is whether the file is now clean, never the fix tools' output:
the file is on disk for the writer to read, and a fault no fix tool repairs is
the writer's to fix by `Edit` and find again with `test`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import blind_server
import rpc

#: `ruff` and `black` over one file, or `eslint --fix`, which `npx` may fetch first
FORMAT_TIMEOUT = 300

NAME = "blind-write"
VERSION = "1"

CLEAN = "clean\n"
UNCLEAN = (
    "not clean: a fault remains that no fix tool repairs. Fix it by Edit, "
    "and run the file through test.\n"
)

TOOLS = (
    rpc.Tool(
        "format",
        "Rewrite one test file of yours with the fix tools of its extension, through "
        "blind.sh format. Returns clean, or that a fault remains that no fix tool repairs.",
        {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The test file, as .claude/worktrees/<slug>-spec/<tests dir>/"
                    "<file> from the main checkout, or <tests dir>/<file> inside a tree.",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    ),
)


def check(arguments: dict[str, Any], tests: str) -> str:
    """The one path `format` takes, checked against its type."""
    extra = sorted(set(arguments) - {"path"})
    if extra:
        raise blind_server.Refused(f"unknown argument: {', '.join(extra)}")
    path = arguments.get("path")
    if not isinstance(path, str):
        raise blind_server.Refused("path must be a string")
    return blind_server.check_path(path, tests)


def handle(name: str, arguments: dict[str, Any], cwd: Path | None = None) -> rpc.Reply:
    """Answer one `format` call; the loop has already refused any other name."""
    where = cwd or blind_server.project()
    try:
        path = check(arguments, blind_server.tests_dir(where))
    except blind_server.Refused as refusal:
        return rpc.Reply(str(refusal), error=True)
    try:
        done = blind_server.run([name, path], where, FORMAT_TIMEOUT)
    except subprocess.TimeoutExpired:
        return rpc.Reply(f"blind.sh {name} ran past {FORMAT_TIMEOUT}s", error=True)
    except OSError as failure:
        return rpc.Reply(f"blind.sh did not start: {failure}", error=True)
    if done.returncode == 0:
        return rpc.Reply(CLEAN)
    if done.returncode == 1:
        return rpc.Reply(UNCLEAN)
    return blind_server.fault(done)


SERVER = rpc.Server(NAME, VERSION, TOOLS, handle)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from blind_write_server_selftest import self_test

        sys.exit(self_test())
    sys.exit(rpc.serve(SERVER))
