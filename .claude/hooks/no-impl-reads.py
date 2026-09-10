#!/usr/bin/env python3
"""PreToolUse hook: keep a blind agent out of the implementation.

Wired from the `hooks:` frontmatter of `.claude/agents/arbiter.md` and
`.claude/agents/testsmith.md`, so it binds those subagents only. The
orchestrator and every other agent are untouched, deliberately: a session-wide
`permissions.deny` would blind the one agent that has to read the code to
adjudicate a failing test.

The rule those two work under is that a spec is judged, and a test written,
from the behavior contract and never from the code under test. A test shaped
against the implementation mirrors it, and goes green on an implementation
that is wrong in exactly the way its author was wrong. A prompt alone does not
enforce that: the agent that must not peek is the same agent deciding whether
it peeked.

**This hook is an allowlist, not a blocklist.** A blind agent may read the
spec's own sources and nothing else. That is the portable direction — a
blocklist has to know what this repo calls its source directory, and gets it
wrong the first time someone adds one — and it fails closed: an unlisted path
is denied, and the denial names the file to widen.

Allowed by default: `docs/`, `tests/`, `specs/`, and documentation files at the
repo root (`*.md`, `*.txt`, `*.pdf`). Extend it per repo with `blind-reads.json`
beside this file:

    {"allow": ["reference/", "vendor/protocol.h"], "runners": ["pytest", "make"]}

`allow` entries are repo-relative paths, a trailing `/` meaning the directory
and everything under it. `runners` are command names whose output may quote
implementation source — a traceback through the code is the cost of running
the suite at all, and running the suite is the point.

Blocked for those agents:

  * `Read` of any path outside the allowlist
  * `Grep`/`Glob` rooted outside it, and `Grep`/`Glob` with no path at all
    (an unrooted search sweeps the tree and prints matching source lines)
  * a `Bash` command naming a path outside it, by any reader the tool reaches
  * a `Bash` fetch of a served source file from localhost (`.js`, `.css`,
    `.map`, `.ts`, `.py`) — the same source by another road
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys

#: repo-relative paths a blind agent may read; a trailing `/` means the subtree
DEFAULT_ALLOW = ("docs/", "tests/", "specs/")
#: repo-root files a blind agent may read, by extension
DEFAULT_ROOT_FILES = (".md", ".txt", ".pdf")
#: commands whose output may quote source, because running them is the job
DEFAULT_RUNNERS = ("pytest", "make", "node", "npx", "npm", "tox", "cargo", "go")

#: a served source file fetched from a local dev server
SERVED = re.compile(
    r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?/[^\s\"']*\.(?:js|css|map|ts|py)\b"
)

_WHY = (
    "Blind agent: the implementation is out of bounds. Work from the approved spec "
    "block, docs/ and tests/. If the spec does not say what the behavior is, report "
    "that gap instead of reading the code to find out. If this path is genuinely a "
    "spec source, add it to the allow list in hooks/blind-reads.json. "
    "(hooks/no-impl-reads.py)"
)
_UNROOTED = (
    "Give Grep/Glob an explicit path (tests/, docs/, specs/): an unrooted search "
    "sweeps the whole tree and prints its source. " + _WHY
)


def repo_root(start: str) -> str | None:
    path = os.path.abspath(start or ".")
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def config() -> dict:
    """Per-repo widening, from `blind-reads.json` beside this file."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blind-reads.json")
    try:
        with open(path, encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _rules(conf: dict) -> tuple[tuple[str, ...], tuple[str, ...]]:
    allow = tuple(DEFAULT_ALLOW) + tuple(conf.get("allow") or ())
    runners = tuple(DEFAULT_RUNNERS) + tuple(conf.get("runners") or ())
    return allow, runners


def readable(target: str, root: str | None, cwd: str, allow: tuple[str, ...]) -> bool:
    """Is this path one of the spec's own sources?

    Outside a checkout there is no repo-relative path to test, so nothing is
    readable but the allowlisted names appearing as path segments. Failing
    closed there is the point: a blind agent in an unknown tree stays blind.
    """
    if not target:
        return True
    resolved = os.path.abspath(os.path.join(cwd or (root or "."), target))
    if root:
        rel = os.path.relpath(resolved, root)
        if rel.startswith(".."):
            return False
    else:
        rel = resolved.lstrip(os.sep)
    #: the allowlist runs first: `tests` is the allowed directory itself, not a
    #: root file that happens to carry no extension
    for entry in allow:
        name = entry.rstrip("/").replace("/", os.sep)
        if entry.endswith("/"):
            if rel == name or rel.startswith(name + os.sep) or (os.sep + name + os.sep) in (
                os.sep + rel
            ):
                return True
        elif rel == name:
            return True
    #: a documentation file sitting at the repo root, by extension
    return root is not None and os.sep not in rel and (
        os.path.splitext(rel)[1].lower() in DEFAULT_ROOT_FILES
    )


def _names_unreadable(command: str, root: str | None, cwd: str, allow: tuple[str, ...]) -> bool:
    """Does any word of the command look like a path outside the allowlist?"""
    try:
        words = shlex.split(command, comments=False, posix=True)
    except ValueError:
        words = command.split()
    candidates = [
        w
        for w in words[1:]
        #: a URL is not a path: `SERVED` above rules on the ones that carry source,
        #: and an API call over HTTP reaches no file this hook is guarding
        if "://" not in w
        and ("/" in w or os.path.splitext(w)[1])
        and not w.startswith("-")
    ]
    return any(not readable(w, root, cwd, allow) for w in candidates)


def _verdict(name: str, tool_input: dict, root: str | None, cwd: str, conf: dict) -> str | None:
    """Why this call is refused, or None to let it through."""
    allow, runners = _rules(conf)
    if name == "Read":
        return None if readable(tool_input.get("file_path", ""), root, cwd, allow) else _WHY
    if name in ("Grep", "Glob"):
        target = tool_input.get("path")
        if target is None:
            return _UNROOTED
        return None if readable(target, root, cwd, allow) else _WHY
    if name == "Bash":
        command = tool_input.get("command", "")
        if SERVED.search(command):
            return _WHY
        head = os.path.basename(shlex.split(command)[0]) if command.strip() else ""
        if head in runners:
            return None
        return _WHY if _names_unreadable(command, root, cwd, allow) else None
    return None


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        return  # never block on our own failure
    cwd = data.get("cwd") or os.getcwd()
    try:
        reason = _verdict(
            data.get("tool_name", ""), data.get("tool_input") or {}, repo_root(cwd), cwd, config()
        )
    except (ValueError, IndexError):
        reason = None  # never block on our own failure
    if reason is None:
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def self_test() -> int:
    """Pin the three spec lines of the blind-read allowlist."""
    root = "/repo"
    conf: dict = {}

    def call(tool: str, tool_input: dict) -> str | None:
        return _verdict(tool, tool_input, root, root, conf)

    def read(path: str) -> str | None:
        return call("Read", {"file_path": path})

    def bash(cmd: str) -> str | None:
        return call("Bash", {"command": cmd})

    denied, allowed = (lambda v: isinstance(v, str)), (lambda v: v is None)
    lines = {
        "1 the spec's own sources are readable, the rest is not": all(
            (
                allowed(read(f"{root}/docs/testing.md")),
                allowed(read(f"{root}/tests/test_lane.py")),
                allowed(read(f"{root}/specs/approved/slug.txt")),
                allowed(read(f"{root}/README.md")),
                denied(read(f"{root}/src/core/manager.py")),
                denied(read(f"{root}/app/main.py")),
                denied(read("/etc/passwd")),
            )
        ),
        "2 an unrooted search is denied, a rooted one follows the allowlist": all(
            (
                denied(call("Grep", {"pattern": "def resolve"})),
                denied(call("Glob", {"pattern": "**/*.py"})),
                allowed(call("Grep", {"pattern": "def test_", "path": f"{root}/tests"})),
                denied(call("Grep", {"pattern": "def resolve", "path": f"{root}/src"})),
            )
        ),
        "3 shell readers follow the same list, runners and API calls pass": all(
            (
                allowed(bash(f"cat {root}/docs/testing.md")),
                denied(bash(f"cat {root}/src/core/manager.py")),
                denied(bash("sed -n '1,40p' src/core/manager.py")),
                allowed(bash("pytest tests/test_lane.py -q")),
                allowed(bash("curl -s http://127.0.0.1:8090/api/state")),
                denied(bash("curl -s http://127.0.0.1:8090/components/copy.js")),
            )
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test()) if "--self-test" in sys.argv else main()
