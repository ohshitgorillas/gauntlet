"""Behavior tests for the merge and impl verbs of the pair.sh spec-lane driver.

The stdout contracts asserted here are documented in docs/agents.md lines
31-42, so the literals are reachable without reading the implementation.
"""

import json
import subprocess
from pathlib import Path

import pytest

from tests.support.pair_fixture import (
    ALPHA_SUITE,
    ASSERTION_X,
    BLOCK_NEW,
    BLOCK_SINGLE_TEST,
    BRAVO_SUITE,
    ENV,
    GATE,
    REVIEWER,
    SLUG,
    SPEC_PATH,
    TARGET,
    TEST_A,
    TEST_A_OTHER,
    TEST_B,
    _git,
    _newest_merge_artifact,
    _pair,
    _pair_status,
    _repo,
    _show,
    _venv_shim,
    _worktree,
)

TEST_A_BASE = "def test_x():\n    " + ASSERTION_X + "\n"
TEST_B_TWO = "def test_b_two():\n    assert 7 + 7 == 14\n"
TEST_B_GREW = TEST_B + "\n\n" + TEST_B_TWO

MERGE_ARTIFACT_ONE = "gauntlet/merge/" + SLUG + ".1.txt"
MERGE_ARTIFACT_TWO = "gauntlet/merge/" + SLUG + ".2.txt"
MERGE_HEADINGS = ("test files:", "diff:", "red output:")

BRIEF_NEW = ("TEST CHECK demo", "merge output: " + MERGE_ARTIFACT_ONE, "END TEST CHECK", 5)
BRIEF_NEW_RECHECKED = (
    "TEST CHECK demo",
    "merge output: " + MERGE_ARTIFACT_TWO,
    "END TEST CHECK",
    5,
)
BRIEF_STRIKE = (
    "OK tests/test_a.py::test_x",
    None,
    "OK tests/test_a.py::test_x",
    1,
)

DIFF_TOKENS = ("+def test_b_two():", "+def test_a_other():")
NAME_TOKENS = ("tests/test_a.py", "tests/test_b.py")
MERGE_RED_TOKENS = ("test_alpha_fails", "test_bravo_fails")


def _brief_shape(lines):
    """Project `pair.sh merge` stdout onto the marker lines docs/agents.md:46 names.

    Returns the first line, the fourth line (None where stdout is shorter than
    four lines), the last line, and how many lines were printed.
    """
    if not lines:
        return (None, None, None, 0)
    return (lines[0], lines[3] if len(lines) > 3 else None, lines[-1], len(lines))


def _section(text, heading):
    """Return the body under `heading` in a gauntlet/merge/<slug>.txt artifact.

    The three headings and their order are documented at docs/agents.md line 48.
    Returns None where the artifact carries no line naming that heading.
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        return None
    body = []
    for line in lines[start:]:
        if line.strip() in MERGE_HEADINGS:
            break
        body.append(line)
    return "\n".join(body)


def _red_section_marks(text):
    """Classify the `red output:` section of a merge artifact by what it names.

    Returns `("no heading",)` where the section is missing, `("empty",)` where it
    carries no content, and otherwise the failing-test names of the fixture
    suites that appear in it, sorted.
    """
    body = _section(text, "red output:")
    if body is None:
        return ("no heading",)
    if not body.strip():
        return ("empty",)
    return tuple(sorted(token for token in MERGE_RED_TOKENS if token in body))


def _merge(tmp_path, changes, base=None, suite=None, block=BLOCK_NEW, checks=1):
    """Drive open, an optional red run, a test commit, a check and merge.

    `base` maps a name under tests/ to its text in the repository before the
    worktree is cut; `changes` maps a name under tests/ to its text in the spec
    worktree, and those are the files the merge sees change. `suite` is the text
    of an extra tests/test_suite.py, whose red run is saved to gauntlet/red, or
    None to leave no saved red log. `checks` is how many times `pair.sh check`
    runs before the merge, since the check verb is what writes the numbered
    artifact and merge refuses a pair no passing check covers. Returns the
    stdout lines of `pair.sh merge` and the text of the newest numbered
    gauntlet/merge/<slug>.<N>.txt, empty where no such file was written.
    """
    repo = _repo(tmp_path, block, REVIEWER)
    for name, text in (base or {}).items():
        (repo / "tests" / name).write_text(text)
    if suite is not None:
        (repo / "tests" / "test_suite.py").write_text(suite)
    if base or suite is not None:
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "base tests")
    _pair(repo, "open", SLUG)
    worktree = _worktree(repo)
    for name, text in changes.items():
        (worktree / "tests" / name).write_text(text)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", "spec tests")
    if suite is not None:
        _venv_shim(worktree)
        _pair(repo, "red", SLUG)
    for _ in range(checks):
        _pair(repo, "check", SLUG)
    lines = _pair(repo, "merge", SLUG)
    return lines, _newest_merge_artifact(repo)


@pytest.mark.parametrize(
    ("block", "changes", "suite", "checks", "expected"),
    [
        (BLOCK_SINGLE_TEST, {"test_a.py": TEST_A_OTHER}, None, 1, BRIEF_STRIKE),
        (BLOCK_NEW, {"test_a.py": TEST_A_OTHER}, None, 1, BRIEF_NEW),
        (
            BLOCK_NEW,
            {"test_a.py": TEST_A_OTHER, "test_b.py": TEST_B_GREW},
            ALPHA_SUITE,
            1,
            BRIEF_NEW,
        ),
        (BLOCK_NEW, {"test_a.py": TEST_A_OTHER}, None, 2, BRIEF_NEW_RECHECKED),
    ],
    ids=[
        "motion-strike",
        "kind-new-one-file",
        "kind-new-two-files-and-a-red-log",
        "kind-new-after-a-second-check",
    ],
)
def test_merge_prints_the_five_line_brief_for_kind_new_whatever_it_merged(
    tmp_path, block, changes, suite, checks, expected
):
    lines, _ = _merge(tmp_path, changes, suite=suite, block=block, checks=checks)
    assert _brief_shape(lines) == expected


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"test_b.py": TEST_B_GREW}, {"+def test_b_two():"}),
        ({"test_a.py": TEST_A}, {"+def test_a_other():"}),
    ],
    ids=["diff-adds-test-b-two", "diff-adds-test-a-other"],
)
def test_merge_artifact_diff_section_carries_the_lines_that_merge_added(
    tmp_path, changes, expected
):
    _, artifact = _merge(tmp_path, changes, base={"test_a.py": TEST_A_BASE})
    body = _section(artifact, "diff:") or ""
    assert {token for token in DIFF_TOKENS if token in body} == expected


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {"test_a.py": TEST_A, "test_b.py": TEST_B_GREW},
            {"tests/test_a.py", "tests/test_b.py"},
        ),
        ({"test_a.py": TEST_A}, {"tests/test_a.py"}),
    ],
    ids=["two-files-changed", "one-file-changed"],
)
def test_merge_artifact_test_files_section_names_the_files_the_merge_changed(
    tmp_path, changes, expected
):
    _, artifact = _merge(tmp_path, changes, base={"test_a.py": TEST_A_BASE})
    body = _section(artifact, "test files:") or ""
    assert {name for name in NAME_TOKENS if name in body} == expected


@pytest.mark.parametrize(
    ("suite", "expected"),
    [
        (ALPHA_SUITE, ("test_alpha_fails",)),
        (BRAVO_SUITE, ("test_bravo_fails",)),
        (None, ("empty",)),
    ],
    ids=["alpha-suite-red-log", "bravo-suite-red-log", "no-red-log-on-disk"],
)
def test_merge_artifact_red_output_section_carries_the_red_run_on_disk(tmp_path, suite, expected):
    _, artifact = _merge(tmp_path, {"test_a.py": TEST_A_OTHER}, suite=suite)
    assert _red_section_marks(artifact) == expected


IMPL_FILE = "impl_work.txt"


def _impl_checkout(repo):
    """Run `pair.sh impl checkout <slug>` and return its stdout lines."""
    return _pair(repo, "impl", "checkout", SLUG)


def _named_dir(lines, repo):
    """Resolve the second whitespace field of a one-line stdout to a directory.

    The field is read relative to the repository root, which leaves an absolute
    field unchanged. Returns None where stdout is not exactly one line, where
    that line carries fewer than two fields, or where the field names no
    directory on disk.
    """
    if len(lines) != 1:
        return None
    fields = lines[0].split()
    if len(fields) < 2:
        return None
    named = repo / fields[1]
    return named if named.is_dir() else None


def _common_git_dir(path):
    """Return the resolved shared git directory of the checkout at `path`.

    A worktree of a repository and that repository report the same path here.
    Returns None where `path` is no checkout at all.
    """
    try:
        shared = _git(path, "rev-parse", "--git-common-dir")
    except RuntimeError:
        return None
    return Path(path, shared).resolve()


def _branch(path):
    """Return the branch name checked out at `path`, or None where it is none."""
    try:
        return _git(path, "rev-parse", "--abbrev-ref", "HEAD")
    except RuntimeError:
        return None


def _rev(repo, rev):
    """Return the full object name `rev` resolves to in `repo`, or "" if none."""
    try:
        return _git(repo, "rev-parse", rev)
    except RuntimeError:
        return ""


def _is_ancestor(repo, ancestor, descendant):
    """Return whether `ancestor` is an ancestor commit of `descendant`."""
    done = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        env=dict(ENV),
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


def _checkout_shape(lines, repo):
    """Project `impl checkout` stdout onto what the path it names is.

    Returns the number of stdout lines, whether the second field names a
    checkout sharing this repository's git directory, and whether that checkout
    is on the same branch as the caller. A field naming no checkout collapses
    both flags to False rather than raising.
    """
    tree = _named_dir(lines, repo)
    shared = None if tree is None else _common_git_dir(tree)
    if shared is None:
        return (len(lines), False, False)
    return (len(lines), shared == _common_git_dir(repo), _branch(tree) == _branch(repo))


def test_impl_checkout_names_a_worktree_of_this_repo_on_another_branch(tmp_path):
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    assert _checkout_shape(_impl_checkout(repo), repo) == (1, True, False)


def _impl_tree_commits(tmp_path):
    """Cut the impl tree, commit in it, then run `impl checkout` a second time.

    Returns the commit the tree was cut at, the commit it carried just before
    the second call, and the commit it carries after it. A first call naming no
    directory collapses all three to distinct placeholders, so that neither the
    equality nor the inequality the caller asserts can hold by accident.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    tree = _named_dir(_impl_checkout(repo), repo)
    if tree is None:
        return ("no branch point", "no commit before", "no commit after")
    branch_point = _git(tree, "rev-parse", "HEAD")
    (tree / IMPL_FILE).write_text("implementation in progress\n")
    _git(tree, "add", "-A")
    _git(tree, "commit", "-m", "impl work")
    before = _git(tree, "rev-parse", "HEAD")
    _impl_checkout(repo)
    after = _git(tree, "rev-parse", "HEAD") if tree.is_dir() else "tree gone"
    return (branch_point, before, after)


def test_a_second_impl_checkout_leaves_the_tree_on_the_commit_it_was_on(tmp_path):
    branch_point, before, after = _impl_tree_commits(tmp_path)
    assert (after == before, after == branch_point) == (True, False)


def _impl_merge_shape(tmp_path):
    """Cut the impl tree, commit in it, then run `pair.sh impl merge <slug>`.

    Returns the number of stdout lines, the second field of the line, whether
    the commit its third field names has the pre-call tip of the impl tree as an
    ancestor, and whether that commit is the primary checkout's HEAD after the
    call. Stdout that is not one line of at least three fields collapses to
    empty and False rather than raising.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    tree = _named_dir(_impl_checkout(repo), repo)
    tip = "no impl tree"
    if tree is not None:
        (tree / IMPL_FILE).write_text("implementation to be merged\n")
        _git(tree, "add", "-A")
        _git(tree, "commit", "-m", "impl work")
        tip = _git(tree, "rev-parse", "HEAD")
    lines = _pair(repo, "impl", "merge", SLUG)
    fields = lines[0].split() if len(lines) == 1 else []
    if len(fields) < 3:
        return (len(lines), "", False, False)
    printed = _rev(repo, fields[2])
    return (
        len(lines),
        fields[1],
        _is_ancestor(repo, tip, fields[2]),
        printed != "" and printed == _rev(repo, "HEAD"),
    )


def test_impl_merge_prints_the_slug_and_a_commit_holding_the_impl_tip(tmp_path):
    assert _impl_merge_shape(tmp_path) == (1, SLUG, True, True)


MOVED_FILE = "moved.txt"
MOVED_TEXT = "the target branch moved under the pair\n"


def _open_on_gate(tmp_path, gate):
    """Open the pair with `gate` as the gate command `blind-reads.json` names.

    Commits a test in the spec worktree, which is the change a convergence
    lands. Returns the repository and the spec worktree.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    (repo / ".claude" / "blind-reads.json").write_text(
        json.dumps({"target_branch": TARGET, "gate_command": gate})
    )
    _pair(repo, "open", SLUG)
    worktree = _worktree(repo)
    (worktree / "tests" / "test_a.py").write_text(TEST_A_OTHER)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", "spec tests")
    return repo, worktree


def _converge(tmp_path, move=False):
    """Open the pair, commit a test in the spec tree, check it, then merge.

    `move` commits a file on the target branch after the pair is cut, so the
    branch has moved under it. The check verb runs before the merge, because
    merge refuses a pair no passing check covers. Returns the stdout lines,
    whether the target branch's HEAD moved, whether the spec worktree is gone,
    and the text of the two files at that HEAD.
    """
    repo, worktree = _open_on_gate(tmp_path, GATE)
    if move:
        (repo / MOVED_FILE).write_text(MOVED_TEXT)
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "the target branch moves")
    _pair(repo, "check", SLUG)
    before = _git(repo, "rev-parse", "HEAD")
    lines = _pair(repo, "merge", SLUG)
    return (
        lines,
        _git(repo, "rev-parse", "HEAD") != before,
        not worktree.is_dir(),
        _show(repo, "HEAD:tests/test_a.py"),
        _show(repo, "HEAD:" + MOVED_FILE),
    )


@pytest.mark.parametrize(
    ("move", "expected"),
    [
        (False, (True, True, TEST_A_OTHER, "")),
        (True, (True, True, TEST_A_OTHER, MOVED_TEXT)),
    ],
    ids=["target-branch-still", "target-branch-moved-under-the-pair"],
)
def test_merge_lands_the_spec_tree_on_a_target_branch_that_moved_under_it(tmp_path, move, expected):
    heading = "TEST CHECK demo"
    lines, moved, gone, landed, carried = _converge(tmp_path, move=move)
    assert (moved, gone, landed, carried, _brief_shape(lines)[0]) == (*expected, heading)


FOLLOW_UP_FILE = "tests/test_d.py"
FOLLOW_UP_TEXT = "def test_d():\n    assert 4 + 4 == 8\n"

#: a committed test the spec worktree carries and the primary checkout does
#: not, since the pair is cut before it is written
SPEC_ONLY_FILE = "tests/test_spec_only.py"
SPEC_ONLY_TEXT = "def test_spec_only():\n    assert 6 + 6 == 12\n"
#: the other side of the same pair: an untracked file written into the primary
#: checkout after the worktree is cut, which nothing carries across to it
CHECKOUT_ONLY_FILE = ".claude/checkout_only.txt"
CHECKOUT_ONLY_TEXT = "a file the primary checkout alone holds\n"


def _merge_after_check(tmp_path, gate, follow_up):
    """Open a pair, run `pair.sh check` unless `gate` is None, then merge.

    `gate` is the gate command `blind-reads.json` names, so "false" drives a
    check whose gate reads red; None runs no check at all. A file only the spec
    worktree holds is committed there and a file only the primary checkout
    holds sits beside it, so a `test -f` gate reads a different answer in each
    of the two trees. `follow_up` commits a further test in the spec worktree
    after the check and before the merge, so the trees moved under the reading
    the check recorded. Returns the merge's first stdout line ("" where it
    printed none), its exit status, and whether the target branch's HEAD moved
    across it.
    """
    repo, worktree = _open_on_gate(tmp_path, GATE if gate is None else gate)
    (worktree / SPEC_ONLY_FILE).write_text(SPEC_ONLY_TEXT)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", "a test the spec tree alone holds")
    (repo / CHECKOUT_ONLY_FILE).write_text(CHECKOUT_ONLY_TEXT)
    if gate is not None:
        _pair(repo, "check", SLUG)
    if follow_up:
        (worktree / FOLLOW_UP_FILE).write_text(FOLLOW_UP_TEXT)
        _git(worktree, "add", "-A")
        _git(worktree, "commit", "-m", "a further test lands in the spec tree")
    before = _git(repo, "rev-parse", "HEAD")
    lines, status = _pair_status(repo, "merge", SLUG)
    return (
        lines[0] if lines else "",
        status,
        _git(repo, "rev-parse", "HEAD") != before,
    )


@pytest.mark.parametrize(
    ("gate", "follow_up", "expected"),
    [
        (None, False, ("UNCHECKED " + SLUG, 1, False)),
        ("false", False, ("UNCHECKED " + SLUG, 1, False)),
        # a passing reading covers the tips it recorded and no later ones
        (GATE, True, ("UNCHECKED " + SLUG, 1, False)),
        (GATE, False, ("TEST CHECK " + SLUG, 0, True)),
        # the declaration's value is a command and its arguments, not one
        # program name: `make check` is the value the kit ships as its default
        ("git version", False, ("TEST CHECK " + SLUG, 0, True)),
        ("git no-such-subcommand", False, ("UNCHECKED " + SLUG, 1, False)),
        # and it reads the tree being merged, not the primary checkout
        ("test -f " + SPEC_ONLY_FILE, False, ("TEST CHECK " + SLUG, 0, True)),
        ("test -f " + CHECKOUT_ONLY_FILE, False, ("UNCHECKED " + SLUG, 1, False)),
    ],
    ids=[
        "no-check-has-run",
        "the-newest-check-read-red",
        "a-commit-followed-the-passing-check",
        "the-newest-check-read-green",
        "a-gate-of-a-program-and-an-argument-that-passes",
        "a-gate-of-a-program-and-an-argument-that-fails",
        "a-gate-on-a-file-the-spec-tree-alone-holds",
        "a-gate-on-a-file-the-checkout-alone-holds",
    ],
)
def test_a_red_gate_leaves_the_target_branch_and_both_trees_exactly_as_they_were(
    tmp_path, gate, follow_up, expected
):
    assert _merge_after_check(tmp_path, gate, follow_up) == expected


def _merge_stderr(tmp_path, tracked):
    """Open, write a test in the spec tree, merge, and return the merge's stderr.

    `tracked` decides whether the checkout carries the block at the base
    commit. Untracked is the shape the chain produces: the block is a file the
    reviewer wrote, and `pair.sh open` is what puts it on the spec branch, so
    that commit is a write the spec tree makes outside the tests directory. The
    lane check is step 1 and prints its refusal on stderr, which is why stderr
    rather than stdout is what this measures.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    if not tracked:
        #: the lane directory stays tracked, which is what the `.gitkeep`
        #: `scripts/init.py` writes is for; the block alone leaves the index
        (repo / "gauntlet" / "specs" / "approved" / ".gitkeep").write_text("")
        _git(repo, "add", "-A")
        _git(repo, "rm", "--cached", "-q", "--", SPEC_PATH)
        _git(repo, "commit", "-m", "the block is the reviewer's, untracked here")
    _pair(repo, "open", SLUG)
    worktree = _worktree(repo)
    (worktree / "tests" / "test_a.py").write_text(TEST_A_OTHER)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", "spec tests")
    env = dict(ENV)
    env["HOME"] = str(repo)
    done = subprocess.run(
        [str(repo / "scripts" / "pair.sh"), "merge", SLUG],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stderr


@pytest.mark.parametrize(
    "tracked",
    [True, False],
    ids=["block-tracked-at-the-base", "block-committed-by-open"],
)
def test_the_block_open_commits_is_inside_the_spec_lane_the_merge_checks(tmp_path, tracked):
    commit_step = "[2/6] commit both trees"
    stderr = _merge_stderr(tmp_path, tracked)
    outside = [line for line in stderr.splitlines() if "wrote outside its lane" in line]
    assert (outside, commit_step in stderr) == ([], True)


def _spec_commit_field(lines):
    """The revision on the brief's `spec commit:` line, or "" where there is none."""
    head = "spec commit: "
    for line in lines:
        if line.startswith(head):
            return line[len(head) :]
    return ""


def test_the_brief_names_a_revision_that_resolves_the_block_as_git_show_spells_it(tmp_path):
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    _pair(repo, "open", SLUG)
    worktree = _worktree(repo)
    (worktree / "tests" / "test_a.py").write_text(TEST_A_OTHER)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", "spec tests")
    #: merge refuses a pair no passing check covers, so the check runs first
    _pair(repo, "check", SLUG)
    revision = _spec_commit_field(_pair(repo, "merge", SLUG))
    #: the `bailiff`'s one shell is `blind.sh show <rev> <slug>`, which spells
    #: `git show <rev>:<path>`; an object name resolves no tree there
    assert _show(repo, revision + ":" + SPEC_PATH) == BLOCK_NEW


SHADOW_FILE = "tests/test_c.py"
SHADOW_LANDING = "def test_c():\n    assert 9 + 9 == 18\n"
SHADOW_OTHER = "def test_c():\n    assert 9 + 9 == 19\n"


def _pair_with_untracked(tmp_path, on_disk):
    """Open a pair whose block is untracked, land a second file over `on_disk`.

    The spec tree commits `SHADOW_FILE` carrying `SHADOW_LANDING`, and the
    primary checkout holds `on_disk` at that path, untracked, or nothing where
    `on_disk` is None. Returns the repository and the merge's stdout lines.
    """
    repo = _checked_pair_with_untracked(tmp_path, on_disk)
    return repo, _pair(repo, "merge", SLUG)


def _checked_pair_with_untracked(tmp_path, on_disk):
    """The setup of `_pair_with_untracked`, stopped short of the merge.

    Returns the repository, checked and holding `on_disk` at `SHADOW_FILE`.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    #: the lane directory stays tracked, the block does not: the shape the
    #: chain produces, where the reviewer wrote the block and `open` commits it
    (repo / "gauntlet" / "specs" / "approved" / ".gitkeep").write_text("")
    _git(repo, "add", "-A")
    _git(repo, "rm", "--cached", "-q", "--", SPEC_PATH)
    _git(repo, "commit", "-m", "the block is the reviewer's, untracked here")
    _pair(repo, "open", SLUG)
    worktree = _worktree(repo)
    (worktree / SHADOW_FILE).write_text(SHADOW_LANDING)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", "spec tests")
    #: merge refuses a pair no passing check covers, so the check runs first
    _pair(repo, "check", SLUG)
    if on_disk is not None:
        (repo / SHADOW_FILE).write_text(on_disk)
    return repo


def test_a_pair_whose_block_is_untracked_in_the_checkout_lands_on_the_target_branch(tmp_path):
    repo, lines = _pair_with_untracked(tmp_path, None)
    landed = (_show(repo, "HEAD:" + SPEC_PATH), _show(repo, "HEAD:" + SHADOW_FILE))
    assert (len(lines), landed) == (5, (BLOCK_NEW, SHADOW_LANDING))


@pytest.mark.parametrize(
    ("on_disk", "expected"),
    [
        (SHADOW_LANDING, (SHADOW_LANDING, True)),
        # a differing untracked file is the owner's work: nothing lands over it
        (SHADOW_OTHER, ("", False)),
    ],
    ids=["untracked-copy-of-what-lands", "untracked-file-that-differs"],
)
def test_only_an_untracked_file_identical_to_what_lands_gives_way_to_it(
    tmp_path, on_disk, expected
):
    repo, _ = _pair_with_untracked(tmp_path, on_disk)
    landed = _show(repo, "HEAD:" + SHADOW_FILE)
    assert ((landed, not _worktree(repo).is_dir()), (repo / SHADOW_FILE).read_text()) == (
        expected,
        on_disk,
    )


def test_a_refused_land_leaves_every_untracked_file_it_moved_aside_where_it_was(tmp_path):
    repo, _ = _pair_with_untracked(tmp_path, SHADOW_OTHER)
    #: the block is the identical copy the land took out of the way, and the
    #: refusal came from the file beside it
    assert (repo / SPEC_PATH).read_text() == BLOCK_NEW


def _merge_output(repo):
    """Run `pair.sh merge <slug>` and return its stdout lines and its stderr."""
    env = dict(ENV)
    env["HOME"] = str(repo)
    done = subprocess.run(
        [str(repo / "scripts" / "pair.sh"), "merge", SLUG],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout.splitlines(), done.stderr


def test_a_refused_land_prints_no_test_check_brief(tmp_path):
    repo = _checked_pair_with_untracked(tmp_path, SHADOW_OTHER)
    lines, _ = _merge_output(repo)
    assert [line for line in lines if line.startswith("TEST CHECK")] == []


def test_a_refused_land_names_the_file_that_blocks_it(tmp_path):
    repo = _checked_pair_with_untracked(tmp_path, SHADOW_OTHER)
    _, stderr = _merge_output(repo)
    _, refused, after = stderr.partition("will not fast-forward")
    assert (refused, SHADOW_FILE in after) == ("will not fast-forward", True)


RED_COMMIT = "red commit: "


def _red_and_brief_commits(tmp_path):
    """Write a test uncommitted, run red, combine an impl commit, check and merge.

    Returns the commit the red log's first line names, the commit the brief's
    `red commit:` line names, the subject of the recorded commit, and the
    target branch's HEAD after the merge. A missing line collapses to "".
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    _pair(repo, "open", SLUG)
    worktree = _worktree(repo)
    (worktree / "tests" / "test_a.py").write_text(TEST_A_OTHER)
    _venv_shim(worktree)
    _pair(repo, "red", SLUG)
    log = (repo / "gauntlet" / "red" / (SLUG + ".txt")).read_text().splitlines()
    recorded = log[0][len(RED_COMMIT) :] if log and log[0].startswith(RED_COMMIT) else ""
    subject = _git(repo, "log", "-1", "--format=%s", recorded) if recorded else ""
    tree = _named_dir(_impl_checkout(repo), repo)
    if tree is not None:
        (tree / IMPL_FILE).write_text("implementation to be combined\n")
        _git(tree, "add", "-A")
        _git(tree, "commit", "-m", "impl work")
    _pair(repo, "check", SLUG)
    briefed = ""
    for line in _pair(repo, "merge", SLUG):
        if line.startswith(RED_COMMIT):
            briefed = line[len(RED_COMMIT) :]
    return recorded, briefed, subject, _git(repo, "rev-parse", "HEAD")


def test_the_brief_names_the_commit_red_recorded_rather_than_the_merge(tmp_path):
    recorded, briefed, subject, landed = _red_and_brief_commits(tmp_path)
    assert (briefed == recorded, recorded != landed, subject) == (True, True, "test: " + SLUG)
