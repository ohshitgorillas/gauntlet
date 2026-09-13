#!/usr/bin/env python3
"""Check a landed tests-only change against the block that approved it.

`kind: excision` and `kind: repair` have no implementation phase, so the
post-merge reviewer round that catches a softened test has no window to watch.
What it watched for still happens here, in one move rather than two: the
deletion is itself the softening. This script is that check, and it is
mechanical so it costs no reviewer round.

Run by `scripts/pair.sh merge`, never by a hook: a PreToolUse entry fires on a
tool call, and a comparison of two commits has none.

It reads the committed `gauntlet/specs/approved/<slug>.txt` and prints one line per
target:

    OK <target>            the excision landed
    UNSATISFIED <target>   the target is still there, assertion and all
    MISSING <as-name>      the replacement the line promised never landed
    UNNAMED <path>         a file under tests/ changed that no line names

An excise target is satisfied on either of two facts: the test name is gone
from the file, or the name is present and the line's quoted `assertion:` text
is no longer in that test's own body. Body, not file: the same assertion text
can sit in a sibling test -- a parametrize case, a shared line -- and a
file-wide search would read the target as unsatisfied on a test no line names.

Nothing here reads `replace:`. It holds prose, and prose has no mechanical
reading; `as:` is the field that names what the replacement must land as.
"""

import argparse
import re
import subprocess
import sys

TESTS = "tests/"

_LINE = re.compile(r"^\s*\d+\.\s+excise\s+(?P<target>\S+)\s*$")
_FIELD = re.compile(r"^\s*(?P<key>rule|assertion|replace|as):\s*(?P<value>.*)$")


class Line:
    """One excision or repair line of an approved block."""

    def __init__(self, target: str) -> None:
        self.target = target
        self.assertion = ""
        self.landing = ""  # the `as:` field, empty on a `kind: excision` line

    @property
    def path(self) -> str:
        return self.target.split("::", 1)[0]

    @property
    def test(self) -> str:
        _, _, name = self.target.partition("::")
        return name


def parse_block(text: str) -> list[Line]:
    """The lines of a block, in spec order. Everything below `--- reviewer ---`
    is the reviewer's own output and is not part of the contract."""
    contract, _, _ = text.partition("--- reviewer ---")
    lines: list[Line] = []
    for raw in contract.splitlines():
        head = _LINE.match(raw)
        if head:
            lines.append(Line(head.group("target")))
            continue
        field = _FIELD.match(raw)
        if field and lines:
            key, value = field.group("key"), field.group("value").strip()
            if key == "assertion":
                lines[-1].assertion = value
            elif key == "as":
                lines[-1].landing = value
    return lines


def _git(*args: str) -> tuple[int, str]:
    done = subprocess.run(
        ("git", *args), capture_output=True, text=True, check=False
    )
    return done.returncode, done.stdout


def file_at(rev: str, path: str) -> str | None:
    """The file's content at that commit, or None where it does not exist."""
    code, out = _git("show", f"{rev}:{path}")
    return out if code == 0 else None


def changed_files(base: str, head: str) -> list[str]:
    _, out = _git("diff", "--name-only", base, head, "--", TESTS)
    return [p for p in out.splitlines() if p.strip()]


def test_body(source: str, name: str) -> str | None:
    """The span from `def <name>` to the next definition at that indent, or
    None where the file defines no test of that name."""
    opener = re.compile(rf"^(?P<indent>\s*)(?:async\s+)?def\s+{re.escape(name)}\s*\(")
    rows = source.splitlines()
    for i, row in enumerate(rows):
        start = opener.match(row)
        if not start:
            continue
        indent = len(start.group("indent"))
        body = [row]
        for follow in rows[i + 1:]:
            if follow.strip() and len(follow) - len(follow.lstrip()) <= indent:
                stripped = follow.lstrip()
                if stripped.startswith(("def ", "async def ", "class ", "@")):
                    break
            body.append(follow)
        return "\n".join(body)
    return None


def excision_verdict(line: Line, head: str) -> str:
    """`OK` or `UNSATISFIED` for one excise target."""
    source = file_at(head, line.path)
    if source is None:
        return f"OK {line.target}"
    if not line.test:
        #: a whole-file target: the file itself is what had to stop existing
        return f"UNSATISFIED {line.target}"
    body = test_body(source, line.test)
    if body is None:
        return f"OK {line.target}"
    if line.assertion and line.assertion in body:
        return f"UNSATISFIED {line.target}"
    return f"OK {line.target}"


def landing_verdict(line: Line, head: str) -> str:
    """`OK` or `MISSING` for one `as:` name."""
    path, _, name = line.landing.partition("::")
    source = file_at(head, path)
    if source is not None and name and test_body(source, name) is not None:
        return f"OK {line.landing}"
    return f"MISSING {line.landing}"


def report(block: str, base: str, head: str) -> list[str]:
    lines = parse_block(block)
    named = {line.path for line in lines}
    named.update(line.landing.split("::", 1)[0] for line in lines if line.landing)

    out = [excision_verdict(line, head) for line in lines]
    out += [landing_verdict(line, head) for line in lines if line.landing]
    out += [
        f"UNNAMED {path}" for path in changed_files(base, head) if path not in named
    ]
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", required=True, help="gauntlet/specs/approved/<slug>.txt")
    ap.add_argument("--base", required=True, help="the commit the change started from")
    ap.add_argument("--head", required=True, help="the commit that landed it")
    args = ap.parse_args(argv)

    with open(args.spec, encoding="utf-8") as fh:
        block = fh.read()

    verdicts = report(block, args.base, args.head)
    for verdict in verdicts:
        print(verdict)
    return 0 if all(v.startswith("OK ") for v in verdicts) else 1


def self_test() -> int:
    """Pin the four lines of the merge check."""
    block = (
        "slug: s\nkind: repair\n\n"
        "1. excise tests/test_a.py::test_x\n"
        "   rule: docs/testing.md rule 7\n"
        "   assertion: assert time.monotonic() - start < 2\n"
        "   replace: the poll stops on the condition\n"
        "   as: tests/test_a.py::test_x\n"
    )
    line = parse_block(block)[0]
    kept = (
        "def test_x():\n"
        "    assert time.monotonic() - start < 2\n\n"
        "def test_sibling():\n"
        "    assert other == 1\n"
    )
    sibling = (
        "def test_x():\n"
        "    assert polls == 3\n\n"
        "def test_sibling():\n"
        "    assert time.monotonic() - start < 2\n"
    )
    gone = "def test_sibling():\n    assert other == 1\n"

    lines = {
        "1 a target keeping its assertion is unsatisfied, one that dropped it is OK": (
            line.assertion in (test_body(kept, "test_x") or "")
            and line.assertion not in (test_body(sibling, "test_x") or "")
        ),
        "2 the assertion is read in the target's body, never in a sibling's": (
            line.assertion in sibling
            and line.assertion not in (test_body(sibling, "test_x") or "")
        ),
        "3 a name the file does not define has no body": (
            test_body(gone, "test_x") is None
        ),
        "4 the block parses to its target, assertion and landing name": (
            line.target == "tests/test_a.py::test_x"
            and line.landing == "tests/test_a.py::test_x"
            and line.path == "tests/test_a.py"
            and line.test == "test_x"
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main(sys.argv[1:]))
