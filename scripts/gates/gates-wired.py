#!/usr/bin/env python3
"""Gate: every gate script in this repository runs in `check-gates.sh`.

    scripts/gates/gates-wired.py [--check]
    scripts/gates/gates-wired.py --self-test

Each gate is wired in by hand, one line in the `gates=(...)` array, and nothing
else notices when a script never acquires that line — or keeps it after the
script is renamed or deleted. An uninvoked gate stops running, and a gate that
stops running rots silently: it can drift all the way to crashing on import
while the report stays green, because a green report lists only the gates it
was told about.

Two sets of scripts must be in the array, for the same reason by two routes. A
`*.py` under `scripts/gates/` is a gate by where it sits; a script anywhere
under `hooks/` or `scripts/` that offers `--self-test` is a gate by what it
answers to. A self-test that no runner invokes is a bar nobody clears.

The mirror drift is checked too: a path named in the array that is not a file
is wiring pointing at nothing, which reads as coverage and is not.

Support modules are not gates. The repository spells an entry point with a
hyphen or a bare word and a support module with an underscore — `lane_config`,
`lanes_selftest`, `file_length_selftest` — and a `*.py` entry point carries a
`__main__` guard. Both tests have to hold for a file to be asked for wiring.

Paths are read relative to the working directory, which is the tree
`check-gates.sh` cds into before it runs anything.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

#: The wiring this gate reads, and the array inside it that does the wiring.
WIRING = "scripts/gates/check-gates.sh"

#: Every `*.py` here is a gate, whether or not it offers `--self-test`.
GATE_DIR = "scripts/gates"

#: Swept for scripts that offer `--self-test` from outside the gate directory.
SWEPT = ("hooks", "scripts")

#: The extensions a gate can be written in.
TRACKED = ("*.py", "*.sh")

MAIN_RE = re.compile(r"^if __name__ ==", re.M)

#: What offering `--self-test` looks like: the flag itself, the shared hook
#: entry point that routes it, or the function the flag reaches.
SELF_TEST_RE = re.compile(r"--self-test|hook_shape\.entry\(|def _?self_test\(")

ARRAY_RE = re.compile(r"^gates=\(\n(.*?)^\)", re.M | re.S)

#: A script path as the array spells one.
PATH_RE = re.compile(r"(?:hooks|scripts)/[\w./-]+\.(?:py|sh)")


def read(name: str) -> str:
    """Return the text of a file, or the empty string when it is unreadable."""
    try:
        return Path(name).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def is_entry(name: str) -> bool:
    """Report whether a path is an entry point rather than a support module."""
    path = Path(name)
    if "_" in path.stem:
        return False
    if path.suffix == ".sh":
        return True
    return bool(MAIN_RE.search(read(name)))


def offers_self_test(name: str) -> bool:
    """Report whether a script answers to `--self-test`."""
    return bool(SELF_TEST_RE.search(read(name)))


def scripts_under(directory: str) -> list[str]:
    """Return every tracked script under a directory, sorted, cache files apart."""
    root = Path(directory)
    found: set[str] = set()
    for pattern in TRACKED:
        for path in root.rglob(pattern):
            if path.is_file() and "__pycache__" not in path.parts:
                found.add(path.as_posix())
    return sorted(found)


def required(gate_dir: str = GATE_DIR, swept: tuple[str, ...] = SWEPT) -> list[tuple[str, str]]:
    """Return every script that must be wired, each with why it must be.

    A gate-directory script is required by where it sits, so it is asked for
    first and never asked for twice.
    """
    gates = [
        (name, "a gate script")
        for name in scripts_under(gate_dir)
        if name != WIRING and is_entry(name)
    ]
    seen = {name for name, _ in gates}
    for directory in swept:
        for name in scripts_under(directory):
            if name in seen or name == WIRING or name.startswith(f"{gate_dir}/"):
                continue
            if is_entry(name) and offers_self_test(name):
                gates.append((name, "accepts --self-test"))
                seen.add(name)
    return gates


def array(wiring: str) -> str:
    """Return the live lines of the `gates=(...)` array, comments dropped.

    A gate commented out is a gate that stopped running, which is the case this
    exists to catch.
    """
    found = ARRAY_RE.search(wiring)
    body = found.group(1) if found else ""
    return "\n".join(line for line in body.splitlines() if not line.lstrip().startswith("#"))


def unwired(entries: str, gates: list[tuple[str, str]]) -> list[str]:
    """Return why each unwired gate fails, in the order the gates were found."""
    return [
        f"{name}: {why}, and no entry in {WIRING} names it"
        for name, why in gates
        if name not in entries
    ]


def stale(entries: str) -> list[str]:
    """Return why each array entry naming no file cannot stand, sorted by path."""
    named = sorted(set(PATH_RE.findall(entries)))
    return [
        f"{WIRING}: the entry for {name!r} names no file"
        for name in named
        if not Path(name).is_file()
    ]


def check(gates: list[tuple[str, str]] | None = None) -> int:
    """Refuse a tree where a gate runs nowhere, or the wiring names nothing.

    Every rule runs every time, so one fix per run is never the shape of this.
    """
    if gates is None:
        gates = required()
    entries = array(read(WIRING))
    problems = unwired(entries, gates) + stale(entries)

    for problem in problems:
        print(problem)
    if problems:
        print(
            f"\n{len(problems)} problem(s). Every gate runs in {WIRING}, and every entry names a gate."
        )
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from gates_wired_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
