"""Behavior tests for the citation resolver CLI."""

import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "cite.py"

FIXTURES = "tests/support/fixtures/cite"
ALPHA = FIXTURES + "/alpha.txt"
BETA = FIXTURES + "/beta.txt"
ABSENT = FIXTURES + "/nowhere.txt"
WORKTREE_NAME = "w1"

STATUSES = ("MISSING", "RANGE", "AMBIGUOUS", "ORPHAN", "QUOTE", "CROSS-REPO")


def _statuses_in(row):
    return [token for token in STATUSES if re.search(r"(?<![A-Z-])" + token + r"(?![A-Z-])", row)]


def _check(tmp_path, body):
    doc = tmp_path / "plan.md"
    doc.write_text(body)
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(doc)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    return done


def _outcome(done):
    """(exit code, status tokens over every row of stdout)."""
    rows = done.stdout.splitlines()
    return (done.returncode, [t for row in rows for t in _statuses_in(row)])


def _outcome_naming(done, text):
    """(exit code, status tokens over the rows that carry `text`)."""
    rows = [row for row in done.stdout.splitlines() if text in row]
    return (done.returncode, [t for row in rows for t in _statuses_in(row)])


def _quote_outcome(done, citation):
    """(exit code, whether a row naming `citation` names QUOTE)."""
    rows = [row for row in done.stdout.splitlines() if citation in row]
    return (done.returncode, any("QUOTE" in _statuses_in(row) for row in rows))


def _fix(doc):
    """Run --fix over `doc` in place; give the document it leaves behind."""
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", str(doc)],
        cwd=doc.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    return doc.read_text()


def _inherited(done, candidates):
    """Per INHERITED-FROM row, which of `candidates` that row names."""
    return [
        [path for path in candidates if path in row]
        for row in done.stdout.splitlines()
        if re.search(r"(?<![A-Z-])INHERITED-FROM(?![A-Z-])", row)
    ]


# 1
@pytest.mark.parametrize(
    ("citation", "expected"),
    [
        (ALPHA + ":2", (0, [])),
        (ABSENT + ":2", (1, ["MISSING"])),
    ],
    ids=["path-in-checkout", "path-absent-from-checkout"],
)
def test_a_path_the_checkout_does_not_have_is_reported_missing(tmp_path, citation, expected):
    done = _check(tmp_path, "The gate sits at `" + citation + "` today.\n")
    assert _outcome_naming(done, citation) == expected


# 2
@pytest.mark.parametrize(
    ("citation", "expected"),
    [
        (ALPHA + ":2-3", (0, [])),
        (ALPHA + ":2-4", (1, ["RANGE"])),
    ],
    ids=["range-ends-on-last-line", "range-ends-past-last-line"],
)
def test_a_range_running_off_the_end_of_the_file_is_reported(tmp_path, citation, expected):
    done = _check(tmp_path, "The construct spans `" + citation + "` there.\n")
    assert _outcome(done) == expected


# 3
def _build_root(root, solo, dup):
    """A root carrying the script, one `solo` file and two copies of `dup`."""
    (root / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts" / "cite.py")
    shutil.copy(SCRIPT.with_name("cite_tree.py"), root / "scripts" / "cite_tree.py")
    (root / "data" / "x").mkdir(parents=True)
    (root / "data" / "y").mkdir(parents=True)
    (root / "data" / solo).write_text("the only copy of this line\n")
    (root / "data" / "x" / dup).write_text("the first copy of this line\n")
    (root / "data" / "y" / dup).write_text("the second copy of this line\n")


def _check_from(root, body):
    """Run the copy of the script at `root` over a document written at `root`."""
    (root / "plan.md").write_text(body)
    done = subprocess.run(
        [sys.executable, str(root / "scripts" / "cite.py"), "--check", "plan.md"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    return done


def _paths_named(row, basename, root):
    """Paths naming `basename` in `row`, each relative to `root` where beneath it."""
    prefix = str(root) + "/"
    named = []
    for token in re.split(r"[\s,]+", row.strip()):
        token = token.strip("`")
        if "/" in token and token.endswith(basename):
            named.append(token[len(prefix) :] if token.startswith(prefix) else token)
    return sorted(named)


def _rows_for(done, basename, root):
    """Per row citing `basename`, its status tokens and the paths it names."""
    return [
        (_statuses_in(row), _paths_named(row, basename, root))
        for row in done.stdout.splitlines()
        if basename + ":1" in row
    ]


@pytest.mark.parametrize(
    "nested",
    [False, True],
    ids=["ordinary-root", "root-under-claude-worktrees"],
)
def test_a_root_under_claude_worktrees_resolves_the_same_rows_as_an_ordinary_one(tmp_path, nested):
    tag = uuid.uuid4().hex[:8]
    solo, dup = "zq" + tag + "solo.txt", "zq" + tag + "dup.txt"
    outer = tmp_path / "checkout"
    inner = outer / ".claude" / "worktrees" / WORKTREE_NAME
    _build_root(outer, solo, dup)
    _build_root(inner, solo, dup)
    root = inner if nested else outer

    done = _check_from(root, "Solo at `" + solo + ":1` and dup at `" + dup + ":1`.\n")

    assert (_rows_for(done, solo, root), _rows_for(done, dup, root)) == (
        [],
        [(["AMBIGUOUS"], ["data/x/" + dup, "data/y/" + dup])],
    )


# 4
@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("The rule is at `" + ALPHA + ":1`, and the guard at `:2`.\n", (0, [])),
        ("The guard sits at `:2` in that file.\n", (1, ["ORPHAN"])),
    ],
    ids=["bare-number-after-a-full-citation", "bare-number-with-no-antecedent"],
)
def test_a_bare_number_with_nothing_to_continue_is_reported_orphan(tmp_path, body, expected):
    done = _check(tmp_path, body)
    assert _outcome(done) == expected


# 5
@pytest.mark.parametrize(
    "bare",
    [":2", ":9"],
    ids=["continuation-resolves", "continuation-past-end-of-file"],
)
def test_a_continuation_names_the_file_it_inherited_whether_or_not_it_resolves(tmp_path, bare):
    body = "The rule is at `" + ALPHA + ":1`, and the guard at `" + bare + "`.\n"
    done = _check(tmp_path, body)
    assert _inherited(done, (ALPHA,)) == [[ALPHA]]


# 6
@pytest.mark.parametrize(
    ("first", "second"),
    [(ALPHA, BETA), (BETA, ALPHA)],
    ids=["alpha-then-beta", "beta-then-alpha"],
)
def test_a_continuation_inherits_the_nearest_preceding_citation(tmp_path, first, second):
    body = "First `" + first + ":1`, then `" + second + ":1`, then `:2` after it.\n"
    done = _check(tmp_path, body)
    assert _inherited(done, (ALPHA, BETA)) == [[second]]


# 9
@pytest.mark.parametrize(
    ("citation", "expected_code"),
    [(ALPHA + ":1", 0), (ALPHA + ":9", 1)],
    ids=["unquoted-citation-in-range", "unquoted-citation-past-end-of-file"],
)
def test_a_citation_with_no_anchor_is_judged_by_its_number_not_the_prose(
    tmp_path, citation, expected_code
):
    body = "The resolver walks the frozen table at `" + citation + "` before the gate runs.\n"
    done = _check(tmp_path, body)
    assert done.returncode == expected_code


# anchor block, 1
def test_the_anchor_is_matched_against_the_cited_line_not_the_whole_file(tmp_path):
    target = tmp_path / "target.txt"
    citation = str(target) + ":2"
    body = "The rule holds `" + citation + '`, "the anchored line" is what it carries.\n'

    target.write_text("first line here\nthe anchored line\nthird line here\n")
    anchor_on_the_cited_line = _quote_outcome(_check(tmp_path, body), citation)

    target.write_text("first line here\nsomething else here\nthe anchored line\n")
    anchor_one_line_away = _quote_outcome(_check(tmp_path, body), citation)

    assert (anchor_on_the_cited_line, anchor_one_line_away) == (
        (0, False),
        (1, True),
    )


# anchor block, 2
def test_the_anchor_may_sit_on_any_line_of_the_cited_span(tmp_path):
    target = tmp_path / "target.txt"
    citation = str(target) + ":2-3"
    body = "The construct spans `" + citation + '`, "the anchored line" is what it carries.\n'

    target.write_text("one here\ntwo here\nthe anchored line\nfour here\nfive here\n")
    anchor_on_the_spans_second_line = _quote_outcome(_check(tmp_path, body), citation)

    target.write_text("one here\ntwo here\nthree here\nfour here\nthe anchored line\n")
    anchor_outside_the_span = _quote_outcome(_check(tmp_path, body), citation)

    assert (anchor_on_the_spans_second_line, anchor_outside_the_span) == (
        (0, False),
        (1, True),
    )


# anchor block, 3
def test_fix_fills_the_number_only_where_the_anchor_matches_one_line(tmp_path):
    target = tmp_path / "target.txt"
    doc = tmp_path / "plan.md"
    handed_in = "The rule holds `" + str(target) + ':1`, "the target line" is what it carries.\n'
    filled = "The rule holds `" + str(target) + ':4`, "the target line" is what it carries.\n'

    target.write_text("one here\ntwo here\nthree here\nthe target line\nfive here\nsix here\n")
    doc.write_text(handed_in)
    after_a_unique_anchor = _fix(doc)

    target.write_text(
        "one here\ntwo here\nthree here\nthe target line\nfive here\n" "the target line\n"
    )
    doc.write_text(handed_in)
    after_a_repeated_anchor = _fix(doc)

    assert (after_a_unique_anchor, after_a_repeated_anchor) == (
        filled,
        handed_in,
    )


# 10
@pytest.mark.parametrize(
    ("outside_exists", "expected"),
    [(True, (0, ["CROSS-REPO"])), (False, (1, ["MISSING"]))],
    ids=["outside-path-exists", "outside-path-absent"],
)
def test_an_absolute_path_outside_the_checkout_resolves_instead_of_missing(
    tmp_path, outside_exists, expected
):
    outside = tmp_path / "elsewhere" / "vendor_note.txt"
    outside.parent.mkdir()
    if outside_exists:
        outside.write_text("vendor note line one\nvendor note line two\n")
    body = "The upstream rule is at `" + str(outside) + ":1` over there.\n"
    done = _check(tmp_path, body)
    assert _outcome_naming(done, str(outside)) == expected


# 11
@pytest.mark.parametrize(
    ("opener", "closer", "expected_code"),
    [("", "", 0), ("`", "`", 1)],
    ids=["bare-prose-number", "same-text-backticked"],
)
def test_only_a_backticked_path_and_number_is_read_as_a_citation(
    tmp_path, opener, closer, expected_code
):
    body = (
        "The rule is at `"
        + ALPHA
        + ":1` and the old draft said "
        + opener
        + ALPHA
        + ":99"
        + closer
        + " once.\n"
    )
    done = _check(tmp_path, body)
    assert done.returncode == expected_code
