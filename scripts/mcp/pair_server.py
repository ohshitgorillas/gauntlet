#!/usr/bin/env python3
"""The pair driver's verbs, served over MCP: one tool per `pair.sh` verb.

    python3 scripts/mcp/pair_server.py              serve on stdin and stdout
    python3 scripts/mcp/pair_server.py --self-test

No hook reads a shell command, so a call that moves a block between the
reviewer, the writer and the tree is better made as a typed tool than as a
string a shell parses. Each tool here takes typed fields and nothing else: a
`slug` by `blind_server.SLUG_RE`, a `rev` by `blind_server.COMMIT_RE`, the two
shapes the blind server already holds, so the two servers cannot part on what a
slug or a revision is. Every field is checked before anything runs, and a call
that passes runs `scripts/pair.sh` as an argv list, with no shell between them.

What comes back is the run itself: a JSON object carrying `exit`, `stdout` and
`stderr`, the two streams verbatim. The stdout of each verb is the contract
`docs/agents.md` tables, so nothing here narrows or rewords it. A non-zero exit
marks the result as an error, and the object is the same either way.

`pair.sh` is found beside this directory, as `blind.sh` is, because the kit
travels as one directory. It runs from the project the session stands in, which
the host names in `CLAUDE_PROJECT_DIR`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import blind_server
import rpc

KIT = Path(__file__).resolve().parents[2]
PAIR = KIT / "scripts" / "pair.sh"

#: `red`, `check` and `merge` run the suite or the project's gate; the rest are git steps
GATE_TIMEOUT = 3600
STEP_TIMEOUT = 300
GATED = frozenset({"red", "check", "merge"})

NAME = "pair"
VERSION = "1"

#: each field's shape, from the blind server, which holds them first
SHAPES = {"slug": blind_server.SLUG_RE, "rev": blind_server.COMMIT_RE}

FIELD_SCHEMA = {
    "slug": {"type": "string", "description": "The pair's slug: lowercase letters, digits, dash."},
    "rev": {"type": "string", "description": "A commit: a hash, HEAD or HEAD~N."},
}

#: tool name -> (the `pair.sh` words before the fields, the fields in argv order, what it does)
VERBS: dict[str, tuple[tuple[str, ...], tuple[str, ...], str]] = {
    "open": (
        ("open",),
        ("slug",),
        "Cut the spec worktree and commit the reviewed block (pair.sh open <slug>).",
    ),
    "respec": (
        ("respec",),
        ("slug",),
        "Land a re-approved block on the open spec branch (pair.sh respec <slug>).",
    ),
    "red": (
        ("red",),
        ("slug",),
        "Run the suite in the spec worktree and remove whole-file targets (pair.sh red <slug>).",
    ),
    "check": (
        ("check",),
        ("slug",),
        "Converge the pair and gate it, landing nothing (pair.sh check <slug>).",
    ),
    "merge": (
        ("merge",),
        ("slug",),
        "Land a pair a check passed on the target branch (pair.sh merge <slug>).",
    ),
    "abort": (
        ("abort",),
        ("slug",),
        "Take the pair back out, trees and branches alike (pair.sh abort <slug>).",
    ),
    "close": (
        ("close",),
        ("slug",),
        "Remove the pair's worktrees, keeping every commit (pair.sh close <slug>).",
    ),
    "list": (("list",), (), "The pairs with a recorded base (pair.sh list)."),
    "review": (
        ("review",),
        ("slug",),
        "The path the next spec round is written to (pair.sh review <slug>).",
    ),
    "review_plan": (
        ("review", "plan"),
        ("slug",),
        "The path the next plan round is written to (pair.sh review plan <slug>).",
    ),
    "restore": (
        ("restore",),
        ("slug", "rev"),
        "Put the approved block back as it was at rev (pair.sh restore <slug> <rev>).",
    ),
    "impl_checkout": (
        ("impl", "checkout"),
        ("slug",),
        "Cut the implementation tree, or name the cut one (pair.sh impl checkout <slug>).",
    ),
    "impl_merge": (
        ("impl", "merge"),
        ("slug",),
        "Merge the implementation tree back (pair.sh impl merge <slug>).",
    ),
}

TOOLS = tuple(
    rpc.Tool(
        name,
        summary + " Returns a JSON object: exit, stdout and stderr, verbatim.",
        {
            "type": "object",
            "properties": {field: FIELD_SCHEMA[field] for field in fields},
            "required": list(fields),
            "additionalProperties": False,
        },
    )
    for name, (_, fields, summary) in VERBS.items()
)

#: what runs one checked argv: the words, the checkout and the timeout in, the run out
Runner = Callable[[list[str], Path, int], subprocess.CompletedProcess[str]]


class Refused(Exception):
    """An argument that fails its type, named for the caller."""


def project() -> Path:
    """The checkout the session stands in."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())


def check(name: str, arguments: dict[str, Any]) -> list[str]:
    """The `pair.sh` argv words for one call, each field checked against its shape."""
    prefix, fields, _ = VERBS[name]
    extra = sorted(set(arguments) - set(fields))
    if extra:
        raise Refused(f"unknown argument: {', '.join(extra)}")
    words = list(prefix)
    for field in fields:
        value = arguments.get(field)
        if not isinstance(value, str):
            raise Refused(f"{field} must be a string")
        if not SHAPES[field].fullmatch(value):
            raise Refused(f"{field} is not a {field}: {value!r}")
        words.append(value)
    return words


def run(words: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    """`pair.sh` with `words` as its argv, from `cwd`, no shell."""
    return subprocess.run(
        [str(PAIR), *words],
        cwd=cwd,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(cwd)},
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def reply(done: subprocess.CompletedProcess[str]) -> rpc.Reply:
    """The run as the caller reads it: exit status and both streams, untouched."""
    body = {"exit": done.returncode, "stdout": done.stdout, "stderr": done.stderr}
    return rpc.Reply(json.dumps(body), error=done.returncode != 0)


def handle(
    name: str, arguments: dict[str, Any], cwd: Path | None = None, runner: Runner = run
) -> rpc.Reply:
    """Answer one tool call; a refused argument runs nothing."""
    try:
        words = check(name, arguments)
    except Refused as refusal:
        return rpc.Reply(str(refusal), error=True)
    timeout = GATE_TIMEOUT if name in GATED else STEP_TIMEOUT
    try:
        done = runner(words, cwd or project(), timeout)
    except subprocess.TimeoutExpired:
        return rpc.Reply(f"pair.sh {' '.join(words)} ran past {timeout}s", error=True)
    except OSError as failure:
        return rpc.Reply(f"pair.sh did not start: {failure}", error=True)
    return reply(done)


SERVER = rpc.Server(NAME, VERSION, TOOLS, handle)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from pair_server_selftest import self_test

        sys.exit(self_test())
    sys.exit(rpc.serve(SERVER))
