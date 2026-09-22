"""Behavior tests for the bwrap-wrap PreToolUse hook.

The hook reads a PreToolUse payload on stdin and answers on stdout. The
`agent_type` key it routes on is documented at docs/approved-specs.md line 98
("The hook keys off the caller's `agent_type`, which is present only on
subagent calls"); the `updatedInput` field of a PreToolUse hook's answer is the
harness's own envelope. Nothing here asserts a string born inside the hook: the
command texts, the fixture tree names and the probe paths are all supplied by
these tests.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

CHECKOUT = Path(__file__).resolve().parent.parent
HOOK = CHECKOUT / "hooks" / "bwrap-wrap.py"

PROSECUTOR = "prosecutor"
ARBITER = "arbiter"
#: the caller with no `agent_type` at all, which is the main agent
MAIN_AGENT = None

SEMICOLON_TEXT = "echo hi; cat /etc/hostname"
HEREDOC_TEXT = "echo $(cat /etc/hostname) <<'X'"

TREE_ALPHA = "alpha-spec"
TREE_BRAVO = "bravo-spec"


def _repo(tmp_path, trees=()):
    """A fixture checkout with the lane directories and `trees` under worktrees.

    The three kit directory names are on disk here as a consumer project's own
    source, which is what makes a write under them an observable outcome.
    """
    repo = tmp_path / "repo"
    (repo / "gauntlet" / "specs" / "approved").mkdir(parents=True)
    (repo / "gauntlet" / "reviews").mkdir(parents=True)
    (repo / ".claude" / "worktrees").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "hooks").mkdir()
    (repo / "agents").mkdir()
    (repo / "tests").mkdir()
    #: a project declares itself, and an absent declaration is a fault the hook
    #: denies on rather than a fall back to these same defaults
    (repo / ".claude" / "blind-reads.json").write_text(json.dumps(DECLARATION))
    for name in trees:
        _add_tree(repo, name)
    return repo


#: the kit's shipped layout, written as a project's own word. Every path this
#: file asserts on is one of these names.
DECLARATION = {
    "tests_dir": "tests",
    "gauntlet_dir": "gauntlet",
    "docs_dir": "docs",
    "target_branch": "main",
    "gate_command": "make check",
    "pytest_command": ".venv/bin/pytest",
    "node_command": "node --test",
}


def _add_tree(repo, name):
    tree = repo / ".claude" / "worktrees" / name
    (tree / "tests").mkdir(parents=True)
    return tree


def _tree_path(repo, name):
    return repo / ".claude" / "worktrees" / name


def _run_hook(repo, agent_type, command, at=None):
    """Feed one PreToolUse Bash payload to the hook; give its decoded answer.

    `at` is the directory the caller's shell stands in, which defaults to the
    checkout root and is a worktree inside it where a case names one; the
    project directory stays the checkout either way.

    Returns the parsed stdout object, or an empty mapping where the hook wrote
    nothing parseable.
    """
    standing = at or repo
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(standing),
        "tool_input": {"command": command},
    }
    #: `agent_type` is present only on subagent calls (docs/approved-specs.md
    #: line 98), so the main agent is the caller that carries no such key
    if agent_type is not None:
        payload["agent_type"] = agent_type
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(repo),
        "CLAUDE_PROJECT_DIR": str(repo),
    }
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        cwd=standing,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    try:
        return json.loads(done.stdout)
    except ValueError:
        return {}


def _updated_command(answer):
    """The replacement command the answer carries, or None where it carries none."""
    nested = answer.get("hookSpecificOutput")
    updated = (nested or {}).get("updatedInput")
    if updated is None:
        updated = answer.get("updatedInput")
    if not isinstance(updated, dict):
        return None
    command = updated.get("command")
    return command if isinstance(command, str) else None


def _denied(answer):
    """Whether the answer refuses the call rather than allowing or rewriting it."""
    nested = answer.get("hookSpecificOutput") or {}
    return nested.get("permissionDecision") == "deny" or answer.get("decision") == "block"


def _carriage(repo, agent_type, command):
    """(the caller's text recovered from the replacement, whether it was denied).

    The first element is `command` itself where the replacement carries the
    caller's text byte for byte; otherwise it is whatever replacement came back
    (None where none did), so a mangled or refused wrap shows in the failure.
    """
    answer = _run_hook(repo, agent_type, command)
    wrapped = _updated_command(answer)
    recovered = command if wrapped is not None and command in wrapped else wrapped
    return (recovered, _denied(answer))


@pytest.mark.parametrize(
    "command",
    [SEMICOLON_TEXT, HEREDOC_TEXT],
    ids=["two-commands-on-one-line", "command-substitution-and-heredoc"],
)
def test_the_callers_command_text_survives_the_wrap_byte_for_byte(tmp_path, command):
    repo = _repo(tmp_path, trees=(TREE_ALPHA,))
    assert _carriage(repo, PROSECUTOR, command) == (command, False)


def _trees_bound(repo, names):
    """(which of `names` the replacement binds, whether a replacement came back).

    Membership is by the tree's absolute path appearing in the replacement
    command, so a tree the hook never binds and a tree it binds from a stale
    cached listing are distinguishable.
    """
    wrapped = _updated_command(_run_hook(repo, PROSECUTOR, SEMICOLON_TEXT))
    if wrapped is None:
        return (set(), False)
    return ({name for name in names if str(_tree_path(repo, name)) in wrapped}, True)


def test_worktree_binds_follow_the_trees_on_disk_at_the_time_of_the_call(tmp_path):
    names = (TREE_ALPHA, TREE_BRAVO)
    populated = _repo(tmp_path, trees=names)
    with_two_trees = _trees_bound(populated, names)

    shutil.rmtree(_tree_path(populated, TREE_BRAVO))
    after_one_was_removed = _trees_bound(populated, names)

    with_no_trees = _trees_bound(_repo(tmp_path / "bare"), names)

    assert (with_two_trees, after_one_was_removed, with_no_trees) == (
        ({TREE_ALPHA, TREE_BRAVO}, True),
        ({TREE_ALPHA}, True),
        (set(), True),
    )


def _bwrap_usable():
    """Whether a trivial bwrap invocation runs on this host."""
    if shutil.which("bwrap") is None:
        return False
    done = subprocess.run(
        ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--", "true"],
        capture_output=True,
        check=False,
    )
    return done.returncode == 0


def _write_outcome(repo, agent_type, relative_path, at=None):
    """Run the replacement for a write at `relative_path`; say what it achieved.

    `relative_path` is read against `at`, the directory the caller's shell stands
    in, which defaults to the checkout root.

    Gives "written" where the invocation exits clean and the file is on disk
    afterwards, "refused" where it is not, and "unwrapped" where the hook
    returned no replacement to run at all.
    """
    standing = at or repo
    target = standing / relative_path
    if target.exists():
        target.unlink()
    command = "printf x > " + relative_path
    wrapped = _updated_command(_run_hook(repo, agent_type, command, at=at))
    if wrapped is None:
        return "unwrapped"
    done = subprocess.run(
        ["/bin/sh", "-c", wrapped], cwd=standing, capture_output=True, text=True, check=False
    )
    return "written" if done.returncode == 0 and target.is_file() else "refused"


#: the two case shapes the parametrize below carries: a write at a path, and a
#: whole command text run through whatever replacement the hook gives back
WRITE = "write"
RUN = "run"

#: one probe per directory the cases below write into. The names are this file's
#: own choice; `probe.txt` is not a name anything in the checkout knows.
KIT_SCRIPTS_PROBE = "scripts/probe.txt"
KIT_HOOKS_PROBE = "hooks/probe.txt"
KIT_AGENTS_PROBE = "agents/probe.txt"
SPEC_LANE_PROBE = "gauntlet/specs/approved/probe.txt"
CLAUDE_DIR_PROBE = ".claude/probe.txt"

ROUND_SLUG = "roundprobe"
SEEDED_ROUNDS = 2
REVIEW_COMMAND = "cd . && scripts/pair.sh review " + ROUND_SLUG
#: one more than what each caller's own view of the reviewers' lane holds: the
#: checkout holds the two seeded rounds, a masked lane holds none
AUTHORS_ROUND = SEEDED_ROUNDS + 1
REVIEWERS_ROUND = 1


def _seed_rounds(repo, slug, count):
    """Put `count` round files for `slug` in the reviewers' lane of `repo`.

    The names are `<slug>.<N>.txt` under `<gauntlet dir>/reviews/`, which is the
    lane's own shape per docs/agents.md "`pair.sh review <slug>`".
    """
    for number in range(1, count + 1):
        (repo / "gauntlet" / "reviews" / f"{slug}.{number}.txt").write_text("round\n")


def _with_driver(repo):
    """Give `repo` a copy of this checkout's scripts and hooks, and a `.git`.

    The command text names a driver relative to the fixture root, so the driver
    has to be on disk there for a wrapped run to have anything to run. The files
    are copied, never read here.
    """
    for name in ("scripts", "hooks"):
        shutil.copytree(CHECKOUT / name, repo / name, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-q", str(repo)], capture_output=True, check=False)
    return repo


#: a wrapped run carries masks over `/tmp` and `/run/user` (README, "Setup"),
#: so a fixture a wrapped command has to reach cannot live under `tmp_path`
IN_TREE_FIXTURES = CHECKOUT / "tests" / ".in-tree-fixtures"


@pytest.fixture
def in_tree_base():
    """A scratch directory inside the checkout, removed when the test ends."""
    IN_TREE_FIXTURES.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(dir=IN_TREE_FIXTURES))
    yield base
    shutil.rmtree(base, ignore_errors=True)


def _prepared(repo, action):
    """Give `repo`, carrying the driver and the seeded rounds where a case runs one."""
    if action == RUN:
        _seed_rounds(_with_driver(repo), ROUND_SLUG, SEEDED_ROUNDS)
    return repo


def _round_number(stdout, stderr):
    """The `<N>` of a `<slug>.<N>.txt` path the run printed, else the run's output.

    Reading the number off the printed path keeps the assertion on a number the
    run produced rather than on any word the driver chose to print beside it.
    """
    for token in reversed(stdout.split()):
        fields = Path(token).name.split(".")
        if len(fields) == 3 and fields[1].isdigit():
            return int(fields[1])
    return (stdout + stderr).strip()


def _printed_round(repo, agent_type, command):
    """Run the replacement for `command`; give the round number its stdout names.

    Gives "unwrapped" where the hook returned no replacement to run at all, and
    the run's own output where no `<slug>.<N>.txt` path came back, so a driver
    that failed shows in the failure rather than as some other number.
    """
    wrapped = _updated_command(_run_hook(repo, agent_type, command))
    if wrapped is None:
        return "unwrapped"
    done = subprocess.run(
        ["/bin/sh", "-c", wrapped],
        cwd=repo,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)},
        capture_output=True,
        text=True,
        check=False,
    )
    return _round_number(done.stdout, done.stderr)


def _case_outcome(repo, agent_type, action, subject):
    """What the case achieved: the write's outcome, or the round number printed."""
    if action == WRITE:
        return _write_outcome(repo, agent_type, subject)
    return _printed_round(repo, agent_type, subject)


@pytest.mark.parametrize(
    ("agent_type", "action", "subject", "expected"),
    [
        (PROSECUTOR, WRITE, "probe.txt", "written"),
        (PROSECUTOR, WRITE, SPEC_LANE_PROBE, "refused"),
        (ARBITER, WRITE, "probe.txt", "refused"),
        (ARBITER, RUN, REVIEW_COMMAND, REVIEWERS_ROUND),
        (MAIN_AGENT, RUN, REVIEW_COMMAND, AUTHORS_ROUND),
        (PROSECUTOR, WRITE, KIT_SCRIPTS_PROBE, "written"),
        (PROSECUTOR, WRITE, KIT_HOOKS_PROBE, "written"),
        (PROSECUTOR, WRITE, KIT_AGENTS_PROBE, "written"),
        (PROSECUTOR, WRITE, CLAUDE_DIR_PROBE, "refused"),
        (ARBITER, WRITE, KIT_SCRIPTS_PROBE, "refused"),
    ],
    ids=[
        "author-at-the-root",
        "author-into-the-spec-lane",
        "reviewer-at-the-root",
        "reviewer-counting-the-rounds-in-the-reviewers-lane",
        "main-agent-counting-the-rounds-in-the-reviewers-lane",
        "author-into-the-scripts-directory",
        "author-into-the-hooks-directory",
        "author-into-the-agents-directory",
        "author-into-the-claude-directory",
        "reviewer-into-the-scripts-directory",
    ],
)
def test_a_write_under_the_replacement_lands_by_path_and_by_caller(
    tmp_path, in_tree_base, agent_type, action, subject, expected
):
    if not _bwrap_usable():
        pytest.skip("bwrap is not runnable on this host")
    base = in_tree_base if action == RUN else tmp_path
    repo = _prepared(_repo(base, trees=(TREE_ALPHA,)), action)
    assert _case_outcome(repo, agent_type, action, subject) == expected


def _kit_shaped(tree):
    """Put a kit directory and a spec lane on disk inside `tree`; give `tree`."""
    (tree / "scripts").mkdir(exist_ok=True)
    (tree / "gauntlet" / "specs" / "approved").mkdir(parents=True, exist_ok=True)
    return tree


def test_a_write_inside_a_worktree_lands_by_path_as_it_does_in_the_checkout(tmp_path):
    if not _bwrap_usable():
        pytest.skip("bwrap is not runnable on this host")
    repo = _repo(tmp_path, trees=(TREE_ALPHA,))
    tree = _kit_shaped(_tree_path(repo, TREE_ALPHA))
    probes = (KIT_SCRIPTS_PROBE, SPEC_LANE_PROBE)
    on_disk = {
        probe for probe in probes if _write_outcome(repo, PROSECUTOR, probe, at=tree) == "written"
    }
    assert on_disk == {KIT_SCRIPTS_PROBE}
