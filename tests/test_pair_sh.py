"""Behavior tests for the pair.sh spec-lane driver.

The stdout contracts asserted here are documented in docs/agents.md lines
31-42, so the literals are reachable without reading the implementation.
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PAIR = REPO / "scripts" / "pair.sh"
EXCISION_DIFF = REPO / "scripts" / "excision-diff.py"
SHELL_SHAPES = REPO / ".claude" / "hooks" / "shell_shapes.py"

SLUG = "demo"

ENV = {
    "PATH": os.environ.get("PATH", ""),
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "Fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
}

GITIGNORE = ".venv/\n.claude/\n.pytest_cache/\n__pycache__/\n"

REVIEWER = (
    "READY\n"
    "discriminates: differential on the widget counter\n"
    "1  KEEP  two widgets -> 2, three widgets -> 3\n"
)
DIVERGED_REVIEWER = (
    "READY\n"
    "discriminates: differential on the widget counter\n"
    "1  KEEP  one widget -> 1, four widgets -> 4\n"
)

ASSERTION_X = "assert 2 + 2 == 4"
ASSERTION_B = "assert 5 + 5 == 10"
TEST_A_OTHER = "def test_a_other():\n    assert 3 + 3 == 6\n"
TEST_A = "def test_x():\n    " + ASSERTION_X + "\n\n\n" + TEST_A_OTHER
TEST_B = "def test_b_one():\n    " + ASSERTION_B + "\n"

BODY_NEW = (
    "slug: demo\n"
    "kind: new\n"
    "brief: none\n"
    "\n"
    "1. The widget counter reports two for two widgets and three for three.\n"
    "   kills: reports zero at every input\n"
    "   bite: null stub fails at both inputs (surface new)\n"
    "   existing: none\n"
)


def _block(body):
    return body + "\n--- reviewer ---\n" + REVIEWER


def _excision_body(target, assertion):
    return (
        "slug: demo\n"
        "kind: excision\n"
        "brief: none\n"
        "\n"
        f"1. excise {target}\n"
        "   rule: docs/testing.md rule 9\n"
        f"   assertion: {assertion}\n"
    )


BLOCK_NEW = _block(BODY_NEW)
BLOCK_WHOLE_FILE = _block(_excision_body("tests/test_b.py", ASSERTION_B))
BLOCK_SINGLE_TEST = _block(_excision_body("tests/test_a.py::test_x", ASSERTION_X))


def _git(cwd, *args):
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=dict(ENV), capture_output=True, text=True
    )
    if done.returncode != 0:
        raise RuntimeError("git " + " ".join(args) + " failed: " + done.stderr)
    return done.stdout.strip()


def _venv_shim(root):
    bindir = root / ".venv" / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    shim = bindir / "pytest"
    shim.write_text('#!/bin/sh\nexec "' + sys.executable + '" -m pytest "$@"\n')
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return shim


def _repo(tmp_path, spec_text, review_text):
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "gauntlet" / "specs" / "approved").mkdir(parents=True)
    (repo / "gauntlet" / "reviews").mkdir(parents=True)
    for source in (PAIR, EXCISION_DIFF):
        landed = repo / "scripts" / source.name
        shutil.copy2(source, landed)
        landed.chmod(landed.stat().st_mode | stat.S_IXUSR)
    #: the scripts read the `tests` key of blind-reads.json through the hooks'
    #: reader, so the fixture ships that one module beside them and no config
    (repo / ".claude" / "hooks").mkdir(parents=True)
    shutil.copy2(SHELL_SHAPES, repo / ".claude" / "hooks" / "shell_shapes.py")
    (repo / "tests" / "test_a.py").write_text(TEST_A)
    (repo / "tests" / "test_b.py").write_text(TEST_B)
    (repo / "gauntlet" / "specs" / "approved" / "demo.txt").write_text(spec_text)
    (repo / "gauntlet" / "reviews" / "demo.1.txt").write_text(review_text)
    (repo / ".gitignore").write_text(GITIGNORE)
    _git(repo, "init", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")
    _venv_shim(repo)
    return repo


def _worktree(repo):
    return repo / ".claude" / "worktrees" / "demo-spec"


def _pair(repo, *args):
    env = dict(ENV)
    env["HOME"] = str(repo)
    done = subprocess.run(
        [str(repo / "scripts" / "pair.sh"), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )
    sys.stderr.write(done.stderr)
    return done.stdout.splitlines()


def _python_listing(directory):
    return {entry.name for entry in directory.iterdir() if entry.suffix == ".py"}


@pytest.mark.parametrize(
    "review_text,expected",
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
    "block,expected",
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


ALPHA_SUITE = (
    "def test_alpha_passes():\n"
    "    assert 2 + 2 == 4\n"
    "\n"
    "\n"
    "def test_alpha_fails():\n"
    "    assert 2 + 2 == 5\n"
)
BRAVO_SUITE = (
    "def test_bravo_passes():\n"
    "    assert 5 + 5 == 10\n"
    "\n"
    "\n"
    "def test_bravo_fails():\n"
    "    assert 5 + 5 == 11\n"
)

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

    Returns the text of the repository's state/red/<slug>.txt, or the empty
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
    saved = repo / "state" / "red" / (SLUG + ".txt")
    return saved.read_text() if saved.is_file() else ""


@pytest.mark.parametrize(
    "suite,expected",
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


TEST_A_BASE = "def test_x():\n    " + ASSERTION_X + "\n"
TEST_B_TWO = "def test_b_two():\n    assert 7 + 7 == 14\n"
TEST_B_GREW = TEST_B + "\n\n" + TEST_B_TWO

MERGE_ARTIFACT = "state/merge/" + SLUG + ".txt"
MERGE_HEADINGS = ("test files:", "diff:", "red output:")

BRIEF_NEW = ("TEST CHECK demo", "merge output: " + MERGE_ARTIFACT, "END TEST CHECK", 5)
BRIEF_EXCISION = (
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
    """Return the body under `heading` in a state/merge/<slug>.txt artifact.

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
    of an extra tests/test_suite.py, whose red run is saved to state/red, or None
    to leave no saved red log. Returns the stdout lines of `pair.sh merge` and
    the text of state/merge/<slug>.txt, empty where no such file was written.
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
    artifact = repo / "state" / "merge" / (SLUG + ".txt")
    return lines, artifact.read_text() if artifact.is_file() else ""


@pytest.mark.parametrize(
    "block,changes,suite,expected",
    [
        (BLOCK_SINGLE_TEST, {"test_a.py": TEST_A_OTHER}, None, BRIEF_EXCISION),
        (BLOCK_NEW, {"test_a.py": TEST_A_OTHER}, None, BRIEF_NEW),
        (
            BLOCK_NEW,
            {"test_a.py": TEST_A_OTHER, "test_b.py": TEST_B_GREW},
            ALPHA_SUITE,
            BRIEF_NEW,
        ),
    ],
    ids=["kind-excision", "kind-new-one-file", "kind-new-two-files-and-a-red-log"],
)
def test_merge_prints_the_five_line_brief_for_kind_new_whatever_it_merged(
    tmp_path, block, changes, suite, expected
):
    lines, _ = _merge(tmp_path, changes, suite=suite, block=block)
    assert _brief_shape(lines) == expected


@pytest.mark.parametrize(
    "changes,expected",
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
    "changes,expected",
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
    "suite,expected",
    [
        (ALPHA_SUITE, ("test_alpha_fails",)),
        (BRAVO_SUITE, ("test_bravo_fails",)),
        (None, ("empty",)),
    ],
    ids=["alpha-suite-red-log", "bravo-suite-red-log", "no-red-log-on-disk"],
)
def test_merge_artifact_red_output_section_carries_the_red_run_on_disk(
    tmp_path, suite, expected
):
    _, artifact = _merge(tmp_path, {"test_a.py": TEST_A_OTHER}, suite=suite)
    assert _red_section_marks(artifact) == expected


SPEC_PATH = "gauntlet/specs/approved/" + SLUG + ".txt"

BODY_V2 = BODY_NEW.replace(
    "reports two for two widgets and three for three",
    "reports four for four widgets and five for five",
)
BLOCK_V2 = _block(BODY_V2)
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
    "target,expected",
    [("first", BLOCK_NEW), ("second", BLOCK_V2)],
    ids=["restore-the-first-revision", "restore-the-second-revision"],
)
def test_restore_puts_the_blocks_bytes_at_the_named_revision_back_on_disk(
    tmp_path, target, expected
):
    _, repo, _ = _restore(tmp_path, target)
    assert (repo / SPEC_PATH).read_text() == expected


@pytest.mark.parametrize(
    "target,expected",
    [("first", BLOCK_NEW), ("second", BLOCK_V2)],
    ids=["restore-the-first-revision", "restore-the-second-revision"],
)
def test_restore_prints_one_line_naming_the_path_it_wrote_and_the_revision(
    tmp_path, target, expected
):
    lines, repo, rev = _restore(tmp_path, target)
    assert _printed(lines, repo) == (1, rev, expected)


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


def _review(tmp_path, rounds, args):
    """Run `pair.sh review` over a reviews directory holding `rounds`."""
    repo = _repo(tmp_path, _block(BODY_NEW), REVIEWER)
    reviews = repo / "gauntlet" / "reviews"
    for name in rounds:
        (reviews / name).write_text("round\n")
    return _pair(repo, "review", *args)


@pytest.mark.parametrize(
    "rounds,args,expected",
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
    lines = _pair(repo, "review", SLUG)
    assert lines == ["REVIEW gauntlet/reviews/demo.1.txt"]
    assert (repo / "gauntlet" / "reviews").is_dir()
