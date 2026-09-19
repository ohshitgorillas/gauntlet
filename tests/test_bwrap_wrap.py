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
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "bwrap-wrap.py"

PROSECUTOR = "prosecutor"
ARBITER = "arbiter"

SEMICOLON_TEXT = "echo hi; cat /etc/hostname"
HEREDOC_TEXT = "echo $(cat /etc/hostname) <<'X'"

PAIR_RED = "scripts/pair.sh red demo"
PAIR_RED_APPENDED = PAIR_RED + "; rm -rf state"
PAIR_RED_PREFIXED = "cd /tmp && " + PAIR_RED

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
    done = subprocess.run(
        ["/bin/sh", "-c", wrapped], cwd=repo, capture_output=True, text=True, check=False
    )
    return "written" if done.returncode == 0 and target.is_file() else "refused"


@pytest.mark.parametrize(
    ("agent_type", "relative_path", "expected"),
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


def _escape_outcome(repo, command):
    """Say "passthrough" where the hook returns no replacement, "resolved" where
    the replacement's head is an absolute path to a file on disk, else "wrapped"."""
    replacement = _updated_command(_run_hook(repo, PROSECUTOR, command))
    if replacement is None:
        return "passthrough"
    head = Path(shlex.split(replacement)[0])
    return "resolved" if head.is_absolute() and head.is_file() else "wrapped"


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (PAIR_RED, "resolved"),
        (PAIR_RED_APPENDED, "wrapped"),
        (PAIR_RED_PREFIXED, "wrapped"),
    ],
    ids=[
        "the-whole-command-is-the-subcommand-call",
        "a-second-command-appended",
        "a-directory-change-in-front",
    ],
)
def test_only_a_whole_command_that_is_one_pair_subcommand_call_escapes_the_wrap(
    tmp_path, command, expected
):
    repo = _repo(tmp_path, trees=(TREE_ALPHA,))
    assert _escape_outcome(repo, command) == expected


def test_an_absolute_pair_head_escapes_with_no_replacement(tmp_path):
    repo = _repo(tmp_path, trees=(TREE_ALPHA,))
    absolute = str(repo / "scripts" / "pair.sh") + " red demo"
    assert _escape_outcome(repo, absolute) == "passthrough"


#: a project's own word about which commands leave the sandbox. The text of the
#: command is the declared thing and carries a `reads` list beside it; both names
#: are the declaration's, written by the project, never by the hook.
UNWRAPPED_KEY = "unwrapped_commands"
READS_KEY = "reads"

RESTART_DECLARED = "sudo systemctl restart hqplayerd"
RESTART_OTHER = "sudo systemctl restart other"

DEPLOY_PAYLOAD = "scripts/deploy.sh --once"
DEPLOY_READ = "scripts/deploy.sh"

PROBE = "probe.txt"
OTHER_PROBE = "other.txt"
PROBE_ALREADY_THERE = "y"
PROBE_WRITTEN = "x"


def _declaring(repo, unwrapped):
    """Rewrite the checkout's declaration to carry `unwrapped` commands; give `repo`.

    A `None` leaves the key out of the file altogether, which is the declaration
    as `_repo` writes it.
    """
    declaration = dict(DECLARATION)
    if unwrapped is not None:
        declaration[UNWRAPPED_KEY] = unwrapped
    (repo / ".claude" / "blind-reads.json").write_text(json.dumps(declaration))
    return repo


def _reading(*paths):
    """One declared command's value, naming the paths it reads."""
    return {READS_KEY: list(paths)}


@pytest.mark.parametrize(
    ("unwrapped", "expected"),
    [
        ({RESTART_DECLARED: _reading()}, "passthrough"),
        ({RESTART_OTHER: _reading()}, "wrapped"),
        (None, "wrapped"),
    ],
    ids=[
        "the-payload-is-the-declared-command",
        "a-different-command-is-declared",
        "the-checkout-declares-nothing",
    ],
)
def test_only_a_command_the_project_itself_declares_escapes_the_wrap(tmp_path, unwrapped, expected):
    repo = _declaring(_repo(tmp_path, trees=(TREE_ALPHA,)), unwrapped)
    assert _carve_out(repo, RESTART_DECLARED) == expected


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (RESTART_DECLARED, "passthrough"),
        (RESTART_DECLARED + " ", "wrapped"),
        (RESTART_DECLARED + " --now", "wrapped"),
        (RESTART_DECLARED + "; rm -rf state", "wrapped"),
        ("cd /tmp && " + RESTART_DECLARED, "wrapped"),
        ("echo " + RESTART_DECLARED, "wrapped"),
    ],
    ids=[
        "the-declared-text-exactly",
        "a-trailing-space",
        "an-argument-appended",
        "a-second-command-appended",
        "a-directory-change-in-front",
        "the-declared-text-as-an-argument",
    ],
)
def test_a_declared_command_matches_by_the_whole_string_and_nothing_less(
    tmp_path, command, expected
):
    repo = _declaring(_repo(tmp_path, trees=(TREE_ALPHA,)), {RESTART_DECLARED: _reading()})
    assert _carve_out(repo, command) == expected


def _probe_content_after_the_write(repo, agent_type, relative_path):
    """Run the replacement for a write at `relative_path`; give the file's content.

    The target is seeded before the run, so a write the wrap refuses leaves the
    seeded text behind and a write it allows replaces it. Gives "unwrapped"
    where the hook returned no replacement to run at all.
    """
    target = repo / relative_path
    target.write_text(PROBE_ALREADY_THERE)
    command = "printf " + PROBE_WRITTEN + " > " + relative_path
    wrapped = _updated_command(_run_hook(repo, agent_type, command))
    if wrapped is None:
        return "unwrapped"
    subprocess.run(
        ["/bin/sh", "-c", wrapped], cwd=repo, capture_output=True, text=True, check=False
    )
    return target.read_text()


@pytest.mark.parametrize(
    ("read_path", "expected"),
    [
        (PROBE, PROBE_ALREADY_THERE),
        (OTHER_PROBE, PROBE_WRITTEN),
    ],
    ids=[
        "the-declared-command-reads-the-probe",
        "the-declared-command-reads-another-file",
    ],
)
def test_a_path_a_declared_command_reads_is_read_only_inside_the_wrap(
    tmp_path, read_path, expected
):
    if not _bwrap_usable():
        pytest.skip("bwrap is not runnable on this host")
    repo = _repo(tmp_path, trees=(TREE_ALPHA,))
    #: both candidate paths are on disk, so the two arms differ by which one the
    #: declaration names and not by whether the declaration resolves at all
    (repo / OTHER_PROBE).write_text(PROBE_ALREADY_THERE)
    _declaring(repo, {RESTART_DECLARED: _reading(read_path)})
    assert _probe_content_after_the_write(repo, PROSECUTOR, PROBE) == expected


def test_a_reads_entry_that_does_not_resolve_voids_the_whole_declaration(tmp_path):
    repo = _repo(tmp_path, trees=(TREE_ALPHA,))
    _declaring(repo, {DEPLOY_PAYLOAD: _reading(DEPLOY_READ)})

    with_the_read_path_absent = _carve_out(repo, DEPLOY_PAYLOAD)

    (repo / DEPLOY_READ).write_text("#!/bin/sh\n")
    after_the_read_path_was_created = _carve_out(repo, DEPLOY_PAYLOAD)

    assert (with_the_read_path_absent, after_the_read_path_was_created) == (
        "wrapped",
        "passthrough",
    )
