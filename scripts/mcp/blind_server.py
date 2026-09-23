#!/usr/bin/env python3
"""The blind agents' tools, served over MCP: `test`, `status` and `show`.

    python3 scripts/mcp/blind_server.py              serve on stdin and stdout
    python3 scripts/mcp/blind_server.py --self-test

No hook reads a shell command, so a blind agent holds no `Bash`. What it holds
instead is three tools whose arguments are typed fields rather than a string a
shell parses. Each field is checked against its type here, and a call that
passes runs `scripts/blind.sh` as an argv list, with no shell between them:

  * `test path` runs `blind.sh test` and returns the narrowed report, one
    `PASSED`, `FAILED` or `ERROR` line per test id. A collection or import
    error keeps its frames under `<tests dir>/` and its exception line, and
    nothing else: a frame inside the implementation, a traceback's source
    line, an assertion's introspection and the lint gates' output never reach
    the caller.
  * `status slug` runs `blind.sh status`, the porcelain check on that block.
  * `show commit slug` runs `blind.sh show`, the block at that commit.

`blind.sh` is found beside this directory, as `hooks/` is found beside
`scripts/`, because the kit travels as one directory. It runs from the
project the session stands in, which the host names in `CLAUDE_PROJECT_DIR`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rpc

KIT = Path(__file__).resolve().parents[2]
BLIND = KIT / "scripts" / "blind.sh"
READER = KIT / "hooks" / "shell_shapes.py"

#: a test run is the suite and the lint gates under `bwrap`; a status or a show is one git read
TEST_TIMEOUT = 900
READ_TIMEOUT = 60

SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
COMMIT_RE = re.compile(r"[0-9a-f]{7,40}|HEAD(~[0-9]{1,4})?")
TEST_SUFFIXES = (".py", ".js", ".mjs", ".cjs")

#: `blind.sh` opens each gate's output with `--- <label>`, or skips it with `SKIP  <label>`
GATE_RE = re.compile(r"(?:--- (\S+)|SKIP  (\S+)\s.*)")

#: pytest's short summary, which `blind.sh` asks for with `-rfEp`
SUMMARY_HEAD_RE = re.compile(r"=+ short test summary info =+")
SUMMARY_RE = re.compile(r"(PASSED|FAILED|ERROR) (.+?)(?: - .*)?")
COLLECTING_RE = re.compile(r"_+ ERROR collecting (.+?) _+")
SECTION_RE = re.compile(r"(?:_+ .* _+|=+ .* =+|=+)")
FRAME_RE = re.compile(r"(\S.*?):(\d+): in .*")
EXCEPTION_RE = re.compile(r"E   [A-Za-z_][\w.]*: .*")

#: `node --test`, in the TAP reporter and in the spec reporter
TAP_RE = re.compile(r"\s*(not ok|ok) \d+ - (.+?)(?: # .*)?")
SPEC_RE = re.compile(r"\s*([✔✖]) (.+?) \([\d.]+m?s\)")
SPEC_FAILURES = "✖ failing tests:"

NAME = "blind"
VERSION = "1"

TOOLS = (
    rpc.Tool(
        "test",
        "Run one test file of yours through blind.sh test. Returns one PASSED, FAILED or "
        "ERROR line per test id; a collection or import error keeps only its frames under "
        "the tests directory and its exception line.",
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
    rpc.Tool(
        "status",
        "Porcelain status of the approved spec block for a slug, in its spec worktree when "
        "one exists. Any line means the block is untracked or edited.",
        {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
            "additionalProperties": False,
        },
    ),
    rpc.Tool(
        "show",
        "The approved spec block for a slug as committed at a commit (a hash, HEAD or HEAD~N).",
        {
            "type": "object",
            "properties": {"commit": {"type": "string"}, "slug": {"type": "string"}},
            "required": ["commit", "slug"],
            "additionalProperties": False,
        },
    ),
)

#: each tool's arguments, in the order `blind.sh` takes them
FIELDS = {tool.name: tuple(tool.schema["required"]) for tool in TOOLS}


class Refused(Exception):
    """An argument that fails its type, named for the caller."""


@dataclass
class Collected:
    """One `ERROR collecting` section: its target and the lines kept from it."""

    target: str
    kept: list[str]


def project() -> Path:
    """The checkout the session stands in."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())


def tests_dir(cwd: Path) -> str:
    """The project's declared tests directory, through the reader `blind.sh` uses."""
    done = subprocess.run(
        [sys.executable, str(READER), "--config", "tests_dir"],
        cwd=cwd,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(cwd)},
        capture_output=True,
        text=True,
        check=False,
        timeout=READ_TIMEOUT,
    )
    lines = done.stdout.splitlines()
    if done.returncode != 0 or len(lines) != 1:
        raise Refused(f"cannot read tests_dir: {done.stderr.strip()}")
    return lines[0]


def check_path(path: str, tests: str) -> str:
    """`path` if it names a test file under a tests directory, else a refusal."""
    parts = path.split("/")
    if path.startswith("/") or any(part in ("", ".", "..") for part in parts):
        raise Refused(f"path must be relative, with no empty, . or .. part: {path!r}")
    if not path.endswith(TEST_SUFFIXES):
        raise Refused(f"path must end in one of {', '.join(TEST_SUFFIXES)}: {path!r}")
    prefix = f"{tests}/"
    spec_tree = re.fullmatch(r"\.claude/worktrees/([^/]+)-spec/(.+)", path)
    rest = spec_tree.group(2) if spec_tree else path
    if spec_tree and not SLUG_RE.fullmatch(spec_tree.group(1)):
        raise Refused(f"no spec worktree slug in {path!r}")
    if not rest.startswith(prefix):
        raise Refused(f"path must lie under {prefix}: {path!r}")
    return path


def check(name: str, arguments: dict[str, Any], tests: str) -> list[str]:
    """The argv words after the subcommand, each checked against its type."""
    fields = FIELDS[name]
    extra = sorted(set(arguments) - set(fields))
    if extra:
        raise Refused(f"unknown argument: {', '.join(extra)}")
    words = []
    for field in fields:
        value = arguments.get(field)
        if not isinstance(value, str):
            raise Refused(f"{field} must be a string")
        words.append(value)
    checks = {"slug": SLUG_RE, "commit": COMMIT_RE}
    for field, value in zip(fields, words, strict=True):
        if field in checks and not checks[field].fullmatch(value):
            raise Refused(f"{field} is not a {field}: {value!r}")
    if name == "test":
        check_path(words[0], tests)
    return words


def gate_sections(stdout: str) -> dict[str, list[str]]:
    """`blind.sh test` output split by gate label; lines before the first label are dropped."""
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in stdout.splitlines():
        gate = GATE_RE.fullmatch(line)
        if gate:
            current = sections.setdefault(gate.group(1) or gate.group(2), [])
            continue
        if current is not None:
            current.append(line)
    return sections


def _collected(lines: list[str], tests: str) -> list[Collected]:
    """Each collection error, cut to its frames under `tests` and its exception lines."""
    found: list[Collected] = []
    current: Collected | None = None
    in_tests = False
    for line in lines:
        head = COLLECTING_RE.fullmatch(line)
        if head:
            current = Collected(head.group(1), [])
            found.append(current)
            in_tests = False
        elif SECTION_RE.fullmatch(line):
            current = None
        elif current is not None:
            in_tests = _keep(line, tests, in_tests, current.kept)
    return found


def _keep(line: str, tests: str, in_tests: bool, kept: list[str]) -> bool:
    """Keep `line` if it belongs; return whether the frame it sits in is a tests frame."""
    frame = FRAME_RE.fullmatch(line)
    if frame:
        in_tests = frame.group(1).startswith(f"{tests}/")
        if in_tests:
            kept.append(line)
    elif EXCEPTION_RE.fullmatch(line) or (in_tests and line.startswith("    ")):
        kept.append(line)
    else:
        in_tests = False
    return in_tests


def narrow_pytest(lines: list[str], tests: str) -> list[str]:
    """pytest output cut to per-id verdicts, with collection errors' tests frames under them.

    A verdict is read only below the summary header, so a line a failing test
    printed, which pytest replays above it, is never read as one.
    """
    start = next((n for n, line in enumerate(lines) if SUMMARY_HEAD_RE.fullmatch(line)), None)
    if start is None:
        return []
    collected = {error.target: error.kept for error in _collected(lines[:start], tests)}
    report: list[str] = []
    for line in lines[start + 1 :]:
        summary = SUMMARY_RE.fullmatch(line)
        if not summary:
            continue
        verdict, ident = summary.groups()
        report.append(f"{verdict} {ident}")
        report.extend(f"  {kept}" for kept in collected.pop(ident, []))
    return report


def narrow_node(lines: list[str], path: str) -> list[str]:
    """`node --test` output cut to one verdict per test name, in either reporter."""
    verdicts: dict[str, str] = {}
    for line in lines:
        if line.strip() == SPEC_FAILURES:
            break
        tap = TAP_RE.fullmatch(line)
        spec = SPEC_RE.fullmatch(line)
        if tap:
            verdicts.setdefault(tap.group(2), "FAILED" if tap.group(1) == "not ok" else "PASSED")
        elif spec:
            verdicts.setdefault(spec.group(2), "FAILED" if spec.group(1) == "✖" else "PASSED")
    return [f"{verdict} {path}::{name}" for name, verdict in verdicts.items()]


def narrow(stdout: str, tests: str, path: str) -> list[str]:
    """The report `test` returns: the runner's per-id verdicts and nothing else."""
    sections = gate_sections(stdout)
    if "pytest" in sections:
        return narrow_pytest(sections["pytest"], tests)
    if "node" in sections:
        return narrow_node(sections["node"], path)
    return []


def run(words: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    """`blind.sh` with `words` as its argv, from `cwd`, no shell."""
    return subprocess.run(
        [str(BLIND), *words],
        cwd=cwd,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(cwd)},
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def fault(done: subprocess.CompletedProcess[str]) -> rpc.Reply:
    """`blind.sh`'s own refusal lines, and nothing any child printed."""
    own = [line for line in done.stderr.splitlines() if line.startswith("blind.sh: ")]
    return rpc.Reply("\n".join(own) or f"blind.sh exited {done.returncode}", error=True)


def handle(name: str, arguments: dict[str, Any], cwd: Path | None = None) -> rpc.Reply:
    """Answer one tool call."""
    where = cwd or project()
    try:
        tests = tests_dir(where)
        words = check(name, arguments, tests)
    except Refused as refusal:
        return rpc.Reply(str(refusal), error=True)
    timeout = TEST_TIMEOUT if name == "test" else READ_TIMEOUT
    try:
        done = run([name, *words], where, timeout)
    except subprocess.TimeoutExpired:
        return rpc.Reply(f"blind.sh {name} ran past {timeout}s", error=True)
    if done.returncode == 2:
        return fault(done)
    if name != "test":
        if done.returncode != 0:
            return fault(done)
        return rpc.Reply(done.stdout or "clean\n")
    report = narrow(done.stdout, tests, words[0])
    if not report:
        return rpc.Reply("no test result in the run", error=True)
    return rpc.Reply("\n".join(report) + "\n")


SERVER = rpc.Server(NAME, VERSION, TOOLS, handle)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from blind_server_selftest import self_test

        sys.exit(self_test())
    sys.exit(rpc.serve(SERVER))
