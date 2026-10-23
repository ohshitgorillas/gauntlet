# Copyright 2026 oh shit, gorillas!
"""Decide durable state and recovery without executing external work."""

from collections import Counter
from collections.abc import Mapping
from dataclasses import replace

from gauntlet.core import records
from gauntlet.core.design import Design, design_problems, home_of, uncovered
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
from gauntlet.core.red import binding_problems, red_problems
from gauntlet.core.schedule import startable
from gauntlet.core.verdicts import Anchor, Candidate, core_missing_problems

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
    if isinstance(answer, records.Approved):
        return _approve(state, pending, answer)
    if pending.status != "started":
        raise StateError(answer.effect, "execution answer requires started work")
    if isinstance(answer, records.Answered) and (
        pending.effect.operation not in {"launch", "build"}
        or answer.role != pending.effect.role
        or answer.trace.id != pending.launch_id
        or answer.trace.role != pending.effect.role
        or (
            isinstance(answer.answer.payload, records.BuildAnswer)
            and answer.answer.payload.step != pending.effect.step
        )
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
    if isinstance(answer, records.Checked):
        return _checked(state, pending, answer)
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
    if (
        state.status == "active"
        and state.shape == Shape.STRUCTURE
        and state.stage == Stage.BUILD
    ):
        return _build_tick(state)
    if state.pending:
        return Action(state, tuple(p.effect for p in state.pending))
    if state.status != "active":
        return Action(state, ())
    if state.shape == Shape.STRUCTURE:
        if state.stage == Stage.DESIGN:
            return _request(state, "launch", "architect")
        if state.stage == Stage.PLAN:
            return _request(state, "launch", "planner", _latest(state, Design))
        if state.stage == Stage.RED_RUN:
            checks = tuple(
                records.Check(
                    f"runner.{index}",
                    records.Verdict.COULD_NOT_JUDGE,
                    command.run,
                    (),
                )
                for index, command in enumerate(state.config.tests)
            )
            return _request_checks(state, checks, "runner-checks")
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
    pending = next(p for p in state.pending if p.effect.id == event.effect)
    completed = replace(
        state,
        pending=tuple(p for p in state.pending if p.effect.id != event.effect),
        receipts=(*state.receipts, records.Receipt(event.effect, event)),
    )
    if isinstance(event, records.Answered):
        return _role_answer(completed, event)
    if pending.effect.operation == "commit-step":
        completed = replace(
            completed,
            steps=tuple(
                replace(run, status="complete", partial_diff=None)
                if run.name == pending.effect.step
                else run
                for run in completed.steps
            ),
        )
    return Action(completed, ())


def _latest[T](state: State, kind: type[T]) -> T:
    return next(
        payload
        for artifact in reversed(state.artifacts)
        if isinstance(payload := artifact.answer.payload, kind)
    )


def _request(
    state: State,
    operation: str,
    role: str | None = None,
    payload: records.Payload | None = None,
    context: records.Artifact | None = None,
    step: str | None = None,
) -> Action:
    identity = (
        state.job,
        state.stage.value,
        state.rounds,
        state.steps,
        len(state.receipts),
    )
    effect = records.Effect(
        repr((identity, operation, role, step)),
        state.stage,
        operation,
        role,
        step,
        payload,
        state.artifacts + (() if context is None else (context,)),
    )
    saved = replace(
        state, pending=(*state.pending, records.Pending(effect, "ready", None))
    )
    return Action(saved, (effect,))


def _request_checks(
    state: State, checks: tuple[records.Check, ...], purpose: str
) -> Action:
    request = records.CheckSet(checks, "continue")
    return _request(
        state,
        "checks",
        payload=request,
        context=records.Artifact(purpose, 1, records.RoleAnswer(request)),
    )


def _save(state: State, name: str, answer: records.RoleAnswer) -> State:
    revision = 1 + sum(a.name == name for a in state.artifacts)
    return replace(
        state, artifacts=(*state.artifacts, records.Artifact(name, revision, answer))
    )


def _consume_round(state: State, loop: records.Loop) -> tuple[State, bool]:
    used = 1 + sum(row.used for row in state.rounds if row.loop == loop)
    saved = replace(
        state,
        rounds=(
            *tuple(row for row in state.rounds if row.loop != loop),
            records.Round(loop, used),
        ),
    )
    caps = {
        records.Loop.DESIGN: state.config.caps.design,
        records.Loop.PLAN: state.config.caps.plan,
        records.Loop.SPEC: state.config.caps.spec,
        records.Loop.JUROR: state.config.caps.juror,
        records.Loop.BUILD: state.config.caps.build,
    }
    return saved, used >= caps[loop]


def _failed(
    state: State, loop: records.Loop, role: str, step: str | None = None
) -> Action:
    saved, exhausted = _consume_round(state, loop)
    if exhausted:
        return _request(replace(saved, status="stopped"), "stop")
    return _request(saved, "build" if step is not None else "launch", role, step=step)


def _wait(state: State) -> Action:
    return _request(replace(state, status="waiting"), "owner")


def _role_answer(state: State, event: records.Answered) -> Action:
    payload = event.answer.payload
    saved = _save(state, state.stage.value, event.answer)
    if isinstance(payload, records.BuildAnswer):
        return _build_answer(saved, payload, event.role)
    if isinstance(payload, Design):
        candidate = state.candidate
        if (
            design_problems(payload)
            or candidate is None
            or home_of(payload, candidate.concern) is None
            or uncovered(payload, state.copies, ())
        ):
            return _failed(saved, records.Loop.DESIGN, "architect")
        return _wait(saved)
    if isinstance(payload, records.Plan):
        if tuple(step.step for step in payload.steps) != _latest(state, Design).order:
            return _failed(saved, records.Loop.PLAN, "planner")
        return _request(saved, "launch", "prosecutor", payload)
    if isinstance(payload, records.CheckSet):
        if payload.disposition == "refuse":
            return _request(replace(saved, status="stopped"), "stop", payload=payload)
        if payload.disposition == "escalate-leave":
            return _request(replace(saved, status="waiting"), "owner", payload=payload)
        if not payload.checks or any(
            check.verdict != records.Verdict.PASS for check in payload.checks
        ):
            return _failed(saved, records.Loop.PLAN, "planner")
        return _wait(saved)
    if isinstance(payload, records.Spec):
        if _spec_problems(state, payload):
            return _failed(saved, records.Loop.SPEC, "planner")
        return _request(saved, "launch", "arbiter", payload)
    if isinstance(payload, records.SpecJudgment):
        spec = _latest(state, records.Spec)
        if Counter(row.line for row in payload.rulings) != Counter(
            line.id for line in spec.lines
        ) or any(row.verdict != records.Verdict.PASS for row in payload.rulings):
            return _failed(saved, records.Loop.SPEC, "planner")
        return _wait(saved)
    if isinstance(payload, records.TestAnswer):
        if binding_problems(_latest(state, records.Spec), payload, state.baselines):
            return _request(saved, "launch", "arbiter", payload)
        return Action(replace(saved, stage=Stage.RED_RUN), ())
    if isinstance(payload, records.RedJudgment):
        if red_problems(
            _latest(state, records.Spec),
            payload,
            _latest(state, records.TestAnswer).bindings,
        ):
            return _failed(saved, records.Loop.JUROR, "arbiter")
        checks = tuple(
            records.Check(
                snapshot.test_id, records.Verdict.COULD_NOT_JUDGE, snapshot.source, ()
            )
            for snapshot in state.baselines
        ) or (
            records.Check(
                "preserved-sources",
                records.Verdict.COULD_NOT_JUDGE,
                "Verify there are no preserved tests requiring source equality",
                (),
            ),
        )
        return _request_checks(saved, checks, "source-checks")
    return Action(state, ())


def _spec_problems(state: State, spec: records.Spec) -> bool:
    ids = tuple(line.id for line in spec.lines)
    keeps = () if state.candidate is None else state.candidate.keeps
    return (
        len(set(ids)) != len(ids)
        or any(not line.claim.strip() or not line.bite.strip() for line in spec.lines)
        or any(type(line.start) is not records.TestStart for line in spec.lines)
        or any(
            line.start == records.TestStart.GREEN
            and (not line.tests or len(set(line.tests)) != len(line.tests))
            for line in spec.lines
        )
        or any(claim not in {line.claim for line in spec.lines} for claim in keeps)
    )


def _approve(state: State, pending: records.Pending, event: records.Approved) -> Action:
    if (
        pending.effect.operation != "owner"
        or state.status != "waiting"
        or state.stage not in {Stage.DESIGN, Stage.PLAN, Stage.SPEC}
    ):
        raise StateError(event.effect, "approval requires a waiting owner request")
    saved = replace(
        state,
        pending=tuple(p for p in state.pending if p != pending),
        receipts=(*state.receipts, records.Receipt(event.effect, event)),
        status="active",
    )
    if state.stage == Stage.DESIGN:
        resolved = event.design
        if resolved is None or resolved.choices or design_problems(resolved):
            return Action(state, ())
        saved = _save(saved, "design", records.RoleAnswer(resolved))
        return Action(replace(saved, stage=Stage.PLAN), ())
    if state.stage == Stage.PLAN:
        return Action(replace(saved, stage=Stage.SPEC), ())
    spec = _latest(state, records.Spec)
    if any(line.start == records.TestStart.GREEN for line in spec.lines):
        return _request(saved, "baseline", payload=spec)
    return Action(replace(saved, stage=Stage.STUBS), ())


def _checked(state: State, pending: records.Pending, event: records.Checked) -> Action:
    request = pending.effect.input
    if pending.effect.operation != "checks" or not isinstance(
        request, records.CheckSet
    ):
        raise StateError(event.effect, "check results require requested checks")
    context = next(
        (
            artifact
            for artifact in reversed(pending.effect.inputs)
            if artifact.name in {"runner-checks", "source-checks", "build-checks"}
            and artifact.answer.payload == request
        ),
        None,
    )
    if context is None:
        raise StateError(event.effect, "check request lacks its bound purpose")
    saved = replace(
        state,
        pending=tuple(p for p in state.pending if p != pending),
        receipts=(*state.receipts, records.Receipt(event.effect, event)),
        checks=(*state.checks, *event.rows),
    )
    if (
        not request.checks
        or Counter(row.check for row in event.rows)
        != Counter(check.id for check in request.checks)
        or any(row.verdict != records.Verdict.PASS for row in event.rows)
    ):
        if context.name == "build-checks":
            step = next(
                row.step
                for row in _latest(state, records.Plan).steps
                if row.step.name == pending.effect.step
            )
            return _failed(saved, records.Loop.BUILD, step.implementer, step.name)
        return _failed(saved, records.Loop.JUROR, "arbiter")
    if context.name == "build-checks":
        return _request(saved, "commit-step", step=pending.effect.step)
    if context.name == "runner-checks":
        return _request(saved, "launch", "juror", _latest(state, records.Spec))
    return _request(replace(saved, stage=Stage.LOCK), "commit-tests")


def _build_tick(state: State) -> Action:
    """Delegate file conflicts and retain independently pending build phases."""
    plan = _latest(state, records.Plan)
    names = startable(
        tuple((row.step.name, frozenset(row.step.paths)) for row in plan.steps),
        tuple(run.name for run in state.steps if run.status == "complete"),
        tuple(run.name for run in state.steps if run.status == "running"),
        state.held,
    )
    saved = state
    for name in names:
        step = next(row.step for row in plan.steps if row.step.name == name)
        saved = replace(
            saved,
            steps=tuple(
                replace(run, attempt=run.attempt + 1, status="running")
                if run.name == name
                else run
                for run in saved.steps
            ),
        )
        saved = _request(saved, "build", step.implementer, step=name).state
    return Action(saved, tuple(p.effect for p in saved.pending))


def _build_answer(state: State, answer: records.BuildAnswer, role: str) -> Action:
    """Separate implementer results from harness checks and commit receipts."""
    if answer.missing is not None and core_missing_problems(
        answer.missing, blocked=answer.status == records.BuildStatus.BLOCKED
    ):
        return _failed(state, records.Loop.BUILD, role, answer.step)
    if answer.status == records.BuildStatus.BLOCKED:
        saved = replace(
            state,
            status="stopped",
            steps=tuple(
                replace(run, status="blocked") if run.name == answer.step else run
                for run in state.steps
            ),
        )
        return _request(saved, "stop")
    if answer.status == records.BuildStatus.PARTIAL:
        state, exhausted = _consume_round(state, records.Loop.BUILD)
        saved = replace(
            state,
            steps=tuple(
                replace(run, status="pending") if run.name == answer.step else run
                for run in state.steps
            ),
        )
        if exhausted:
            return _request(replace(saved, status="stopped"), "stop")
        return Action(saved, ())
    checks = (
        *(
            records.Check(
                f"build.runner.{index}",
                records.Verdict.COULD_NOT_JUDGE,
                command.run,
                (),
            )
            for index, command in enumerate(state.config.tests)
        ),
        records.Check(
            "build.gate", records.Verdict.COULD_NOT_JUDGE, state.config.gates, ()
        ),
    )
    request = records.CheckSet(checks, "continue")
    return _request(
        state,
        "checks",
        payload=request,
        step=answer.step,
        context=records.Artifact("build-checks", 1, records.RoleAnswer(request)),
    )


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
