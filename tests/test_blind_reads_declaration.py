"""Wire tests for the sibling declaration file ``blind-reads.json``.

The surface is the same one ``test_hook_wire.py`` drives: one JSON object on
stdin carrying ``tool_name``, ``tool_input`` and ``cwd``, and the hook answers
on stdout with either nothing at all (the call is allowed, ``SILENT`` here) or
a JSON object whose ``hookSpecificOutput.permissionDecision`` is ``deny``
(``DENY`` here).

The second variable here is one a payload cannot carry: the hook directory's
own sibling ``blind-reads.json``.  Every test below runs one family of payloads
against copies of ``.claude/hooks/`` that differ only in that file, and asserts
the *set of payloads whose answer differs between two copies* -- "the changed
set".  A copy is the whole directory, so a hook keeps the siblings it imports.

Nothing in this file reads a hook's source; every expectation comes from the
approved spec block ``docs/gauntlet/specs/blind-readonly.txt``.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

# The hooks under test are the ones in this worktree; the copies are made from
# this directory.
WORKTREE_ROOT = Path(__file__).resolve().parents[1]
HOOK_DIR = WORKTREE_ROOT / ".claude" / "hooks"

DECLARATION_NAME = "blind-reads.json"


def _main_checkout_root():
    """Absolute path of the checkout the copies were made from.

    Discovered rather than typed.  A git worktree's own root carries a ``.git``
    *file*, so the common git dir's parent is the checkout root -- the same
    ``cwd`` every payload in ``test_hook_wire.py`` is measured with.
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

# The three copies of the hook directory.  BARE carries no declaration at all;
# TESTS and PLANS carry one that differs only in the value of `prefix`.
BARE = "BARE"
TESTS = "TESTS"
PLANS = "PLANS"

TESTS_LANE_PREFIX = "tests"
PLANS_LANE_PREFIX = "docs/gauntlet/plans"

# The entry path and the fixed argument words that follow it.
ENTRY = "scripts/blind.sh"
ENTRY_ARGS = ["test"]

# The four lane hooks the grid is spelled against.
LANE_HOOKS = (
    "tests-lane.py",
    "plans-lane.py",
    "specs-lane.py",
    "verdicts-lane.py",
)

_COPIES = {}
_TMPDIR = None


def declaration_text(prefix):
    """The whole content of a ``blind-reads.json`` declaring one invocation.

    The three keys are the declaration: ``entry`` is the entry path, ``args``
    the fixed argument words that follow it, ``prefix`` the path prefix its one
    remaining argument sits under.
    """
    return json.dumps(
        {"runner_invocations": [{"entry": ENTRY, "args": ENTRY_ARGS, "prefix": prefix}]}
    )


def setUpModule():
    """Make the three copies of the hook directory, once for the file."""
    global _TMPDIR
    _TMPDIR = tempfile.TemporaryDirectory(prefix="blind-reads-hook-copies-")
    root = Path(_TMPDIR.name)
    for label, prefix in (
        (BARE, None),
        (TESTS, TESTS_LANE_PREFIX),
        (PLANS, PLANS_LANE_PREFIX),
    ):
        destination = root / label
        shutil.copytree(HOOK_DIR, destination)
        sibling = destination / DECLARATION_NAME
        if prefix is None:
            sibling.unlink(missing_ok=True)
        else:
            sibling.write_text(declaration_text(prefix))
        _COPIES[label] = destination


def tearDownModule():
    _TMPDIR.cleanup()


def hook_decision(copy_label, hook_name, command):
    """Feed one Bash payload to one hook in one copy; return its decision.

    Returns ``SILENT`` for empty stdout, the ``permissionDecision`` value when
    stdout is a hook answer, and the raw stdout otherwise so that an
    unrecognised answer shows up in the failure rather than being swallowed.
    """
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(REPO_CWD),
    }
    completed = subprocess.run(
        [sys.executable, str(_COPIES[copy_label] / hook_name)],
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


# The two labels a payload's differential can carry, plus the catch-all that
# keeps any other pair of answers visible in the failure.
OPENED = "DENY without the declaration, SILENT with it"
UNCHANGED = "the same answer under both copies"


def differential(base, other):
    """How one payload's answer moved between two copies of the hook dir."""
    if (base, other) == (DENY, SILENT):
        return OPENED
    if base == other:
        return UNCHANGED
    return "changed {0!r} -> {1!r}".format(base, other)


def _token():
    return uuid.uuid4().hex[:8]


def generate_listing():
    """Invent a listing at run time: ``(name, under_tests)`` pairs.

    Some names sit under ``tests`` and the rest under lane directories and
    under ``.claude/hooks``.  The flag is the generator's own label for how it
    built each name, never a recomputation of the hook's path normalisation.
    """
    return [
        ("tests/test_{0}.py".format(_token()), True),
        ("tests/unit_{0}/test_{1}.py".format(_token(), _token()), True),
        ("docs/gauntlet/plans/{0}.txt".format(_token()), False),
        ("docs/gauntlet/specs/{0}.txt".format(_token()), False),
        ("docs/gauntlet/verdicts/{0}.txt".format(_token()), False),
        (".claude/hooks/{0}.py".format(_token()), False),
    ]


def declared_invocation(name):
    """The declared entry, its fixed argument words, and one path argument."""
    return "{0} {1} {2}".format(ENTRY, " ".join(ENTRY_ARGS), name)


def traversal_spelling(name, under_tests):
    """Rewrite one listed name so that it opens under ``tests`` and walks.

    A name under ``tests`` becomes one that re-enters the same file through a
    ``..`` segment; a name outside ``tests`` becomes one reached from ``tests``
    through a ``..`` segment.  Every spelling this returns carries a ``..``.
    """
    if under_tests:
        _, _, tail = name.partition("/")
        return "tests/{0}/../{1}".format(_token(), tail)
    return "tests/../{0}".format(name)


class BlindRunnerDeclarationOnTheTestsLane(unittest.TestCase):
    """tests-lane.py, against a declaration naming its own lane directory."""

    maxDiff = None

    def test_only_the_bare_declared_invocation_under_the_prefix_opens(self):
        # Spec line 1.  Three families off one run-time listing, all on
        # tests-lane.py: the declared invocation bare, the same behind a
        # command word and behind a separator, and the two-argument form.  An
        # implementation that admits the declared entry wherever it appears in
        # the stage, rather than keying the whole invocation and its arity,
        # opens every `rm tests/t.py && scripts/blind.sh test <name>` payload,
        # so an agent that may not edit a test deletes one under a spelling the
        # lane answers nothing to; an arity-blind one opens the two-name form.
        listing = generate_listing()
        commands = {}
        expected = {}
        for stage_prefix in ("", "bash", "rm tests/t.py &&"):
            for name, under_tests in listing:
                invocation = declared_invocation(name)
                if stage_prefix:
                    invocation = "{0} {1}".format(stage_prefix, invocation)
                key = (stage_prefix, name)
                commands[key] = invocation
                opens = under_tests and not stage_prefix
                expected[key] = OPENED if opens else UNCHANGED
        for (first, _), (second, _) in zip(listing, listing[1:]):
            key = ("two names", "{0} {1}".format(first, second))
            commands[key] = "{0} {1}".format(declared_invocation(first), second)
            expected[key] = UNCHANGED
        actual = {
            key: differential(
                hook_decision(BARE, "tests-lane.py", command),
                hook_decision(TESTS, "tests-lane.py", command),
            )
            for key, command in commands.items()
        }
        self.assertEqual(actual, expected)


class BlindRunnerDeclarationAcrossTheLanes(unittest.TestCase):
    """The four lane hooks, against a declaration and against a foreign one."""

    maxDiff = None

    def test_the_declaration_opens_its_own_lane_only_at_its_own_prefix(self):
        # Spec line 2.  Two halves that fail to different implementations.  An
        # implementation keyed on the entry path and its fixed argument words
        # alone, with no constraint on the one remaining argument, opens the
        # lane-directory names under their own hooks, so one declaration turns
        # off the lane holding the plan gate's one-writer rule for every
        # command spelled with that entry.  An implementation that honours
        # whatever prefix a declaration names makes the BARE/PLANS changed set
        # nonempty, so a declaration file no lane hook guards turns off the
        # lane that guards the plan gate by naming its directory.
        listing = generate_listing()
        expected = {}
        actual = {}
        for hook_name in LANE_HOOKS:
            for name, under_tests in listing:
                command = declared_invocation(name)
                key = (hook_name, name)
                opens_here = hook_name == "tests-lane.py" and under_tests
                expected[key] = (OPENED if opens_here else UNCHANGED, UNCHANGED)
                bare = hook_decision(BARE, hook_name, command)
                actual[key] = (
                    differential(bare, hook_decision(TESTS, hook_name, command)),
                    differential(bare, hook_decision(PLANS, hook_name, command)),
                )
        self.assertEqual(actual, expected)


class BlindRunnerDeclarationOnTraversalSpellings(unittest.TestCase):
    """tests-lane.py, on arguments that open under the prefix and walk."""

    maxDiff = None

    def test_a_traversal_spelling_is_judged_by_where_it_normalizes(self):
        # Spec line 3.  Every payload here carries a `..`, and only where it
        # normalizes divides them.  An implementation that tests the declared
        # prefix against the raw argument text opens every spelling that opens
        # under `tests` and walks out of it, so an argument reaches an approved
        # plan through the spelling line 2 keeps out; an implementation that
        # refuses every `..` outright empties the changed set instead.
        listing = generate_listing()
        commands = {}
        expected = {}
        for name, under_tests in listing:
            spelling = traversal_spelling(name, under_tests)
            commands[spelling] = declared_invocation(spelling)
            expected[spelling] = OPENED if under_tests else UNCHANGED
        actual = {
            spelling: differential(
                hook_decision(BARE, "tests-lane.py", command),
                hook_decision(TESTS, "tests-lane.py", command),
            )
            for spelling, command in commands.items()
        }
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
