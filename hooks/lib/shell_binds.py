"""The lane table as a mount table: what a wrapped shell may not write.

`lanes.py` holds the lanes at the tool call and reads no shell command. What
holds a shell out of a lane is the mount table `bwrap-wrap.py` builds, and this
module is where the lane table is projected onto it, so that the two answers
come from one place.

Every lane projects whole: a lane belongs to one agent, nothing else writes
into it, and the directory is bound read-only. The tests lane included.

It was not always. A fixture checkout that a wrapped child process had to reach
could not live under the masked `/tmp`, because each wrap mounted its own empty
tmpfs there and the inner command saw none of the outer command's work, so
fixtures were built inside the checkout and the lane had to stay writable
around them. Binding it file by file cost one bind per collected test: 387 of
them in a real consumer checkout, 54,944 characters in a single `bwrap`
argument at the parent tree and 222.8KB in a worktree, past the kernel's
`MAX_ARG_STRLEN`. Every `Bash` call in those sessions died with `E2BIG`.

`bwrap-wrap.py` now binds one scratch directory per checkout at `/tmp` rather
than masking it, and a nested wrap resolves the same directory, so a fixture
belongs outside the checkout again. The lane goes back to one bind, and the
mount table stops scaling with the suite.
"""

import fnmatch
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lane_config  # noqa: E402

#: bound read-only inside every checkout, on top of a writable repository. The
#: lane directories come from the one place they are defined, the tests lane
#: among them: one bind per lane, whatever the lane holds.
PROTECTED_DIRS = tuple(lane_config.LANE_DIRS) + (
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


def readonly_paths(checkout: str) -> list[str]:
    """Every path one checkout binds read-only: one per lane, and nothing per file.

    The length of this list is the length of `PROTECTED_DIRS`, whatever the
    checkout holds. That is the whole of the fix for `E2BIG`: the mount table
    is a property of the kit, not of the suite it is wrapped around.
    """
    return [str(Path(checkout) / relative) for relative in PROTECTED_DIRS]


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
            "the tests lane is bound whole": str(lane) in bound,
            "every lane is bound whole, the tests lane among them": (
                set(lane_config.LANE_DIRS) <= set(PROTECTED_DIRS)
            ),
            "no collected test file is bound on its own": (
                {str(lane / "test_one.py"), str(lane / "deep" / "test_three.py")}.isdisjoint(bound)
            ),
            "the mount table is one bind per lane, whatever the suite holds": (
                len(readonly_paths(root)) == len(PROTECTED_DIRS)
            ),
            "a checkout with no tests lane binds the same paths as one with": (
                len(readonly_paths(root + "/nowhere")) == len(readonly_paths(root))
            ),
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
