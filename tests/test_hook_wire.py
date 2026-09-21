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
#: The read guard is held under every spelling a blind sweeper arrives as, so
#: the allowlist is one table for the tuple rather than one per name.
BLIND_READERS = ("scrivener", "auditor", "gauntlet:auditor")


#: ``plugin_root=`` selectors for ``hook_decision``. The default leaves the
#: launching shell's ``CLAUDE_PLUGIN_ROOT`` exactly as it came; ``ABSENT``
#: takes the variable off the child's environment entirely. Anything else is a
#: path the child is run with.
INHERIT_PLUGIN_ROOT = object()
ABSENT_PLUGIN_ROOT = object()


def hook_decision(hook_name, payload, plugin_root=INHERIT_PLUGIN_ROOT):
    """Feed one payload to one hook on stdin; return its decision.

    Returns ``SILENT`` for empty stdout, the ``permissionDecision`` value when
    stdout is a hook answer, and the raw stdout otherwise so that an
    unrecognised answer shows up in the failure rather than being swallowed.

    ``GAUNTLET`` is cleared for the child. Under ``GAUNTLET=off`` a hook
    returns at its first line, so a bypassed session would run this whole file
    against hooks that decide nothing.

    ``plugin_root`` sets the ``CLAUDE_PLUGIN_ROOT`` the child runs under:
    ``ABSENT_PLUGIN_ROOT`` unsets it, a path sets it, and the default carries
    the caller's own through.
    """
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    if plugin_root is ABSENT_PLUGIN_ROOT:
        environment.pop("CLAUDE_PLUGIN_ROOT", None)
    elif plugin_root is not INHERIT_PLUGIN_ROOT:
        environment["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    completed = subprocess.run(
        [sys.executable, str(HOOK_DIR / hook_name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=environment,
        check=False,
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


def plugin_root_states(kitless_directory):
    """The ``CLAUDE_PLUGIN_ROOT`` states a hook has to answer the same under.

    A hook's answer is a property of the tree it is asked about, so the map it
    returns cannot move when the launching shell names no plugin root, names
    the checkout whose hooks are under test, or names a directory holding no
    kit at all.
    """
    return {
        "no CLAUDE_PLUGIN_ROOT": ABSENT_PLUGIN_ROOT,
        "CLAUDE_PLUGIN_ROOT on the checkout under test": WORKTREE_ROOT,
        "CLAUDE_PLUGIN_ROOT on a kitless directory": kitless_directory,
    }


def kitless_directory(tmp_path):
    """A directory that exists and holds no kit."""
    directory = tmp_path / "kitless"
    directory.mkdir()
    return directory


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
        assert lane_sweep(expected, REPO_CWD) == expected

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
        assert actual == {agent: expected for agent in reviewers}


class NoImplReadsShellShapes(unittest.TestCase):
    """no-impl-reads.py, the guard that keeps the blind agent blind."""

    maxDiff = None

    def test_allowlisted_directories_are_anchored_at_the_repo_root(self):
        # Spec line 6.  Read tool surface.  `docs` and `tests` name allowlisted
        # directories at the root; nested under src/ they name implementation.
        # A guard matching an allowlist entry at any depth hands the blind agent
        # src/docs/impl.py whole.
        # auditor line 2.  The sweeper keeps the reads a sweep is made of by
        # the same root-anchored table, under both spellings it arrives as.
        paths = {
            str(REPO_CWD / "src" / "docs" / "impl.py"): DENY,
            str(REPO_CWD / "src" / "tests" / "impl.py"): DENY,
            str(REPO_CWD / "docs" / "testing.md"): SILENT,
            str(REPO_CWD / "tests" / "test_hook_wire.py"): SILENT,
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
        expected = {
            (reader, file_path): verdict
            for reader in BLIND_READERS
            for file_path, verdict in paths.items()
        }
        actual = sweep(
            "no-impl-reads.py",
            expected,
            lambda key: read_payload(key[1], REPO_CWD, key[0]),
        )
        assert actual == expected


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
        assert actual == expected


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
        assert actual == expected


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
            "prosecutor": SILENT,
        }
        plan = REPO_CWD / "gauntlet" / "plans" / "approved" / "demo.txt"
        actual = sweep(
            "lanes.py",
            expected,
            lambda agent_type: write_payload(plan, REPO_CWD, agent_type),
        )
        assert actual == expected


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
        assert actual == expected


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
        assert actual == expected


class TheCallerGate(unittest.TestCase):
    """The two caller-gated hooks, over the callers session wiring hands them.

    Frontmatter wiring is gone: a plugin-shipped agent definition runs none, so
    `no-impl-reads.py` and `blind-bash.py` are wired session-wide and every
    caller's tool call reaches them. What keeps them off the main agent is the
    `agent_type` key, and these cases are both directions of that one rule.
    """

    maxDiff = None

    #: two implementation paths on no allowlist, sharing no directory, one of
    #: them under a name the allowlist admits only at the root; and a shell
    #: command that is not the blind agents' one entry point
    SOURCES = ("hooks/shell_shapes.py", "src/docs/impl.py")
    COMMAND = "cat hooks/shell_shapes.py"

    #: the writing verb of the one entry point, which is the writer's own and
    #: nobody else's: the reviewing agents run the suite, they do not rewrite it
    FORMAT = "scripts/blind.sh format tests/t.py"

    #: an admitted Bash call comes back as an `updatedInput` rewrite carrying
    #: the command, rather than as the silence an unjudged caller gets
    ADMITTED = "admitted"

    def test_the_blind_agents_are_read_blocked_and_the_main_agent_is_not(self):
        # An absent `agent_type` is the main agent, which has to read the
        # implementation to adjudicate a failing test. A guard that judged
        # every caller would blind it the moment the hook went session-wide.
        callers = {
            "arbiter": DENY,
            "scrivener": DENY,
            "juror": DENY,
            "bailiff": DENY,
            "auditor": DENY,
            "gauntlet:auditor": DENY,
            None: SILENT,
            "": SILENT,
            "prosecutor": SILENT,
            "examiner": SILENT,
            "detective": SILENT,
            "general-purpose": SILENT,
        }
        expected = {
            (agent, source): verdict
            for agent, verdict in callers.items()
            for source in self.SOURCES
        }
        actual = {
            (agent, source): hook_decision(
                "no-impl-reads.py",
                read_payload(REPO_CWD / source, REPO_CWD, agent),
            )
            for agent, source in expected
        }
        assert actual == expected

    def test_the_two_shell_locked_agents_are_locked_and_no_other_caller_is(self):
        # `blind-bash.py` is an allowlist of one entry point, so a caller it
        # judges loses every other command. Wired session-wide without the
        # gate it would take the main agent's shell outright.
        # The allowlist is read per caller and not per command: the writer is
        # the one caller that may rewrite the lane, so the writing verb is the
        # one command the two judged callers are answered differently at, and
        # a hook admitting it for its whole blind tuple hands the reviewing
        # agent a write into the tests dir every other route denies it.
        judged = {
            "scrivener": DENY,
            "bailiff": DENY,
            None: SILENT,
            "": SILENT,
            "arbiter": SILENT,
            "juror": SILENT,
            "prosecutor": SILENT,
            "general-purpose": SILENT,
        }
        expected = {
            **{(agent, self.COMMAND): verdict for agent, verdict in judged.items()},
            **{(agent, self.FORMAT): verdict for agent, verdict in judged.items()},
            ("scrivener", self.FORMAT): self.ADMITTED,
        }

        def classify(command, answer):
            return self.ADMITTED if command in answer else answer

        actual = {
            (agent, command): classify(
                command,
                hook_decision("blind-bash.py", bash_payload(command, REPO_CWD, agent)),
            )
            for agent, command in expected
        }
        assert actual == expected

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
        assert {guard: guard in wired for guard in blind_guards} == dict.fromkeys(
            blind_guards, True
        )

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
        assert [command for command in sorted(project_wired) if "/hooks/" in command] == []

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
        assert actual == {
            "count": 9,
            "off the plugin root": [],
            "on the project dir": [],
            "absent from the kit": [],
        }

    def test_no_agent_definition_wires_a_hook_in_its_own_frontmatter(self):
        definitions = sorted((WORKTREE_ROOT / "agents").glob("*.md"))
        wiring = [
            definition.name for definition in definitions if "hooks:" in definition.read_text()
        ]
        assert (bool(definitions), wiring) == (True, [])


if __name__ == "__main__":
    unittest.main()
