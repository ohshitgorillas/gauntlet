"""Wire tests for the four PreToolUse hooks in hooks/.

Each hook is invoked exactly as Claude Code invokes it: one JSON object on
stdin carrying ``tool_name``, ``tool_input`` and ``cwd``, and the hook answers
on stdout with either nothing at all (the call is allowed, ``SILENT`` here) or
a JSON object whose ``hookSpecificOutput.permissionDecision`` is ``deny``
(``DENY`` here).

Nothing in this file reads a hook's source; every expectation comes from the
approved spec block ``specs/approved/shell-shape-classification.txt``.
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

# The hooks under test are the ones in this worktree.
WORKTREE_ROOT = Path(__file__).resolve().parents[1]
HOOK_DIR = WORKTREE_ROOT / "hooks"

#: The kit's own wiring. It moved out of `.claude/settings.json` and into the
#: plugin manifest, which is what an installed copy reads; the project file is
#: a consumer's own business and wires none of these.
MANIFEST = json.loads((WORKTREE_ROOT / ".claude-plugin" / "plugin.json").read_text())


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

#: `no-impl-reads.py` and `blind-bash.py` are wired session-wide and gated on
#: `agent_type`, so a payload naming no caller is the main agent and passes
#: both unjudged. Every case about what a blind agent may read or run names one.
BLIND_READER = "scrivener"


def hook_decision(hook_name, payload):
    """Feed one payload to one hook on stdin; return its decision.

    Returns ``SILENT`` for empty stdout, the ``permissionDecision`` value when
    stdout is a hook answer, and the raw stdout otherwise so that an
    unrecognised answer shows up in the failure rather than being swallowed.

    ``GAUNTLET`` is cleared for the child, and nothing else about the caller's
    environment is. Under ``GAUNTLET=off`` a hook returns at its first line, so
    a bypassed session would run this whole file against hooks that decide
    nothing.
    """
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    completed = subprocess.run(
        [sys.executable, str(HOOK_DIR / hook_name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=environment,
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


def bash_payload(command, cwd, agent_type=None):
    """A PreToolUse payload for a Bash call.

    ``agent_type`` as in ``write_payload``: ``None`` leaves the key off.
    """
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}
    if agent_type is not None:
        payload["agent_type"] = agent_type
    return payload


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


def grep_payload(path, cwd, agent_type=None):
    """A PreToolUse payload for a Grep call rooted at ``path``.

    ``agent_type`` as in ``write_payload``: ``None`` leaves the key off.
    """
    payload = {
        "tool_name": "Grep",
        "tool_input": {"pattern": "demo", "path": str(path)},
        "cwd": str(cwd),
    }
    if agent_type is not None:
        payload["agent_type"] = agent_type
    return payload


def read_payload(file_path, cwd, agent_type=None):
    """A PreToolUse payload for a Read call.

    ``agent_type`` as in ``write_payload``: ``None`` leaves the key off.
    """
    payload = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(file_path)},
        "cwd": str(cwd),
    }
    if agent_type is not None:
        payload["agent_type"] = agent_type
    return payload


#: the leaves re-allowed inside the denied gauntlet base: the approved spec
#: block a blind agent works from, and the two run artifacts it certifies
ALLOWED_UNDER_GAUNTLET = (
    "gauntlet/specs/approved/",
    "gauntlet/red/",
    "gauntlet/merge/",
)


def ls_files(pathspec):
    """Every tracked path a ``git ls-files`` of ``pathspec`` returns, as a list.

    Listed from the tree the hooks under test sit in, so the enumeration is of
    the checkout being judged rather than of whatever some other checkout holds.
    Paths come back relative to that tree's root, which is how the payloads
    below hang them under ``REPO_CWD``.
    """
    completed = subprocess.run(
        ["git", "ls-files", "-z", *pathspec],
        cwd=str(WORKTREE_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return [path for path in completed.stdout.split("\0") if path]


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


class TestsLaneGitSubcommands(unittest.TestCase):
    """tests-lane.py, on git commands that name tests/."""

    maxDiff = None

    def test_read_only_git_subcommands_naming_tests_pass_the_lane(self):
        # git-read-subcommands line 1.  A lane that admits `git grep` and no
        # other read-only git subcommand still refuses `git ls-tree HEAD tests/`
        # and `git cat-file -p HEAD:tests/...`.  An unknown subcommand stays a
        # write, and a redirection into tests/ stays a write even behind the
        # very subcommand admitted as a read.
        expected = {
            "git grep -n foo -- tests/": SILENT,
            "git grep -n 'tests/' -- hooks": SILENT,
            "git ls-tree HEAD tests/": SILENT,
            "git cat-file -p HEAD:tests/test_hook_wire.py": SILENT,
            "git rev-list HEAD -- tests/": SILENT,
            "git shortlog -sn HEAD -- tests/": SILENT,
            "git reflog show HEAD -- tests/": SILENT,
            "git merge-base HEAD impl/tests/x": SILENT,
            "git describe --match 'tests/*'": SILENT,
            "git frobnicate -- tests/": DENY,
            "git grep foo -- tests/ > tests/x": DENY,
        }
        actual = sweep(
            "tests-lane.py",
            expected,
            lambda command: bash_payload(command, REPO_CWD),
        )
        self.assertEqual(actual, expected)

    def test_write_forms_of_read_only_git_subcommands_are_denied(self):
        # git-read-subcommands line 2.  A lane that counts a read-only git
        # subcommand as a read in every form lets `git diff --output=tests/x`
        # write into the lane and `git grep -O` run a command against it.
        # `-o` beside `-O`, `--grep=` beside `--output=`, and `--stat` keep the
        # reading of flags from collapsing into "any flag is a write".
        expected = {
            "git diff --output=tests/x": DENY,
            "git log --output tests/x": DENY,
            "git diff --outp=tests/x": DENY,
            "git rev-list --output=tests/x HEAD": DENY,
            "git shortlog --output=tests/x HEAD": DENY,
            "git grep -Ovim foo -- tests/": DENY,
            "git grep -nO foo -- tests/": DENY,
            "git grep --open foo -- tests/": DENY,
            "git reflog delete refs/tests/x@{0}": DENY,
            "git grep -o foo -- tests/": SILENT,
            "git log --grep=expire -- tests/": SILENT,
            "git diff --stat -- tests/": SILENT,
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
            "node -e \"console.log(require('fs')" ".readFileSync('src/core.py','utf8'))\"": DENY,
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
            lambda command: bash_payload(command, REPO_CWD, BLIND_READER),
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
            # gauntlet-dir-move line 7.  A gauntlet/ denial the revision-prefix
            # stripping never reaches answers SILENT for the plan read and
            # hands a blind agent an approved plan's file:line citations out of
            # history, while the approved spec the same agent is spawned
            # against stays readable and docs/ is swept the whole way down.
            "git show HEAD:gauntlet/specs/approved/pair-sh.txt": SILENT,
            "git show HEAD:gauntlet/plans/approved/demo.txt": DENY,
            "grep -rn cite docs/": SILENT,
            "find docs/ -name *.txt": SILENT,
        }
        actual = sweep(
            "no-impl-reads.py",
            expected,
            lambda command: bash_payload(command, REPO_CWD, BLIND_READER),
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
            lambda command: bash_payload(command, REPO_CWD, BLIND_READER),
        )
        self.assertEqual(actual, expected)

    def test_a_search_rooted_at_the_bare_gauntlet_directory_is_denied(self):
        # gauntlet-dir-move line 4.  Grep tool surface, each path a directory
        # named with no trailing separator.  A denial written as a prefix test
        # alone -- "gauntlet" plus a separator -- never matches the bare
        # directory, so the one search that sweeps every approved plan at once
        # is the one it lets through, returning their citation lines to a blind
        # agent.  A re-allowance tested on the stage directory returns the
        # drafts beside the approved block, and one matching on the string
        # takes the sibling approved-old and refuses the approved directory's
        # own subdirectory.
        expected = {
            str(REPO_CWD / "gauntlet"): DENY,
            str(REPO_CWD / "gauntlet" / "plans"): DENY,
            str(REPO_CWD / "gauntlet" / "specs"): DENY,
            str(REPO_CWD / "gauntlet" / "specs" / "drafts"): DENY,
            str(REPO_CWD / "gauntlet" / "specs" / "approved-old"): DENY,
            str(REPO_CWD / "gauntlet" / "specs" / "approved"): SILENT,
            str(REPO_CWD / "gauntlet" / "specs" / "approved" / "sub"): SILENT,
            str(REPO_CWD / "docs"): SILENT,
        }
        actual = sweep(
            "no-impl-reads.py",
            expected,
            lambda path: grep_payload(path, REPO_CWD, BLIND_READER),
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
            # gauntlet-dir-move line 3.  The gauntlet/ denial carries one
            # re-allowance, and it is rooted at the approved specs rather than
            # at the stage directory above them: rebased one level up it hands
            # the blind writer the unreviewed draft beside the block, and
            # written as a string test it takes the sibling approved-old and
            # refuses the approved block's own subdirectory.
            str(REPO_CWD / "gauntlet" / "specs" / "approved" / "demo.txt"): SILENT,
            str(REPO_CWD / "gauntlet" / "specs" / "approved" / "sub" / "x.txt"): SILENT,
            str(REPO_CWD / "gauntlet" / "specs" / "approved-old" / "x.txt"): DENY,
            str(REPO_CWD / "gauntlet" / "plans" / "approved" / "demo.txt"): DENY,
            str(REPO_CWD / "gauntlet" / "reviews" / "demo.plan.4.txt"): DENY,
            str(REPO_CWD / "gauntlet" / "plans" / "drafts" / "demo.txt"): DENY,
            str(REPO_CWD / "gauntlet" / "specs" / "drafts" / "demo.txt"): DENY,
            str(REPO_CWD / "gauntlet" / "verdicts" / "demo.txt"): DENY,
        }
        actual = sweep(
            "no-impl-reads.py",
            expected,
            lambda file_path: read_payload(file_path, REPO_CWD, BLIND_READER),
        )
        self.assertEqual(actual, expected)


class NoImplReadsOverTheTrackedTree(unittest.TestCase):
    """no-impl-reads.py, over every tracked path of two listings."""

    maxDiff = None

    def test_the_denied_set_is_the_gauntlet_tree_less_its_allowed_leaves(self):
        # gauntlet-dir-move line 5.  One Read payload per tracked path of each
        # listing; the answer asserted is which of them come back DENY.  A base
        # constant left at docs/gauntlet alongside the move leaves a denied
        # subtree nested inside an allowed docs/ -- the nesting the move exists
        # to remove -- and shows up as a nonempty denied set over the first
        # listing; a base moved with no re-allowance under it denies the very
        # approved block the blind agent is spawned against, and shows up as a
        # denied set over the second listing that reaches inside
        # gauntlet/specs/approved/.
        listings = {
            "docs/ tests/ state/": ["docs/", "tests/", "state/"],
            "gauntlet/": ["gauntlet/"],
        }
        expected = {
            "docs/ tests/ state/": set(),
            "gauntlet/": {
                path
                for path in ls_files(listings["gauntlet/"])
                if not path.startswith(ALLOWED_UNDER_GAUNTLET)
            },
        }
        actual = {
            label: {
                path
                for path in ls_files(pathspec)
                if hook_decision(
                    "no-impl-reads.py",
                    read_payload(REPO_CWD / path, REPO_CWD, BLIND_READER),
                )
                == DENY
            }
            for label, pathspec in listings.items()
        }
        self.assertEqual(actual, expected)


class SpecsLaneCallers(unittest.TestCase):
    """specs-lane.py, the lane that owns writes under the approved specs."""

    maxDiff = None

    def test_only_the_spec_reviewer_may_write_an_approved_block(self):
        # gauntlet-dir-move line 2.  One tool, one path, one cwd: only the
        # caller varies.  A lane constant left at the old specs path answers
        # SILENT for the main agent at the new one, so a block no arbiter
        # passed reaches the folder the blind writer works from.
        expected = {
            None: DENY,
            "prosecutor": DENY,
            "arbiter": SILENT,
        }
        block = REPO_CWD / "gauntlet" / "specs" / "approved" / "demo.txt"
        actual = sweep(
            "specs-lane.py",
            expected,
            lambda agent_type: write_payload(block, REPO_CWD, agent_type),
        )
        self.assertEqual(actual, expected)


class LanesWithoutGitRoot(unittest.TestCase):
    """specs-lane.py and plans-lane.py, where no `.git` sits above the cwd."""

    maxDiff = None

    def test_approved_directories_are_in_lane_without_a_git_root(self):
        # gauntlet-dir-move line 9.  No `.git` sits at or above /nogit and no
        # payload carries an agent_type.  A lane resolved through the repo root
        # alone answers SILENT where there is none, so the write that creates
        # the approved directory in a fresh checkout goes to any agent that
        # asks; a lane rebased to the stage directory rather than to the
        # approved one inside it answers DENY for the main agent's own draft,
        # which now sits under that stage rather than beside it.
        expected = {
            ("specs-lane.py", "/nogit/gauntlet/specs/approved"): DENY,
            ("specs-lane.py", "/nogit/gauntlet/specs/approved/s.txt"): DENY,
            ("specs-lane.py", "/nogit/gauntlet/specs/drafts/s.txt"): SILENT,
            ("plans-lane.py", "/nogit/gauntlet/plans/approved/p.txt"): DENY,
            ("plans-lane.py", "/nogit/gauntlet/plans/drafts/p.txt"): SILENT,
        }
        actual = {
            (hook_name, file_path): hook_decision(hook_name, write_payload(file_path, NOGIT_CWD))
            for hook_name, file_path in expected
        }
        self.assertEqual(actual, expected)


class RedirectionsIntoTheOtherLanes(unittest.TestCase):
    """specs-, reviews- and verdicts-lane.py, on the same redirection shape."""

    maxDiff = None

    def test_file_descriptor_redirection_into_a_lane_is_a_write(self):
        # gauntlet-dir-move line 10, the three lanes the tests-lane table
        # cannot hold.  No payload carries an `agent_type` key: with one, the
        # reviews-lane hook refuses a reviewer's metered shell whatever the
        # command classifies as, and the redirection would be pinning nothing.
        # A lane constant left at the old path answers SILENT for all three
        # redirections, so an approved block, a reviewer round and a juror's
        # verdict are each written by a shell redirect that names no lane the
        # hook knows -- while reading the same verdict file stays allowed.
        expected = {
            ("specs-lane.py", "cat impl.py 1> gauntlet/specs/approved/s.txt"): DENY,
            ("reviews-lane.py", "cat impl.py 1> gauntlet/reviews/s.9.txt"): DENY,
            ("verdicts-lane.py", "cat impl.py 1> gauntlet/verdicts/demo.txt"): DENY,
            ("verdicts-lane.py", "cat gauntlet/verdicts/demo.txt"): SILENT,
        }
        actual = {
            (hook_name, command): hook_decision(hook_name, bash_payload(command, REPO_CWD))
            for hook_name, command in expected
        }
        self.assertEqual(actual, expected)


class GitSubcommandsInTheOtherLanes(unittest.TestCase):
    """specs-, plans-, verdicts- and reviews-lane.py, on git commands."""

    maxDiff = None

    def test_git_reads_pass_and_git_output_writes_are_denied_in_each_lane(self):
        # gauntlet-dir-move line 11.  No `agent_type` key on any payload.  Lane
        # constants moved in the `Write` road alone still let
        # `git diff --output=gauntlet/specs/approved/x.txt` type an approved
        # spec file that no arbiter passed, and still refuse `git grep` over
        # the same directory.
        lanes = {
            "specs-lane.py": "gauntlet/specs/approved",
            "plans-lane.py": "gauntlet/plans/approved",
            "verdicts-lane.py": "gauntlet/verdicts",
            "reviews-lane.py": "gauntlet/reviews",
        }
        expected = {}
        for hook_name, lane in lanes.items():
            expected[(hook_name, f"git grep -n foo -- {lane}/")] = SILENT
            expected[(hook_name, f"git ls-tree HEAD {lane}/")] = SILENT
            expected[(hook_name, f"git diff --output={lane}/x.txt")] = DENY
        actual = {
            (hook_name, command): hook_decision(hook_name, bash_payload(command, REPO_CWD))
            for hook_name, command in expected
        }
        self.assertEqual(actual, expected)


class PlansLaneCallers(unittest.TestCase):
    """plans-lane.py, the lane that owns writes under docs/gauntlet/plans/."""

    maxDiff = None

    def test_only_the_plan_reviewer_may_write_an_approved_plan(self):
        # gauntlet-dir-move line 1.  One tool, one path, one cwd: only the
        # caller varies, and `prosecutor` sits beside `prosecutor` so
        # both sides of the boundary are in the same sweep.  A lane constant
        # left at the old plans path answers SILENT for every caller at the new
        # one, and an approved plan is then typed by a hand that did not hold
        # the plan gate.
        expected = {
            None: DENY,
            "arbiter": DENY,
            "scrivener": DENY,
            "prosecutor": DENY,
            "prosecutor": SILENT,
        }
        plan = REPO_CWD / "gauntlet" / "plans" / "approved" / "demo.txt"
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
        # gauntlet-dir-move line 8.  Same tool, same path, same cwd, two
        # reviewers.  A reviewer carve-out left at the old plans path answers
        # DENY for the prosecutor too, so the one agent that may write
        # an approved plan is locked out of its own lane.
        expected = {
            "prosecutor": SILENT,
            "arbiter": DENY,
        }
        plan = REPO_CWD / "gauntlet" / "plans" / "approved" / "demo.txt"
        actual = sweep(
            "reviews-lane.py",
            expected,
            lambda agent_type: write_payload(plan, REPO_CWD, agent_type),
        )
        self.assertEqual(actual, expected)


class ReviewsLaneArbiterGit(unittest.TestCase):
    """reviews-lane.py, on the spec reviewer's git commands."""

    maxDiff = None

    def test_the_arbiters_git_commands_are_judged_by_form_not_name(self):
        # gauntlet-dir-move line 14.  Every payload carries `agent_type`
        # arbiter.  Judged by subcommand name alone, `git grep foo`
        # is refused with no lane named while `git diff --output=out.txt`
        # writes a file and is allowed; `grep` sits on both sides of this
        # sweep, and with the reviewer's lane constant left at the old reviews
        # path the arbiter's `git grep foo -- gauntlet/reviews/` reads the
        # rounds it may not read and is allowed.
        expected = {
            "git grep foo": SILENT,
            "git ls-tree HEAD": SILENT,
            "git log --oneline": SILENT,
            "git grep foo -- gauntlet/reviews/": DENY,
            "git reflog expire --all": DENY,
            "git diff --output=out.txt": DENY,
        }
        actual = sweep(
            "reviews-lane.py",
            expected,
            lambda command: bash_payload(command, REPO_CWD, "arbiter"),
        )
        self.assertEqual(actual, expected)


#: the five hooks the plugin manifest wires on `Bash` that judge every
#: caller, so this is the set a main-agent shell command is actually judged by.
#: `no-impl-reads.py` and `blind-bash.py` are wired on `Bash` session-wide too,
#: but each gates on `agent_type` and answers `SILENT` for every caller outside
#: its own `BLIND` tuple, so neither adds a denial here. `TheCallerGate` below
#: is where that is pinned, and it is pinned rather than assumed because
#: session wiring is what puts a main-agent command in front of them at all.
SESSION_LANE_HOOKS = (
    "specs-lane.py",
    "plans-lane.py",
    "tests-lane.py",
    "reviews-lane.py",
    "verdicts-lane.py",
)


def lane_denials(command, cwd, agent_type=None):
    """Which session-wide lane hooks deny this command, in wiring order."""
    return tuple(
        hook
        for hook in SESSION_LANE_HOOKS
        if hook_decision(hook, bash_payload(command, cwd, agent_type)) == DENY
    )


def lane_sweep(commands, cwd, agent_type=None):
    return {command: lane_denials(command, cwd, agent_type) for command in commands}


#: Nothing denies it. The tuple is spelled out rather than left implicit so a
#: hook that starts denying a read names itself in the failure.
PASSES = ()
TESTS = ("tests-lane.py",)
REVIEWS = ("reviews-lane.py",)


class LanesOnReadOnlyShellShapes(unittest.TestCase):
    """The lane hooks over the read-only shapes an agent's shell is made of.

    A lane owns the writes into one directory. It owes every other command an
    answer of silence, and the commands it kept denying were the ones a lane
    path merely *appears* in: quoted in a heredoc body, quoted in a `for` list,
    quoted as an argument to `echo`, or sitting in the source half of a
    redirection whose target is somewhere else entirely. None of those writes
    the lane, and a lane that denies them denies the reading every round of the
    chain is made of.
    """

    maxDiff = None

    def test_a_lane_path_that_is_not_a_write_target_passes_every_lane(self):
        # The path is named, and the write goes somewhere else -- or there is
        # no write at all. A lane that searched the text of a write stage
        # denied all six.
        expected = {
            # the body of a heredoc is the content being written, not the
            # target of the write; the target is on the redirection
            "cat > gauntlet/specs/drafts/x.txt <<EOF\n"
            "existing: grep -rn cite tests/\nEOF": PASSES,
            "cat > /tmp/x.txt <<'EOF'\nsee gauntlet/specs/approved/x.txt\nEOF": PASSES,
            # a `for` header runs no command, so its list is strings
            'for c in "printf x | tee gauntlet/reviews/a.txt"; do echo "$c"; done': PASSES,
            # the redirection target is the write; the lane path is an argument
            'echo "tests/x" >> notes.txt': PASSES,
            'echo "tests/ is closed"': PASSES,
            'printf "%s\\n" "gauntlet/plans/approved/x"': PASSES,
            "echo hi # see tests/": PASSES,
            'git commit -m "test: pins tests/ layout"': PASSES,
        }
        self.assertEqual(lane_sweep(expected, REPO_CWD), expected)

    def test_the_readers_a_search_is_made_of_pass_every_lane(self):
        # `find`, `xargs`, `awk`, `cmp` and `ruff check` read. Off the
        # read-only list they were unknown head words, and an unknown head word
        # is a write, so every one of these denied at the lane it named.
        expected = {
            'find tests -name "*.py"': PASSES,
            'find tests -name "*.py" | xargs grep -n foo': PASSES,
            "awk '{print}' tests/x.py": PASSES,
            "cmp gauntlet/specs/drafts/x.txt gauntlet/specs/approved/x.txt": PASSES,
            ".venv/bin/ruff check tests": PASSES,
            "find gauntlet/reviews -name 'pair-sh.*'": PASSES,
            "ls gauntlet/reviews/": PASSES,
            "ls gauntlet/reviews/pair-sh.*.txt": PASSES,
            # the same heads in the forms that do write
            "find tests -name '*.py' -delete": TESTS,
            "find tests -name '*.py' | xargs rm": TESTS,
            "awk '{print > \"tests/x.py\"}' a.txt": TESTS,
            ".venv/bin/ruff check --fix tests": TESTS,
            ".venv/bin/ruff format tests": TESTS,
            ".venv/bin/ruff format --check tests": PASSES,
        }
        self.assertEqual(lane_sweep(expected, REPO_CWD), expected)

    def test_a_redirection_inside_quotes_is_not_a_redirection(self):
        # A `>` the shell never performs: it is a character inside an argument.
        # Scanned without regard to quoting it made every one of these a write,
        # and the lane then read the rest of the stage for a path.
        expected = {
            "grep -n 'a > b' tests/": PASSES,
            'grep -rn "x >> y" gauntlet/reviews/': PASSES,
            "git log --oneline --grep='moved > tests/'": PASSES,
            # and the real thing, still a write, quoted target included
            'cat impl.py > "tests/t.py"': TESTS,
            "cat impl.py > tests/t.py": TESTS,
        }
        self.assertEqual(lane_sweep(expected, REPO_CWD), expected)

    def test_git_reading_forms_naming_a_lane_pass(self):
        expected = {
            "git ls-tree -r --name-only main -- scripts gauntlet/specs agents": PASSES,
            "git log --oneline -- tests/": PASSES,
            "git diff main -- tests/test_x.py": PASSES,
            "git show HEAD:tests/test_x.py": PASSES,
            "git grep -n foo -- tests/": PASSES,
            "git status --short tests/": PASSES,
            "git rev-parse --show-toplevel": PASSES,
            "git stash": PASSES,
            "git add tests/x.py && git commit -m x": PASSES,
            "git checkout main -- tests/x.py": PASSES,
            "git worktree add .claude/worktrees/x-spec -b spec/x": PASSES,
            # a git read whose output is redirected writes where it points,
            # and that is the draft lane, which no hook owns
            "git show 50ad52f:gauntlet/specs/approved/x.txt > gauntlet/specs/drafts/x.txt": PASSES,
            "git cat-file -p 0123456789abcdef > gauntlet/specs/drafts/x.txt": PASSES,
            # the same shape pointed the other way is the write the lane owns
            "git show 50ad52f:x.txt > gauntlet/specs/approved/x.txt": ("specs-lane.py",),
        }
        self.assertEqual(lane_sweep(expected, REPO_CWD), expected)

    def test_the_plain_readers_and_runners_pass(self):
        expected = {
            "ls gauntlet/specs/approved": PASSES,
            "wc -l tests/*.py": PASSES,
            "cat tests/test_x.py": PASSES,
            "grep -rn 'def test_' tests/": PASSES,
            "diff tests/a.py tests/b.py": PASSES,
            "sed -n '1,20p' tests/x.py": PASSES,
            "head -20 tests/x.py": PASSES,
            "grep -l slug gauntlet/specs/approved/*.txt": PASSES,
            ".venv/bin/pytest tests/test_x.py -q": PASSES,
            "node --test tests/x.test.js": PASSES,
            "scripts/pair.sh red x": PASSES,
            "scripts/gates/check-gates.sh": PASSES,
            "python3 scripts/gates/md-softwrap.py --check docs/testing.md": PASSES,
        }
        self.assertEqual(lane_sweep(expected, REPO_CWD), expected)

    def test_the_writes_the_lanes_exist_for_are_still_denied(self):
        # The other half of the same change: nothing above widened the lane.
        expected = {
            "cp a.py tests/a.py": TESTS,
            "sed -i s/a/b/ tests/a.py": TESTS,
            "rm tests/x.py": TESTS,
            "mv tests/a.py tests/b.py": TESTS,
            "cd tests && echo x > a.py": TESTS,
            "(echo x > tests/a.py)": TESTS,
            'printf "%s" x | tee gauntlet/reviews/a.txt': REVIEWS,
        }
        self.assertEqual(lane_sweep(expected, REPO_CWD), expected)

    def test_the_blind_writer_is_judged_by_the_same_lane_answers(self):
        # The lane hooks are wired session-wide, so a subagent's shell gets the
        # same answer the main agent's does; the writer's own confinement is
        # `blind-bash.py`, which is a different hook and a different question.
        reads = (
            'find tests -name "*.py"',
            "awk '{print}' tests/x.py",
            'find tests -name "*.py" | xargs grep -n foo',
            "cat > /tmp/x.txt <<'EOF'\nsee gauntlet/specs/approved/x.txt\nEOF",
            'echo "tests/x" >> notes.txt',
        )
        expected = {command: PASSES for command in reads}
        self.assertEqual(lane_sweep(expected, REPO_CWD, "scrivener"), expected)

    def test_the_blind_writer_shell_is_one_command_whatever_the_lanes_say(self):
        # Every command above is denied for the writer by blind-bash.py, which
        # answers on the caller and the entry point rather than on any path.
        # A lane that stopped denying a read did not widen that shell.
        commands = (
            'find tests -name "*.py"',
            "cat tests/test_x.py",
            "scripts/gates/check-gates.sh",
            ".venv/bin/ruff check tests",
        )
        expected = {command: DENY for command in commands}
        actual = sweep(
            "blind-bash.py",
            expected,
            lambda command: bash_payload(command, REPO_CWD, "scrivener"),
        )
        self.assertEqual(actual, expected)


class ReviewsLaneOnTheReviewersOwnShell(unittest.TestCase):
    """reviews-lane.py, over the commands a reviewer reaches for.

    A reviewer is denied the round files and every shell write, and that is the
    rule, not a defect: it is why `scripts/pair.sh review` hands the reviewer
    the path it is to write rather than leaving it to count the directory.
    What the same reviewer is owed is every other read.
    """

    maxDiff = None

    def test_a_reviewer_reads_outside_the_round_files(self):
        expected = {
            "cmp gauntlet/specs/drafts/x.txt gauntlet/specs/approved/x.txt": PASSES,
            'find tests -name "*.py"': PASSES,
            "awk '{print}' docs/testing.md": PASSES,
            ".venv/bin/ruff check tests": PASSES,
        }
        for agent in ("arbiter", "prosecutor"):
            with self.subTest(agent=agent):
                self.assertEqual(lane_sweep(expected, REPO_CWD, agent), expected)

    def test_a_reviewer_is_still_denied_the_rounds_and_every_shell_write(self):
        expected = {
            "ls gauntlet/reviews/": REVIEWS,
            "ls gauntlet/reviews/pair-sh.*.txt": REVIEWS,
            "find gauntlet/reviews -name 'pair-sh.*'": REVIEWS,
            "git show 50ad52f:gauntlet/specs/approved/x.txt"
            " > gauntlet/specs/drafts/x.txt": REVIEWS,
            "git cat-file -p 0123456789abcdef > gauntlet/specs/drafts/x.txt": REVIEWS,
        }
        for agent in ("arbiter", "prosecutor"):
            with self.subTest(agent=agent):
                self.assertEqual(lane_sweep(expected, REPO_CWD, agent), expected)


class TheCallerGate(unittest.TestCase):
    """The two caller-gated hooks, over the callers session wiring hands them.

    Frontmatter wiring is gone: a plugin-shipped agent definition runs none, so
    `no-impl-reads.py` and `blind-bash.py` are wired session-wide and every
    caller's tool call reaches them. What keeps them off the main agent is the
    `agent_type` key, and these cases are both directions of that one rule.
    """

    maxDiff = None

    #: an implementation path on no allowlist, and a shell command that is not
    #: the blind agents' one entry point
    SOURCE = "hooks/shell_shapes.py"
    COMMAND = "cat hooks/shell_shapes.py"

    def test_the_blind_agents_are_read_blocked_and_the_main_agent_is_not(self):
        # An absent `agent_type` is the main agent, which has to read the
        # implementation to adjudicate a failing test. A guard that judged
        # every caller would blind it the moment the hook went session-wide.
        expected = {
            "arbiter": DENY,
            "scrivener": DENY,
            "juror": DENY,
            "bailiff": DENY,
            None: SILENT,
            "": SILENT,
            "prosecutor": SILENT,
            "examiner": SILENT,
            "detective": SILENT,
            "general-purpose": SILENT,
        }
        actual = {
            agent: hook_decision(
                "no-impl-reads.py",
                read_payload(REPO_CWD / self.SOURCE, REPO_CWD, agent),
            )
            for agent in expected
        }
        self.assertEqual(actual, expected)

    def test_the_two_shell_locked_agents_are_locked_and_no_other_caller_is(self):
        # `blind-bash.py` is an allowlist of one entry point, so a caller it
        # judges loses every other command. Wired session-wide without the
        # gate it would take the main agent's shell outright.
        expected = {
            "scrivener": DENY,
            "bailiff": DENY,
            None: SILENT,
            "": SILENT,
            "arbiter": SILENT,
            "juror": SILENT,
            "prosecutor": SILENT,
            "general-purpose": SILENT,
        }
        actual = {
            agent: hook_decision(
                "blind-bash.py",
                bash_payload(self.COMMAND, REPO_CWD, agent),
            )
            for agent in expected
        }
        self.assertEqual(actual, expected)

    def test_both_hooks_are_wired_session_wide_rather_than_from_frontmatter(self):
        # The gate is only half the change: it is safe because the hook now
        # runs for everyone, and it is load-bearing because nothing else wires
        # these two any more. A frontmatter block left in an agent definition
        # reads as enforcement a plugin runtime never executes.
        wired = {
            hook["command"].rsplit("/", 1)[-1]
            for entry in MANIFEST["hooks"]["PreToolUse"]
            for hook in entry["hooks"]
        }
        self.assertIn("no-impl-reads.py", wired)
        self.assertIn("blind-bash.py", wired)

    def test_the_manifest_is_the_only_place_the_kit_hooks_are_wired(self):
        # This repo is its own consumer, so a kit hook left declared in
        # `.claude/settings.json` fires a second time beside the installed
        # plugin's copy. Every lane would judge each call twice.
        settings_path = WORKTREE_ROOT / ".claude" / "settings.json"
        settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        project_wired = {
            hook.get("command", "")
            for event in settings.get("hooks", {}).values()
            for entry in event
            for hook in entry.get("hooks", ())
        }
        for command in project_wired:
            with self.subTest(command=command):
                self.assertNotIn("/hooks/", command)

    def test_every_hook_command_the_manifest_names_resolves_in_the_kit(self):
        # `${CLAUDE_PLUGIN_ROOT}` is the root of this repo once it is installed,
        # so a manifest naming a script that is not here wires nothing.
        commands = [
            hook["command"]
            for event in MANIFEST["hooks"].values()
            for entry in event
            for hook in entry["hooks"]
        ]
        self.assertEqual(len(commands), 11)
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("${CLAUDE_PLUGIN_ROOT}", command)
                self.assertNotIn("${CLAUDE_PROJECT_DIR}", command)
                script = command.split("/hooks/", 1)[1].split()[0]
                self.assertTrue((HOOK_DIR / script).is_file())

        definitions = sorted((WORKTREE_ROOT / "agents").glob("*.md"))
        self.assertTrue(definitions)
        for definition in definitions:
            with self.subTest(agent=definition.name):
                self.assertNotIn("hooks:", definition.read_text())


if __name__ == "__main__":
    unittest.main()
