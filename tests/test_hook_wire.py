"""Wire tests for the four PreToolUse hooks in .claude/hooks/.

Each hook is invoked exactly as Claude Code invokes it: one JSON object on
stdin carrying ``tool_name``, ``tool_input`` and ``cwd``, and the hook answers
on stdout with either nothing at all (the call is allowed, ``SILENT`` here) or
a JSON object whose ``hookSpecificOutput.permissionDecision`` is ``deny``
(``DENY`` here).

Nothing in this file reads a hook's source; every expectation comes from the
approved spec block ``specs/approved/shell-shape-classification.txt``.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# The hooks under test are the ones in this worktree.
WORKTREE_ROOT = Path(__file__).resolve().parents[1]
HOOK_DIR = WORKTREE_ROOT / ".claude" / "hooks"


def _main_checkout_root():
    """Absolute path of the main checkout, discovered rather than hard-coded.

    The spec measured every Bash and Read payload with ``cwd`` set to the root
    of a real checkout -- one with a ``.git`` directory at it, holding ``docs/``
    and no ``tests/``.  A git worktree's own root carries a ``.git`` *file*, so
    the common git dir's parent is the checkout the spec describes.
    """
    completed = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=str(WORKTREE_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(completed.stdout.strip()).parent


REPO_CWD = _main_checkout_root()

# The two answers the wire can carry.
SILENT = ""
DENY = "deny"

# A path with no `.git` at or above it, used by the specs-lane cases.
NOGIT_CWD = "/nogit"


def hook_decision(hook_name, payload):
    """Feed one payload to one hook on stdin; return its decision.

    Returns ``SILENT`` for empty stdout, the ``permissionDecision`` value when
    stdout is a hook answer, and the raw stdout otherwise so that an
    unrecognised answer shows up in the failure rather than being swallowed.
    """
    completed = subprocess.run(
        [sys.executable, str(HOOK_DIR / hook_name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout.strip()
    if not stdout:
        return SILENT
    try:
        answer = json.loads(stdout)
    except ValueError:
        return stdout
    specific = (answer or {}).get("hookSpecificOutput") or {}
    return specific.get("permissionDecision") or stdout


def bash_payload(command, cwd):
    """A PreToolUse payload for a Bash call."""
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}


def write_payload(file_path, cwd):
    """A PreToolUse payload for a Write call."""
    return {
        "tool_name": "Write",
        "tool_input": {"file_path": str(file_path), "content": ""},
        "cwd": str(cwd),
    }


def read_payload(file_path, cwd):
    """A PreToolUse payload for a Read call."""
    return {
        "tool_name": "Read",
        "tool_input": {"file_path": str(file_path)},
        "cwd": str(cwd),
    }


def sweep(hook_name, cases, make_payload):
    """Run every case through the hook; return {case key: decision}."""
    return {key: hook_decision(hook_name, make_payload(key)) for key in cases}


class TestsLaneShellShapes(unittest.TestCase):
    """tests-lane.py, the lane that owns writes under tests/."""

    maxDiff = None

    def test_writes_under_tests_are_denied_in_every_shell_shape(self):
        # Spec line 1.  Every command on the DENY side removes or overwrites a
        # file under tests/; the two on the SILENT side only read one.  A lane
        # that classifies on the command's first word lets the separator,
        # backgrounding, find -delete, inline-script and cd shapes straight
        # through, so an agent barred from Edit deletes the test with
        # `cd tests && rm t.py` and hears nothing back.
        expected = {
            "cat tests/t.py\nrm tests/t.py": DENY,
            "cat README.md & rm tests/t.py": DENY,
            "find tests -name '*.py' -delete": DENY,
            "node -e \"require('fs').writeFileSync('tests/t.py','')\"": DENY,
            "cd tests && rm t.py": DENY,
            "sed -i 's/a/b/' tests/t.py": DENY,
            "cat tests/t.py": SILENT,
            "grep -rn 'def test_' tests/": SILENT,
        }
        actual = sweep(
            "tests-lane.py",
            expected,
            lambda command: bash_payload(command, REPO_CWD),
        )
        self.assertEqual(actual, expected)

    def test_runner_invocations_pass_the_lane_but_inline_scripts_do_not(self):
        # Spec line 2.  `python` and `node` each appear on both sides: spelled
        # as a runner they run the suite, spelled with -m/-c/-e they are a write
        # primitive.  A lane reading only the first word refuses the red run
        # when it is spelled `python -m pytest` while letting the same
        # interpreter write a test file outright.
        expected = {
            "python -m pytest tests/ -q": SILENT,
            ".venv/bin/pytest tests/t.py -q": SILENT,
            "node --test tests/t.test.js": SILENT,
            "python -c \"open('tests/t.py','w')\"": DENY,
            "node -e \"require('fs').writeFileSync('tests/t.py','')\"": DENY,
        }
        actual = sweep(
            "tests-lane.py",
            expected,
            lambda command: bash_payload(command, REPO_CWD),
        )
        self.assertEqual(actual, expected)


class NoImplReadsShellShapes(unittest.TestCase):
    """no-impl-reads.py, the guard that keeps the blind agent blind."""

    maxDiff = None

    def test_inline_scripts_are_denied_while_runner_invocations_pass(self):
        # Spec line 3.  `node` and `npx` sit on both sides of this table.  A
        # guard that blanket-passes any command whose first word is on its
        # runner list prints src/core.py to the blind agent through `node -e`
        # while refusing `python -c` printing the very same file.
        expected = {
            "node -e \"console.log(require('fs')"
            ".readFileSync('src/core.py','utf8'))\"": DENY,
            "python -c \"print(open('src/core.py').read())\"": DENY,
            "pytest tests/test_lane.py -q": SILENT,
            "npx vitest run": SILENT,
        }
        actual = sweep(
            "no-impl-reads.py",
            expected,
            lambda command: bash_payload(command, REPO_CWD),
        )
        self.assertEqual(actual, expected)

    def test_unrooted_recursive_search_is_denied(self):
        # Spec line 5.  The same search, the same flags, the same pattern: only
        # the root differs.  A guard that judges a search by the path words it
        # carries finds nothing to test in `.` or in no path at all, so the
        # recursive sweep of the implementation is the one search it never
        # examines, while the one rooted at docs/ is the one it does.
        expected = {
            "grep -rn secret .": DENY,
            "grep -rn secret": DENY,
            "grep -rn secret docs/": SILENT,
        }
        actual = sweep(
            "no-impl-reads.py",
            expected,
            lambda command: bash_payload(command, REPO_CWD),
        )
        self.assertEqual(actual, expected)

    def test_allowlisted_directories_are_anchored_at_the_repo_root(self):
        # Spec line 6.  Read tool surface.  `docs` and `tests` name allowlisted
        # directories at the root; nested under src/ they name implementation.
        # A guard matching an allowlist entry at any depth hands the blind agent
        # src/docs/impl.py whole.
        expected = {
            str(REPO_CWD / "src" / "docs" / "impl.py"): DENY,
            str(REPO_CWD / "src" / "tests" / "impl.py"): DENY,
            str(REPO_CWD / "docs" / "testing.md"): SILENT,
        }
        actual = sweep(
            "no-impl-reads.py",
            expected,
            lambda file_path: read_payload(file_path, REPO_CWD),
        )
        self.assertEqual(actual, expected)


class SpecsLaneWithoutGitRoot(unittest.TestCase):
    """specs-lane.py, the lane that owns specs/approved/."""

    maxDiff = None

    def test_approved_spec_directory_is_in_lane_without_a_git_root(self):
        # Spec line 4.  No `.git` sits at or above /nogit.  A lane whose
        # in-lane test fails one path component short treats the approved-spec
        # directory itself as outside its own lane, so the write that creates
        # that directory in a fresh checkout goes to any agent that asks --
        # while a draft spec, genuinely outside the lane, stays allowed.
        expected = {
            "/nogit/specs/approved": DENY,
            "/nogit/specs/approved/s.txt": DENY,
            "/nogit/specs/draft/s.txt": SILENT,
        }
        actual = sweep(
            "specs-lane.py",
            expected,
            lambda file_path: write_payload(file_path, NOGIT_CWD),
        )
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
