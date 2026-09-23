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

#: the whole observation an unusable declaration must come back with: every key
#: at its default, and the two default lanes guarded again
FALLEN_BACK = {
    **{key: [default] for key, default in DEFAULTS.items()},
    "tests lane": DENY,
    "specs lane": DENY,
}


def copy_hook_dir(tmp, label, conf):
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


def decision(hook_dir, hook_name, payload):
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


def _config_run(hook_dir, key):
    """The reader as a shell sees it: status, stdout lines, stderr."""
    completed = subprocess.run(
        [sys.executable, str(hook_dir / "lib" / "shell_shapes.py"), "--config", key],
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
    return decision(hook_dir, hook_name, payload)


def _read(hook_dir, path, agent="scrivener"):
    return decision(
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
        cls.bare = copy_hook_dir(cls.tmp.name, "BARE", {})
        cls.moved = copy_hook_dir(cls.tmp.name, "MOVED", {"tests_dir": "spec"})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_default_lane_is_tests_when_no_declaration_names_one(self):
        observed = {
            "tests/t.py": _write(self.bare, "lanes.py", "/repo/tests/t.py"),
            "spec/t.py": _write(self.bare, "lanes.py", "/repo/spec/t.py"),
            "tests_dir": _config_lines(self.bare, "tests_dir"),
        }
        assert observed == {"tests/t.py": DENY, "spec/t.py": SILENT, "tests_dir": ["tests"]}

    def test_named_dir_is_the_lane_and_tests_is_not(self):
        observed = {
            "spec/t.py": _write(self.moved, "lanes.py", "/repo/spec/t.py"),
            "tests/t.py": _write(self.moved, "lanes.py", "/repo/tests/t.py"),
            "tests_dir": _config_lines(self.moved, "tests_dir"),
        }
        assert observed == {"spec/t.py": DENY, "tests/t.py": SILENT, "tests_dir": ["spec"]}

    def test_writer_writes_the_named_dir_of_its_spec_tree_only(self):
        tree = "/repo/.claude/worktrees/x-spec"
        writer = "scrivener"
        observed = {
            "lane, tree": _write(self.moved, "lanes.py", f"{tree}/spec/t.py", writer),
            "default, tree": _write(self.moved, "lanes.py", f"{tree}/tests/t.py", writer),
            "lane, checkout": _write(self.moved, "lanes.py", "/repo/spec/t.py", writer),
        }
        assert observed == {"lane, tree": SILENT, "default, tree": DENY, "lane, checkout": DENY}


#: the four artifact lanes under the base, and the agent each one admits
LANE_SUFFIXES = (
    ("specs/approved", "arbiter"),
    ("plans/approved", "prosecutor"),
    ("verdicts", "juror"),
    ("reviews", "arbiter"),
)


class GauntletDirMovesEveryLane(unittest.TestCase):
    """``gauntlet_dir`` moves all four artifact lanes and nothing under them."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")
        cls.bare = copy_hook_dir(cls.tmp.name, "BARE", {})
        cls.moved = copy_hook_dir(cls.tmp.name, "MOVED", {"gauntlet_dir": "work/chain"})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_each_lane_hook_guards_the_lane_under_the_named_base(self):
        # The base the kit ships is an ordinary directory once moved, and the
        # hook of a repo that has not moved still guards the shipped base.
        wanted = {
            "moved, agent": DENY,
            "moved, reviewer": SILENT,
            "base, moved": SILENT,
            "base, unmoved": DENY,
        }
        observed = {}
        for suffix, reviewer in LANE_SUFFIXES:
            moved = f"/repo/work/chain/{suffix}/slug.txt"
            base = f"/repo/gauntlet/{suffix}/slug.txt"
            observed[suffix, "moved, agent"] = _write(self.moved, "lanes.py", moved)
            observed[suffix, "moved, reviewer"] = _write(self.moved, "lanes.py", moved, reviewer)
            observed[suffix, "base, moved"] = _write(self.moved, "lanes.py", base)
            observed[suffix, "base, unmoved"] = _write(self.bare, "lanes.py", base)
        assert observed == {
            (suffix, case): value for suffix, _ in LANE_SUFFIXES for case, value in wanted.items()
        }

    def test_the_structure_under_the_base_does_not_move(self):
        expected = {
            "gauntlet_dir": ["work/chain"],
            "specs_lane": ["work/chain/specs/approved"],
            "plans_lane": ["work/chain/plans/approved"],
            "reviews_lane": ["work/chain/reviews"],
            "verdicts_lane": ["work/chain/verdicts"],
        }
        observed = {key: _config_lines(self.moved, key) for key in expected}
        assert observed == expected

    def test_the_blind_agent_reads_the_moved_block_and_not_the_moved_base(self):
        # The one subtree of the base a blind agent works from moves with it,
        # and the rest of the base stays denied at its new location.  An
        # implementation re-allowing the specs by a literal hands a moved repo's
        # blind writer either nothing or the whole base.
        expected = {
            "work/chain/specs/approved/demo.txt": SILENT,
            "work/chain/plans/approved/demo.txt": DENY,
            "work/chain/reviews/demo.1.txt": DENY,
            "work/chain/specs/drafts/demo.txt": DENY,
        }
        observed = {path: _read(self.moved, path) for path in expected}
        assert observed == expected


class DocsDirMovesTheBlindReadAllowance(unittest.TestCase):
    """``docs_dir`` names the prose a blind agent may read."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")
        cls.bare = copy_hook_dir(cls.tmp.name, "BARE", {})
        cls.moved = copy_hook_dir(cls.tmp.name, "MOVED", {"docs_dir": "prose"})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_named_dir_is_readable_and_the_default_name_is_not(self):
        observed = {
            "named": _read(self.moved, "prose/testing.md"),
            "default, moved": _read(self.moved, "docs/testing.md"),
            "default, unmoved": _read(self.bare, "docs/testing.md"),
            "docs_dir": _config_lines(self.moved, "docs_dir"),
        }
        assert observed == {
            "named": SILENT,
            "default, moved": DENY,
            "default, unmoved": SILENT,
            "docs_dir": ["prose"],
        }

    def test_the_allowance_is_anchored_at_the_repo_root(self):
        # An entry is the repository's own file of that name, never any
        # directory so named: a `src/prose/testing.md` read as documentation
        # hands the blind agent the implementation under a directory it chose.
        # And the allowance is that one policy file, not the prose around it:
        # a design note there quotes the code it describes.
        observed = {
            "a directory of that name": _read(self.moved, "src/prose/testing.md"),
            "prose beside the file": _read(self.moved, "prose/sub/deep.md"),
        }
        assert observed == {"a directory of that name": DENY, "prose beside the file": DENY}


class AnOverlappingSetMovesNothing(unittest.TestCase):
    """Any pair of names that touch voids the whole declaration."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _observe(self, label, conf):
        """Every key as the reader answers it, and the two default lanes' decisions."""
        copy = copy_hook_dir(self.tmp.name, label, conf)
        observed = {key: _config_lines(copy, key) for key in DEFAULTS}
        observed["tests lane"] = _write(copy, "lanes.py", "/repo/tests/t.py")
        observed["specs lane"] = _write(copy, "lanes.py", "/repo/gauntlet/specs/approved/s.txt")
        return observed

    def test_a_lane_directory_itself(self):
        observed = self._observe("LANE", {"tests_dir": "gauntlet/specs/approved"})
        assert observed == FALLEN_BACK

    def test_a_name_under_another(self):
        observed = {
            "UNDER": self._observe("UNDER", {"tests_dir": "gauntlet/x"}),
            "BASEUNDER": self._observe("BASEUNDER", {"gauntlet_dir": "tests/artifacts"}),
        }
        assert observed == {"UNDER": FALLEN_BACK, "BASEUNDER": FALLEN_BACK}

    def test_a_name_over_another(self):
        observed = {
            "OVER": self._observe("OVER", {"tests_dir": "."}),
            "BASEOVER": self._observe("BASEOVER", {"gauntlet_dir": "."}),
        }
        assert observed == {"OVER": FALLEN_BACK, "BASEOVER": FALLEN_BACK}

    def test_a_key_the_file_omits_still_collides(self):
        # `tests_dir` of `docs` is a usable name read on its own.  It is the
        # default `docs_dir` it lands on, so an implementation checking only the
        # keys the file declares puts the writer's lane over the prose.
        observed = {
            "DEFAULTCLASH": self._observe("DEFAULTCLASH", {"tests_dir": "docs"}),
            "BASECLASH": self._observe("BASECLASH", {"gauntlet_dir": "docs"}),
        }
        assert observed == {"DEFAULTCLASH": FALLEN_BACK, "BASECLASH": FALLEN_BACK}

    def test_two_declared_keys_naming_the_same_directory(self):
        observed = self._observe("SAME", {"tests_dir": "one", "docs_dir": "one"})
        assert observed == FALLEN_BACK

    def test_a_traversal_that_resolves_into_another(self):
        observed = self._observe("WALK", {"tests_dir": "spec/../gauntlet/reviews"})
        assert observed == FALLEN_BACK

    def test_an_absolute_path_and_a_walk_out_of_the_checkout(self):
        observed = {
            "ABS": self._observe("ABS", {"tests_dir": "/repo/spec"}),
            "OUT": self._observe("OUT", {"tests_dir": "../spec"}),
        }
        assert observed == {"ABS": FALLEN_BACK, "OUT": FALLEN_BACK}

    def test_a_value_that_is_not_a_string(self):
        observed = {
            "LIST": self._observe("LIST", {"tests_dir": ["spec"]}),
            "EMPTY": self._observe("EMPTY", {"docs_dir": ""}),
        }
        assert observed == {"LIST": FALLEN_BACK, "EMPTY": FALLEN_BACK}

    def test_one_bad_key_does_not_leave_the_others_moved(self):
        # The whole point of the all-or-nothing rule: a set that would be
        # usable but for one name moves no directory at all, so a typo cannot
        # half-apply a layout and leave one hook guarding a directory the rest
        # of the kit no longer uses.
        observed = self._observe(
            "PARTIAL", {"tests_dir": "spec", "gauntlet_dir": "spec/chain", "docs_dir": "prose"}
        )
        assert observed == FALLEN_BACK


class OneReaderOneKeySet(unittest.TestCase):
    """``shell_shapes.py --config`` answers the five keys, the four lanes, nothing else."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")
        cls.bare = copy_hook_dir(cls.tmp.name, "BARE", {})
        cls.extra = copy_hook_dir(
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
        observed = {
            "tests_dir": _config_lines(self.extra, "tests_dir"),
            "allow": _config_lines(self.extra, "allow"),
            "runners": _config_lines(self.extra, "runners"),
            "plans": _read(self.extra, "gauntlet/plans/approved/demo.txt"),
            "reviews": _read(self.extra, "gauntlet/reviews/demo.1.txt"),
            "specs": _read(self.extra, "gauntlet/specs/approved/demo.txt"),
        }
        assert observed == {
            "tests_dir": ["spec"],
            "allow": [],
            "runners": [],
            "plans": DENY,
            "reviews": DENY,
            "specs": SILENT,
        }

    def test_an_unknown_key_asked_of_the_reader_is_no_lines(self):
        keys = ("tests.dir", "runner_invocations", "agents.writer")
        observed = {key: _config_lines(self.bare, key) for key in keys}
        assert observed == {key: [] for key in keys}


class BlindAgentReadsTheConfig(unittest.TestCase):
    """``no-impl-reads.py`` allows the one file that says where the directories are."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="dirs-config-")
        cls.bare = copy_hook_dir(cls.tmp.name, "BARE", {})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_blind_reads_json_is_readable_and_its_siblings_are_not(self):
        expected = {
            ".claude/blind-reads.json": SILENT,
            "hooks/lib/shell_shapes.py": DENY,
            ".claude/settings.json": DENY,
        }
        observed = {path: _read(self.bare, path) for path in expected}
        assert observed == expected


class BlindShellReadsTheSameKeys(unittest.TestCase):
    """``scripts/blind.sh`` takes its lane and its block path from the same reader."""

    def test_the_script_reads_the_keys_the_reader_answers(self):
        # The script and the hooks share one reader, so a repo that moved a
        # directory moves both together.  A script reading a key the reader does
        # not answer gets an empty value and binds or shows the wrong path.
        text = BLIND_SH.read_text()
        present = ("--config", "tests_dir", "specs_lane")
        absent = ("tests.dir", "runner_invocations")
        observed = {name: name in text for name in present + absent}
        assert observed == {
            **{name: True for name in present},
            **{name: False for name in absent},
        }

    def test_the_script_names_no_lane_of_its_own(self):
        # Every artifact path it types comes from the reader; a literal here is
        # a second place a moved repo would have to be edited, and the one the
        # lane hooks would not agree with.
        assert "gauntlet/specs/approved" not in BLIND_SH.read_text()


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
        cls.absent = copy_hook_dir(cls.tmp.name, "FABSENT", None)
        cls.broken = copy_hook_dir(cls.tmp.name, "FBROKEN", "{not json")
        cls.not_object = copy_hook_dir(cls.tmp.name, "FLIST", '["tests_dir"]')
        cls.empty = copy_hook_dir(cls.tmp.name, "FEMPTY", {})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_reader_exits_non_zero_and_names_the_path(self):
        cases = (
            ("absent", self.absent),
            ("malformed", self.broken),
            ("not an object", self.not_object),
        )
        observed = {}
        for label, copy in cases:
            status, lines, stderr = _config_run(copy, "tests_dir")
            observed[label] = (status, lines, ".claude/blind-reads.json" in stderr)
        assert observed == {label: (2, [], True) for label, _ in cases}

    def test_a_hook_denies_rather_than_guarding_the_default_lane(self):
        # The lane is a configured directory.  A hook that cannot read the
        # declaration does not know which directory it guards, so it refuses
        # instead of guarding the kit's and calling that a decision.
        cases = (("absent", self.absent), ("malformed", self.broken))
        observed = {}
        for label, copy in cases:
            observed[label, "src/main.py"] = _write(copy, "lanes.py", "/repo/src/main.py")
            observed[label, "README.md"] = _write(copy, "lanes.py", "/repo/README.md")
        assert observed == {
            (label, name): DENY for label, _ in cases for name in ("src/main.py", "README.md")
        }

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
            check=False,
        )
        reason = json.loads(completed.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        named = ("blind-reads.json", "scripts/init.py")
        observed = {name: name in reason for name in named}
        assert observed == {name: True for name in named}

    def test_the_empty_object_is_the_projects_word_and_resolves(self):
        # `{}` is how a project asks for the shipped layout and means it.  It is
        # the one shape `scripts/init.py` cannot be needed for, and the one that
        # separates "declared nothing" from "declared the defaults".
        observed = {key: _config_lines(self.empty, key) for key in DEFAULTS}
        observed["tests lane"] = _write(self.empty, "lanes.py", "/repo/tests/t.py")
        observed["src/main.py"] = _write(self.empty, "lanes.py", "/repo/src/main.py")
        defaults = {key: [default] for key, default in DEFAULTS.items()}
        assert observed == {**defaults, "tests lane": DENY, "src/main.py": SILENT}


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
        cls.bare = copy_hook_dir(cls.tmp.name, "SBARE", {})
        cls.named = copy_hook_dir(
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
        observed = {key: _config_lines(self.bare, key) for key in SCALARS}
        assert observed == {key: [default] for key, default in SCALARS.items()}

    def test_the_reader_answers_the_two_names_a_project_gives(self):
        keys = ("target_branch", "gate_command")
        observed = {key: _config_lines(self.named, key) for key in keys}
        assert observed == {
            "target_branch": ["dev"],
            "gate_command": ["scripts/gates/check-gates.sh"],
        }

    def test_an_unusable_value_falls_back_alone(self):
        # A newline is what separates a branch name from a second command
        # smuggled after it, so a multi-line value is not a scalar at all.
        cases = (
            ("SLIST", {"target_branch": ["dev"], "gate_command": "gate"}, ["main", "gate"]),
            ("SEMPTY", {"target_branch": "  ", "gate_command": "gate"}, ["main", "gate"]),
            (
                "SLINES",
                {"target_branch": "dev", "gate_command": "a\nrm -rf /"},
                ["dev", "make check"],
            ),
        )
        observed = {}
        for label, conf, _ in cases:
            copy = copy_hook_dir(self.tmp.name, label, conf)
            observed[label] = [
                _config_lines(copy, "target_branch")[0],
                _config_lines(copy, "gate_command")[0],
            ]
        assert observed == {label: expected for label, _, expected in cases}

    def test_a_directory_set_that_moves_nothing_still_leaves_the_scalars(self):
        # The all-or-nothing rule is about names that can collide.  A branch and
        # a command cannot collide with a lane, so voiding the directories has
        # no reason to reach them, and a merge that silently converged on the
        # wrong branch is the cost of letting it.
        copy = copy_hook_dir(
            self.tmp.name,
            "SVOID",
            {"tests_dir": "docs", "target_branch": "dev", "gate_command": "gate"},
        )
        observed = {key: _config_lines(copy, key) for key in DEFAULTS}
        observed["target_branch"] = _config_lines(copy, "target_branch")
        observed["gate_command"] = _config_lines(copy, "gate_command")
        defaults = {key: [default] for key, default in DEFAULTS.items()}
        assert observed == {**defaults, "target_branch": ["dev"], "gate_command": ["gate"]}


def _git(cwd, *args):
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"},
    )
