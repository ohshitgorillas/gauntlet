"""Behavior tests for the pair.sh spec-lane driver.

The stdout contracts asserted here are documented in docs/agents.md lines
31-42, so the literals are reachable without reading the implementation.

The merge and impl verbs are measured in tests/test_pair_sh_merge.py.
"""

import itertools
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.support.pair_fixture import (
    ALPHA_SUITE,
    ASSERTION_X,
    BLOCK_NEW,
    BLOCK_SINGLE_TEST,
    BLOCK_V2,
    BLOCK_WHOLE_FILE,
    BODY_NEW,
    BODY_V2,
    BRAVO_SUITE,
    DIVERGED_REVIEWER,
    ENV,
    REVIEWER,
    SLUG,
    SPEC_PATH,
    TEST_A_OTHER,
    _block,
    _git,
    _pair,
    _pair_status,
    _python_listing,
    _repo,
    _show,
    _venv_shim,
    _worktree,
)


@pytest.mark.parametrize(
    ("review_text", "expected"),
    [
        (REVIEWER, "OPEN .claude/worktrees/demo-spec"),
        (DIVERGED_REVIEWER, "MISMATCH gauntlet/reviews/demo.1.txt"),
    ],
    ids=["reviewer-section-matches-round-file", "reviewer-section-differs"],
)
def test_open_reports_mismatch_only_where_the_round_file_text_differs(
    tmp_path, review_text, expected
):
    repo = _repo(tmp_path, BLOCK_NEW, review_text)
    assert _pair(repo, "open", SLUG)[:1] == [expected]


@pytest.mark.parametrize(
    ("block", "expected"),
    [
        (BLOCK_WHOLE_FILE, {"test_a.py"}),
        (BLOCK_SINGLE_TEST, {"test_a.py", "test_b.py"}),
    ],
    ids=["whole-file-target", "single-test-target"],
)
def test_red_removes_whole_file_targets_and_keeps_single_test_target_files(
    tmp_path, block, expected
):
    repo = _repo(tmp_path, block, REVIEWER)
    _pair(repo, "open", SLUG)
    _venv_shim(_worktree(repo))
    _pair(repo, "red", SLUG)
    assert _python_listing(_worktree(repo) / "tests") == expected


RED_TOKENS = (
    "test_alpha_passes",
    "test_alpha_fails",
    "test_bravo_passes",
    "test_bravo_fails",
    "assert 2 + 2 == 5",
    "assert 5 + 5 == 11",
)


def _red_text(tmp_path, suite):
    """Drive open then red over a repo carrying `suite` as its only test file.

    Returns the text of the repository's gauntlet/red/<slug>.txt, or the empty
    string where no such file was written.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    (repo / "tests" / "test_a.py").unlink()
    (repo / "tests" / "test_b.py").unlink()
    (repo / "tests" / "test_suite.py").write_text(suite)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "single suite")
    _pair(repo, "open", SLUG)
    _venv_shim(_worktree(repo))
    _pair(repo, "red", SLUG)
    saved = repo / "gauntlet" / "red" / (SLUG + ".txt")
    return saved.read_text() if saved.is_file() else ""


@pytest.mark.parametrize(
    ("suite", "expected"),
    [
        (
            ALPHA_SUITE,
            {"test_alpha_passes", "test_alpha_fails", "assert 2 + 2 == 5"},
        ),
        (
            BRAVO_SUITE,
            {"test_bravo_passes", "test_bravo_fails", "assert 5 + 5 == 11"},
        ),
    ],
    ids=["alpha-suite", "bravo-suite"],
)
def test_red_saves_output_naming_passing_and_failing_tests_of_the_suite_it_ran(
    tmp_path, suite, expected
):
    red_text = _red_text(tmp_path, suite)
    assert {token for token in RED_TOKENS if token in red_text} == expected


SCRATCH_BLOCK = (
    "slug: demo\n"
    "kind: new\n"
    "brief: none\n"
    "\n"
    "1. a scratch edit that was never committed anywhere\n"
    "   kills: nothing\n"
    "   bite: nothing\n"
    "   existing: none\n"
)


def _restore(tmp_path, target):
    """Drive `pair.sh restore` over two committed revisions of the demo block.

    The first commit carries BLOCK_NEW, the second carries BLOCK_V2, and the
    working tree is then overwritten with SCRATCH_BLOCK, which is committed
    nowhere. `target` picks which revision to restore, "first" or "second".
    Returns the stdout lines of the call, the repository root, and the
    revision that was passed.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    first = _git(repo, "rev-parse", "HEAD")
    (repo / SPEC_PATH).write_text(BLOCK_V2)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "second block")
    second = _git(repo, "rev-parse", "HEAD")
    rev = first if target == "first" else second
    (repo / SPEC_PATH).write_text(SCRATCH_BLOCK)
    return _pair(repo, "restore", SLUG, rev), repo, rev


def _printed(lines, repo):
    """Project `pair.sh restore` stdout onto (line count, third field, text).

    The text is that of the file the second field names, read relative to the
    repository root. Stdout that is not exactly one line, a line of fewer than
    three fields, and a second field naming no file on disk each collapse to
    empty strings rather than raising.
    """
    if len(lines) != 1:
        return (len(lines), "", "")
    fields = lines[0].split()
    if len(fields) < 3:
        return (1, "", "")
    named = repo / fields[1]
    return (1, fields[2], named.read_text() if named.is_file() else "")


@pytest.mark.parametrize(
    ("target", "expected"),
    [("first", BLOCK_NEW), ("second", BLOCK_V2)],
    ids=["restore-the-first-revision", "restore-the-second-revision"],
)
def test_restore_puts_the_blocks_bytes_at_the_named_revision_back_on_disk(
    tmp_path, target, expected
):
    _, repo, _ = _restore(tmp_path, target)
    assert (repo / SPEC_PATH).read_text() == expected


@pytest.mark.parametrize(
    ("target", "expected"),
    [("first", BLOCK_NEW), ("second", BLOCK_V2)],
    ids=["restore-the-first-revision", "restore-the-second-revision"],
)
def test_restore_prints_one_line_naming_the_path_it_wrote_and_the_revision(
    tmp_path, target, expected
):
    lines, repo, rev = _restore(tmp_path, target)
    assert _printed(lines, repo) == (1, rev, expected)


def _review(tmp_path, rounds, args):
    """Run `pair.sh review` over a reviews directory holding `rounds`."""
    repo = _repo(tmp_path, _block(BODY_NEW), REVIEWER)
    reviews = repo / "gauntlet" / "reviews"
    for name in rounds:
        (reviews / name).write_text("round\n")
    return _pair(repo, "review", *args)


@pytest.mark.parametrize(
    ("rounds", "args", "expected"),
    [
        ((), (SLUG,), "REVIEW gauntlet/reviews/demo.2.txt"),
        (("demo.2.txt", "demo.3.txt"), (SLUG,), "REVIEW gauntlet/reviews/demo.4.txt"),
        # the count is of what is on disk, so a gap does not lower it and a
        # round that wrote nothing leaves its number for the next one
        (("demo.7.txt",), (SLUG,), "REVIEW gauntlet/reviews/demo.8.txt"),
        # a slug with no round at all starts at 1
        ((), ("other",), "REVIEW gauntlet/reviews/other.1.txt"),
        # the plan series is counted apart from the spec series, and neither
        # name is a round of the other
        ((), ("plan", SLUG), "REVIEW gauntlet/reviews/demo.plan.1.txt"),
        (
            ("demo.plan.1.txt", "demo.plan.2.txt"),
            ("plan", SLUG),
            "REVIEW gauntlet/reviews/demo.plan.3.txt",
        ),
        (("demo.plan.9.txt",), (SLUG,), "REVIEW gauntlet/reviews/demo.2.txt"),
        (("demo.4.txt",), ("plan", SLUG), "REVIEW gauntlet/reviews/demo.plan.1.txt"),
        # a name that is not a numbered round is not counted
        (("demo.draft.txt", "demo.txt"), (SLUG,), "REVIEW gauntlet/reviews/demo.2.txt"),
    ],
    ids=[
        "fixture-round-only",
        "highest-of-several",
        "gap-in-the-numbering",
        "slug-with-no-round",
        "plan-series-empty",
        "plan-series-counted",
        "plan-rounds-are-not-spec-rounds",
        "spec-rounds-are-not-plan-rounds",
        "unnumbered-names-are-not-rounds",
    ],
)
def test_review_prints_the_next_round_path_of_the_series_it_is_asked_for(
    tmp_path, rounds, args, expected
):
    assert _review(tmp_path, rounds, args) == [expected]


def test_review_creates_the_reviews_directory_the_reviewer_writes_into(tmp_path):
    # The reviewer's Write is its own; the directory under it is not, and a
    # reviewer denied every read of the lane cannot tell whether it is there.
    repo = _repo(tmp_path, _block(BODY_NEW), REVIEWER)
    shutil.rmtree(repo / "gauntlet" / "reviews")
    announced = ["REVIEW gauntlet/reviews/demo.1.txt"]
    lines = _pair(repo, "review", SLUG)
    assert (lines, (repo / "gauntlet" / "reviews").is_dir()) == (announced, True)


NEW_ROUND = (
    "READY\n"
    "discriminates: differential on the widget counter\n"
    "1  KEEP  four widgets -> 4, five widgets -> 5\n"
)


def _with_round(body, round_text):
    return body + "\n--- reviewer ---\n" + round_text


def _collateral_body(breaks):
    """BODY_NEW with one collateral row whose single `breaks:` field is `breaks`.

    The row is the `collateral:` line at column zero beneath the behavior lines,
    the row itself, and the row's fields indented two spaces under it. The
    target and the assertion are the fixture repository's own tests/test_a.py.
    """
    return (
        BODY_NEW
        + "\ncollateral:\n"
        + "- tests/test_a.py::test_x\n"
        + "  breaks: "
        + breaks
        + "\n"
        + "  assertion: "
        + ASSERTION_X
        + "\n"
    )


BODY_COLLATERAL = _collateral_body("the keyword the helper passes was renamed")
BODY_COLLATERAL_V2 = _collateral_body("the helper now passes the row count instead")


def _respec(tmp_path, committed, round_text, block_text):
    """Open the demo pair, then re-approve it with `block_text` under `round_text`.

    `committed` is the block the pair is cut from, `round_text` lands as the
    newest round on disk and `block_text` as the approved block, both after the
    pair is open. Returns the stdout lines of `pair.sh respec` and the spec
    worktree it ran against.
    """
    repo = _repo(tmp_path, committed, REVIEWER)
    _pair(repo, "open", SLUG)
    (repo / "gauntlet" / "reviews" / "demo.2.txt").write_text(round_text)
    (repo / SPEC_PATH).write_text(block_text)
    return _pair(repo, "respec", SLUG), _worktree(repo)


def _respec_shape(lines, tree):
    """Project `pair.sh respec` stdout onto its marker and the landed block.

    The marker is the run of leading all-capital words, so a one-word marker and
    a two-word one are told apart; the fields after it name a path and a commit,
    neither of which is fixed. The block is read from the spec branch's HEAD,
    which is where the writer's delta reads it. Stdout that is not exactly one
    line collapses the marker to the empty string rather than raising.
    """
    fields = lines[0].split() if len(lines) == 1 else []
    marker = itertools.takewhile(lambda field: field.isalpha() and field.isupper(), fields)
    return (" ".join(marker), _show(tree, "HEAD:" + SPEC_PATH))


@pytest.mark.parametrize(
    ("committed", "round_text", "block_text", "expected"),
    [
        (
            BLOCK_NEW,
            NEW_ROUND,
            _with_round(BODY_V2, NEW_ROUND),
            ("RESPEC", _with_round(BODY_V2, NEW_ROUND)),
        ),
        # the two blocks differ in a collateral row alone, and in nothing else
        (
            _block(BODY_COLLATERAL),
            NEW_ROUND,
            _with_round(BODY_COLLATERAL_V2, NEW_ROUND),
            ("RESPEC COLLATERAL", _with_round(BODY_COLLATERAL_V2, NEW_ROUND)),
        ),
        # the block's reviewer section is not the round file on disk
        (BLOCK_NEW, NEW_ROUND, _with_round(BODY_V2, REVIEWER), ("MISMATCH", BLOCK_NEW)),
        # the newest round is the one the spec branch already committed
        (BLOCK_NEW, REVIEWER, _with_round(BODY_V2, REVIEWER), ("", BLOCK_NEW)),
    ],
    ids=[
        "new-round-lands",
        "collateral-rows-differ-alone",
        "reviewer-section-differs",
        "round-already-committed",
    ],
)
def test_respec_lands_the_block_only_under_a_round_newer_than_the_committed_one(
    tmp_path, committed, round_text, block_text, expected
):
    lines, tree = _respec(tmp_path, committed, round_text, block_text)
    assert _respec_shape(lines, tree) == expected


def _pair_state(repo):
    """(`pair.sh list` stdout, the spec tree exists, the spec branch exists)."""
    listed = _pair(repo, "list")
    branches = subprocess.run(
        ["git", "branch", "--list", "spec/" + SLUG],
        cwd=repo,
        env=dict(ENV),
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return (listed, _worktree(repo).is_dir(), bool(branches.strip()))


def _opened_then(tmp_path, verb):
    """Open the demo pair, then run `verb` on it where one is named.

    Returns the pair state before and after. `verb` of None runs nothing, so the
    two states are the same reading twice.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    _pair(repo, "open", SLUG)
    before = _pair_state(repo)
    if verb is not None:
        _pair(repo, verb, SLUG)
    return before, _pair_state(repo)


def _listing_shape(state):
    """Project a pair state onto the first two fields of each listed line.

    Two fields rather than the whole line, because a `PAIR` line carries the
    commit the pair was cut at and how far the target branch has moved since,
    neither of which is fixed. The fields kept are the marker and the slug.
    """
    listed, tree, branch = state
    return (tuple(" ".join(line.split()[:2]) for line in listed), tree, branch)


@pytest.mark.parametrize(
    ("verb", "expected"),
    [
        ("abort", (("NO PAIRS",), False, False)),
        (None, (("PAIR demo",), True, True)),
    ],
    ids=["abort-takes-the-pair-out", "an-open-pair-is-listed"],
)
def test_abort_removes_the_tree_and_the_branch_that_list_reports(tmp_path, verb, expected):
    _, after = _opened_then(tmp_path, verb)
    assert _listing_shape(after) == expected


def test_list_reports_the_open_pair_before_abort_and_none_after(tmp_path):
    before, after = _opened_then(tmp_path, "abort")
    assert (_listing_shape(before)[0], _listing_shape(after)[0]) == (
        ("PAIR demo",),
        ("NO PAIRS",),
    )


def _worktree_paths(repo):
    """The resolved paths `git worktree list --porcelain` reports in `repo`.

    The porcelain form carries one `worktree <path>` line per checkout, the
    primary one included, and the paths it prints are absolute.
    """
    listed = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo,
        env=dict(ENV),
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return {
        Path(line.split(" ", 1)[1]).resolve()
        for line in listed.splitlines()
        if line.startswith("worktree ")
    }


def _closed_over_spec_tree(tmp_path, dirty):
    """Open the demo pair, dirty its spec tree where asked, then close it.

    `dirty` overwrites a tracked file of the spec worktree and commits it
    nowhere. Returns the worktree paths git reports before the close, the ones
    it reports after it, and the resolved path of the spec worktree itself.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    _pair(repo, "open", SLUG)
    spec_tree = _worktree(repo)
    if dirty:
        (spec_tree / "tests" / "test_a.py").write_text(TEST_A_OTHER)
    before = _worktree_paths(repo)
    _pair(repo, "close", SLUG)
    return before, _worktree_paths(repo), spec_tree.resolve()


@pytest.mark.parametrize(
    ("dirty", "removed"),
    [(False, True), (True, False)],
    ids=["spec-tree-clean", "spec-tree-holds-an-uncommitted-change"],
)
def test_close_takes_out_a_clean_spec_tree_and_leaves_a_dirty_one_standing(
    tmp_path, dirty, removed
):
    before, after, spec_tree = _closed_over_spec_tree(tmp_path, dirty)
    assert (spec_tree in before, after) == (True, before - ({spec_tree} if removed else set()))


def _impl_tree(repo):
    """Cut the pair's implementation worktree and return the path it names.

    The path is the second whitespace field of the one line `impl checkout`
    prints, read relative to the repository root. Returns None where stdout is
    not one line of at least two fields.
    """
    lines = _pair(repo, "impl", "checkout", SLUG)
    fields = lines[0].split() if len(lines) == 1 else []
    return repo / fields[1] if len(fields) > 1 else None


def _close_status(tmp_path, dirty_tree):
    """Open a pair with both trees cut, dirty one of them, then close it.

    `dirty_tree` of "impl" overwrites a tracked file of the implementation
    worktree and commits it nowhere, leaving the spec worktree clean; None
    leaves both trees clean. Returns the exit status of `pair.sh close <slug>`.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    _pair(repo, "open", SLUG)
    impl_tree = _impl_tree(repo)
    if dirty_tree == "impl":
        (impl_tree / "tests" / "test_a.py").write_text(TEST_A_OTHER)
    return _pair_status(repo, "close", SLUG)[1]


@pytest.mark.parametrize(
    ("dirty_tree", "expected"),
    [(None, 0), ("impl", 1)],
    ids=["both-trees-clean", "impl-tree-holds-an-uncommitted-change"],
)
def test_close_exits_zero_only_where_every_tree_of_the_pair_was_clean(
    tmp_path, dirty_tree, expected
):
    assert _close_status(tmp_path, dirty_tree) == expected
