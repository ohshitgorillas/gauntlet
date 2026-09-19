"""Wire tests for the PreToolUse hooks in hooks/.

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

# A path with no `.git` at or above it, used by the approved-spec cases.
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


class RemovedWithTheClassifier(unittest.TestCase):
    """The lane hooks over `Bash`, which is no lane hook's business any more.

    Whole classes here pinned how a lane read a command string: separators,
    redirections, heredocs, inline scripts, runner spellings, git read and
    write forms. That reading is gone, and the question it answered is gone
    with it -- a lane's shell half is the mount table now, and
    `bwrap-wrap.py` binds every lane directory read-only inside every wrapped
    profile. What is left to pin from this side is that no lane hook answers a
    `Bash` call at all, whatever the command names.
    """

    maxDiff = None

    def test_no_lane_hook_answers_a_bash_call_whatever_it_names(self):
        commands = (
            "sed -i 's/a/b/' tests/t.py",
            "cd tests && rm t.py",
            "find tests -name '*.py' -delete",
            "cat impl.py 1> gauntlet/specs/approved/s.txt",
            "python3 - <<EOF\nopen('tests/t.py','w')\nEOF",
            "git diff --output=gauntlet/reviews/x.txt",
            "printf '%s' x | tee gauntlet/reviews/a.txt",
            "echo RED > gauntlet/verdicts/demo.txt",
            "cat tests/t.py",
        )
        expected = {command: PASSES for command in commands}
        self.assertEqual(lane_sweep(expected, REPO_CWD), expected)

    def test_a_reviewers_own_shell_is_held_by_its_profile_and_not_by_a_lane(self):
        # The reviewer read-block still fires on `Read` and `Grep`; on `Bash` it
        # is the reviewer profile -- read-only everywhere, tmpfs over the lane --
        # that leaves the rounds unreadable and the checkout unchanged.
        commands = (
            "ls gauntlet/reviews/",
            "find gauntlet/reviews -name 'pair-sh.*'",
            "sed -i 's/a/b/' src/m.py",
        )
        expected = {command: PASSES for command in commands}
        reviewers = ("arbiter", "prosecutor")
        actual = {agent: lane_sweep(expected, REPO_CWD, agent) for agent in reviewers}
        self.assertEqual(actual, {agent: expected for agent in reviewers})


class NoImplReadsShellShapes(unittest.TestCase):
    """no-impl-reads.py, the guard that keeps the blind agent blind."""

    maxDiff = None

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
    """The lane table's row for the approved specs."""

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
            "lanes.py",
            expected,
            lambda agent_type: write_payload(block, REPO_CWD, agent_type),
        )
        self.assertEqual(actual, expected)


class LanesWithoutGitRoot(unittest.TestCase):
    """The approved-spec and approved-plan rows, where no `.git` sits above the cwd."""

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
            ("lanes.py", "/nogit/gauntlet/specs/approved"): DENY,
            ("lanes.py", "/nogit/gauntlet/specs/approved/s.txt"): DENY,
            ("lanes.py", "/nogit/gauntlet/specs/drafts/s.txt"): SILENT,
            ("lanes.py", "/nogit/gauntlet/plans/approved/p.txt"): DENY,
            ("lanes.py", "/nogit/gauntlet/plans/drafts/p.txt"): SILENT,
        }
        actual = {
            (hook_name, file_path): hook_decision(hook_name, write_payload(file_path, NOGIT_CWD))
            for hook_name, file_path in expected
        }
        self.assertEqual(actual, expected)


class PlansLaneCallers(unittest.TestCase):
    """The lane table's row for the approved plans."""

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
            "lanes.py",
            expected,
            lambda agent_type: write_payload(plan, REPO_CWD, agent_type),
        )
        self.assertEqual(actual, expected)


class ReviewsLaneOnAnApprovedPlan(unittest.TestCase):
    """The reviewers' row, on the plan path the plan reviewer owns."""

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
            "lanes.py",
            expected,
            lambda agent_type: write_payload(plan, REPO_CWD, agent_type),
        )
        self.assertEqual(actual, expected)


#: the lane hook, wired on the write tools and on `Read`/`Grep` and not on
#: `Bash`. It is run against a shell payload here anyway, because a hook
#: answers what it is handed whatever the manifest says, and the answer that
#: has to hold is silence: the mount table is what stops a shell write into a
#: lane now.
SESSION_LANE_HOOKS = ("lanes.py",)


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


class TheBlindWritersShell(unittest.TestCase):
    """`blind-bash.py` over the writer's shell: one entry point, nothing else.

    No lane hook answers a `Bash` call any more, so this hook is the whole of
    what holds that shell shut on the path side; the mount table is what holds
    it on the filesystem side.
    """

    maxDiff = None

    def test_the_blind_writer_shell_is_one_command(self):
        # `blind-bash.py` answers on the caller and the entry point rather
        # than on any path, so an ordinary read is denied the writer exactly
        # as a write is.
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
        blind_guards = ("no-impl-reads.py", "blind-bash.py")
        self.assertEqual({guard: guard in wired for guard in blind_guards}, dict.fromkeys(blind_guards, True))

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
        self.assertEqual([command for command in sorted(project_wired) if "/hooks/" in command], [])

    def test_every_hook_command_the_manifest_names_resolves_in_the_kit(self):
        # `${CLAUDE_PLUGIN_ROOT}` is the root of this repo once it is installed,
        # so a manifest naming a script that is not here wires nothing.
        commands = [
            hook["command"]
            for event in MANIFEST["hooks"].values()
            for entry in event
            for hook in entry["hooks"]
        ]
        scripts = [command.split("/hooks/", 1)[1].split()[0] for command in commands]
        actual = {
            "count": len(commands),
            "off the plugin root": [c for c in commands if "${CLAUDE_PLUGIN_ROOT}" not in c],
            "on the project dir": [c for c in commands if "${CLAUDE_PROJECT_DIR}" in c],
            "absent from the kit": [s for s in scripts if not (HOOK_DIR / s).is_file()],
        }
        self.assertEqual(
            actual,
            {"count": 9, "off the plugin root": [], "on the project dir": [], "absent from the kit": []},
        )

    def test_no_agent_definition_wires_a_hook_in_its_own_frontmatter(self):
        definitions = sorted((WORKTREE_ROOT / "agents").glob("*.md"))
        wiring = [definition.name for definition in definitions if "hooks:" in definition.read_text()]
        self.assertEqual((bool(definitions), wiring), (True, []))


if __name__ == "__main__":
    unittest.main()
