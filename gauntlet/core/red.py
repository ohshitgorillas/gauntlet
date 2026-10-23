# Copyright 2026 oh shit, gorillas!
"""Validate approved starting verdicts and preserved test bindings."""

from collections import Counter
from collections.abc import Sequence

from gauntlet.core.records import (
    RedJudgment,
    Spec,
    TestAnswer,
    TestBinding,
    TestSnapshot,
    TestStart,
)


def _valid_start(start: object) -> bool:
    return isinstance(start, TestStart)


def _mark_problems(spec: Spec) -> tuple[str, ...]:
    problems: list[str] = []
    for line in spec.lines:
        if not _valid_start(line.start):
            problems.append(f"{line.id}: starting mark must be RED or GREEN")
        elif line.start == TestStart.GREEN and (
            not line.tests or len(set(line.tests)) != len(line.tests)
        ):
            problems.append(f"{line.id}: GREEN requires nonempty unique approved ids")
    return tuple(problems)


def _binding_problems(spec: Spec, bindings: Sequence[TestBinding]) -> tuple[str, ...]:
    problems = _mark_problems(spec)
    if problems:
        return problems
    if Counter(binding.line for binding in bindings) != Counter(
        line.id for line in spec.lines
    ):
        return ("Bindings must cover each approved line exactly once",)
    approved = {line.id: line for line in spec.lines}
    for binding in bindings:
        if not binding.ids or len(set(binding.ids)) != len(binding.ids):
            return (f"{binding.line}: binding requires nonempty unique test ids",)
        line = approved[binding.line]
        if line.start == TestStart.GREEN and set(binding.ids) != set(line.tests):
            return (f"{binding.line}: binding differs from approved GREEN ids",)
    return ()


def red_problems(
    spec: Spec, judgment: RedJudgment, bindings: Sequence[TestBinding]
) -> tuple[str, ...]:
    """Require one matching starting verdict and exact evidence per approved line."""
    problems = _binding_problems(spec, bindings)
    if problems:
        return problems
    if Counter(row.line for row in judgment.lines) != Counter(
        line.id for line in spec.lines
    ):
        return ("Judgments must cover each approved line exactly once",)
    approved = {line.id: line for line in spec.lines}
    bound = {binding.line: binding.ids for binding in bindings}
    for row in judgment.lines:
        if Counter(row.tests) != Counter(bound[row.line]):
            return (f"{row.line}: judgment test ids differ from bound tests",)
        if row.verdict.value != approved[row.line].start.value:
            return (f"{row.line}: verdict differs from approved starting mark",)
    return ()


def binding_problems(
    spec: Spec, answer: TestAnswer, baselines: Sequence[TestSnapshot]
) -> tuple[str, ...]:
    """Require complete bindings and exact, nonblank preserved-test snapshots."""
    problems = _binding_problems(spec, answer.bindings)
    if problems:
        return problems
    if answer.untestable:
        return ("Every approved line must be testable",)
    preserved = {
        test_id
        for line in spec.lines
        if line.start == TestStart.GREEN
        for test_id in line.tests
    }
    if Counter(snapshot.test_id for snapshot in baselines) != Counter(preserved):
        return ("Baselines must cover exactly the preserved test ids once",)
    if any(not snapshot.source.strip() for snapshot in baselines):
        return ("Every baseline must have nonblank source",)
    return ()
