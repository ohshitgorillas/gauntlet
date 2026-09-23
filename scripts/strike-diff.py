#!/usr/bin/env python3
"""Check a landed change's tests against the block that approved it.

Two shapes come here. `motion: strike`, `motion: amend` and `motion: rehome` have no
implementation phase, so the post-merge reviewer round that catches a softened
test has no window to watch; what it watched for still happens in one move
rather than two, because the deletion is itself the softening. A `kind:` block
has that phase and takes its reviewer round, and what comes here is its
`collateral:` rows -- tests the change breaks and no behavior line pins, whose
assertions the block promised would survive byte-identical. Both checks are
mechanical, so neither costs a reviewer round.

Run by `scripts/pair.sh merge`, never by a hook: a PreToolUse entry fires on a
tool call, and a comparison of two commits has none.

It reads the committed approved block for a slug and prints one line per
target:

    OK <target>            the strike landed, or the row's assertion survived
    UNSATISFIED <target>   the target is still there, assertion and all,
                           or an in-place rehome's body never changed
    MISSING <name>         the replacement the line promised never landed, or
                           a row's target is no longer defined
    ALTERED <name>         a rehome's landing is there with its assertion
                           rewritten, or a row's target no longer carries the
                           quoted assertion in its own body
    UNNAMED <path>         a file under tests/ changed that no line names

A strike target is satisfied on either of two facts: the test name is gone
from the file, or the name is present and the line's quoted `assertion:` text
is no longer in that test's own body. Body, not file: the same assertion text
can sit in a sibling test -- a parametrize case, a shared line -- and a
file-wide search would read the target as unsatisfied on a test no line names.

Nothing here reads `replace:` or `moved:`. They hold prose, and prose has no
mechanical reading; `as:` is the field that names what the replacement must
land as.

`motion: rehome` reads its `as:` name the other way round. An amend's
replacement pins behavior the block describes in prose, so the only mechanical
fact is that a test of that name exists. A rehome moves an assertion it says is
unchanged, so the landing is checked for that assertion byte-identical in its
own body, and a landing that rewrote it is `ALTERED` rather than `OK`.

A rehome whose `as:` names its own target is an in-place one: the assertion
survives while what surrounds it moves. Nothing leaves the file, so the two
facts that satisfy a strike cannot hold, and the target is read against `base`
instead -- its body has to differ from the one it had there. A body that is
byte-identical on both sides records nothing and is `UNSATISFIED`.

`--collateral` reads the `collateral:` rows instead of the numbered lines, and
sweeps no unnamed file. A `kind:` block's merge lands every test its writer
wrote for the behavior lines, and no row names one of them, so the `UNNAMED`
line `report()` prints would fire on the whole landed suite.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

_HOOKS = str(Path(__file__).resolve().parent / ".." / "hooks" / "lib")
sys.path.insert(0, _HOOKS)

try:
    import lane_config  # noqa: E402
except ImportError:
    sys.exit(f"strike-diff.py: no lane_config.py in {_HOOKS}: scripts/ ships with hooks/")

#: the blind writer's lane, `tests/` unless `blind-reads.json` names another
TESTS = lane_config.tests_dir() + "/"

_LINE = re.compile(r"^\s*\d+\.\s+strike\s+(?P<target>\S+)\s*$")
_FIELD = re.compile(r"^\s*(?P<key>rule|assertion|replace|as|breaks):\s*(?P<value>.*)$")
#: the structure line, `kind:` or `motion:`, whichever comes first
_KIND = re.compile(r"^\s*(?:kind|motion):\s*(?P<kind>.*?)\s*$")
#: the `collateral:` header of a `kind:` block, and the `- <target>` rows under it
_COLLATERAL = re.compile(r"^\s*collateral:\s*$")
_ROW = re.compile(r"^\s*-\s+(?P<target>\S+)\s*$")


class Line:
    """One strike or amend line, or one `collateral:` row, of an approved block."""

    def __init__(self, target: str) -> None:
        self.target = target
        self.assertion = ""
        self.landing = ""  # the `as:` field, empty on a `motion: strike` line
        self.breaks = ""  # the `breaks:` field, empty outside a `collateral:` row

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


def parse_collateral(text: str) -> list[Line]:
    """The `collateral:` rows of a block, in block order.

    The section sits under the behavior lines and runs to the end of the
    contract, so any later unindented line closes it. A block with no header,
    and a header with no row under it, both read as no rows: the absent section
    is how a block says it breaks nothing.
    """
    contract, _, _ = text.partition("--- reviewer ---")
    rows: list[Line] = []
    inside = False
    for raw in contract.splitlines():
        if _COLLATERAL.match(raw):
            inside = True
            continue
        if not inside:
            continue
        head = _ROW.match(raw)
        if head:
            rows.append(Line(head.group("target")))
            continue
        field = _FIELD.match(raw)
        if field and rows:
            key, value = field.group("key"), field.group("value").strip()
            if key == "assertion":
                rows[-1].assertion = value
            elif key == "breaks":
                rows[-1].breaks = value
        elif raw.strip() and not raw.startswith((" ", "\t")):
            inside = False
    return rows


def block_kind(text: str) -> str:
    """The block's structure line, read from the contract and not the round."""
    contract, _, _ = text.partition("--- reviewer ---")
    for raw in contract.splitlines():
        found = _KIND.match(raw)
        if found:
            return found.group("kind")
    return ""


def _git(*args: str) -> tuple[int, str]:
    done = subprocess.run(("git", *args), capture_output=True, text=True, check=False, timeout=60)
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
        for follow in rows[i + 1 :]:
            if follow.strip() and len(follow) - len(follow.lstrip()) <= indent:
                stripped = follow.lstrip()
                if stripped.startswith(("def ", "async def ", "class ", "@")):
                    break
            body.append(follow)
        return "\n".join(body)
    return None


def moved_in_place(before: str | None, after: str | None, name: str) -> bool:
    """True where the named test's body differs between the two sources.

    The one mechanical fact an in-place rehome can offer: the test is still
    where it was, so what is asked is that it changed for the reason `moved:`
    names.
    """
    was = test_body(before, name) if before is not None and name else None
    now = test_body(after, name) if after is not None and name else None
    return now is not None and now != was


def inplace_strike_verdict(line: Line, base: str, head: str) -> str:
    """`OK` or `UNSATISFIED` for a rehome line whose `as:` is its own target."""
    before = file_at(base, line.path)
    after = file_at(head, line.path)
    if moved_in_place(before, after, line.test):
        return f"OK {line.target}"
    return f"UNSATISFIED {line.target}"


def strike_verdict(line: Line, head: str) -> str:
    """`OK` or `UNSATISFIED` for one strike target."""
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


def rehome_verdict(line: Line, head: str) -> str:
    """`OK`, `MISSING` or `ALTERED` for one `as:` name under `motion: rehome`.

    The motion's whole claim is that the assertion did not change, so the name
    landing is not enough: the quoted text has to be in that test's own body,
    byte for byte.
    """
    path, _, name = line.landing.partition("::")
    source = file_at(head, path)
    body = test_body(source, name) if source is not None and name else None
    if body is None:
        return f"MISSING {line.landing}"
    if line.assertion and line.assertion in body:
        return f"OK {line.landing}"
    return f"ALTERED {line.landing}"


def report(block: str, base: str, head: str) -> list[str]:
    lines = parse_block(block)
    named = {line.path for line in lines}
    named.update(line.landing.split("::", 1)[0] for line in lines if line.landing)
    rehome = block_kind(block) == "rehome"
    landing = rehome_verdict if rehome else landing_verdict

    out = [
        (
            inplace_strike_verdict(line, base, head)
            if rehome and line.landing and line.landing == line.target
            else strike_verdict(line, head)
        )
        for line in lines
    ]
    out += [landing(line, head) for line in lines if line.landing]
    out += [f"UNNAMED {path}" for path in changed_files(base, head) if path not in named]
    return out


def collateral_body_verdict(source: str | None, line: Line) -> str:
    """`OK`, `MISSING` or `ALTERED` for one row, against one file's text.

    The row's whole promise is that the named test's own assertion came through
    the change untouched, so the quoted text is read in that test's body and
    nowhere else. A target the head no longer defines is `MISSING` rather than
    `ALTERED`: a deleted test is a deletion, and reporting it as a rewritten
    assertion would name a softening of a test that is not there.
    """
    body = test_body(source, line.test) if source is not None and line.test else None
    if body is None:
        return f"MISSING {line.target}"
    if line.assertion and line.assertion in body:
        return f"OK {line.target}"
    return f"ALTERED {line.target}"


def collateral_verdict(line: Line, head: str) -> str:
    """The row's verdict against the file as that commit holds it."""
    return collateral_body_verdict(file_at(head, line.path), line)


def collateral_report(block: str, base: str, head: str) -> list[str]:  # noqa: ARG001
    """One verdict per `collateral:` row, and no sweep of the changed files.

    `base` is taken so the call reads like `report()`'s at the one call site
    that makes both, and it is not read: a row's promise is about the head
    alone, and the tests a `kind:` block's writer landed are files no row names.
    """
    return [collateral_verdict(row, head) for row in parse_collateral(block)]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", required=True, help=lane_config.specs_lane() + "/<slug>.txt")
    ap.add_argument("--base", required=True, help="the commit the change started from")
    ap.add_argument("--head", required=True, help="the commit that landed it")
    ap.add_argument(
        "--collateral",
        action="store_true",
        help="read the block's collateral: rows instead of its numbered lines",
    )
    args = ap.parse_args(argv)

    block = Path(args.spec).read_text(encoding="utf-8")

    run = collateral_report if args.collateral else report
    verdicts = run(block, args.base, args.head)
    for verdict in verdicts:
        print(verdict)
    return 0 if all(v.startswith("OK ") for v in verdicts) else 1


def self_test() -> int:
    """Pin the thirteen lines of the merge check."""
    block = (
        "slug: s\nmotion: amend\n\n"
        "1. strike tests/test_a.py::test_x\n"
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
    softened = "def test_x():\n    assert time.monotonic() - start < 9\n"
    in_place = (
        "def test_x():\n"
        "    start = clock.monotonic()\n"
        "    assert time.monotonic() - start < 2\n\n"
        "def test_sibling():\n"
        "    assert other == 1\n"
    )

    rows_block = (
        "slug: s\nkind: new\n\n"
        "1. the banner names the empty set\n"
        "   kills: it names the first row instead\n"
        "\n"
        "collateral:\n"
        "- tests/test_a.py::test_x\n"
        "  breaks: the keyword the helper passes was renamed\n"
        '  assertion: assert banner() == "no rows to show"\n'
    )
    row = parse_collateral(rows_block)[0]
    held = (
        "def test_x():\n"
        '    assert banner() == "no rows to show"\n\n'
        "def test_y():\n"
        "    assert other == 1\n"
    )
    to_sibling = (
        "def test_x():\n"
        '    assert banner() == "nothing here"\n\n'
        "def test_y():\n"
        '    assert banner() == "no rows to show"\n'
    )
    deleted = "def test_y():\n    assert other == 1\n"

    lines = {
        "1 a target keeping its assertion is unsatisfied, one that dropped it is OK": (
            line.assertion in (test_body(kept, "test_x") or "")
            and line.assertion not in (test_body(sibling, "test_x") or "")
        ),
        "2 the assertion is read in the target's body, never in a sibling's": (
            line.assertion in sibling and line.assertion not in (test_body(sibling, "test_x") or "")
        ),
        "3 a name the file does not define has no body": (test_body(gone, "test_x") is None),
        "4 the block parses to its target, assertion and landing name": (
            line.target == "tests/test_a.py::test_x"
            and line.landing == "tests/test_a.py::test_x"
            and line.path == "tests/test_a.py"
            and line.test == "test_x"
        ),
        "5 a rehome landing that kept the assertion byte-identical is the only OK one": (
            line.assertion in (test_body(kept, "test_x") or "")
            and line.assertion not in (test_body(softened, "test_x") or "")
        ),
        "6 the block kind is its first kind: or motion: line": (
            block_kind(block) == "amend"
            and block_kind("slug: s\nmotion: rehome\n") == "rehome"
            and block_kind("slug: s\n") == ""
        ),
        "7 an in-place rehome is OK where the body moved and the assertion survived": (
            moved_in_place(kept, in_place, "test_x")
            and line.assertion in (test_body(in_place, "test_x") or "")
        ),
        "8 an in-place line whose body is byte-identical moved nothing": (
            not moved_in_place(kept, kept, "test_x")
        ),
        "9 a collateral row parses to its target, its breaks and its quoted assertion": (
            row.target == "tests/test_a.py::test_x"
            and row.breaks == "the keyword the helper passes was renamed"
            and row.assertion == 'assert banner() == "no rows to show"'
        ),
        "10 a row whose assertion survived in its own body is OK": (
            collateral_body_verdict(held, row) == "OK tests/test_a.py::test_x"
        ),
        "11 a row whose assertion moved to a sibling is ALTERED": (
            collateral_body_verdict(to_sibling, row) == "ALTERED tests/test_a.py::test_x"
        ),
        "12 a row whose target is gone is MISSING, never ALTERED": (
            collateral_body_verdict(deleted, row) == "MISSING tests/test_a.py::test_x"
            and collateral_body_verdict(None, row) == "MISSING tests/test_a.py::test_x"
        ),
        "13 only the rows are rows: a behavior line and a block with no section are none": (
            [one.target for one in parse_collateral(rows_block)] == ["tests/test_a.py::test_x"]
            and parse_collateral(block) == []
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main(sys.argv[1:]))
