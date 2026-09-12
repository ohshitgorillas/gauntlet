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


def write_payload(file_path, cwd, agent_type=None):
    """A PreToolUse payload for a Write call.

    ``agent_type`` is the subagent name Claude Code puts beside ``tool_input``
    for a subagent's call.  ``None`` leaves the key off the payload entirely,
    which is the shape a call that came from no subagent carries.
    """
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(file_path), "content": ""},
        "cwd": str(cwd),
    }
    if agent_type is not None:
        payload["agent_type"] = agent_type
    return payload


def grep_payload(path, cwd):
    """A PreToolUse payload for a Grep call rooted at ``path``."""
    return {
        "tool_name": "Grep",
        "tool_input": {"pattern": "demo", "path": str(path)},
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
            # fail-open-bypasses line 1.  A redirection read only when no file
            # descriptor precedes it lets `cat impl.py 1> tests/t.py` write the
            # test the agent was barred from writing with Edit, while the same
            # lane refuses `2>&1` on a plain read.  /dev/null is not a write.
            "cat impl.py 1> tests/t.py": DENY,
            "cat impl.py 2> tests/t.py": DENY,
            "cat impl.py &> tests/t.py": DENY,
            "cat impl.py > tests/t.py 2>/dev/null": DENY,
            "cat impl.py > tests/nullish": DENY,
            "grep x tests/t.py 2>&1": SILENT,
            "echo hi >&2": SILENT,
            "cat tests/t.py 2>/dev/null": SILENT,
            # fail-open-bypasses line 2.  A heredoc body dropped before any
            # check names its target where nothing looks, so `python3 - <<EOF`
            # writes a test unseen; a delimiter merely carrying a hyphen is no
            # reason to treat the same body differently, and prose stays prose.
            "python3 - <<EOF\nopen('tests/t.py','w')\nEOF": DENY,
            "python3 - <<EOF\nopen('tests/t.py','w')": DENY,
            "python3 - <<'EOF-1'\nopen('tests/t.py','w')\nEOF-1": DENY,
            "echo hi && python3 - <<EOF\nopen('tests/t.py','w')\nEOF": DENY,
            "cat <<EOF\nprose about tests/t.py\nEOF": SILENT,
            # fail-open-bypasses line 5.  `pytest` accepted with any arguments
            # at all is a write primitive handed an output path: the runner the
            # lane exists to let through becomes the way into the lane.
            "pytest --junitxml=tests/out.xml": DENY,
            "pytest --cov-report=html:tests/cov tests/": DENY,
            "pytest --basetemp=tests/tmp tests/": DENY,
            "pytest tests/ -q": SILENT,
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
            # fail-open-bypasses line 4.  An inline-script flag read without the
            # head word in front of it turns the two standard ways of spelling a
            # pytest run -- with a config file, without a cache directory --
            # into writes, and the lane refuses its own red run.
            "pytest -p no:cacheprovider tests/": SILENT,
            "pytest -c pytest.ini tests/": SILENT,
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
            # fail-open-bypasses line 4, the guard's half of the same flag.
            # Read against the head word the flag still refuses `python -c` and
            # `node -e` above, and `python3 -` reading the implementation on
            # stdin, while a pytest run carrying a config file goes through.
            "pytest -c pytest.ini tests/": SILENT,
            "python3 - < src/core.py": DENY,
        }
        actual = sweep(
            "no-impl-reads.py",
            expected,
            lambda command: bash_payload(command, REPO_CWD),
        )
        self.assertEqual(actual, expected)

    def test_git_subcommands_that_print_content_need_an_allowlisted_path(self):
        # fail-open-bypasses line 3.  A git command scored only by the
        # path-shaped words it carries hands `git show HEAD` -- the whole
        # implementation -- to the blind agent because it names no path, and
        # refuses `git show HEAD:specs/approved/...` because the revision
        # prefix makes an allowlisted spec look like a filename.  Metadata
        # subcommands print no content; an unknown one is treated as content.
        expected = {
            "git show HEAD": DENY,
            "git log -p": DENY,
            "git diff HEAD~1": DENY,
            "git stash show -p": DENY,
            "git frobnicate": DENY,
            "git cat-file -p HEAD": DENY,
            "git status": SILENT,
            "git log --oneline": SILENT,
            "git show HEAD:docs/gauntlet/specs/pair-sh.txt": SILENT,
            # docs-gauntlet-base line 7.  A docs/gauntlet/ denial the
            # revision-prefix stripping never reaches answers SILENT for the
            # plan read and hands a blind agent an approved plan's file:line
            # citations out of history, while the approved spec the same agent
            # is spawned against stays readable.
            "git show HEAD:docs/gauntlet/plans/demo.txt": DENY,
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

    def test_a_search_rooted_at_the_bare_gauntlet_directory_is_denied(self):
        # docs-gauntlet-base line 3.  Grep tool surface, each path a directory
        # named with no trailing separator.  A denial written as a prefix test
        # alone -- "docs/gauntlet" plus a separator -- never matches the bare
        # directory, so the one search that sweeps every approved plan at once
        # is the one it lets through, returning their citation lines to a blind
        # agent; a search rooted at the approved specs stays allowed.
        expected = {
            str(REPO_CWD / "docs" / "gauntlet"): DENY,
            str(REPO_CWD / "docs" / "gauntlet" / "plans"): DENY,
            str(REPO_CWD / "docs" / "gauntlet" / "specs"): SILENT,
        }
        actual = sweep(
            "no-impl-reads.py",
            expected,
            lambda path: grep_payload(path, REPO_CWD),
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
            # docs-gauntlet-base line 2.  The docs/gauntlet/ denial sits under
            # the docs/ allowance and above a re-allowance of the approved
            # specs.  Tested the other way round it answers DENY for the very
            # path the blind gauntlet-scrivener is spawned against and reads
            # from its worktree, while plans, reviews and drafts stay shut.
            str(REPO_CWD / "docs" / "gauntlet" / "specs" / "demo.txt"): SILENT,
            str(REPO_CWD / "docs" / "gauntlet" / "plans" / "demo.txt"): DENY,
            str(REPO_CWD / "docs" / "gauntlet" / "reviews" / "demo.plan.4.txt"): DENY,
            str(REPO_CWD / "docs" / "gauntlet" / "drafts" / "plans" / "demo.txt"): DENY,
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
            "/nogit/docs/gauntlet/specs": DENY,
            "/nogit/docs/gauntlet/specs/s.txt": DENY,
            "/nogit/docs/gauntlet/drafts/specs/s.txt": SILENT,
        }
        actual = sweep(
            "specs-lane.py",
            expected,
            lambda file_path: write_payload(file_path, NOGIT_CWD),
        )
        self.assertEqual(actual, expected)


class RedirectionsIntoTheOtherLanes(unittest.TestCase):
    """specs-lane.py and reviews-lane.py, on the same redirection shape."""

    maxDiff = None

    def test_file_descriptor_redirection_into_a_lane_is_a_write(self):
        # fail-open-bypasses line 1, the two lanes the tests-lane table cannot
        # hold.  The same `1>` that writes a test writes an approved spec block
        # and a review verdict, so a lane reading a redirection only when no
        # file descriptor precedes it fails open on all three.  The
        # reviews-lane payload carries no `agent_type` key: with one, that hook
        # refuses a reviewer's metered shell whatever the command classifies
        # as, and the redirection would be pinning nothing.
        expected = {
            ("specs-lane.py", "cat impl.py 1> docs/gauntlet/specs/s.txt"): DENY,
            ("reviews-lane.py", "cat impl.py 1> docs/gauntlet/reviews/s.9.txt"): DENY,
        }
        actual = {
            (hook_name, command): hook_decision(
                hook_name, bash_payload(command, REPO_CWD)
            )
            for hook_name, command in expected
        }
        self.assertEqual(actual, expected)


class PlansLaneCallers(unittest.TestCase):
    """plans-lane.py, the lane that owns writes under docs/gauntlet/plans/."""

    maxDiff = None

    def test_only_the_plan_reviewer_may_write_an_approved_plan(self):
        # docs-gauntlet-base line 1.  One tool, one path, one cwd: only the
        # caller varies, and `prosecutor` sits beside `gauntlet-prosecutor` so
        # both sides of the boundary are in the same sweep.  A lane written on
        # the directory alone admits any caller that asks, answering SILENT for
        # the gauntlet-arbiter, and an approved plan can then be typed by a
        # hand that never held the plan gate.
        expected = {
            None: DENY,
            "gauntlet-arbiter": DENY,
            "gauntlet-scrivener": DENY,
            "prosecutor": DENY,
            "gauntlet-prosecutor": SILENT,
        }
        plan = REPO_CWD / "docs" / "gauntlet" / "plans" / "demo.txt"
        actual = sweep(
            "plans-lane.py",
            expected,
            lambda agent_type: write_payload(plan, REPO_CWD, agent_type),
        )
        self.assertEqual(actual, expected)


class ReviewsLaneOnAnApprovedPlan(unittest.TestCase):
    """reviews-lane.py, on the plan path the plan reviewer owns."""

    maxDiff = None

    def test_the_plan_reviewer_is_carved_out_where_the_spec_one_is_not(self):
        # docs-gauntlet-base line 4.  Same tool, same path, same cwd, two
        # reviewers.  A carve-out written on the directory rather than on the
        # agent answers SILENT for the gauntlet-arbiter too, so the spec
        # reviewer may write an approved plan that no plan reviewer passed.
        expected = {
            "gauntlet-prosecutor": SILENT,
            "gauntlet-arbiter": DENY,
        }
        plan = REPO_CWD / "docs" / "gauntlet" / "plans" / "demo.txt"
        actual = sweep(
            "reviews-lane.py",
            expected,
            lambda agent_type: write_payload(plan, REPO_CWD, agent_type),
        )
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
