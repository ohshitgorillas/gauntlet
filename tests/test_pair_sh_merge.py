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
    _pair,
    _repo,
    _show,
    _venv_shim,
    _worktree,
)

TEST_A_BASE = "def test_x():\n    " + ASSERTION_X + "\n"
TEST_B_TWO = "def test_b_two():\n    assert 7 + 7 == 14\n"
TEST_B_GREW = TEST_B + "\n\n" + TEST_B_TWO

MERGE_ARTIFACT = "gauntlet/merge/" + SLUG + ".txt"
MERGE_HEADINGS = ("test files:", "diff:", "red output:")

BRIEF_NEW = ("TEST CHECK demo", "merge output: " + MERGE_ARTIFACT, "END TEST CHECK", 5)
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


def _merge(tmp_path, changes, base=None, suite=None, block=BLOCK_NEW):
    """Drive open, an optional red run, a test commit and merge for the demo slug.

    `base` maps a name under tests/ to its text in the repository before the
    worktree is cut; `changes` maps a name under tests/ to its text in the spec
    worktree, and those are the files the merge sees change. `suite` is the text
    of an extra tests/test_suite.py, whose red run is saved to gauntlet/red, or
    None to leave no saved red log. Returns the stdout lines of `pair.sh merge`
    and the text of gauntlet/merge/<slug>.txt, empty where no such file was written.
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
    lines = _pair(repo, "merge", SLUG)
    artifact = repo / "gauntlet" / "merge" / (SLUG + ".txt")
    return lines, artifact.read_text() if artifact.is_file() else ""


@pytest.mark.parametrize(
    ("block", "changes", "suite", "expected"),
    [
        (BLOCK_SINGLE_TEST, {"test_a.py": TEST_A_OTHER}, None, BRIEF_STRIKE),
        (BLOCK_NEW, {"test_a.py": TEST_A_OTHER}, None, BRIEF_NEW),
        (
            BLOCK_NEW,
            {"test_a.py": TEST_A_OTHER, "test_b.py": TEST_B_GREW},
            ALPHA_SUITE,
            BRIEF_NEW,
        ),
    ],
    ids=["motion-strike", "kind-new-one-file", "kind-new-two-files-and-a-red-log"],
)
def test_merge_prints_the_five_line_brief_for_kind_new_whatever_it_merged(
    tmp_path, block, changes, suite, expected
):
    lines, _ = _merge(tmp_path, changes, suite=suite, block=block)
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


def _converge(tmp_path, move=False, gate=GATE):
    """Open the pair, commit a test in the spec tree, then merge.

    `move` commits a file on the target branch after the pair is cut, so the
    branch has moved under it. `gate` is the command `blind-reads.json` names,
    so a merge can be driven onto a red gate. Returns the stdout lines, whether
    the target branch's HEAD moved, whether the spec worktree is gone, and the
    text of the two files at that HEAD.
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
    if move:
        (repo / MOVED_FILE).write_text(MOVED_TEXT)
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "the target branch moves")
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


@pytest.mark.parametrize(
    ("gate", "expected"),
    [
        (GATE, (5, True, True, TEST_A_OTHER)),
        # nothing landed, so the target branch still carries the fixture's file
        ("false", (0, False, False, TEST_A)),
    ],
    ids=["gate-passes", "gate-fails-and-nothing-lands"],
)
def test_a_red_gate_leaves_the_target_branch_and_both_trees_exactly_as_they_were(
    tmp_path, gate, expected
):
    lines, moved, gone, landed, _ = _converge(tmp_path, gate=gate)
    assert (len(lines), moved, gone, landed) == expected


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
    if on_disk is not None:
        (repo / SHADOW_FILE).write_text(on_disk)
    return repo, _pair(repo, "merge", SLUG)


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
