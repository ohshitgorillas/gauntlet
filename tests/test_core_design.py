# Copyright 2026 oh shit, gorillas!
"""Design checks from structure-first-design.md, Modules: core/design.py."""

from dataclasses import replace
from typing import TypedDict

import pytest

from gauntlet.core.design import (
    Choice,
    Design,
    Home,
    Module,
    Step,
    design_problems,
    home_of,
    uncovered,
)
from gauntlet.core.verdicts import Anchor
from tests.support.answers import design as d


class _DesignFields(TypedDict):
    modules: tuple[Module, ...]
    homes: tuple[Home, ...]
    order: tuple[Step, ...]
    choices: tuple[Choice, ...]


_D: _DesignFields = {
    "modules": (Module("pkg/home.py", "Run processes", (), ()),),
    "homes": (Home("process running", "pkg/home.py", "running a process"),),
    "order": (Step("build", ("pkg/home.py",), "core-builder"),),
    "choices": (),
}


def test_valid_design_has_no_problems() -> None:
    """Breaks when a valid design is rejected, including the five-item limits."""
    design = d(**_D)
    choice = Choice("runner", "one home", "local runners", "migration work")
    design = replace(
        design,
        order=(Step("build", ("a", "b", "c", "d", "pkg/home.py"), "builder"),),
        choices=(choice,) * 5,
    )
    assert design_problems(design) == ()


@pytest.mark.parametrize("count", [2, 3])
def test_duplicate_concern_is_reported_once(count: int) -> None:
    """Breaks when a repeated concern is accepted or reported per home."""
    design = d(**_D)
    design = replace(design, homes=design.homes * count)
    assert design_problems(design) == (f"concern process running: {count} homes",)


def test_home_must_name_a_design_module() -> None:
    """Breaks when an unknown home module is accepted."""
    design = replace(d(**_D), homes=(Home("running", "absent.py", "copies"),))
    assert design_problems(design) == ("home running: module absent.py not in design",)


@pytest.mark.parametrize("count", [2, 3])
def test_duplicate_module_path_is_reported_once(count: int) -> None:
    """Breaks when module definitions sharing a path are accepted or overcounted."""
    design = d(**_D)
    design = replace(design, modules=design.modules * count)
    assert design_problems(design) == (f"module pkg/home.py: defined {count} times",)


def test_module_needs_a_step_writing_its_exact_path() -> None:
    """Breaks when a directory or a filename prefix counts as writing a module."""
    design = replace(
        d(**_D), order=(Step("build", ("pkg", "pkg/home.py.old"), "builder"),)
    )
    assert design_problems(design) == ("module pkg/home.py: no step writes it",)


def test_step_cannot_write_six_paths() -> None:
    """Breaks when the five-path bound is raised or the reported count is wrong."""
    design = replace(
        d(**_D),
        order=(Step("build", ("pkg/home.py", "a", "b", "c", "d", "e"), "builder"),),
    )
    assert design_problems(design) == ("step build: 6 paths, at most five",)


@pytest.mark.parametrize("blank", ["", " \t\n"])
def test_step_needs_a_nonblank_implementer(blank: str) -> None:
    """Breaks when an empty or whitespace-only implementer is accepted."""
    design = replace(d(**_D), order=(Step("build", ("pkg/home.py",), blank),))
    assert design_problems(design) == ("step build: no implementer",)


@pytest.mark.parametrize("count", [2, 3])
def test_duplicate_step_name_is_reported_once(count: int) -> None:
    """Breaks when duplicate step names are accepted or reported repeatedly."""
    design = d(**_D)
    design = replace(design, order=design.order * count)
    assert design_problems(design) == (f"step build: named {count} times",)


def test_port_before_first_home_write_is_one_problem_per_triple() -> None:
    """Breaks when later home writes or repeated anchor lines multiply a problem."""
    design = d(**_D)
    module = replace(
        design.modules[0],
        replaces=(Anchor("old.py", 1), Anchor("old.py", 9), Anchor("old.py", 1)),
    )
    design = replace(
        design,
        modules=(module,),
        order=(
            Step("port", ("old.py", "old.py"), "builder"),
            Step("build", ("pkg/home.py",), "builder"),
            Step("amend", ("pkg/home.py",), "builder"),
        ),
    )
    assert design_problems(design) == (
        "step port: writes old.py before step build writes pkg/home.py",
    )


@pytest.mark.parametrize("port_position", [0, 1])
def test_port_with_or_after_home_write_is_valid(port_position: int) -> None:
    """Breaks when the replacing module must be written strictly before a port."""
    design = d(**_D)
    module = replace(design.modules[0], replaces=(Anchor("old.py", 1),))
    paths = ("pkg/home.py", "old.py") if port_position == 0 else ("pkg/home.py",)
    order: tuple[Step, ...] = (Step("build", paths, "builder"),)
    if port_position == 1:
        order += (Step("port", ("old.py",), "builder"),)
    assert design_problems(replace(design, modules=(module,), order=order)) == ()


def test_choices_cannot_exceed_five() -> None:
    """Breaks when six complete choices are accepted."""
    choice = Choice("runner", "one home", "local runners", "migration work")
    assert design_problems(replace(d(**_D), choices=(choice,) * 6)) == (
        "choices: 6, at most five",
    )


@pytest.mark.parametrize("field", ["recommend", "alternative", "cost"])
@pytest.mark.parametrize("blank", ["", " \t\n"])
def test_choice_needs_each_nonblank_field(field: str, blank: str) -> None:
    """Breaks when any required choice field accepts blanks or names another field."""
    choice = Choice("runner", "one home", "local runners", "migration work")
    if field == "recommend":
        choice = replace(choice, recommend=blank)
    elif field == "alternative":
        choice = replace(choice, alternative=blank)
    else:
        choice = replace(choice, cost=blank)
    assert design_problems(replace(d(**_D), choices=(choice,))) == (
        f"choice runner: no {field}",
    )


def test_two_problems_keep_check_order() -> None:
    """Breaks when checking choices before modules, or stopping at the first defect."""
    design = replace(
        d(**_D),
        order=(),
        choices=(Choice("runner", "one home", "local runners", ""),),
    )
    assert design_problems(design) == (
        "module pkg/home.py: no step writes it",
        "choice runner: no cost",
    )


def test_all_problem_kinds_keep_documented_check_order() -> None:
    """Breaks when any validation kind moves ahead of an earlier check."""
    module = Module("home.py", "One home", (), (Anchor("old.py", 1),))
    choice = Choice("runner", "", "", "")
    choices: tuple[Choice, ...] = (choice,)
    choices += (Choice("complete", "yes", "no", "work"),) * 5
    design = Design(
        modules=(module, module, Module("unwritten.py", "Unused", (), ())),
        homes=(Home("running", "missing.py", "copies"),) * 2,
        order=(
            Step("port", ("old.py", "a", "b", "c", "d", "e"), ""),
            Step("build", ("home.py",), "builder"),
            Step("build", (), "builder"),
        ),
        choices=choices,
    )
    assert design_problems(design) == (
        "concern running: 2 homes",
        "home running: module missing.py not in design",
        "home running: module missing.py not in design",
        "module home.py: defined 2 times",
        "module unwritten.py: no step writes it",
        "step port: 6 paths, at most five",
        "step port: no implementer",
        "step build: named 2 times",
        "step port: writes old.py before step build writes home.py",
        "choices: 6, at most five",
        "choice runner: no recommend",
        "choice runner: no alternative",
        "choice runner: no cost",
    )


def test_home_lookup_uses_first_exact_concern() -> None:
    """Breaks when lookup returns a prefix match or the last matching home."""
    first = Home("running", "first.py", "copies")
    design = replace(
        d(**_D),
        homes=(
            Home("running extra", "prefix.py", "copies"),
            first,
            Home("running", "last.py", "copies"),
        ),
    )
    assert home_of(design, "running") == first


@pytest.mark.parametrize("homes", [(), (Home("Running", "home.py", "copies"),)])
def test_home_lookup_returns_none_for_absent_concern(homes: tuple[Home, ...]) -> None:
    """Breaks when an absent concern gets a home, including a case-only match."""
    assert home_of(replace(d(**_D), homes=homes), "running") is None


@pytest.mark.parametrize(
    ("replaced", "paths", "done", "expected"),
    [
        (False, (), (), (Anchor("old.py", 1),)),
        (False, ("old.py",), (), (Anchor("old.py", 1),)),
        (False, ("old.py",), ("port",), (Anchor("old.py", 1),)),
        (True, (), (), (Anchor("old.py", 1),)),
        (True, ("old.py.old",), (), (Anchor("old.py", 1),)),
        (True, ("old.py",), (), ()),
        (True, ("old.py",), ("other",), ()),
        (True, ("old.py",), ("port",), (Anchor("old.py", 1),)),
    ],
)
def test_coverage_needs_replacement_and_pending_path(
    *,
    replaced: bool,
    paths: tuple[str, ...],
    done: tuple[str, ...],
    expected: tuple[Anchor, ...],
) -> None:
    """Breaks when either the replacement or pending exact-path write is omitted."""
    copy = Anchor("old.py", 1)
    module = Module("home.py", "One home", (), (copy,) if replaced else ())
    design = Design((module,), (), (Step("port", paths, "builder"),), ())
    assert uncovered(design, (copy,), done) == expected


def test_uncovered_deduplicates_exact_copies_and_keeps_input_order() -> None:
    """Breaks when copies repeat, sort, or collapse different lines of one path."""
    first = Anchor("z.py", 8)
    second = Anchor("a.py", 1)
    third = Anchor("z.py", 9)
    assert uncovered(Design((), (), (), ()), (first, second, first, third), ()) == (
        first,
        second,
        third,
    )


def test_replacement_matches_anchor_not_just_path() -> None:
    """Breaks when naming one copy covers a different line in the same file."""
    copy = Anchor("old.py", 1)
    other = Anchor("old.py", 2)
    module = Module("home.py", "One home", (), (copy,))
    design = Design((module,), (), (Step("port", ("old.py",), "builder"),), ())
    assert uncovered(design, (copy, other), ()) == (other,)


def test_any_pending_step_and_any_replacing_module_can_cover() -> None:
    """Breaks when only the first module or first path-writing step is checked."""
    copy = Anchor("old.py", 1)
    design = Design(
        (Module("a.py", "Other", (), ()), Module("b.py", "Home", (), (copy,))),
        (),
        (Step("done", ("old.py",), "builder"), Step("later", ("old.py",), "builder")),
        (),
    )
    assert uncovered(design, (copy,), ("done",)) == ()


def test_every_done_step_leaves_every_copy_uncovered() -> None:
    """Breaks when a completed port hides a copy still found by REVIEW."""
    copies = (Anchor("old.py", 1), Anchor("other.py", 4))
    design = Design(
        (Module("home.py", "Home", (), copies),),
        (),
        (Step("port", ("old.py", "other.py"), "builder"),),
        (),
    )
    assert uncovered(design, copies, {"port"}) == copies


def test_no_copies_leaves_nothing_uncovered() -> None:
    """Breaks when the design invents copies absent from the supplied survey."""
    assert uncovered(d(**_D), (), ()) == ()
