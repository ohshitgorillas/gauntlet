"""The lane table as a mount table: what a wrapped shell may not write.

`lanes.py` holds the lanes at the tool call and reads no shell command. What
holds a shell out of a lane is the mount table `bwrap-wrap.py` builds, and this
module is where the lane table is projected onto it, so that the two answers
come from one place.

Most lanes project whole: an artifact directory belongs to one agent, nothing
else writes into it, and the directory is bound read-only. The tests lane does
not. It is a source directory of the project rather than an artifact lane, and
a suite legitimately writes beside its own files -- a fixture checkout that a
wrapped child process has to reach cannot live under the masked `/tmp`, so it
is built inside the checkout. Binding that directory read-only stops the suite
from running at all.

So the tests lane is bound file by file: what a runner collects is read-only,
and everything else under the lane is scratch. A shell cannot rewrite an
assertion a spec block pinned, which is what the lane is for. A test file
created after the wrap is not bound and is not protected there; `lanes.py`
holds that case at the write tools.
"""

import fnmatch
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lane_config  # noqa: E402

#: bound read-only inside every checkout, on top of a writable repository. The
#: lane directories come from the one place they are defined; the tests lane is
#: not among them and is answered by `TEST_GLOBS` instead.
PROTECTED_DIRS = tuple(
    lane for lane in lane_config.LANE_DIRS if lane != lane_config.tests_dir()
) + (
    lane_config.gauntlet_dir() + "/red",
    lane_config.gauntlet_dir() + "/merge",
    ".claude",
    ".git/hooks",
    ".git/config",
)

#: what a runner collects as a test, and what a shell therefore may not rewrite
TEST_GLOBS = (
    "test_*.py",
    "*_test.py",
    "conftest.py",
    "*.test.js",
    "*.test.mjs",
    "*.test.ts",
)


def test_files(checkout: str) -> list[str]:
    """Every collected test file under one checkout's tests lane, sorted.

    An empty list where the lane is not on disk, which is every checkout of a
    project that keeps its tests elsewhere or has none yet.
    """
    lane = Path(checkout) / lane_config.tests_dir()
    if not lane.is_dir():
        return []
    found = {str(path) for glob in TEST_GLOBS for path in lane.rglob(glob) if path.is_file()}
    return sorted(found)


def readonly_paths(checkout: str) -> list[str]:
    """Every path one checkout binds read-only, directories first then tests."""
    return [str(Path(checkout) / relative) for relative in PROTECTED_DIRS] + test_files(checkout)


#: what the `Stop` gate says about a test file no commit carries
UNTRACKED = "{path}: untracked test. Nothing pinned it, and the mount table cannot stop a "
UNTRACKED += "shell creating one. A test lands through an approved spec block and the "
UNTRACKED += "scrivener: take it through the chain, or delete it."


def collected(name: str) -> bool:
    """Whether a runner collects a file of this name."""
    return any(fnmatch.fnmatch(name, glob) for glob in TEST_GLOBS)


def untracked_tests(root: Path | str) -> list[str]:
    """One complaint per collected test file under the lane that git does not track.

    The mount table binds those files read-only, so no shell rewrites one. What
    a shell can still do is create one, and git answers that at the end of the
    turn: a file no commit carries and no `.gitignore` covers is a test nothing
    pinned. A path under a dot-prefixed directory is scratch a run built and is
    not named.

    An empty list wherever git cannot answer -- no repository, no git on
    `PATH`, a call that does not return. The gate holds what it can read.
    """
    lane = lane_config.tests_dir()
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "--", lane],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if done.returncode != 0:
        return []
    named = [
        line
        for line in done.stdout.splitlines()
        if collected(PurePosixPath(line).name)
        and not any(part.startswith(".") for part in PurePosixPath(line).parts)
    ]
    return [UNTRACKED.format(path=line) for line in sorted(named)]


def _untracked_rule() -> bool:
    """A real repository, one untracked test and one scratch file beside it."""
    with tempfile.TemporaryDirectory() as root:
        lane = Path(root) / lane_config.tests_dir()
        (lane / ".scratch").mkdir(parents=True)
        (lane / "test_new.py").write_text("", encoding="utf-8")
        (lane / "helper.py").write_text("", encoding="utf-8")
        (lane / ".scratch" / "test_probe.py").write_text("", encoding="utf-8")
        done = subprocess.run(
            ["git", "-C", root, "init", "-q"], capture_output=True, timeout=30, check=False
        )
        if done.returncode != 0:
            return False
        named = untracked_tests(root)
        return len(named) == 1 and f"{lane_config.tests_dir()}/test_new.py" in named[0]


def self_test() -> int:
    """One PASS or FAIL per rule this module exists to hold. Non-zero on any FAIL."""
    with tempfile.TemporaryDirectory() as root:
        lane = Path(root) / lane_config.tests_dir()
        (lane / "deep").mkdir(parents=True)
        for name in ("test_one.py", "two_test.py", "conftest.py", "helper.py"):
            (lane / name).write_text("", encoding="utf-8")
        (lane / "deep" / "test_three.py").write_text("", encoding="utf-8")
        (lane / ".fixtures").mkdir()
        bound = set(readonly_paths(root))
        rules = {
            "the tests lane is never bound whole": str(lane) not in bound,
            "every lane but the tests lane is bound whole": (
                set(lane_config.LANE_DIRS) - {lane_config.tests_dir()} <= set(PROTECTED_DIRS)
                and lane_config.tests_dir() not in PROTECTED_DIRS
            ),
            "a collected test file is bound, at any depth": (
                {str(lane / "test_one.py"), str(lane / "deep" / "test_three.py")} <= bound
            ),
            "both runner spellings and the fixture file are collected": (
                {str(lane / "two_test.py"), str(lane / "conftest.py")} <= bound
            ),
            "a file the runner does not collect stays writable": (
                str(lane / "helper.py") not in bound
            ),
            "a scratch directory inside the lane stays writable": (
                str(lane / ".fixtures") not in bound
            ),
            "a checkout with no tests lane binds no test file": test_files(root + "/nowhere") == [],
            "a directory git cannot answer for names no untracked test": (
                untracked_tests(root + "/nowhere") == []
            ),
            "an untracked test is named, and scratch beside it is not": _untracked_rule(),
            "a runner collects both spellings, a conftest and neither helper nor scratch": (
                collected("test_one.py")
                and collected("two_test.py")
                and collected("conftest.py")
                and not collected("helper.py")
            ),
        }
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else 0)
