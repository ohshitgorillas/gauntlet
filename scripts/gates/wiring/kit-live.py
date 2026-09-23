#!/usr/bin/env python3
"""Gate: the kit announces itself at SessionStart, as a process, not as a function.

    scripts/gates/wiring/kit-live.py [--check]
    scripts/gates/wiring/kit-live.py --self-test

`hooks/kit-probe.py` is the kit's one statement that it is there. Two things
have to hold for that statement to reach a session, and neither is a property of
the probe's own logic:

  * the manifest wires it at `SessionStart`, under a group with no matcher --
    a matcher on `SessionStart` is read against a tool name that event has none
    of, so a wired probe with a matcher announces nothing;
  * it runs. The probe is executed here as a real process, against a kit built
    with a hook file taken out of it, and the announcement is read off stdout.
    A probe that raises at import prints its traceback into the session and
    leaves the missing lane unmentioned, which is the failure it exists to
    prevent, arriving by another door.

Exit status is a rule of its own. A `SessionStart` hook that exits non-zero
takes the session down with it, so the probe exits 0 whether the kit is whole
or not, and this gate reads that both ways.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

MANIFEST = ".claude-plugin/plugin.json"

PROBE = "hooks/kit-probe.py"

#: the probe reads a manifest and stats a handful of files
TIMEOUT = 60

#: the file taken out of the scratch kit, so the probe has something to name
ABSENT = "hooks/lanes.py"


def manifest(root: Path) -> dict[str, Any]:
    """The manifest as an object, or an empty one when it cannot be read."""
    try:
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def wiring_problems(root: Path) -> list[str]:
    """Why the probe would not fire at SessionStart, if it would not."""
    hooks = manifest(root).get("hooks")
    groups = hooks.get("SessionStart") if isinstance(hooks, dict) else None
    if not isinstance(groups, list) or not groups:
        return [f"{MANIFEST}: nothing is wired at SessionStart"]
    wired = [
        group
        for group in groups
        if isinstance(group, dict)
        and any(
            PROBE in entry.get("command", "")
            for entry in group.get("hooks", [])
            if isinstance(entry, dict)
        )
    ]
    if not wired:
        return [f"{MANIFEST}: {PROBE} is not wired at SessionStart, so the kit announces nothing"]
    return [
        f"{MANIFEST}: the SessionStart group wiring {PROBE} carries a matcher, "
        "and SessionStart has no tool name to match"
        for group in wired
        if group.get("matcher") is not None
    ]


def scratch_kit(root: Path, source: Path) -> None:
    """Copy the manifest and every wired hook but one into a throwaway kit."""
    (root / MANIFEST).parent.mkdir(parents=True)
    (root / MANIFEST).write_text((source / MANIFEST).read_text(encoding="utf-8"), encoding="utf-8")
    (root / "hooks").mkdir()
    for path in sorted((source / "hooks").rglob("*.py")):
        name = f"hooks/{path.relative_to(source / 'hooks').as_posix()}"
        if name != ABSENT:
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def run(root: Path, source: Path) -> subprocess.CompletedProcess[str]:
    """Run the live probe as a process, pointed at one kit root."""
    return subprocess.run(
        [sys.executable, str(source / PROBE)],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=False,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PLUGIN_ROOT": str(root), "HOME": str(Path.home())},
    )


def judge(
    incomplete: subprocess.CompletedProcess[str], whole: subprocess.CompletedProcess[str]
) -> list[str]:
    """Why the probe cannot stand as a SessionStart hook, if it cannot."""
    problems = []
    if ABSENT not in incomplete.stdout:
        problems.append(
            f"the probe did not name {ABSENT} in a kit that does not hold it: "
            f"{incomplete.stdout.strip()!r} {incomplete.stderr.strip()[-200:]!r}"
        )
    if incomplete.returncode != 0:
        problems.append(
            f"the probe exited {incomplete.returncode} on an incomplete kit; a "
            "SessionStart hook that fails takes the session with it"
        )
    if whole.stdout.strip() or whole.returncode != 0:
        problems.append(
            f"the probe spoke about a whole kit: exit {whole.returncode}, "
            f"{whole.stdout.strip()!r}. Every session would carry that line"
        )
    return problems


def check(source: Path = ROOT) -> int:
    """Read the wiring, then run the probe against a broken kit and a whole one."""
    problems = wiring_problems(source)
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        scratch_kit(root, source)
        problems += judge(run(root, source), run(source, source))

    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} problem(s). A kit that is not whole says so, in every session.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from kit_live_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
