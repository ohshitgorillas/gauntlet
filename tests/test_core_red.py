# Copyright 2026 oh shit, gorillas!
"""Approved starting verdicts and bindings from the M1 records design."""

from dataclasses import replace

import pytest

from gauntlet.core import records, red

_NEW = "tests/test_new.py::test_added"
_OLD = ("tests/test_old.py::test_kept[a]", "tests/test_old.py::test_kept[b]")
_SPEC = records.Spec(
    (
        records.SpecLine(
            "S1", "New behavior", "Fails before build", records.TestStart.RED
        ),
        records.SpecLine(
            "S2", "Kept behavior", "Passes unchanged", records.TestStart.GREEN, _OLD
        ),
    ),
    (),
)
_BINDINGS = (records.TestBinding("S1", (_NEW,)), records.TestBinding("S2", _OLD))
_JUDGMENT = records.RedJudgment(
    (
        records.RedLine("S1", records.RedVerdict.RED, (_NEW,)),
        records.RedLine("S2", records.RedVerdict.GREEN, _OLD),
    )
)
_BASELINES = (
    records.TestSnapshot(
        _OLD[0],
        "@parametrize('value', ['a', 'b'])\ndef test_kept(value):\n    assert value\n",
    ),
    records.TestSnapshot(
        _OLD[1],
        "@parametrize('value', ['a', 'b'])\ndef test_kept(value):\n    assert value\n",
    ),
)


# Requiring every line to start RED rejects an approved mixed starting run.
def test_mixed_starting_verdicts_match_approved_marks() -> None:
    """Accept explicit RED and GREEN without changing the approved spec."""
    assert red.red_problems(_SPEC, _JUDGMENT, _BINDINGS) == ()
    assert (
        red.binding_problems(_SPEC, records.TestAnswer(_BINDINGS, ()), _BASELINES) == ()
    )


# Treating record order as identity rejects equivalent sets of approved ids.
def test_rows_and_test_ids_may_be_reordered() -> None:
    """Match line and test identities independently of sequence order."""
    bindings = (_BINDINGS[1], _BINDINGS[0])
    judgment = records.RedJudgment(
        (replace(_JUDGMENT.lines[1], tests=tuple(reversed(_OLD))), _JUDGMENT.lines[0])
    )
    answer = records.TestAnswer(
        (replace(_BINDINGS[1], ids=tuple(reversed(_OLD))), _BINDINGS[0]), ()
    )
    assert red.red_problems(_SPEC, judgment, list(bindings)) == ()
    assert red.binding_problems(_SPEC, answer, list(reversed(_BASELINES))) == ()


# Inferring a baseline requirement for new behavior rejects a valid all-RED spec.
def test_all_red_needs_no_preserved_source() -> None:
    """Accept new tests with no existing-test baseline."""
    spec = replace(_SPEC, lines=(_SPEC.lines[0],))
    bindings = (_BINDINGS[0],)
    assert (
        red.red_problems(spec, records.RedJudgment((_JUDGMENT.lines[0],)), bindings)
        == ()
    )
    assert red.binding_problems(spec, records.TestAnswer(bindings, ()), ()) == ()


# Accepting any non-error verdict permits a verdict contrary to approval.
@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("verdict", tuple(records.RedVerdict))
def test_every_wrong_starting_verdict_fails(
    index: int, verdict: records.RedVerdict
) -> None:
    """Reject opposite marks, ERROR, INVALID and inability for each line."""
    rows = list(_JUDGMENT.lines)
    rows[index] = replace(rows[index], verdict=verdict)
    result = red.red_problems(_SPEC, records.RedJudgment(tuple(rows)), _BINDINGS)
    if verdict == _JUDGMENT.lines[index].verdict:
        assert result == ()
    else:
        assert result


# Collapsing or ignoring rows lets missing, duplicate and unknown rulings pass.
@pytest.mark.parametrize(
    "rows",
    [
        (),
        _JUDGMENT.lines[:1],
        _JUDGMENT.lines[1:],
        (*_JUDGMENT.lines, _JUDGMENT.lines[0]),
        (*_JUDGMENT.lines, replace(_JUDGMENT.lines[0], line="S3")),
        (replace(_JUDGMENT.lines[0], line=" S1"), _JUDGMENT.lines[1]),
    ],
)
def test_judgment_requires_exactly_one_row_per_line(
    rows: tuple[records.RedLine, ...],
) -> None:
    """Require exact approved line identities, including absent rows."""
    assert red.red_problems(_SPEC, records.RedJudgment(rows), _BINDINGS)


# Checking verdicts without exact ids accepts evidence for other tests.
@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("ids", [(), ("other",), (_NEW, _NEW), (*_OLD, "extra")])
def test_judgment_requires_exact_bound_tests(index: int, ids: tuple[str, ...]) -> None:
    """Reject absent, substituted, duplicated and added juror test ids."""
    rows = list(_JUDGMENT.lines)
    rows[index] = replace(rows[index], tests=ids)
    assert red.red_problems(_SPEC, records.RedJudgment(tuple(rows)), _BINDINGS)


# Omitting binding validation allows a ruling to stand without unique evidence.
@pytest.mark.parametrize(
    "bindings",
    [
        (),
        (_BINDINGS[0],),
        (_BINDINGS[1],),
        (*_BINDINGS, _BINDINGS[0]),
        (*_BINDINGS, records.TestBinding("S3", ("unknown",))),
        (replace(_BINDINGS[0], line=" S1"), _BINDINGS[1]),
        (replace(_BINDINGS[0], ids=()), _BINDINGS[1]),
        (replace(_BINDINGS[0], ids=(_NEW, _NEW)), _BINDINGS[1]),
        (_BINDINGS[0], replace(_BINDINGS[1], ids=(_OLD[0], _OLD[0]))),
    ],
)
def test_bindings_require_complete_unique_line_and_test_ids(
    bindings: tuple[records.TestBinding, ...],
) -> None:
    """Reject missing, unknown, duplicate or empty bindings at both boundaries."""
    assert red.binding_problems(_SPEC, records.TestAnswer(bindings, ()), _BASELINES)
    assert red.red_problems(_SPEC, _JUDGMENT, bindings)


# Inferring new GREEN ids from the supplied binding changes owner approval.
@pytest.mark.parametrize(
    "ids",
    [
        (),
        (_OLD[0],),
        ("replacement", _OLD[1]),
        (*_OLD, "new"),
        (" " + _OLD[0], _OLD[1]),
    ],
)
def test_green_bindings_preserve_exact_approved_ids(ids: tuple[str, ...]) -> None:
    """Reject removal, substitution, addition and normalization of kept ids."""
    bindings = (_BINDINGS[0], replace(_BINDINGS[1], ids=ids))
    rows = (_JUDGMENT.lines[0], replace(_JUDGMENT.lines[1], tests=ids))
    assert red.binding_problems(_SPEC, records.TestAnswer(bindings, ()), _BASELINES)
    assert red.red_problems(_SPEC, records.RedJudgment(rows), bindings)


# Ignoring untestable declarations can falsely certify complete coverage.
@pytest.mark.parametrize("untestable", [("S1",), ("S2",), ("S3",), ("S1", "S1")])
def test_untestable_lines_always_fail(untestable: tuple[str, ...]) -> None:
    """Reject claimed, preserved, unknown and duplicate untestable ids."""
    assert red.binding_problems(
        _SPEC, records.TestAnswer(_BINDINGS, untestable), _BASELINES
    )


# Treating a nonempty baseline collection as sufficient misses incomplete sources.
@pytest.mark.parametrize(
    "baselines",
    [
        (),
        (_BASELINES[0],),
        (_BASELINES[1],),
        (*_BASELINES, _BASELINES[0]),
        (*_BASELINES, replace(_BASELINES[0], source="different source")),
        (*_BASELINES, records.TestSnapshot("unknown", "def test_other(): pass")),
        (*_BASELINES, records.TestSnapshot(_NEW, "def test_added(): pass")),
        (replace(_BASELINES[0], test_id="replacement"), _BASELINES[1]),
    ],
)
def test_baselines_cover_exactly_the_preserved_ids_once(
    baselines: tuple[records.TestSnapshot, ...],
) -> None:
    """Require one snapshot per approved preserved id with no extra ids."""
    assert red.binding_problems(_SPEC, records.TestAnswer(_BINDINGS, ()), baselines)


# Accepting whitespace as source certifies a baseline with no preserved definition.
@pytest.mark.parametrize("source", ["", " ", "\t\n"])
@pytest.mark.parametrize("index", [0, 1])
def test_each_baseline_source_is_nonblank(index: int, source: str) -> None:
    """Reject blank sources for either preserved test."""
    baselines = list(_BASELINES)
    baselines[index] = replace(baselines[index], source=source)
    assert red.binding_problems(_SPEC, records.TestAnswer(_BINDINGS, ()), baselines)


# Inferring a missing or invalid mark from the observed verdict bypasses approval.
@pytest.mark.parametrize("mark", [None, "", "RED", "unknown", 0])
@pytest.mark.parametrize("index", [0, 1])
def test_start_marks_are_explicit_and_valid(index: int, mark: object) -> None:
    """Reject absent and invalid marks even when verdicts and ids otherwise match."""
    lines = list(_SPEC.lines)
    lines[index] = replace(lines[index])
    object.__setattr__(lines[index], "start", mark)
    spec = replace(_SPEC, lines=tuple(lines))
    assert red.red_problems(spec, _JUDGMENT, _BINDINGS)
    assert red.binding_problems(spec, records.TestAnswer(_BINDINGS, ()), _BASELINES)


# Deduplicating or inventing approved GREEN ids accepts an invalid starting mark.
@pytest.mark.parametrize("ids", [(), (*_OLD, _OLD[0])])
def test_green_mark_requires_nonempty_unique_approved_ids(ids: tuple[str, ...]) -> None:
    """Require GREEN's existing id declaration to be nonempty and unique."""
    spec = replace(_SPEC, lines=(_SPEC.lines[0], replace(_SPEC.lines[1], tests=ids)))
    assert red.red_problems(spec, _JUDGMENT, _BINDINGS)
    assert red.binding_problems(spec, records.TestAnswer(_BINDINGS, ()), _BASELINES)
