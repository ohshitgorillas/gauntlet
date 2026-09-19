#!/usr/bin/env python3
"""Gate: a commit's prefix names its kind, and an approved-spec commit says so.

    scripts/gates/commit-msg.py [<ref>]
    scripts/gates/commit-msg.py -
    scripts/gates/commit-msg.py --self-test

`CLAUDE.md`'s Commits section fixes the prefixes in use — `spec:`, `test:`,
`feat:`, `fix:`, `docs:`, `merge:` — and says a `spec: approved block for <x>`
commit is load-bearing evidence the scrivener checks for, so an approved block
may not be folded into a `feat:` or a `docs:` commit instead.

Two rules follow from that, and both are checked here:

1. The subject line starts with one of the six prefixes, colon and space.
2. A `feat:` or `docs:` commit whose diff touches `specs/approved/` is refused
   — that content belongs in a `spec:` commit, named as such.

With no argument the commit under test is `HEAD`: its message comes from
`git log -1 --format=%B` and its changed paths from `git diff-tree`. A ref on
argv (a hash, a branch, anything `git log`/`git diff-tree` accept) checks that
commit instead. `-` reads the message from stdin and skips rule 2, since stdin
carries no commit to diff.
"""

from __future__ import annotations

import re
import subprocess
import sys

PREFIXES = ("spec:", "test:", "feat:", "fix:", "docs:", "merge:")

#: prefixes barred from touching an approved spec block by themselves
NO_APPROVED_DIFF = ("feat:", "docs:")

APPROVED_PATH = "specs/approved/"

SUBJECT_PATTERN = re.compile(r"^(?:" + "|".join(re.escape(p) for p in PREFIXES) + r")\s")

REDIRECT = (
    "A commit's subject starts with one of spec:, test:, feat:, fix:, docs:,\n"
    "merge: and a space. An approved spec block is its own spec: commit, never\n"
    "folded into a feat: or a docs: commit."
)


def subject_of(text: str) -> str:
    """Return the first line of a commit message, or the empty string for a blank one."""
    lines = text.splitlines()
    return lines[0] if lines else ""


def prefix_of(subject: str) -> str | None:
    """Return the recognized prefix (with its colon) the subject starts with, or None."""
    for prefix in PREFIXES:
        if subject.startswith(prefix + " "):
            return prefix
    return None


def touches_approved(paths: list[str]) -> bool:
    """Report whether any changed path falls under specs/approved/."""
    return any(path.startswith(APPROVED_PATH) for path in paths)


def check_commit(text: str, paths: list[str] | None = None) -> list[str]:
    """Return one complaint per rule this gate holds that the commit fails.

    `paths` is the commit's changed files, empty when none is known (the
    stdin path), in which case rule 2 has nothing to check and is silent.
    """
    complaints = []
    subject = subject_of(text)
    prefix = prefix_of(subject)
    if prefix is None:
        complaints.append(
            f"subject {subject!r}: no recognized prefix (one of {', '.join(PREFIXES)})"
        )
        return complaints
    if prefix in NO_APPROVED_DIFF and touches_approved(paths or []):
        complaints.append(
            f"subject {subject!r}: a {prefix} commit touches {APPROVED_PATH} — that belongs in a spec: commit"
        )
    return complaints


def message_of(ref: str | None) -> str:
    """Return the commit message of `ref`, or of HEAD when `ref` is None."""
    args = ["git", "log", "-1", "--format=%B"]
    if ref:
        args.append(ref)
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def paths_of(ref: str | None) -> list[str]:
    """Return the files `ref` (or HEAD) changed, one path per line."""
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", ref or "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main(argv: list[str]) -> int:
    """Check the message on stdin (`-`), a named ref, or HEAD by default."""
    arg = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else None
    if arg == "-":
        complaints = check_commit(sys.stdin.read())
    else:
        complaints = check_commit(message_of(arg), paths_of(arg))

    for complaint in complaints:
        print(complaint)
    if complaints:
        print(f"\n{REDIRECT}")
    return 1 if complaints else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from commit_msg_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
