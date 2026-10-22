# Copyright 2026 oh shit, gorillas!
"""Frozen record payloads from structure-first-design.md, Modules."""

from dataclasses import FrozenInstanceError

import pytest

from gauntlet.core.causes import Cause, DesignChange, FixStep
from gauntlet.core.design import Choice, Design, Home, Module, Step, Stub
from gauntlet.core.verdicts import (
    Anchor,
    Candidate,
    Category,
    CoreMissing,
    Finding,
    Survey,
)


def _frozen_cases() -> tuple[tuple[object, str], ...]:
    anchor = Anchor("callers/worker.py", 17)
    finding = Finding(
        anchor, "Wrong exit.", Category.DEFECT, blocking=True, concern=None
    )
    candidate = Candidate("process running", "One policy.", "Porting risk.", ())
    cause = Cause("exit-policy", "Exit status is interpreted twice.", None, (finding,))
    records: tuple[tuple[object, tuple[str, ...]], ...] = (
        (anchor, ("path", "line")),
        (finding, ("anchor", "scenario", "category", "blocking", "concern", "also")),
        (candidate, ("concern", "payoff", "risk", "keeps", "why")),
        (
            CoreMissing("One policy is needed.", candidate, (anchor,)),
            ("need", "candidate", "also"),
        ),
        (
            Survey((finding,), (candidate,), ("The codec has one home.",)),
            ("findings", "candidates", "sound"),
        ),
        (
            Stub("Clock.now", "def now(self) -> float: raise NotImplementedError"),
            ("name", "text"),
        ),
        (
            Module("pkg/runner.py", "Run processes.", (), (anchor,)),
            ("path", "job", "stubs", "replaces"),
        ),
        (
            Home("process running", "pkg/runner.py", "Process starts elsewhere."),
            ("concern", "module", "forbids"),
        ),
        (
            Step("build home", ("pkg/runner.py",), "seam-builder"),
            ("name", "paths", "implementer"),
        ),
        (
            Choice("One home?", "Yes.", "Keep copies.", "Porting work."),
            ("question", "recommend", "alternative", "cost"),
        ),
        (Design((), (), (), ()), ("modules", "homes", "order", "choices")),
        (cause, ("id", "claim", "concern", "findings")),
        (
            FixStep(cause, "seam-builder", ("pkg/runner.py",)),
            ("cause", "implementer", "paths"),
        ),
        (DesignChange(cause), ("cause",)),
    )
    return tuple((record, field) for record, fields in records for field in fields)


@pytest.mark.parametrize(("record", "field"), _frozen_cases())
def test_record_fields_reject_assignment_and_deletion(
    record: object, field: str
) -> None:
    """Breaks when any documented record field permits assignment or deletion."""
    with pytest.raises(FrozenInstanceError):
        setattr(record, field, object())
    with pytest.raises(FrozenInstanceError):
        delattr(record, field)


@pytest.mark.parametrize("line", [1, 17])
def test_anchor_preserves_its_tree_location_and_is_frozen(line: int) -> None:
    """Breaks when anchors lose their path or line, or permit mutation."""
    anchor = Anchor("callers/worker.py", line)
    assert (anchor.path, anchor.line) == ("callers/worker.py", line)


def test_finding_preserves_every_instance_and_is_frozen() -> None:
    """Breaks when findings lose review payloads or permit mutation."""
    anchor = Anchor("callers/worker.py", 17)
    also = (Anchor("callers/batch.py", 23), Anchor("callers/web.py", 8))
    finding = Finding(
        anchor,
        "The copied process policy can diverge.",
        Category.COPY,
        blocking=True,
        concern="process running",
        also=also,
    )
    default_finding = Finding(
        anchor, "Wrong result.", Category.DEFECT, blocking=False, concern=None
    )
    assert (
        finding.anchor,
        finding.scenario,
        finding.category,
        finding.blocking is True,
        finding.concern,
        finding.also,
        default_finding.also,
    ) == (
        anchor,
        "The copied process policy can diverge.",
        Category.COPY,
        True,
        "process running",
        also,
        (),
    )


def test_candidate_preserves_its_offer_and_keeps_and_is_frozen() -> None:
    """Breaks when offers lose preserved behaviors or permit mutation."""
    keeps = ("Signal exits remain distinguishable.", "Empty output stays empty.")
    candidate = Candidate(
        "process running",
        "One policy serves every caller.",
        "Porting could change exit reporting.",
        keeps,
        "The caller cannot report failure correctly without the policy.",
    )
    optional = Candidate("optional", "One home.", "Porting work.", ())
    assert (
        candidate.concern,
        candidate.payoff,
        candidate.risk,
        candidate.keeps,
        candidate.why,
        optional.why is None,
    ) == (
        "process running",
        "One policy serves every caller.",
        "Porting could change exit reporting.",
        keeps,
        "The caller cannot report failure correctly without the policy.",
        True,
    )


def test_core_missing_preserves_the_need_and_callers_and_is_frozen() -> None:
    """Breaks when missing-core reports lose their need or permit mutation."""
    candidate = Candidate("process running", "One policy.", "Porting risk.", ())
    copies = (Anchor("callers/batch.py", 23), Anchor("callers/web.py", 8))
    missing = CoreMissing(
        "The step needs a shared policy for signal exits.", candidate, copies
    )
    assert (missing.need, missing.candidate, missing.also) == (
        "The step needs a shared policy for signal exits.",
        candidate,
        copies,
    )


def test_survey_preserves_ranked_candidates_and_sound_lines_and_is_frozen() -> None:
    """Breaks when surveys reorder or lose their payloads, or permit mutation."""
    finding = Finding(
        Anchor("callers/worker.py", 17),
        "The process policy is copied.",
        Category.COPY,
        blocking=True,
        concern="process running",
        also=(Anchor("callers/web.py", 8),),
    )
    candidates = (
        Candidate("process running", "Large payoff.", "Small risk.", ()),
        Candidate("parsing", "Smaller payoff.", "Larger risk.", ()),
    )
    sound = ("The record codec has one home.", "The runner accepts an injected clock.")
    survey = Survey((finding,), candidates, sound)
    assert (survey.findings, survey.candidates, survey.sound) == (
        (finding,),
        candidates,
        sound,
    )


def test_stub_preserves_its_public_signature_and_is_frozen() -> None:
    """Breaks when stubs lose their public name or body, or permit mutation."""
    stub = Stub("Clock.now", "def now(self) -> float: raise NotImplementedError")
    assert (stub.name, stub.text) == (
        "Clock.now",
        "def now(self) -> float: raise NotImplementedError",
    )


def test_module_preserves_its_job_stubs_and_copies_and_is_frozen() -> None:
    """Breaks when modules lose their responsibility or stubs, or permit mutation."""
    stubs = (
        Stub("Clock.now", "def now(self) -> float: raise NotImplementedError"),
        Stub("Clock.wait", "def wait(self) -> None: raise NotImplementedError"),
    )
    copies = (Anchor("old/worker.py", 4), Anchor("old/web.py", 11))
    module = Module(
        "pkg/clock.py", "Supply the injected clock boundary.", stubs, copies
    )
    assert (module.path, module.job, module.stubs, module.replaces) == (
        "pkg/clock.py",
        "Supply the injected clock boundary.",
        stubs,
        copies,
    )


def test_home_preserves_its_exclusive_responsibility_and_is_frozen() -> None:
    """Breaks when homes lose their forbidden copies or permit mutation."""
    home = Home("process running", "pkg/runner.py", "Starting subprocesses elsewhere.")
    assert (home.concern, home.module, home.forbids) == (
        "process running",
        "pkg/runner.py",
        "Starting subprocesses elsewhere.",
    )


def test_step_preserves_its_declared_work_and_is_frozen() -> None:
    """Breaks when steps lose their path order or implementer, or permit mutation."""
    paths = ("pkg/runner.py", "callers/worker.py")
    step = Step("port worker", paths, "seam-builder")
    assert (step.name, step.paths, step.implementer) == (
        "port worker",
        paths,
        "seam-builder",
    )


def test_choice_preserves_both_options_and_costs_and_is_frozen() -> None:
    """Breaks when choices lose owner decision payloads or permit mutation."""
    choice = Choice(
        "Where does the clock live?",
        "Inject one clock.",
        "Give each caller a clock.",
        "Injection needs porting; separate clocks have unmeasured drift.",
    )
    assert (choice.question, choice.recommend, choice.alternative, choice.cost) == (
        "Where does the clock live?",
        "Inject one clock.",
        "Give each caller a clock.",
        "Injection needs porting; separate clocks have unmeasured drift.",
    )


def test_design_preserves_its_complete_structure_and_is_frozen() -> None:
    """Breaks when designs lose their records or step order, or permit mutation."""
    modules = (Module("pkg/runner.py", "Run processes.", (), ()),)
    homes = (Home("process running", "pkg/runner.py", "Process starts elsewhere."),)
    order = (
        Step("build home", ("pkg/runner.py",), "seam-builder"),
        Step("port worker", ("callers/worker.py",), "seam-builder"),
    )
    choices = (Choice("One home?", "Yes.", "Keep copies.", "Porting work."),)
    design = Design(modules, homes, order, choices)
    assert (design.modules, design.homes, design.order, design.choices) == (
        modules,
        homes,
        order,
        choices,
    )


def test_cause_preserves_the_stable_claim_and_instances_and_is_frozen() -> None:
    """Breaks when causes lose their underlying claim or permit mutation."""
    finding = Finding(
        Anchor("worker.py", 17),
        "Wrong exit.",
        Category.DEFECT,
        blocking=True,
        concern=None,
    )
    cause = Cause("exit-policy", "Exit status is interpreted twice.", None, (finding,))
    assert (cause.id, cause.claim, cause.concern is None, cause.findings) == (
        "exit-policy",
        "Exit status is interpreted twice.",
        True,
        (finding,),
    )


def test_fix_step_preserves_the_cause_owner_and_paths_and_is_frozen() -> None:
    """Breaks when fix steps lose routing payloads or permit mutation."""
    cause = Cause("exit-policy", "Exit status is interpreted twice.", "running", ())
    paths = ("pkg/runner.py", "callers/worker.py")
    fix = FixStep(cause, "seam-builder", paths)
    assert (fix.cause, fix.implementer, fix.paths) == (cause, "seam-builder", paths)


def test_design_change_preserves_its_cause_and_is_frozen() -> None:
    """Breaks when design changes lose their originating cause or permit mutation."""
    cause = Cause("exit-policy", "The design lacks an exit policy.", "running", ())
    change = DesignChange(cause)
    assert change.cause == cause
