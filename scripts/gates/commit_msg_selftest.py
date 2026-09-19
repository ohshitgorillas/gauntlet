#!/usr/bin/env python3
"""The `--self-test` body of `commit-msg.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it for the same reason
`file_length_selftest.py` sits beside `file-length.py`: the gate stays
readable as a prefix check and a diff check, and
`python3 scripts/gates/commit-msg.py --self-test` runs it.

Each case calls `check_commit(text, paths)` directly — no real commit, no
subprocess, no repository state — since that is the whole of the gate's
observable contract: the list of complaints it hands back for a message and
the paths a commit changed.
"""

from __future__ import annotations

import importlib.util
import sys
from types import ModuleType
from pathlib import Path

GATE_PATH = Path(__file__).resolve().parent / "commit-msg.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location("commit_msg_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def self_test() -> int:
    """One PASS or FAIL per rule this gate exists to hold."""
    failed = 0

    def check(rule: str, got: object, want: object) -> None:
        nonlocal failed
        if got == want:
            print(f"PASS {rule}")
        else:
            failed += 1
            print(f"FAIL {rule}: {got!r} != {want!r}")

    check_commit = GATE.check_commit

    for prefix in GATE.PREFIXES:
        check(
            f"a {prefix} subject with no approved-path diff passes",
            check_commit(f"{prefix} a clean summary\n", ["hooks/small.py"]),
            [],
        )

    check(
        "a subject with no recognized prefix fails",
        len(check_commit("tidy up a thing\n", [])),
        1,
    )
    check(
        "a subject with a prefix word but no colon fails",
        len(check_commit("feature: add a thing\n", [])),
        1,
    )
    check(
        "an empty message fails",
        len(check_commit("", [])),
        1,
    )

    check(
        "a feat: commit touching specs/approved/ fails",
        len(check_commit("feat: add a rule\n", ["specs/approved/foo.txt"])),
        1,
    )
    check(
        "a docs: commit touching specs/approved/ fails",
        len(check_commit("docs: note a rule\n", ["specs/approved/foo.txt"])),
        1,
    )
    check(
        "a spec: commit touching specs/approved/ passes",
        check_commit("spec: approved block for foo\n", ["specs/approved/foo.txt"]),
        [],
    )
    check(
        "a test: commit touching specs/approved/ passes",
        check_commit("test: pin foo\n", ["specs/approved/foo.txt"]),
        [],
    )
    check(
        "a fix: commit touching specs/approved/ passes",
        check_commit("fix: correct foo\n", ["specs/approved/foo.txt"]),
        [],
    )
    check(
        "a feat: commit touching an unrelated path only passes",
        check_commit("feat: add a rule\n", ["hooks/small.py"]),
        [],
    )
    check(
        "a feat: commit touching an approved path among others still fails",
        len(check_commit("feat: add a rule\n", ["hooks/small.py", "specs/approved/foo.txt"])),
        1,
    )
    check(
        "no changed paths known (stdin) skips the diff rule",
        check_commit("docs: note a rule\n", None),
        [],
    )

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
