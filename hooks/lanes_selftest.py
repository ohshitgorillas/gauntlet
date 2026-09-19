#!/usr/bin/env python3
"""The `--self-test` body of `lanes.py`: one line per spec line of every lane
row in the table, and of the `--stop` gate.

It lives beside the hook rather than inside it so the hook stays readable as a
table, and `python3 hooks/lanes.py --self-test` runs it.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lanes  # noqa: E402
import hook_payload  # noqa: E402
import hook_shape  # noqa: E402
import lane_config  # noqa: E402
import lane_paths  # noqa: E402
from lanes import (  # noqa: E402
    GUARDS,
    JUROR,
    LANES,
    PLAN_REVIEWER,
    RED_DIR,
    ROOT,
    SPEC_REVIEWER,
    SPECS,
    VERDICTS,
    WRITER,
    _complaints,
    _MISSING,
    _verdict,
    looping,
    stop,
)


def self_test() -> int:  # noqa: PLR0915
    """Pin the spec lines of every lane in the table, and the `--stop` gate."""
    import contextlib
    import importlib
    import io
    import tempfile
    import time

    root = "/repo"
    here = lane_paths.checkout_root(str(Path(__file__).resolve().parent)) or root
    spec = str(Path(here) / ".claude" / "worktrees" / "x-spec")
    impl = str(Path(here) / ".claude" / "worktrees" / "x-impl")

    write, bash = hook_shape.probes(_verdict, root)
    in_tree = hook_shape.rebased(hook_shape.probe(_verdict, here, "Edit"))
    read = hook_shape.rebased(hook_shape.probe(_verdict, root, "Read"))
    grep = hook_shape.rebased(hook_shape.probe(_verdict, root, "Grep", "path"))
    denied, allowed = hook_shape.denied, hook_shape.allowed

    def spellings(tmp: str) -> dict[str, bool]:
        """The path spellings a lane has to collapse, on a tree that exists.

        Every line here is the same file under a different name. They need a
        real tree rather than `/repo`: a symlink is resolved by the kernel, so
        a check for one is only a check when there is something to resolve.
        """
        base = Path(tmp) / "repo"
        (base / ".git").mkdir(parents=True)
        (base / SPECS).mkdir(parents=True)
        (base / "src").mkdir()
        (base / SPECS / "x.txt").write_text("")
        (base / "link.txt").symlink_to(base / SPECS / "x.txt")
        (base / "alias").symlink_to(base / SPECS)
        (base / "out.txt").symlink_to(base / "src" / "s.py")

        #: the other direction: the lane directory is itself the symlink, and
        #: its contents sit outside the tree the repo-relative path shows
        moved = Path(tmp) / "moved"
        (moved / ".git").mkdir(parents=True)
        (moved / SPECS).parent.mkdir(parents=True)
        (moved / "elsewhere").mkdir()
        (moved / SPECS).symlink_to(moved / "elsewhere")

        at_root = hook_shape.probe(_verdict, str(base), "Edit")
        at_lane = hook_shape.probe(_verdict, str(base / SPECS), "Edit")
        at_moved = hook_shape.probe(_verdict, str(moved), "Edit")
        return {
            "path 1 a symlinked file is the file it points at": denied(at_root("link.txt")),
            "path 2 a symlinked parent directory is the directory it points at": denied(
                at_root("alias/x.txt")
            ),
            "path 3 a relative path is read against the cwd of the call": denied(at_lane("x.txt")),
            "path 4 a `..` walk back into the lane is in the lane": denied(
                at_root("src/../" + SPECS + "/x.txt")
            ),
            "path 5 a target whose parent does not exist yet still resolves": denied(
                at_root(SPECS + "/not/here/yet/x.txt")
            ),
            "path 6 a lane directory that is a symlink is still the lane": denied(
                at_moved(SPECS + "/x.txt")
            ),
            #: resolving both sides collapses spellings onto one file; it does
            #: not widen the lane to whatever a link happens to sit beside
            "path 7 a symlink that lands outside the lane stays open": allowed(at_root("out.txt")),
        }

    with tempfile.TemporaryDirectory() as paths_tmp:
        by_spelling = spellings(paths_tmp)

    def tree(tmp: str, *, red: str | None, verdict: str | None, order: str = "red-first") -> Path:
        """A checkout with one red run and at most one verdict, mtimes ordered."""
        base = Path(tmp)
        (base / RED_DIR).mkdir(parents=True, exist_ok=True)
        (base / VERDICTS).mkdir(parents=True, exist_ok=True)
        writes = [(base / RED_DIR / "demo.txt", red), (base / VERDICTS / "demo.txt", verdict)]
        if order != "red-first":
            writes.reverse()
        for index, (path, body) in enumerate(writes):
            if index:
                time.sleep(0.01)
            if body is not None:
                path.write_text(body)
        return base

    def gate(**kw: Any) -> int:
        #: the exit code is the subject; the block's own message is line 6's
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            return stop(tree(tmp, **kw))

    def loop_gate(payload: str, **kw: Any) -> tuple[int, str]:
        """`--stop`'s exit code and its stderr, for one `Stop` payload on stdin."""
        held, stdin = io.StringIO(), sys.stdin
        sys.stdin = io.StringIO(payload)
        try:
            with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(held):
                code = stop(tree(tmp, **kw), loop=looping())
        finally:
            sys.stdin = stdin
        return code, held.getvalue()

    def slugs(**files: tuple[str, str | None]) -> list[str]:
        """The slugs `--stop` names, for a tree of `slug=(red, verdict)` pairs."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / RED_DIR).mkdir(parents=True)
            (base / VERDICTS).mkdir(parents=True)
            for slug, (red, verdict) in files.items():
                (base / RED_DIR / f"{slug}.txt").write_text(red)
                time.sleep(0.01)
                if verdict is not None:
                    (base / VERDICTS / f"{slug}.txt").write_text(verdict)
            return [line.split(":", 1)[0] for line in _complaints(base)]

    lines = {
        "specs 1 gauntlet/specs/approved/ closed to every agent but the arbiter": all(
            (
                denied(write(f"{root}/gauntlet/specs/approved/slug.txt")),
                denied(write("gauntlet/specs/approved/slug.txt")),
                denied(write(f"{root}/gauntlet/specs/approved/slug.txt", "scrivener")),
                denied(write(f"{root}/gauntlet/specs/approved/slug.txt", "cavecrew-builder")),
                allowed(write(f"{root}/gauntlet/specs/approved/slug.txt", SPEC_REVIEWER)),
                #: installed as a plugin the harness spells the name with its
                #: plugin in front of it, and that is the same agent
                allowed(
                    write(f"{root}/gauntlet/specs/approved/slug.txt", f"gauntlet:{SPEC_REVIEWER}")
                ),
            )
        ),
        "specs 2 every other path stays open, drafts included": all(
            (
                allowed(write(f"{root}/gauntlet/specs/drafts/slug.txt")),
                allowed(write(f"{root}/gauntlet/plans/approved/slug.txt", PLAN_REVIEWER)),
                allowed(write(f"{root}/docs/lane.txt")),
            )
        ),
        "specs 4 the lane directory itself is in the lane, checkout or not": all(
            (
                #: outside any checkout the path is read off its own segments, and
                #: the last segment is one of them: the write that creates the
                #: directory is the lane's first write, not its exception
                denied(write("/nogit/gauntlet/specs/approved")),
                denied(write("/nogit/gauntlet/specs/approved/slug.txt")),
                allowed(write("/nogit/gauntlet/specs/drafts/slug.txt")),
                allowed(write(f"{root}/gauntlet/specs/approved", SPEC_REVIEWER)),
            )
        ),
        "plans 1 gauntlet/plans/approved/ closed to every agent but the prosecutor": all(
            (
                denied(write(f"{root}/gauntlet/plans/approved/slug.txt")),
                denied(write("gauntlet/plans/approved/slug.txt")),
                denied(write(f"{root}/gauntlet/plans/approved/slug.txt", SPEC_REVIEWER)),
                denied(write(f"{root}/gauntlet/plans/approved/slug.txt", WRITER)),
                allowed(write(f"{root}/gauntlet/plans/approved/slug.txt", PLAN_REVIEWER)),
                allowed(
                    write(f"{root}/gauntlet/plans/approved/slug.txt", f"gauntlet:{PLAN_REVIEWER}")
                ),
            )
        ),
        "plans 2 every other path stays open, drafts included": all(
            (
                allowed(write(f"{root}/gauntlet/plans/drafts/slug.txt")),
                allowed(write(f"{root}/gauntlet/specs/approved/slug.txt", SPEC_REVIEWER)),
                allowed(write(f"{root}/docs/plans.md")),
            )
        ),
        "plans 4 the lane directory itself is in the lane, checkout or not": all(
            (
                denied(write("/nogit/gauntlet/plans/approved")),
                denied(write("/nogit/gauntlet/plans/approved/slug.txt")),
                allowed(write("/nogit/gauntlet/plans/drafts/slug.txt")),
                allowed(write(f"{root}/gauntlet/plans/approved", PLAN_REVIEWER)),
            )
        ),
        "tests 1 tests/ closed to all but the writer in a spec tree": all(
            (
                denied(in_tree(f"{here}/tests/t.py")),
                denied(in_tree(f"{impl}/tests/t.py")),
                denied(in_tree(f"{spec}/tests/t.py")),
                denied(in_tree(f"{impl}/tests/t.py", "cavecrew-builder")),
                allowed(in_tree(f"{spec}/tests/t.py", WRITER)),
                denied(in_tree(f"{impl}/tests/t.py", WRITER)),
                allowed(in_tree(f"{spec}/tests/t.py", f"gauntlet:{WRITER}")),
                denied(in_tree(f"{impl}/tests/t.py", f"gauntlet:{WRITER}")),
            )
        ),
        "tests 2 writer confined to its spec tree's tests/": all(
            (
                denied(in_tree(f"{spec}/src/m.py", WRITER)),
                denied(in_tree(f"{spec}/docs/testing.md", WRITER)),
                allowed(in_tree(f"{spec}/tests/conftest.py", WRITER)),
            )
        ),
        "reviews 1 gauntlet/reviews/ closed to everyone but the two reviewers": all(
            (
                denied(write(f"{root}/gauntlet/reviews/slug.1.txt")),
                denied(write(f"{root}/gauntlet/reviews/slug.1.txt", WRITER)),
                allowed(write(f"{root}/gauntlet/reviews/slug.1.txt", SPEC_REVIEWER)),
                allowed(write(f"{root}/gauntlet/reviews/slug.1.txt", PLAN_REVIEWER)),
                allowed(write(f"{root}/gauntlet/reviews/slug.1.txt", f"gauntlet:{SPEC_REVIEWER}")),
                allowed(write(f"{root}/gauntlet/reviews/slug.1.txt", f"gauntlet:{PLAN_REVIEWER}")),
            )
        ),
        "reviews 2 a reviewer writes its verdict and nothing else": all(
            (
                denied(write(f"{root}/src/m.py", SPEC_REVIEWER)),
                denied(write(f"{root}/tests/t.py", SPEC_REVIEWER)),
                denied(write(f"{root}/docs/testing.md", PLAN_REVIEWER)),
                denied(write(f"{root}/gauntlet/plans/drafts/slug.txt", PLAN_REVIEWER)),
            )
        ),
        "reviews 3 the arbiter alone also writes gauntlet/specs/approved/": all(
            (
                allowed(write(f"{root}/gauntlet/specs/approved/slug.txt", SPEC_REVIEWER)),
                denied(write(f"{root}/gauntlet/specs/approved/slug.txt", PLAN_REVIEWER)),
                denied(write(f"{root}/gauntlet/specs/drafts/slug.txt", SPEC_REVIEWER)),
            )
        ),
        "reviews 4 the prosecutor alone also writes gauntlet/plans/approved/": all(
            (
                allowed(write(f"{root}/gauntlet/plans/approved/slug.txt", PLAN_REVIEWER)),
                denied(write(f"{root}/gauntlet/plans/approved/slug.txt", SPEC_REVIEWER)),
                denied(write(f"{root}/docs/plans.md", PLAN_REVIEWER)),
            )
        ),
        "reviews 5 a reviewer never reads the round files": all(
            (
                denied(read(f"{root}/gauntlet/reviews/slug.1.txt", SPEC_REVIEWER)),
                denied(read(f"{root}/gauntlet/reviews/slug.1.txt", PLAN_REVIEWER)),
                denied(read(f"{root}/gauntlet/reviews/slug.1.txt", f"gauntlet:{SPEC_REVIEWER}")),
                denied(grep(f"{root}/gauntlet/reviews", SPEC_REVIEWER)),
                allowed(read(f"{root}/gauntlet/reviews/slug.1.txt")),
                allowed(read(f"{root}/tests/t.py", SPEC_REVIEWER)),
                #: no other lane's writer is read-blocked from its own lane
                allowed(read(f"{root}/gauntlet/specs/approved/slug.txt", SPEC_REVIEWER)),
                allowed(read(f"{root}/gauntlet/verdicts/demo.txt", JUROR)),
            )
        ),
        "verdicts 1 gauntlet/verdicts/ closed to every agent but the juror": all(
            (
                denied(write(f"{root}/gauntlet/verdicts/demo.txt")),
                denied(write("gauntlet/verdicts/demo.txt")),
                denied(write(f"{root}/gauntlet/verdicts/demo.txt", SPEC_REVIEWER)),
                denied(write(f"{root}/gauntlet/verdicts/demo.txt", PLAN_REVIEWER)),
                denied(write(f"{root}/gauntlet/verdicts/demo.txt", WRITER)),
                allowed(write(f"{root}/gauntlet/verdicts/demo.txt", JUROR)),
                allowed(write(f"{root}/gauntlet/verdicts/demo.txt", f"gauntlet:{JUROR}")),
                #: the lane denies its own directory, and no other lane's
                denied(write("/nogit/gauntlet/verdicts")),
                allowed(write(f"{root}/gauntlet/reviews/demo.1.txt", SPEC_REVIEWER)),
                allowed(write(f"{root}/state/verdicts/demo.txt")),
                allowed(write(f"{root}/docs/testing.md")),
            )
        ),
        #: the classifier is gone: every lane's shell half is the mount table,
        #: which binds these directories read-only inside every wrapped profile
        "a Bash call is not this hook's business, whatever it names": all(
            (
                allowed(bash("sed -i 's/a/b/' gauntlet/specs/approved/slug.txt")),
                allowed(bash("cat > gauntlet/plans/approved/slug.txt <<'EOF'\nslug: x\nEOF")),
                allowed(bash("echo RED > gauntlet/verdicts/demo.txt")),
                allowed(bash("echo x > gauntlet/reviews/slug.1.txt")),
                allowed(bash("rm tests/t.py")),
                allowed(bash("find tests -name '*.py' -delete")),
                allowed(bash("cat gauntlet/reviews/slug.1.txt", SPEC_REVIEWER)),
                allowed(bash("sed -i 's/a/b/' src/m.py", SPEC_REVIEWER)),
                allowed(bash(".venv/bin/pytest tests/t.py -q", WRITER)),
            )
        ),
        "stop 3 a red run with no verdict blocks the turn, a ruled one does not": all(
            (
                gate(red="1 failed", verdict=None) == 2,
                gate(red="1 failed", verdict="RED 1: assert x") == 0,
            )
        ),
        "stop 4 a verdict older than the run it answers blocks the turn": all(
            (
                gate(red="1 failed", verdict="RED 1", order="verdict-first") == 2,
                gate(red="1 failed", verdict="RED 1", order="red-first") == 0,
            )
        ),
        "stop 5 an empty red run blocks the turn, verdict or no verdict": all(
            (
                gate(red="", verdict="RED 1") == 2,
                gate(red="x", verdict="RED 1") == 0,
            )
        ),
        "stop 6 every unruled slug is named, not the first": all(
            (
                slugs(alpha=("1 failed", None), bravo=("1 failed", "RED 1")) == ["alpha"],
                slugs(alpha=("1 failed", None), bravo=("1 failed", None)) == ["alpha", "bravo"],
            )
        ),
        "stop 7 no red directory is not an unruled run": all(
            (
                stop(Path(tempfile.gettempdir()) / "gauntlet-no-such-checkout") == 0,
                _complaints(ROOT) is not None,
            )
        ),
        "stop 11 a second Stop on the same turn prints the complaints and ends it": all(
            (
                #: the complaints still reach the user; only the hold is dropped
                loop_gate('{"stop_hook_active": true}', red="1 failed", verdict=None)
                == (0, _MISSING.format(slug="demo") + "\n"),
                loop_gate('{"stop_hook_active": false}', red="1 failed", verdict=None)[0] == 2,
                #: a payload with no such key, and one this cannot read at all,
                #: are not loops: the gate holds at its normal strength
                loop_gate("{}", red="1 failed", verdict=None)[0] == 2,
                loop_gate("not json", red="1 failed", verdict=None)[0] == 2,
                loop_gate('"a string"', red="1 failed", verdict=None)[0] == 2,
                loop_gate('{"stop_hook_active": "true"}', red="1 failed", verdict=None)[0] == 2,
                #: a loop on a clean tree is still a clean tree
                loop_gate('{"stop_hook_active": true}', red="1 failed", verdict="RED 1") == (0, ""),
            )
        ),
        #: the table is the policy, so a row that names no lane, no writer or no
        #: refusal is a lane that silently holds nothing
        "every row carries a lane, a writer and a refusal": all(
            bool(row.lane) and bool(row.writers) and bool(row.lane_msg)
            #: a refusal names the file the reader has to open to change it
            and Path(lanes.__file__).name in row.lane_msg
            for row in LANES
        )
        and all(
            #: a second lane belongs to one writer of its own row, and the row
            #: that owns it is the row that reserves it
            agent in row.writers and any(other.lane == second for other in LANES)
            for row in LANES
            for agent, second in row.second.items()
        ),
        **by_spelling,
        #: the mount table and this table are one fact stated twice. A lane the
        #: write tools hold and `bwrap` leaves writable is a lane a shell walks
        #: into; a lane bound read-only and held by no row is a directory
        #: nothing explains. Both are edits to one of the two that missed the
        #: other, and both fail here rather than in a session.
        "one writable set: these rows are the lanes bwrap binds read-only": (
            {row.lane for row in LANES} == set(lane_config.LANE_DIRS)
            and set(lane_config.LANE_DIRS)
            <= set(importlib.import_module("bwrap-wrap").PROTECTED_IN_CHECKOUT)
        ),
        #: a hook decides a tool call, so its own crash is a denial -- and a
        #: payload it cannot read is a call it cannot decide, which is a refusal.
        #: The `--stop` entry point decides no call, so it withholds no
        #: permission and has nothing to refuse; what it owes is the older half
        #: alone, because a non-zero exit there holds the turn open and a crash
        #: in it is a loop with no way out.
        "every payload shape is answered, and an unreadable one is refused": (
            hook_payload.survives_hostile_payloads(lanes.__file__, guards=GUARDS)
            and hook_payload.survives_hostile_payloads(
                lanes.__file__, "--stop", refuses_undecidable=False
            )
        ),
    }
    return hook_shape.report(lines)
