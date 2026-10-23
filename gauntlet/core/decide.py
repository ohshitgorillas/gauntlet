# Copyright 2026 oh shit, gorillas!
"""Decide durable state and recovery without executing external work."""

from collections.abc import Mapping
from dataclasses import replace

from gauntlet.core import records
from gauntlet.core.errors import StateError
from gauntlet.core.records import (
    Action,
    Answer,
    Config,
    Shape,
    Stage,
    StageRule,
    State,
)
from gauntlet.core.red import binding_problems
from gauntlet.core.verdicts import Anchor, Candidate

FIRST: Mapping[Shape, Stage] = {
    Shape.JOB: Stage.BRIEF,
    Shape.TEST_AUDIT: Stage.SPEC,
    Shape.STRUCTURE: Stage.DESIGN,
}
SKIPPED: Mapping[Shape, frozenset[Stage]] = {
    Shape.JOB: frozenset(),
    Shape.TEST_AUDIT: frozenset({Stage.STUBS, Stage.BUILD, Stage.REVIEW}),
    Shape.STRUCTURE: frozenset(),
}
_LOOPS = {
    Stage.DESIGN: records.Loop.DESIGN,
    Stage.PLAN: records.Loop.PLAN,
    Stage.SPEC: records.Loop.SPEC,
    Stage.RED_RUN: records.Loop.JUROR,
    Stage.BUILD: records.Loop.BUILD,
    Stage.REVIEW: records.Loop.REVIEW,
}
STAGES: tuple[StageRule, ...] = tuple(
    StageRule(
        stage,
        successor,
        _LOOPS.get(stage),
        stage in {Stage.DESIGN, Stage.PLAN, Stage.SPEC, Stage.LAND},
    )
    for stage, successor in zip(Stage, (*tuple(Stage)[1:], None), strict=True)
)
_GIT = frozenset({"commit-tests", "commit-step", "land"})


def initial(
    job: str,
    shape: Shape,
    config: Config,
    *,
    candidate: Candidate | None = None,
    copies: tuple[Anchor, ...] = (),
) -> State:
    """Open an empty workflow at the entry point for its shape."""
    return State(
        job=job,
        revision=0,
        shape=shape,
        stage=FIRST[shape],
        status="active",
        config=config,
        candidate=candidate,
        copies=copies,
        artifacts=(),
        rounds=(),
        steps=(),
        owners=(),
        cause_rounds=(),
        held=(),
        checks=(),
        bypasses=(),
        amendments=(),
        controls=(),
        launches=(),
        pending=(),
        receipts=(),
        baselines=(),
    )


def state_problems(state: State) -> tuple[str, ...]:
    """Report contradictory durable identities and recovery checkpoints."""
    problems: list[str] = []
    if state.shape == Shape.STRUCTURE and state.candidate is None:
        problems.append("STRUCTURE requires a candidate")
    identities = (
        tuple(p.effect.id for p in state.pending),
        tuple(row.id for row in state.launches),
        tuple(row.id for row in state.checks),
        tuple((receipt.effect, receipt.event) for receipt in state.receipts),
    )
    problems.extend(
        "duplicate identity" for group in identities if len(set(group)) != len(group)
    )
    receipt_events: dict[tuple[str, int | None], set[Answer]] = {}
    for receipt in state.receipts:
        event = receipt.event
        if isinstance(event, records.Recovered) and isinstance(
            event.result, records.Reconciled
        ):
            event = records.Completed(event.effect, event.dispatch, event.result.commit)
        key = (
            receipt.effect,
            None if isinstance(event, records.Tick) else event.dispatch,
        )
        receipt_events.setdefault(key, set()).add(event)
    problems.extend(
        "contradictory receipts"
        for events in receipt_events.values()
        if len(events) > 1
    )
    for pending in state.pending:
        problems.extend(_pending_problems(pending, state.launches))
    problems.extend(
        "complete step retains a partial diff"
        for step in state.steps
        if step.status == "complete" and step.partial_diff is not None
    )
    return tuple(problems)


def _pending_problems(
    pending: records.Pending,
    launches: tuple[records.TraceRow, ...],
) -> tuple[str, ...]:
    effect = pending.effect
    problems: list[str] = []
    if pending.status == "ready":
        if pending.launch_id is not None:
            problems.append("ready work has an active launch")
    else:
        point = pending.recovery
        if point is None or point.dispatch != pending.dispatch:
            problems.append("started work lacks its dispatch checkpoint")
        elif effect.operation in _GIT:
            if point.git is None:
                problems.append("git work lacks its intent")
        elif point.workspace is None:
            problems.append("mutable work lacks its workspace checkpoint")
    if effect.operation == "launch":
        if effect.role is None or effect.step is not None:
            problems.append("invalid launch role or step")
        if pending.launch_id is not None:
            matching = tuple(row for row in launches if row.id == pending.launch_id)
            if not matching or matching[0].role != effect.role:
                problems.append("launch ledger association differs")
    return tuple(problems)


def decide(state: State, answer: Answer) -> Action:
    """Validate identity before accepting events or reproducing pending work."""
    problems = state_problems(state)
    if problems:
        identity = "state"
        raise StateError(identity, "; ".join(problems))
    if isinstance(answer, records.Tick):
        return _tick(state)
    receipts = tuple(r for r in state.receipts if r.effect == answer.effect)
    if records.Receipt(answer.effect, answer) in receipts:
        return Action(state, ())
    for receipt in receipts:
        if (
            not isinstance(receipt.event, records.Recovered)
            or receipt.event.dispatch == answer.dispatch
        ):
            raise StateError(answer.effect, "conflicting receipt")
    pending = next((p for p in state.pending if p.effect.id == answer.effect), None)
    if pending is None or pending.dispatch != answer.dispatch:
        raise StateError(answer.effect, "event does not match pending dispatch")
    if isinstance(answer, records.Recovered):
        return _recover(state, pending, answer)
    if pending.status != "started":
        raise StateError(answer.effect, "execution answer requires started work")
    if isinstance(answer, records.Answered) and (
        pending.effect.operation != "launch"
        or answer.role != pending.effect.role
        or answer.trace.id != pending.launch_id
        or answer.trace.role != pending.effect.role
    ):
        raise StateError(answer.effect, "answer does not match launch")
    if isinstance(answer, records.Answered):
        completed = _completed(state, answer)
        return replace(
            completed,
            state=replace(
                completed.state,
                launches=tuple(
                    answer.trace if row.id == answer.trace.id else row
                    for row in state.launches
                ),
            ),
        )
    if isinstance(answer, records.Baselined):
        return _baseline(state, pending, answer)
    if isinstance(answer, records.Completed) and pending.effect.operation in _GIT:
        point = pending.recovery
        if point is None or point.git is None or point.git.after != answer.commit:
            raise StateError(answer.effect, "completion differs from git intent")
        return _completed(state, answer)
    raise StateError(answer.effect, "stage transition unavailable")


def _tick(state: State) -> Action:
    interrupted = tuple(p for p in state.pending if p.status != "ready")
    if interrupted:
        pending = tuple(
            replace(p, status="recovering") if p in interrupted else p
            for p in state.pending
        )
        return Action(
            replace(state, pending=pending), tuple(p.effect for p in interrupted)
        )
    if state.pending:
        return Action(state, tuple(p.effect for p in state.pending))
    if state.status != "active":
        return Action(state, ())
    identity = (state.job, state.stage.value, state.rounds, state.steps, 0)
    effect = records.Effect(
        repr(identity),
        state.stage,
        "stop",
        None,
        None,
        None,
        state.artifacts,
    )
    stopped = replace(
        state,
        status="stopped",
        pending=(records.Pending(effect, "ready", None),),
    )
    return Action(stopped, (effect,))


def _recover(
    state: State, pending: records.Pending, event: records.Recovered
) -> Action:
    if isinstance(event.result, records.Reconciled):
        point = pending.recovery
        if (
            pending.effect.operation not in _GIT
            or point is None
            or point.git is None
            or event.result.commit != point.git.after
        ):
            raise StateError(event.effect, "reconciliation differs from git intent")
        completed = records.Completed(event.effect, event.dispatch, event.result.commit)
        action = _completed(state, completed)
        return replace(
            action,
            state=replace(
                action.state,
                receipts=(*action.state.receipts, records.Receipt(event.effect, event)),
            ),
        )
    replay = replace(
        pending,
        status="ready",
        dispatch=pending.dispatch + 1,
        launch_id=None,
        recovery=None,
    )
    launches = tuple(
        replace(row, outcome="interrupted") if row.id == pending.launch_id else row
        for row in state.launches
    )
    checks = state.checks
    if pending.effect.operation == "checks":
        checks = (
            *checks,
            records.CheckRow(
                f"{event.effect}.check.{event.dispatch}",
                pending.effect.stage,
                0,
                "interruption",
                records.Verdict.COULD_NOT_JUDGE,
                "check interrupted before completion",
            ),
        )
    restored = replace(
        state,
        pending=tuple(replay if p == pending else p for p in state.pending),
        launches=launches,
        checks=checks,
        receipts=(*state.receipts, records.Receipt(event.effect, event)),
    )
    return Action(restored, ())


def _completed(state: State, event: records.Answered | records.Completed) -> Action:
    completed = replace(
        state,
        pending=tuple(p for p in state.pending if p.effect.id != event.effect),
        receipts=(*state.receipts, records.Receipt(event.effect, event)),
    )
    return Action(completed, ())


def _baseline(
    state: State, pending: records.Pending, event: records.Baselined
) -> Action:
    spec = pending.effect.input
    if pending.effect.operation != "baseline" or not isinstance(spec, records.Spec):
        raise StateError(event.effect, "baseline requires its approved spec effect")
    preserved = replace(
        spec,
        lines=tuple(
            line for line in spec.lines if line.start == records.TestStart.GREEN
        ),
    )
    approved = records.TestAnswer(
        tuple(records.TestBinding(line.id, line.tests) for line in preserved.lines), ()
    )
    if binding_problems(preserved, approved, event.tests):
        raise StateError(event.effect, "baseline differs from approved test ids")
    saved = replace(
        state,
        baselines=event.tests,
        pending=tuple(p for p in state.pending if p != pending),
        receipts=(*state.receipts, records.Receipt(event.effect, event)),
    )
    return Action(saved, ())
