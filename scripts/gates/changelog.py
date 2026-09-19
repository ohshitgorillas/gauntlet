#!/usr/bin/env python3
"""Gate: entries under ``[Unreleased]`` are short, impersonal, and shaped alike.

    scripts/gates/changelog.py [CHANGELOG.md]
    scripts/gates/changelog.py --self-test

The changelog is written by whoever made the change, which in this repo is
usually an agent that has just spent an hour inside the fix and wants to say all
of it. Left alone that produces ten-line entries carrying enumeration ids, file
paths and the order the daemon does things in — the fix's autobiography, not the
release note a reader hitting the bug needs. It also produces a second
``### Added`` heading under the same version, and prose that addresses the
reader ("your DAC correction") in a document nobody reads a sentence of.

``CLAUDE.md`` states two further rules this gate holds: an entry under
``[Unreleased]`` never names tests, fixtures, fakes or test policy — "nobody
changelogs tests" — and a version carries at most one heading of each kind,
``[Unreleased]`` included but not it alone.

None of that survives review, so it costs a review round every time. This gate
spends the round at write time instead.

What it enforces on ``[Unreleased]`` only — released sections are history and
are never rewritten:

* one bullet is one logical line, at most ``WORD_CAP`` words
* a bullet opens with a bold lead: what it does now, in a clause
* no second person
* no marketing register (``HYPE``)
* no narration by negation (``NEGATION``)
* no mention of tests, fixtures, fakes or test policy (``TEST_TALK``)

What it enforces on every version, ``[Unreleased]`` included:

* one heading per kind, in Keep a Changelog order

What it cannot enforce is tone. ``reads as advice`` passes every rule here and
is still marketing. The cap and the wordlists take the bulk off; the residue is
a human's call, and always was.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

#: The section this gate holds to the fuller bar. Everything below it has shipped.
UNRELEASED = "## [Unreleased]"

#: Words per bullet. Enough for cause and fix in one line; not enough for the
#: fix's autobiography.
WORD_CAP = 75

#: Keep a Changelog's order, plus the ``Internal`` bucket this repo uses for
#: changes with no user-visible face.
ORDER = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security", "Internal")

SECOND_PERSON = re.compile(
    r"\b(you|your|yours|yourself|you're|you've|you'd|you'll)\b", re.IGNORECASE
)

#: Register, not vocabulary: each of these reaches for the reader's feelings
#: about the change instead of stating it. ``finally`` and ``quietly`` are here
#: because they editorialize a fix that the sentence beside them already states.
HYPE = (
    "simply",
    "seamless",
    "seamlessly",
    "powerful",
    "robust",
    "delightful",
    "dramatically",
    "significantly",
    "blazing",
    "finally",
    "quietly",
    "magic",
    "just works",
    "under the hood",
    "where they belong",
    "out of the box",
)

#: Narration by negation: a clause whose content is that something did *not*
#: change. It reads as reassurance and carries nothing — a changelog says what
#: changed, and a reader assumes everything it does not mention stayed put. Where
#: the clause is load-bearing it is a scope boundary, and a scope boundary states
#: positively which things the change reached: "only chainless profiles are
#: filled in", not "profiles that already carry a chain are untouched".
NEGATION = (
    "is unchanged",
    "are unchanged",
    "remains unchanged",
    "remain unchanged",
    "stays unchanged",
    "otherwise unchanged",
    "unaffected",
    "untouched",
    "nothing changed",
    "nothing else changes",
    "nothing else is affected",
    "everything else is unchanged",
    "everything else works as before",
    "no other settings",
)

#: ``CLAUDE.md``: "Tests and test policy never go in it. Not a test added,
#: removed or rewritten, not a fixture or fake, not a change to how this repo
#: tests itself." A consumer of this repo never sees the test suite; an entry
#: that mentions one is describing work this document does not cover.
TEST_TALK = (
    "test",
    "tests",
    "testing",
    "tested",
    "fixture",
    "fixtures",
    "fake",
    "fakes",
    "test policy",
)

VERSION_RE = re.compile(r"^## ")
HEADING_RE = re.compile(r"^### (.+?)\s*$")
BULLET_RE = re.compile(r"^- ")
CODE_RE = re.compile(r"`[^`]*`")
MARKUP_RE = re.compile(r"[*_]")

Entry = tuple[int, list[str]]


def sections(lines: list[str]) -> list[tuple[int, str, list[tuple[int, str]]]]:
    """(heading line number, heading text, body) for every ``## `` version section, 1-indexed.

    ``[Unreleased]`` is one section among these; nothing here privileges it.
    """
    found: list[tuple[int, str, list[tuple[int, str]]]] = []
    for number, line in enumerate(lines, start=1):
        if VERSION_RE.match(line):
            found.append((number, line.rstrip(), []))
        elif found:
            found[-1][2].append((number, line))
    return found


def unreleased(lines: list[str]) -> list[tuple[int, str]]:
    """(line number, text) for the ``[Unreleased]`` section's body, 1-indexed."""
    for number, heading, body in sections(lines):
        if heading == UNRELEASED:
            return body
    return []


def entries(body: list[tuple[int, str]]) -> list[Entry]:
    """(line number, lines) for every bullet, continuation lines included."""
    found: list[Entry] = []
    for number, line in body:
        if BULLET_RE.match(line):
            found.append((number, [line]))
        elif found and line.strip() and line.startswith((" ", "\t")):
            found[-1][1].append(line)
    return found


def headings(body: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """(line number, kind) for every ``###`` heading in a section body."""
    return [(n, m.group(1)) for n, line in body if (m := HEADING_RE.match(line))]


def words(text: str) -> int:
    """Word count of a bullet.

    Code spans and emphasis markers are dropped, and so is any token carrying no
    letter or digit: a dash standing between two clauses is punctuation the
    author chose over a comma, and pricing it as a word taxes the punctuation
    rather than the prose.
    """
    stripped = MARKUP_RE.sub("", CODE_RE.sub(" ", text))
    return sum(1 for token in stripped.split() if any(char.isalnum() for char in token))


def _entry_problems(number: int, block: list[str]) -> list[str]:
    """Every rule this one bullet breaks."""
    text = " ".join(line.strip() for line in block)
    found = []
    if len(block) > 1:
        found.append(f"line {number}: entry runs to a second paragraph — one entry, one line")
    if (count := words(text)) > WORD_CAP:
        found.append(f"line {number}: entry is {count} words, cap is {WORD_CAP}")
    if not text.startswith("- **"):
        found.append(f"line {number}: entry does not open with a bold lead (`- **…**`)")
    if match := SECOND_PERSON.search(text):
        found.append(f"line {number}: second person {match.group(0)!r} — write it impersonally")
    lowered = text.lower()
    found.extend(
        f"line {number}: {word!r} is marketing register — state the change"
        for word in HYPE
        if re.search(rf"\b{re.escape(word)}\b", lowered)
    )
    found.extend(
        f"line {number}: {phrase!r} narrates by negation — cut it, or state the scope positively"
        for phrase in NEGATION
        if re.search(rf"\b{re.escape(phrase)}\b", lowered)
    )
    found.extend(
        f"line {number}: {word!r} names tests or test policy — CHANGELOG.md is not the place, nobody changelogs tests"
        for word in TEST_TALK
        if re.search(rf"\b{re.escape(word)}\b", lowered)
    )
    return found


def _heading_problems(heading: str, found: list[tuple[int, str]]) -> list[str]:
    """Duplicate, unknown, or out-of-order section headings under one version heading."""
    problems = []
    seen: dict[str, int] = {}
    rank = -1
    for number, kind in found:
        if kind in seen:
            problems.append(
                f"line {number}: second '### {kind}' under {heading!r} — one heading per kind, merged"
            )
        seen[kind] = number
        if kind not in ORDER:
            problems.append(f"line {number}: unknown section '{kind}' — one of {list(ORDER)}")
            continue
        if (position := ORDER.index(kind)) < rank:
            problems.append(
                f"line {number}: '### {kind}' is out of order under {heading!r} — {list(ORDER)}"
            )
        rank = max(rank, position)
    return problems


def check(path: Path) -> int:
    """Report every problem in the file: the fuller bar under ``[Unreleased]``, one heading

    per kind everywhere.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    problems = []
    for _, heading, body in sections(lines):
        problems.extend(_heading_problems(heading, headings(body)))
    for number, block in entries(unreleased(lines)):
        problems.extend(_entry_problems(number, block))

    for problem in problems:
        print(f"{path}:{problem}")
    if problems:
        print(f"\n{len(problems)} problem(s). See CONTRIBUTING.md.")
        return 1
    print(f"[ok] {path} reads clean")
    return 0


def main(argv: list[str]) -> int:
    """Check the paths on argv, or this repo's changelog when argv names none."""
    names = [arg for arg in argv[1:] if arg != "--self-test"]
    paths = [Path(name) for name in names] or [ROOT / "CHANGELOG.md"]
    return max(check(path) for path in paths)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from changelog_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
