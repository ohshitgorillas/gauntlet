"""Behavior tests for the pair.sh spec-lane driver.

The stdout contracts asserted here are documented in docs/agents.md lines
31-42, so the literals are reachable without reading the implementation.

The merge and impl verbs are measured in tests/test_pair_sh_merge.py.
"""

import shutil
import subprocess

import pytest

from tests.support.pair_fixture import (
    ALPHA_SUITE,
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
    _block,
    _git,
    _pair,
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


def _respec(tmp_path, round_text, block_text):
    """Open the demo pair, then re-approve it with `block_text` under `round_text`.

    `round_text` lands as the newest round on disk and `block_text` as the
    approved block, both after the pair is open. Returns the stdout lines of
    `pair.sh respec` and the spec worktree it ran against.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    _pair(repo, "open", SLUG)
    (repo / "gauntlet" / "reviews" / "demo.2.txt").write_text(round_text)
    (repo / SPEC_PATH).write_text(block_text)
    return _pair(repo, "respec", SLUG), _worktree(repo)


def _respec_shape(lines, tree):
    """Project `pair.sh respec` stdout onto its first field and the landed block.

    The block is read from the spec branch's HEAD, which is where the writer's
    delta reads it. Stdout that is not exactly one line collapses the field to
    the empty string rather than raising.
    """
    fields = lines[0].split() if len(lines) == 1 else []
    return (fields[0] if fields else "", _show(tree, "HEAD:" + SPEC_PATH))


@pytest.mark.parametrize(
    ("round_text", "block_text", "expected"),
    [
        (NEW_ROUND, _with_round(BODY_V2, NEW_ROUND), ("RESPEC", _with_round(BODY_V2, NEW_ROUND))),
        # the block's reviewer section is not the round file on disk
        (NEW_ROUND, _with_round(BODY_V2, REVIEWER), ("MISMATCH", BLOCK_NEW)),
        # the newest round is the one the spec branch already committed
        (REVIEWER, _with_round(BODY_V2, REVIEWER), ("", BLOCK_NEW)),
    ],
    ids=["new-round-lands", "reviewer-section-differs", "round-already-committed"],
)
def test_respec_lands_the_block_only_under_a_round_newer_than_the_committed_one(
    tmp_path, round_text, block_text, expected
):
    lines, tree = _respec(tmp_path, round_text, block_text)
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
