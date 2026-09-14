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
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "bwrap-wrap.py"

PROSECUTOR = "gauntlet-prosecutor"
ARBITER = "gauntlet-arbiter"

SEMICOLON_TEXT = "echo hi; cat /etc/hostname"
HEREDOC_TEXT = "echo $(cat /etc/hostname) <<'X'"

PAIR_RED = "scripts/pair.sh red demo"
PAIR_RED_APPENDED = PAIR_RED + "; rm -rf state"
PAIR_RED_PREFIXED = "cd /tmp && " + PAIR_RED
PAIR_RED_ESCAPING_ARG = "scripts/pair.sh red ../../etc"

TREE_ALPHA = "alpha-spec"
TREE_BRAVO = "bravo-spec"


def _repo(tmp_path, trees=()):
    """A fixture checkout with the lane directories and `trees` under worktrees."""
    repo = tmp_path / "repo"
    (repo / "gauntlet" / "specs" / "approved").mkdir(parents=True)
    (repo / "gauntlet" / "reviews").mkdir(parents=True)
    (repo / ".claude" / "worktrees").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "tests").mkdir()
    for name in trees:
        _add_tree(repo, name)
    return repo


def _add_tree(repo, name):
    tree = repo / ".claude" / "worktrees" / name
    (tree / "tests").mkdir(parents=True)
    return tree


def _tree_path(repo, name):
    return repo / ".claude" / "worktrees" / name


def _run_hook(repo, agent_type, command):
    """Feed one PreToolUse Bash payload to the hook; give its decoded answer.

    Returns the parsed stdout object, or an empty mapping where the hook wrote
    nothing parseable.
    """
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(repo),
        "agent_type": agent_type,
        "tool_input": {"command": command},
    }
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(repo),
        "CLAUDE_PROJECT_DIR": str(repo),
    }
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
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
    )
    return done.returncode == 0


def _write_outcome(repo, agent_type, relative_path):
    """Run the replacement for a write at `relative_path`; say what it achieved.

    Gives "written" where the invocation exits clean and the file is on disk
    afterwards, "refused" where it is not, and "unwrapped" where the hook
    returned no replacement to run at all.
    """
    target = repo / relative_path
    if target.exists():
        target.unlink()
    command = "printf x > " + relative_path
    wrapped = _updated_command(_run_hook(repo, agent_type, command))
    if wrapped is None:
        return "unwrapped"
    done = subprocess.run(wrapped, shell=True, cwd=repo, capture_output=True, text=True)
    return "written" if done.returncode == 0 and target.is_file() else "refused"


@pytest.mark.parametrize(
    "agent_type,relative_path,expected",
    [
        (PROSECUTOR, "probe.txt", "written"),
        (PROSECUTOR, "gauntlet/specs/approved/probe.txt", "refused"),
        (ARBITER, "probe.txt", "refused"),
    ],
    ids=["author-at-the-root", "author-into-the-spec-lane", "reviewer-at-the-root"],
)
def test_a_write_under_the_replacement_lands_by_path_and_by_caller(
    tmp_path, agent_type, relative_path, expected
):
    if not _bwrap_usable():
        pytest.skip("bwrap is not runnable on this host")
    repo = _repo(tmp_path, trees=(TREE_ALPHA,))
    assert _write_outcome(repo, agent_type, relative_path) == expected


def _carve_out(repo, command):
    """Say "passthrough" where the hook returns no replacement, else "wrapped"."""
    answer = _run_hook(repo, PROSECUTOR, command)
    return "passthrough" if _updated_command(answer) is None else "wrapped"


@pytest.mark.parametrize(
    "command,expected",
    [
        (PAIR_RED, "passthrough"),
        (PAIR_RED_APPENDED, "wrapped"),
        (PAIR_RED_PREFIXED, "wrapped"),
        (PAIR_RED_ESCAPING_ARG, "wrapped"),
    ],
    ids=[
        "the-whole-command-is-the-subcommand-call",
        "a-second-command-appended",
        "a-directory-change-in-front",
        "an-argument-of-the-wrong-shape",
    ],
)
def test_only_a_whole_command_that_is_one_pair_subcommand_call_escapes_the_wrap(
    tmp_path, command, expected
):
    repo = _repo(tmp_path, trees=(TREE_ALPHA,))
    assert _carve_out(repo, command) == expected
