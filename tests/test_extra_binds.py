"""Behavior tests for the `extra_binds` key of a project's own declaration.

The hook reads a PreToolUse payload on stdin and answers on stdout; the
`agent_type` key it routes on is documented at docs/approved-specs.md line 98
("The hook keys off the caller's `agent_type`, which is present only on subagent
calls"), and `updatedInput` is the harness's own envelope. The declaration file
`.claude/blind-reads.json` and the key names inside it are the project's word,
written by these tests. Every path asserted on here is derived from `tmp_path`,
so no string born inside the hook reaches an assertion.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "bwrap-wrap.py"

PROSECUTOR = "prosecutor"
ARBITER = "arbiter"

#: the kit's shipped layout, written as a project's own word
DECLARATION = {
    "tests_dir": "tests",
    "gauntlet_dir": "gauntlet",
    "docs_dir": "docs",
    "target_branch": "main",
    "gate_command": "make check",
    "pytest_command": ".venv/bin/pytest",
    "node_command": "node --test",
}

EXTRA_BINDS_KEY = "extra_binds"

TREE_ALPHA = "alpha-spec"

OUTSIDE = "outside"
SPARE = "spare"
PROBE = "probe.txt"

WRITTEN = "written"
REFUSED = "refused"
UNWRAPPED = "unwrapped"


def _repo(tmp_path, extra_binds):
    """A checkout at `<tmp>/repo` declaring `extra_binds`, with `<tmp>` siblings made.

    `<tmp>/outside` and `<tmp>/spare` are both on disk, so an arm that observes
    nothing observes an unbound directory and never an absent one. A `None`
    leaves the key out of the declaration altogether.
    """
    (tmp_path / OUTSIDE).mkdir(exist_ok=True)
    (tmp_path / SPARE).mkdir(exist_ok=True)
    repo = tmp_path / "repo"
    (repo / "gauntlet" / "specs" / "approved").mkdir(parents=True)
    (repo / "gauntlet" / "reviews").mkdir(parents=True)
    (repo / ".claude" / "worktrees" / TREE_ALPHA / "tests").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "tests").mkdir()
    declaration = dict(DECLARATION)
    if extra_binds is not None:
        declaration[EXTRA_BINDS_KEY] = extra_binds
    (repo / ".claude" / "blind-reads.json").write_text(json.dumps(declaration))
    return repo


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
    done = subprocess.run(  # noqa: PLW1510
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


def _bwrap_usable():
    """Whether a trivial bwrap invocation runs on this host."""
    if shutil.which("bwrap") is None:
        return False
    done = subprocess.run(  # noqa: PLW1510
        ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--", "true"],
        capture_output=True,
    )
    return done.returncode == 0


def _write_outcome(repo, agent_type, target):
    """Run the replacement for a write at absolute `target`; say what it achieved.

    Gives "written" where the invocation exits clean and the file is on disk
    afterwards, "refused" where it is not, and "unwrapped" where the hook
    returned no replacement to run at all.
    """
    if target.exists():
        target.unlink()
    command = "printf x > " + str(target)
    wrapped = _updated_command(_run_hook(repo, agent_type, command))
    if wrapped is None:
        return UNWRAPPED
    done = subprocess.run(  # noqa: PLW1510, S602
        wrapped, shell=True, cwd=repo, capture_output=True, text=True
    )
    return WRITTEN if done.returncode == 0 and target.is_file() else REFUSED


def _outside_declared(tmp_path):
    return [str(tmp_path / OUTSIDE)]


def _spare_declared(tmp_path):
    return [str(tmp_path / SPARE)]


def _the_whole_tmp_declared(tmp_path):
    return [str(tmp_path)]


def _outside_and_a_number(tmp_path):
    return [str(tmp_path / OUTSIDE), 5]


def _outside_and_spare(tmp_path):
    return [str(tmp_path / OUTSIDE), str(tmp_path / SPARE)]


@pytest.mark.parametrize(
    ("declare", "expected"),
    [
        (_outside_declared, WRITTEN),
        (_spare_declared, REFUSED),
    ],
    ids=["the-probes-own-directory-is-declared", "another-directory-is-declared"],
)
def test_a_path_outside_the_checkout_is_writable_only_where_the_project_declares_it(
    tmp_path, declare, expected
):
    if not _bwrap_usable():
        pytest.skip("bwrap is not runnable on this host")
    repo = _repo(tmp_path, declare(tmp_path))
    assert _write_outcome(repo, PROSECUTOR, tmp_path / OUTSIDE / PROBE) == expected


@pytest.mark.parametrize(
    ("declare", "expected"),
    [
        (_the_whole_tmp_declared, REFUSED),
        (_spare_declared, WRITTEN),
    ],
    ids=["the-entry-contains-the-checkout", "the-entry-is-beside-the-checkout"],
)
def test_an_entry_that_contains_the_checkout_is_dropped_whole_rather_than_bound(
    tmp_path, declare, expected
):
    if not _bwrap_usable():
        pytest.skip("bwrap is not runnable on this host")
    repo = _repo(tmp_path, declare(tmp_path))
    assert _write_outcome(repo, PROSECUTOR, tmp_path / SPARE / PROBE) == expected


@pytest.mark.parametrize(
    ("agent_type", "expected"),
    [
        (PROSECUTOR, WRITTEN),
        (ARBITER, REFUSED),
    ],
    ids=["the-author", "the-reviewer"],
)
def test_a_declared_extra_bind_reaches_the_author_and_not_the_reviewer(
    tmp_path, agent_type, expected
):
    if not _bwrap_usable():
        pytest.skip("bwrap is not runnable on this host")
    repo = _repo(tmp_path, _outside_declared(tmp_path))
    assert _write_outcome(repo, agent_type, tmp_path / OUTSIDE / PROBE) == expected


@pytest.mark.parametrize(
    ("declare", "expected"),
    [
        (_outside_and_a_number, REFUSED),
        (_outside_and_spare, WRITTEN),
    ],
    ids=["a-second-entry-that-is-not-a-string", "a-second-entry-that-is-a-string"],
)
def test_an_entry_that_is_not_a_string_voids_the_whole_extra_binds_key(tmp_path, declare, expected):
    if not _bwrap_usable():
        pytest.skip("bwrap is not runnable on this host")
    repo = _repo(tmp_path, declare(tmp_path))
    assert _write_outcome(repo, PROSECUTOR, tmp_path / OUTSIDE / PROBE) == expected
