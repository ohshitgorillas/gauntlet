"""Behavior tests for the check verb of the pair.sh spec-lane driver.

The verdict words, the exit statuses and the numbered artifact asserted here
are the approved block's, gauntlet/specs/approved/pair-sh-check.txt, so the
literals are reachable without reading the implementation.
"""

import json

from tests.support.pair_fixture import (
    BLOCK_NEW,
    REVIEWER,
    SLUG,
    TARGET,
    TEST_A_OTHER,
    _gate_line,
    _git,
    _merge_artifacts,
    _merge_dir,
    _newest_merge_artifact,
    _pair,
    _pair_status,
    _repo,
    _worktree,
)

IMPL_FILE = "impl_work.txt"
IMPL_GATE = "test -f " + IMPL_FILE

ARTIFACT_ONE = SLUG + ".1.txt"
ARTIFACT_TWO = SLUG + ".2.txt"


def _impl_tree(repo):
    """Cut the implementation worktree and return the directory it sits in.

    `impl checkout` prints one line whose second whitespace field is the path,
    read relative to the repository root. Returns None where stdout is not one
    line of at least two fields, or where the field names no directory.
    """
    lines = _pair(repo, "impl", "checkout", SLUG)
    if len(lines) != 1:
        return None
    fields = lines[0].split()
    if len(fields) < 2:
        return None
    named = repo / fields[1]
    return named if named.is_dir() else None


def _pair_on_the_impl_gate(tmp_path):
    """Open a pair whose configured gate command is `test -f impl_work.txt`.

    Commits a test in the spec worktree, so the pair carries the change a
    convergence would land, and cuts the implementation worktree. Returns the
    repository, the spec worktree and the implementation worktree.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    (repo / ".claude" / "blind-reads.json").write_text(
        json.dumps({"target_branch": TARGET, "gate_command": IMPL_GATE})
    )
    _pair(repo, "open", SLUG)
    worktree = _worktree(repo)
    (worktree / "tests" / "test_a.py").write_text(TEST_A_OTHER)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", "spec tests")
    return repo, worktree, _impl_tree(repo)


def _impl_commit(tree, carries, message):
    """Commit the implementation tree with `impl_work.txt` present or gone."""
    path = tree / IMPL_FILE
    if carries:
        path.write_text("implementation in progress\n")
    elif path.is_file():
        path.unlink()
    _git(tree, "add", "-A")
    _git(tree, "commit", "-m", message)


def _check_verdict(repo):
    """The last word of `pair.sh check`'s last stdout line and its exit status.

    Returns ("", status) where the verb printed nothing on stdout at all.
    """
    lines, status = _pair_status(repo, "check", SLUG)
    words = lines[-1].split() if lines else []
    return (words[-1] if words else "", status)


def _check_shape(repo, worktree, impl):
    """Run `pair.sh check` and measure what the run left behind it.

    Returns whether the target branch's HEAD moved across the call, whether the
    spec worktree is still a directory, whether the implementation worktree is,
    and the `gate:` line of the newest numbered file under gauntlet/merge/,
    which is "" where there is none. An implementation worktree that was never
    cut reads False rather than raising.
    """
    before = _git(repo, "rev-parse", "HEAD")
    _pair_status(repo, "check", SLUG)
    return (
        _git(repo, "rev-parse", "HEAD") != before,
        worktree.is_dir(),
        impl is not None and impl.is_dir(),
        _gate_line(_newest_merge_artifact(repo)),
    )


def _gate_lines(repo, names):
    """The `gate:` line each named file under gauntlet/merge/ carries."""
    return [_gate_line((_merge_dir(repo) / name).read_text()) for name in names]


def test_check_passes_over_the_implementation_tree_s_commit_and_fails_once_it_is_gone(tmp_path):
    repo, _, impl = _pair_on_the_impl_gate(tmp_path)
    _impl_commit(impl, True, "the implementation adds the file the gate wants")
    first = _check_verdict(repo)
    _impl_commit(impl, False, "the implementation takes that file back out")
    second = _check_verdict(repo)
    assert (first, second) == (("PASS", 0), ("FAIL", 1))


def test_every_check_writes_its_own_numbered_artifact_carrying_that_run_s_gate_line(tmp_path):
    repo, _, impl = _pair_on_the_impl_gate(tmp_path)
    _impl_commit(impl, True, "the implementation adds the file the gate wants")
    _pair_status(repo, "check", SLUG)
    _impl_commit(impl, False, "the implementation takes that file back out")
    _pair_status(repo, "check", SLUG)
    names = _merge_artifacts(repo)
    assert (names, _gate_lines(repo, names)) == (
        [ARTIFACT_ONE, ARTIFACT_TWO],
        ["gate: PASS", "gate: FAIL"],
    )


def test_check_lands_nothing_and_removes_no_worktree_whichever_way_the_gate_goes(tmp_path):
    repo, worktree, impl = _pair_on_the_impl_gate(tmp_path)
    red = _check_shape(repo, worktree, impl)
    _impl_commit(impl, True, "the implementation adds the file the gate wants")
    green = _check_shape(repo, worktree, impl)
    assert (red, green) == (
        (False, True, True, "gate: FAIL"),
        (False, True, True, "gate: PASS"),
    )
