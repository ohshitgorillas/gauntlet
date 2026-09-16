"""Wire tests for the five keys of the sibling ``blind-reads.json``.

The surface is a copy of ``hooks/`` that differs only in its
``blind-reads.json``, a JSON payload on a hook's stdin, and the hook's decision
on stdout.  A second surface is the reader the scripts use,
``shell_shapes.py --config <key>``, whose stdout is the value a shell script
gets.  A third is ``scripts/blind.sh``, whose ``test`` lane and whose
``status``/``show`` paths are read through that same reader.

Every expectation here is about what a repo can and cannot move by naming a
key: ``tests_dir`` moves the writer's lane, ``gauntlet_dir`` moves all four
artifact lanes at once, ``docs_dir`` moves the prose a blind agent reads, and
any set whose names overlap moves nothing at all.  ``target_branch`` and
``gate_command`` are scalars rather than paths, so they resolve one key at a
time and a directory set that moves nothing leaves them standing.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKTREE_ROOT = Path(__file__).resolve().parents[1]
HOOK_DIR = WORKTREE_ROOT / "hooks"
BLIND_SH = WORKTREE_ROOT / "scripts" / "blind.sh"


def _main_checkout_root():
    """The checkout the copies were made from, as ``no-impl-reads.py`` anchors a path.

    That hook fails closed outside a checkout, so its payloads carry a real
    ``cwd``; the lane hooks take the name ``/repo`` and never look at disk.
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

DENY = "deny"
SILENT = ""

#: what each key is when the file names none, and what every unusable set
#: falls back to together
DEFAULTS = {"tests_dir": "tests", "gauntlet_dir": "gauntlet", "docs_dir": "docs"}


def _copy(tmp, label, conf):
    """A copy of the hook directory, in a project carrying ``conf`` as its declaration.

    The declaration is the project's, at ``<project>/.claude/blind-reads.json``,
    which is where the kit reads it from once it ships as a plugin: the hook
    directory travels with the plugin and carries no copy to fall back to.
    """
    project = Path(tmp) / label
    destination = project / "hooks"
    shutil.copytree(HOOK_DIR, destination)
    declaration = project / ".claude" / "blind-reads.json"
    declaration.parent.mkdir(parents=True, exist_ok=True)
    if conf is None:
        declaration.unlink(missing_ok=True)
    elif isinstance(conf, str):
        declaration.write_text(conf)
    else:
        declaration.write_text(json.dumps(conf))
    return destination


def _environment(project=None):
    """The caller's environment with ``GAUNTLET`` cleared, so a hook decides.

    Under ``GAUNTLET=off`` every hook returns silent at its first line, and a
    suite run from such a session would read that silence as an allow.

    ``CLAUDE_PROJECT_DIR`` names the copy's own project, so the declaration the
    copy reads is the one this surface wrote.  Without it the reader would walk
    up from the working directory and find this repository's own file, and
    every expectation here would be about that instead.
    """
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    if project is None:
        environment.pop("CLAUDE_PROJECT_DIR", None)
    else:
        environment["CLAUDE_PROJECT_DIR"] = str(project)
    return environment


def _decision(hook_dir, hook_name, payload):
    """One payload to one hook of one copy; its decision, or its raw stdout.

    ``hook_name`` is joined on with ``pathlib``, so an absolute path handed to it
    is the script that runs.  Stdout that is not a hook answer comes back raw
    rather than raising, so an unrecognised answer shows up in the failure
    instead of being swallowed.
    """
    completed = subprocess.run(
        [sys.executable, str(hook_dir / hook_name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=_environment(Path(hook_dir).parent),
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


def _config_run(hook_dir, key):
    """The reader as a shell sees it: status, stdout lines, stderr."""
    completed = subprocess.run(
        [sys.executable, str(hook_dir / "shell_shapes.py"), "--config", key],
        capture_output=True,
        text=True,
        check=False,
        env=_environment(Path(hook_dir).parent),
    )
    return completed.returncode, completed.stdout.splitlines(), completed.stderr


def _config_lines(hook_dir, key):
    status, lines, stderr = _config_run(hook_dir, key)
    if status != 0:
        raise AssertionError(f"the reader faulted on {key}: {stderr.strip()}")
    return lines


def _write(hook_dir, hook_name, path, agent=None):
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": path, "content": "x"},
        "cwd": "/repo",
    }
    if agent is not None:
        payload["agent_type"] = agent
    return _decision(hook_dir, hook_name, payload)


def _bash(hook_dir, hook_name, command, agent=None):
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": "/repo",
    }
    if agent is not None:
        payload["agent_type"] = agent
    return _decision(hook_dir, hook_name, payload)


def _read(hook_dir, path, agent="scrivener"):
    return _decision(
        hook_dir,
        "no-impl-reads.py",
        {
            "tool_name": "Read",
            "tool_input": {"file_path": str(REPO_CWD / path)},
            "cwd": str(REPO_CWD),
            "agent_type": agent,
        },
    )


class TestsDirMovesTheWritersLane(unittest.TestCase):
    """``tests_dir`` names the directory ``lanes.py`` guards."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")
        cls.bare = _copy(cls.tmp.name, "BARE", {})
        cls.moved = _copy(cls.tmp.name, "MOVED", {"tests_dir": "spec"})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_default_lane_is_tests_when_no_declaration_names_one(self):
        self.assertEqual(_write(self.bare, "lanes.py", "/repo/tests/t.py"), DENY)
        self.assertEqual(_write(self.bare, "lanes.py", "/repo/spec/t.py"), SILENT)
        self.assertEqual(_config_lines(self.bare, "tests_dir"), ["tests"])

    def test_named_dir_is_the_lane_and_tests_is_not(self):
        self.assertEqual(_write(self.moved, "lanes.py", "/repo/spec/t.py"), DENY)
        self.assertEqual(_write(self.moved, "lanes.py", "/repo/tests/t.py"), SILENT)
        self.assertEqual(_config_lines(self.moved, "tests_dir"), ["spec"])

    def test_writer_writes_the_named_dir_of_its_spec_tree_only(self):
        tree = "/repo/.claude/worktrees/x-spec"
        writer = "scrivener"
        self.assertEqual(_write(self.moved, "lanes.py", f"{tree}/spec/t.py", writer), SILENT)
        self.assertEqual(_write(self.moved, "lanes.py", f"{tree}/tests/t.py", writer), DENY)
        self.assertEqual(_write(self.moved, "lanes.py", "/repo/spec/t.py", writer), DENY)

    def test_the_blind_runner_reads_the_named_lane_and_not_the_default(self):
        # `scripts/blind.sh test <path>` is the blind agents' one entry point,
        # and the path it takes is the lane this repo named.  An implementation
        # reading the lane from a table instead of from the declaration admits
        # the argument under `tests/` in a repo whose lane is `spec/`, which is
        # a shell the writer can point at a directory no hook is guarding.
        # an admitted call comes back as an `updatedInput` rewrite of the head
        # rather than as silence, so what is read here is the command it left
        self.assertIn(
            "scripts/blind.sh test spec/t.py",
            _bash(self.moved, "blind-bash.py", "scripts/blind.sh test spec/t.py", "scrivener"),
        )
        self.assertEqual(
            _bash(self.moved, "blind-bash.py", "scripts/blind.sh test tests/t.py", "scrivener"),
            DENY,
        )
        self.assertIn(
            "scripts/blind.sh test tests/t.py",
            _bash(self.bare, "blind-bash.py", "scripts/blind.sh test tests/t.py", "scrivener"),
        )
        # the shape is the whole invocation and its arity, at either lane
        self.assertEqual(
            _bash(
                self.moved,
                "blind-bash.py",
                "rm spec/t.py && scripts/blind.sh test spec/t.py",
                "scrivener",
            ),
            DENY,
        )
        self.assertEqual(
            _bash(
                self.moved,
                "blind-bash.py",
                "scripts/blind.sh test spec/a.py spec/b.py",
                "scrivener",
            ),
            DENY,
        )
        # and an argument that opens under the lane and walks out of it is not a run
        self.assertEqual(
            _bash(
                self.moved,
                "blind-bash.py",
                "scripts/blind.sh test spec/a/../../gauntlet/specs/approved/x.txt",
                "scrivener",
            ),
            DENY,
        )


class GauntletDirMovesEveryLane(unittest.TestCase):
    """``gauntlet_dir`` moves all four artifact lanes and nothing under them."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")
        cls.bare = _copy(cls.tmp.name, "BARE", {})
        cls.moved = _copy(cls.tmp.name, "MOVED", {"gauntlet_dir": "work/chain"})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_each_lane_hook_guards_the_lane_under_the_named_base(self):
        for hook, suffix, reviewer in (
            ("lanes.py", "specs/approved", "arbiter"),
            ("lanes.py", "plans/approved", "prosecutor"),
            ("lanes.py", "verdicts", "juror"),
            ("lanes.py", "reviews", "arbiter"),
        ):
            with self.subTest(hook=hook):
                moved_path = f"/repo/work/chain/{suffix}/slug.txt"
                default_path = f"/repo/gauntlet/{suffix}/slug.txt"
                self.assertEqual(_write(self.moved, hook, moved_path), DENY)
                self.assertEqual(_write(self.moved, hook, moved_path, reviewer), SILENT)
                # the base the kit ships is an ordinary directory once moved
                self.assertEqual(_write(self.moved, hook, default_path), SILENT)
                # and the hook that has not moved still guards the shipped base
                self.assertEqual(_write(self.bare, hook, default_path), DENY)

    def test_the_structure_under_the_base_does_not_move(self):
        self.assertEqual(_config_lines(self.moved, "gauntlet_dir"), ["work/chain"])
        self.assertEqual(_config_lines(self.moved, "specs_lane"), ["work/chain/specs/approved"])
        self.assertEqual(_config_lines(self.moved, "plans_lane"), ["work/chain/plans/approved"])
        self.assertEqual(_config_lines(self.moved, "reviews_lane"), ["work/chain/reviews"])
        self.assertEqual(_config_lines(self.moved, "verdicts_lane"), ["work/chain/verdicts"])

    def test_the_blind_agent_reads_the_moved_block_and_not_the_moved_base(self):
        # The one subtree of the base a blind agent works from moves with it,
        # and the rest of the base stays denied at its new location.  An
        # implementation re-allowing the specs by a literal hands a moved repo's
        # blind writer either nothing or the whole base.
        self.assertEqual(_read(self.moved, "work/chain/specs/approved/demo.txt"), SILENT)
        self.assertEqual(_read(self.moved, "work/chain/plans/approved/demo.txt"), DENY)
        self.assertEqual(_read(self.moved, "work/chain/reviews/demo.1.txt"), DENY)
        self.assertEqual(_read(self.moved, "work/chain/specs/drafts/demo.txt"), DENY)


class DocsDirMovesTheBlindReadAllowance(unittest.TestCase):
    """``docs_dir`` names the prose a blind agent may read."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")
        cls.bare = _copy(cls.tmp.name, "BARE", {})
        cls.moved = _copy(cls.tmp.name, "MOVED", {"docs_dir": "prose"})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_named_dir_is_readable_and_the_default_name_is_not(self):
        self.assertEqual(_read(self.moved, "prose/testing.md"), SILENT)
        self.assertEqual(_read(self.moved, "docs/testing.md"), DENY)
        self.assertEqual(_read(self.bare, "docs/testing.md"), SILENT)
        self.assertEqual(_config_lines(self.moved, "docs_dir"), ["prose"])

    def test_the_allowance_is_anchored_at_the_repo_root(self):
        # An entry is the repository's own file of that name, never any
        # directory so named: a `src/prose/testing.md` read as documentation
        # hands the blind agent the implementation under a directory it chose.
        self.assertEqual(_read(self.moved, "src/prose/testing.md"), DENY)
        # and the allowance is that one policy file, not the prose around it:
        # a design note there quotes the code it describes.
        self.assertEqual(_read(self.moved, "prose/sub/deep.md"), DENY)


class AnOverlappingSetMovesNothing(unittest.TestCase):
    """Any pair of names that touch voids the whole declaration."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _falls_back(self, label, conf):
        """Every key at its default, and the default lanes guarded again."""
        copy = _copy(self.tmp.name, label, conf)
        for key, default in DEFAULTS.items():
            self.assertEqual(_config_lines(copy, key), [default], (conf, key))
        self.assertEqual(_write(copy, "lanes.py", "/repo/tests/t.py"), DENY, conf)
        self.assertEqual(
            _write(copy, "lanes.py", "/repo/gauntlet/specs/approved/s.txt"), DENY, conf
        )

    def test_a_lane_directory_itself(self):
        self._falls_back("LANE", {"tests_dir": "gauntlet/specs/approved"})

    def test_a_name_under_another(self):
        self._falls_back("UNDER", {"tests_dir": "gauntlet/x"})
        self._falls_back("BASEUNDER", {"gauntlet_dir": "tests/artifacts"})

    def test_a_name_over_another(self):
        self._falls_back("OVER", {"tests_dir": "."})
        self._falls_back("BASEOVER", {"gauntlet_dir": "."})

    def test_a_key_the_file_omits_still_collides(self):
        # `tests_dir` of `docs` is a usable name read on its own.  It is the
        # default `docs_dir` it lands on, so an implementation checking only the
        # keys the file declares puts the writer's lane over the prose.
        self._falls_back("DEFAULTCLASH", {"tests_dir": "docs"})
        self._falls_back("BASECLASH", {"gauntlet_dir": "docs"})

    def test_two_declared_keys_naming_the_same_directory(self):
        self._falls_back("SAME", {"tests_dir": "one", "docs_dir": "one"})

    def test_a_traversal_that_resolves_into_another(self):
        self._falls_back("WALK", {"tests_dir": "spec/../gauntlet/reviews"})

    def test_an_absolute_path_and_a_walk_out_of_the_checkout(self):
        self._falls_back("ABS", {"tests_dir": "/repo/spec"})
        self._falls_back("OUT", {"tests_dir": "../spec"})

    def test_a_value_that_is_not_a_string(self):
        self._falls_back("LIST", {"tests_dir": ["spec"]})
        self._falls_back("EMPTY", {"docs_dir": ""})

    def test_one_bad_key_does_not_leave_the_others_moved(self):
        # The whole point of the all-or-nothing rule: a set that would be
        # usable but for one name moves no directory at all, so a typo cannot
        # half-apply a layout and leave one hook guarding a directory the rest
        # of the kit no longer uses.
        self._falls_back(
            "PARTIAL", {"tests_dir": "spec", "gauntlet_dir": "spec/chain", "docs_dir": "prose"}
        )


class OneReaderOneKeySet(unittest.TestCase):
    """``shell_shapes.py --config`` answers the five keys, the four lanes, nothing else."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")
        cls.bare = _copy(cls.tmp.name, "BARE", {})
        cls.extra = _copy(
            cls.tmp.name,
            "EXTRA",
            {"tests_dir": "spec", "runners": ["pytest"], "allow": ["gauntlet/"]},
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_an_unknown_key_in_the_file_is_ignored_and_the_known_one_read(self):
        # There is no `allow` key and no `runners` key.  A declaration carrying
        # one names nothing: an implementation honouring an `allow` entry over
        # the artifact base re-opens the plans and the reviewer rounds to a
        # blind agent, which is the whole of what the base is denied for.
        self.assertEqual(_config_lines(self.extra, "tests_dir"), ["spec"])
        self.assertEqual(_config_lines(self.extra, "allow"), [])
        self.assertEqual(_config_lines(self.extra, "runners"), [])
        self.assertEqual(_read(self.extra, "gauntlet/plans/approved/demo.txt"), DENY)
        self.assertEqual(_read(self.extra, "gauntlet/reviews/demo.1.txt"), DENY)
        self.assertEqual(_read(self.extra, "gauntlet/specs/approved/demo.txt"), SILENT)

    def test_an_unknown_key_asked_of_the_reader_is_no_lines(self):
        self.assertEqual(_config_lines(self.bare, "tests.dir"), [])
        self.assertEqual(_config_lines(self.bare, "runner_invocations"), [])
        self.assertEqual(_config_lines(self.bare, "agents.writer"), [])



class BlindAgentReadsTheConfig(unittest.TestCase):
    """``no-impl-reads.py`` allows the one file that says where the directories are."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")
        cls.bare = _copy(cls.tmp.name, "BARE", {})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_blind_reads_json_is_readable_and_its_siblings_are_not(self):
        self.assertEqual(_read(self.bare, ".claude/blind-reads.json"), SILENT)
        self.assertEqual(_read(self.bare, "hooks/shell_shapes.py"), DENY)
        self.assertEqual(_read(self.bare, ".claude/settings.json"), DENY)


class BlindShellReadsTheSameKeys(unittest.TestCase):
    """``scripts/blind.sh`` takes its lane and its block path from the same reader."""

    def test_the_script_reads_the_keys_the_reader_answers(self):
        # The script and the hooks share one reader, so a repo that moved a
        # directory moves both together.  A script reading a key the reader does
        # not answer gets an empty value and binds or shows the wrong path.
        text = BLIND_SH.read_text()
        self.assertIn("--config", text)
        for key in ("tests_dir", "specs_lane"):
            self.assertIn(key, text, key)
        for gone in ("tests.dir", "runner_invocations"):
            self.assertNotIn(gone, text, gone)

    def test_the_script_names_no_lane_of_its_own(self):
        # Every artifact path it types comes from the reader; a literal here is
        # a second place a moved repo would have to be edited, and the one the
        # lane hooks would not agree with.
        self.assertNotIn("gauntlet/specs/approved", BLIND_SH.read_text())


class ADeclarationThatIsAFault(unittest.TestCase):
    """An absent or malformed file is a fault, and never the kit's defaults.

    The three cases were one answer once: a project that declared nothing, a
    project whose file was a typo, and a project that meant the defaults all
    resolved to the same empty config.  That made a typo in `target_branch` a
    merge onto `main` and a typo in `pytest_command` a red run with its
    deselection dropped, in both cases with nothing said to anyone.  Only the
    third is a word now; the other two reach the operator, as a denial out of a
    hook and as a non-zero exit out of the reader.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="fault-config-")
        cls.absent = _copy(cls.tmp.name, "FABSENT", None)
        cls.broken = _copy(cls.tmp.name, "FBROKEN", "{not json")
        cls.not_object = _copy(cls.tmp.name, "FLIST", '["tests_dir"]')
        cls.empty = _copy(cls.tmp.name, "FEMPTY", {})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_reader_exits_non_zero_and_names_the_path(self):
        for label, copy in (
            ("absent", self.absent),
            ("malformed", self.broken),
            ("not an object", self.not_object),
        ):
            status, lines, stderr = _config_run(copy, "tests_dir")
            self.assertEqual(status, 2, label)
            self.assertEqual(lines, [], label)
            self.assertIn(".claude/blind-reads.json", stderr, label)

    def test_a_hook_denies_rather_than_guarding_the_default_lane(self):
        # The lane is a configured directory.  A hook that cannot read the
        # declaration does not know which directory it guards, so it refuses
        # instead of guarding the kit's and calling that a decision.
        for label, copy in (("absent", self.absent), ("malformed", self.broken)):
            self.assertEqual(_write(copy, "lanes.py", "/repo/src/main.py"), DENY, label)
            self.assertEqual(_write(copy, "lanes.py", "/repo/README.md"), DENY, label)

    def test_the_denial_names_the_file_and_the_way_out(self):
        completed = subprocess.run(
            [sys.executable, str(self.absent / "lanes.py")],
            input=json.dumps(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Write",
                    "cwd": str(REPO_CWD),
                    "tool_input": {"file_path": "/repo/src/main.py"},
                }
            ),
            capture_output=True,
            text=True,
            env=_environment(Path(self.absent).parent),
        )
        reason = json.loads(completed.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("blind-reads.json", reason)
        self.assertIn("scripts/init.py", reason)

    def test_the_empty_object_is_the_projects_word_and_resolves(self):
        # `{}` is how a project asks for the shipped layout and means it.  It is
        # the one shape `scripts/init.py` cannot be needed for, and the one that
        # separates "declared nothing" from "declared the defaults".
        for key, default in DEFAULTS.items():
            self.assertEqual(_config_lines(self.empty, key), [default], key)
        self.assertEqual(_write(self.empty, "lanes.py", "/repo/tests/t.py"), DENY)
        self.assertEqual(_write(self.empty, "lanes.py", "/repo/src/main.py"), SILENT)


if __name__ == "__main__":
    unittest.main()


#: the two scalars, and what each is when the file names none
SCALARS = {"target_branch": "main", "gate_command": "make check"}


class TwoScalarsResolvedOnTheirOwn(unittest.TestCase):
    """``target_branch`` and ``gate_command`` fall back one key at a time.

    They are what ``scripts/pair.sh merge`` converges onto, and neither can
    collide with a lane or with the other, so an unusable value has nothing to
    take down with it.  A directory set is the opposite case: its names overlap
    each other, so one bad name voids all three together.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="scalars-config-")
        cls.bare = _copy(cls.tmp.name, "SBARE", {})
        cls.named = _copy(
            cls.tmp.name,
            "SNAMED",
            {"target_branch": "dev", "gate_command": "scripts/gates/check-gates.sh"},
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_a_file_that_names_neither_is_the_defaults(self):
        # The empty object names neither and is still the project's word, so
        # both scalars are the kit's.  An absent file is a fault instead, and
        # `ADeclarationThatIsAFault` is where that is pinned.
        for key, default in SCALARS.items():
            self.assertEqual(_config_lines(self.bare, key), [default], key)

    def test_the_reader_answers_the_two_names_a_project_gives(self):
        self.assertEqual(_config_lines(self.named, "target_branch"), ["dev"])
        self.assertEqual(
            _config_lines(self.named, "gate_command"), ["scripts/gates/check-gates.sh"]
        )

    def test_an_unusable_value_falls_back_alone(self):
        # A newline is what separates a branch name from a second command
        # smuggled after it, so a multi-line value is not a scalar at all.
        for label, conf, expected in (
            ("SLIST", {"target_branch": ["dev"], "gate_command": "gate"}, ["main", "gate"]),
            ("SEMPTY", {"target_branch": "  ", "gate_command": "gate"}, ["main", "gate"]),
            (
                "SLINES",
                {"target_branch": "dev", "gate_command": "a\nrm -rf /"},
                ["dev", "make check"],
            ),
        ):
            copy = _copy(self.tmp.name, label, conf)
            read = [
                _config_lines(copy, "target_branch")[0],
                _config_lines(copy, "gate_command")[0],
            ]
            self.assertEqual(read, expected, conf)

    def test_a_directory_set_that_moves_nothing_still_leaves_the_scalars(self):
        # The all-or-nothing rule is about names that can collide.  A branch and
        # a command cannot collide with a lane, so voiding the directories has
        # no reason to reach them, and a merge that silently converged on the
        # wrong branch is the cost of letting it.
        copy = _copy(
            self.tmp.name,
            "SVOID",
            {"tests_dir": "docs", "target_branch": "dev", "gate_command": "gate"},
        )
        for key, default in DEFAULTS.items():
            self.assertEqual(_config_lines(copy, key), [default], key)
        self.assertEqual(_config_lines(copy, "target_branch"), ["dev"])
        self.assertEqual(_config_lines(copy, "gate_command"), ["gate"])


def _git(cwd, *args):
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"},
    )


class TheWalkFindsTheProjectFromInsideAWorktree(unittest.TestCase):
    """What the reader answers with ``CLAUDE_PROJECT_DIR`` unset, from a worktree.

    A worktree's ``.git`` is a pointer file rather than a directory, so a walk
    that stops at the first ``.git`` stops in the worktree.  The worktree
    carries no ``.claude/blind-reads.json`` of its own -- the declaration is
    committed in the project, and the tree is a checkout of a branch, not a
    second project -- so stopping there reads the declaration as absent, which
    is a fault the reader exits non-zero on rather than a lane moved silently
    back to its kit default.

    The variable is the knob and both scripts export it, so this is the
    fallback rather than the usual path.  It is still the path any other
    ``Bash`` child takes.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.project = Path(cls.tmp.name) / "project"
        cls.project.mkdir()
        _git(cls.tmp.name, "init", "-q", "-b", "main", "project")
        (cls.project / "README").write_text("x")
        _git(cls.project, "add", "-A")
        _git(cls.project, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
        #: written after the commit, so the worktree gets no copy of it -- which
        #: is the shape the walk stopped on
        (cls.project / ".claude").mkdir()
        (cls.project / ".claude" / "blind-reads.json").write_text(
            json.dumps({"tests_dir": "spec"})
        )
        cls.tree = cls.project / ".claude" / "worktrees" / "slug-spec"
        _git(cls.project, "worktree", "add", "-q", "-b", "slug", str(cls.tree))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _run(self, cwd):
        environment = dict(os.environ)
        environment.pop("GAUNTLET", None)
        environment.pop("CLAUDE_PROJECT_DIR", None)
        completed = subprocess.run(
            [sys.executable, str(HOOK_DIR / "shell_shapes.py"), "--config", "tests_dir"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
        return completed

    def _tests_dir(self, cwd):
        completed = self._run(cwd)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout.strip()

    def test_the_worktree_carries_no_declaration_of_its_own(self):
        self.assertFalse((self.tree / ".claude" / "blind-reads.json").exists())
        self.assertTrue((self.tree / ".git").is_file())

    def test_the_main_checkout_reads_its_declaration(self):
        self.assertEqual(self._tests_dir(self.project), "spec")

    def test_the_worktree_reads_the_projects_declaration_and_not_the_default(self):
        self.assertEqual(self._tests_dir(self.tree), "spec")

    def test_a_directory_under_the_worktree_reads_it_too(self):
        deeper = self.tree / "spec" / "unit"
        deeper.mkdir(parents=True, exist_ok=True)
        self.assertEqual(self._tests_dir(deeper), "spec")

    def test_outside_any_checkout_there_is_no_project_and_that_is_a_fault(self):
        # No project and no copy beside the kit is no declaration at all.  The
        # reader exits non-zero and names the file, because a `tests_dir` printed
        # here would be substituted into a shell that binds a lane with it.
        completed = self._run(self.tmp.name)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("blind-reads.json", completed.stderr)
