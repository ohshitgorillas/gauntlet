# Copyright 2026 oh shit, gorillas!
"""Declare composite answers, workflow state and recovery contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from gauntlet.core.design import Design, Step, Stub
from gauntlet.core.verdicts import Anchor, Candidate, CoreMissing, Finding, Survey

if TYPE_CHECKING:
    from gauntlet.core.causes import Cause


class Stage(StrEnum):
    """Name a workflow stage."""

    BRIEF = "brief"
    DISCOVERY = "discovery"
    OUTLINE = "outline"
    DESIGN = "design"
    PLAN = "plan"
    SPEC = "spec"
    STUBS = "stubs"
    TESTS = "tests"
    RED_RUN = "red-run"
    LOCK = "lock"
    BUILD = "build"
    REVIEW = "review"
    BAILIFF = "bailiff"
    LAND = "land"


class Shape(StrEnum):
    """Name a job shape."""

    JOB = "job"
    TEST_AUDIT = "test-audit"
    STRUCTURE = "structure"


class Verdict(StrEnum):
    """Name a check verdict."""

    PASS = auto()
    FAIL = "fail"
    COULD_NOT_JUDGE = "could-not-judge"


class Loop(StrEnum):
    """Name a capped workflow loop."""

    DESIGN = "design"
    PLAN = "plan"
    SPEC = "spec"
    JUROR = "juror"
    BUILD = "build"
    REVIEW = "review"
    REOPEN = "reopen"


class Kind(StrEnum):
    """Name an agent kind."""

    JUDGE = "judge"
    READER = "reader"
    COORDINATOR = "coordinator"
    SCRATCH = "scratch"
    TESTER = "tester"
    IMPLEMENTER = "implementer"


class TestStart(StrEnum):
    """Name an explicitly approved starting verdict."""

    RED = "red"
    GREEN = "green"


class RedVerdict(StrEnum):
    """Name a starting-run judgment."""

    RED = "red"
    ERROR = "error"
    GREEN = "green"
    INVALID = "invalid"
    COULD_NOT_JUDGE = "could-not-judge"


class BuildStatus(StrEnum):
    """Name a build result."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Brief:
    """Record the requested work."""

    text: str


@dataclass(frozen=True)
class Citation:
    """Connect a claim to its source."""

    claim: str
    anchor: Anchor


@dataclass(frozen=True)
class Discovery:
    """Record discovery citations."""

    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class PlanStep:
    """Bind a design step to its spec lines and stubs."""

    step: Step
    serves: tuple[str, ...]
    stubs: tuple[Stub, ...]


@dataclass(frozen=True)
class Outline:
    """Record proposed steps and affected areas."""

    steps: tuple[Step, ...]
    areas: tuple[str, ...]
    shared_structure: bool = False


@dataclass(frozen=True)
class Plan:
    """Record the planned steps."""

    steps: tuple[PlanStep, ...]


@dataclass(frozen=True)
class SpecLine:
    """Record one claim and its explicit starting verdict."""

    id: str
    claim: str
    bite: str
    start: TestStart
    tests: tuple[str, ...] = ()


@dataclass(frozen=True)
class Collateral:
    """Record the required disposition of an existing assertion."""

    test_id: str
    assertion: str
    disposition: str


@dataclass(frozen=True)
class Spec:
    """Record claims and collateral assertions."""

    lines: tuple[SpecLine, ...]
    collateral: tuple[Collateral, ...]


@dataclass(frozen=True)
class SpecDefect:
    """Record evidence of a spec defect."""

    line: str
    claim: str
    evidence: tuple[Citation, ...]


@dataclass(frozen=True)
class Check:
    """Record one cited check result."""

    id: str
    verdict: Verdict
    reason: str
    citations: tuple[Anchor, ...]


@dataclass(frozen=True)
class CheckSet:
    """Record checks and their disposition."""

    checks: tuple[Check, ...]
    disposition: str


@dataclass(frozen=True)
class SpecRuling:
    """Record a ruling on one spec line."""

    line: str
    verdict: Verdict
    reason: str


@dataclass(frozen=True)
class SpecJudgment:
    """Record spec rulings."""

    rulings: tuple[SpecRuling, ...]


@dataclass(frozen=True)
class Evidence:
    """Record measured evidence."""

    measurements: tuple[Citation, ...]


@dataclass(frozen=True)
class TestBinding:
    """Bind a spec line to test ids."""

    line: str
    ids: tuple[str, ...]


@dataclass(frozen=True)
class TestAnswer:
    """Record test bindings and untestable lines."""

    bindings: tuple[TestBinding, ...]
    untestable: tuple[str, ...]


@dataclass(frozen=True)
class RedLine:
    """Record the starting verdict for bound tests."""

    line: str
    verdict: RedVerdict
    tests: tuple[str, ...]


@dataclass(frozen=True)
class RedJudgment:
    """Record starting-run rulings."""

    lines: tuple[RedLine, ...]


@dataclass(frozen=True)
class TestSnapshot:
    """Preserve the exact source of an existing test."""

    test_id: str
    source: str


@dataclass(frozen=True)
class BuildAnswer:
    """Record a step's build result."""

    step: str
    status: BuildStatus
    reason: str
    missing: CoreMissing | None = None


@dataclass(frozen=True)
class ReviewAnswer:
    """Record review findings."""

    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class CausesAnswer:
    """Record grouped causes."""

    causes: tuple[Cause, ...]


@dataclass(frozen=True)
class Pin:
    """Record a spec assertion's pin ruling."""

    line: str
    verdict: str
    reason: str


@dataclass(frozen=True)
class CollateralRuling:
    """Record an existing test's collateral ruling."""

    test_id: str
    verdict: str
    reason: str


@dataclass(frozen=True)
class BailiffAnswer:
    """Record pins and collateral rulings."""

    pins: tuple[Pin, ...]
    collateral: tuple[CollateralRuling, ...]


@dataclass(frozen=True)
class AuditRow:
    """Record a test audit ruling."""

    test_id: str
    verdict: str
    reason: str


@dataclass(frozen=True)
class AuditAnswer:
    """Record test audit rulings."""

    rows: tuple[AuditRow, ...]


@dataclass(frozen=True)
class EpicJob:
    """Record one job in an epic."""

    id: str
    brief: str
    depends: tuple[str, ...]
    areas: tuple[str, ...]


@dataclass(frozen=True)
class EpicAnswer:
    """Record epic jobs and a possible stop reason."""

    jobs: tuple[EpicJob, ...]
    stop: str | None


type Payload = (
    Brief
    | Discovery
    | Outline
    | Design
    | Plan
    | Spec
    | CheckSet
    | SpecJudgment
    | Evidence
    | TestAnswer
    | RedJudgment
    | BuildAnswer
    | ReviewAnswer
    | CausesAnswer
    | BailiffAnswer
    | Survey
    | AuditAnswer
    | EpicAnswer
)


@dataclass(frozen=True)
class RoleAnswer:
    """Record a role payload and possible spec defect."""

    payload: Payload
    spec_defect: SpecDefect | None = None


@dataclass(frozen=True)
class Caps:
    """Record per-loop round caps."""

    design: int = 2
    plan: int = 2
    spec: int = 2
    juror: int = 2
    build: int = 2
    review: int = 2
    reopen: int = 2


@dataclass(frozen=True)
class TestCommand:
    """Record an opaque test command and directory."""

    directory: str
    run: str


@dataclass(frozen=True)
class InterfaceCommand:
    """Record an opaque interface command for a language."""

    language: str
    run: str


@dataclass(frozen=True)
class RoleSetting:
    """Record model and effort choices for a role."""

    name: str
    model: str | None
    effort: str | None


DEFAULT_READINESS_TIMEOUT_SECONDS: int = 10


@dataclass(frozen=True)
class ProxyRoute:
    """Record one permitted proxy method, path and query names."""

    method: str
    path: str
    query_parameters: tuple[str, ...] = ()


DEFAULT_PROXY_ROUTES: tuple[ProxyRoute, ...] = (
    ProxyRoute("POST", "/v1/messages", ("beta",)),
    ProxyRoute("POST", "/v1/messages/count_tokens", ("beta",)),
)


@dataclass(frozen=True)
class ProxyLimits:
    """Record proxy header, body and connection limits."""

    header_bytes: int = 65536
    body_bytes: int = 33554432
    connections: int = 8


@dataclass(frozen=True)
class Config:
    """Record harness configuration."""

    image: str
    tests: tuple[TestCommand, ...]
    gates: str
    test_policy: str
    interface: tuple[InterfaceCommand, ...]
    test_helpers: tuple[str, ...] = ()
    protected: tuple[str, ...] = ()
    test_lint: str | None = None
    implementer_network: bool = False
    caps: Caps = Caps()
    roles: tuple[RoleSetting, ...] = ()
    readiness_timeout_seconds: int = DEFAULT_READINESS_TIMEOUT_SECONDS
    proxy_limits: ProxyLimits = ProxyLimits()
    proxy_extra_routes: tuple[ProxyRoute, ...] = ()


@dataclass(frozen=True)
class RoleSpec:
    """Record a role's kind and accepted schema tags."""

    name: str
    kind: Kind
    schemas: tuple[str, ...]


@dataclass(frozen=True)
class StageRule:
    """Record a stage's successor, loop and approval requirement."""

    stage: Stage
    successor: Stage | None
    loop: Loop | None
    approval: bool


@dataclass(frozen=True)
class CheckRow:
    """Record one execution of a check."""

    id: str
    stage: Stage
    round: int
    check: str
    verdict: Verdict
    evidence: str


@dataclass(frozen=True)
class Bypass:
    """Record a stage bypass with its reason and detail."""

    stage: Stage
    reason: str
    detail: str


@dataclass(frozen=True)
class Amendment:
    """Record amended spec lines and a reason."""

    lines: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class OwnerUse:
    """Record an owner command at a stage."""

    command: str
    stage: Stage
    detail: str


@dataclass(frozen=True)
class TraceRow:
    """Record one dispatched launch attempt."""

    id: str
    role: str
    model: str
    effort: str
    tokens: int | None
    cost: str | None
    outcome: str


@dataclass(frozen=True)
class Round:
    """Record consumed rounds in one loop."""

    loop: Loop
    used: int


@dataclass(frozen=True)
class Artifact:
    """Record one revision of a role answer."""

    name: str
    revision: int
    answer: RoleAnswer


@dataclass(frozen=True)
class StepRun:
    """Record a step attempt and saved partial work."""

    name: str
    attempt: int
    base_commit: str
    partial_diff: str | None
    status: str


@dataclass(frozen=True)
class CauseRound:
    """Record failed rounds for one cause."""

    id: str
    failures: int


@dataclass(frozen=True)
class Effect:
    """Record a pending operation with immutable role inputs."""

    id: str
    stage: Stage
    operation: str
    role: str | None
    step: str | None
    input: Payload | None
    inputs: tuple[Artifact, ...]


@dataclass(frozen=True)
class GitIntent:
    """Record the exact reference change an effect intends."""

    repository: str
    reference: str
    before: str
    after: str


@dataclass(frozen=True)
class RecoveryPoint:
    """Record executor recovery data for one dispatch."""

    dispatch: int
    workspace: str | None
    git: GitIntent | None


@dataclass(frozen=True)
class Pending:
    """Record an effect's durable dispatch state."""

    effect: Effect
    status: str
    launch_id: str | None
    dispatch: int = 0
    recovery: RecoveryPoint | None = None


@dataclass(frozen=True)
class State:
    """Record complete durable job state."""

    job: str
    revision: int
    shape: Shape
    stage: Stage
    status: str
    config: Config
    candidate: Candidate | None
    copies: tuple[Anchor, ...]
    artifacts: tuple[Artifact, ...]
    rounds: tuple[Round, ...]
    steps: tuple[StepRun, ...]
    owners: tuple[tuple[str, str], ...]
    cause_rounds: tuple[CauseRound, ...]
    held: tuple[str, ...]
    checks: tuple[CheckRow, ...]
    bypasses: tuple[Bypass, ...]
    amendments: tuple[Amendment, ...]
    controls: tuple[OwnerUse, ...]
    launches: tuple[TraceRow, ...]
    pending: tuple[Pending, ...]
    receipts: tuple[Receipt, ...]
    baselines: tuple[TestSnapshot, ...]


@dataclass(frozen=True)
class Action:
    """Record a state transition and its effects."""

    state: State
    effects: tuple[Effect, ...]


@dataclass(frozen=True)
class Tick:
    """Request the next decision without an execution result."""


@dataclass(frozen=True)
class Answered:
    """Record a role answer and its completed launch trace."""

    effect: str
    dispatch: int
    role: str
    answer: RoleAnswer
    trace: TraceRow


@dataclass(frozen=True)
class Checked:
    """Record check results for an effect dispatch."""

    effect: str
    dispatch: int
    rows: tuple[CheckRow, ...]


@dataclass(frozen=True)
class Approved:
    """Record owner approval and design choices."""

    effect: str
    dispatch: int
    choices: tuple[tuple[str, str], ...]
    design: Design | None = None


@dataclass(frozen=True)
class Baselined:
    """Record captured existing test sources."""

    effect: str
    dispatch: int
    tests: tuple[TestSnapshot, ...]


@dataclass(frozen=True)
class Restored:
    """Record a restored workspace."""


@dataclass(frozen=True)
class Reconciled:
    """Record a verified completed git intent."""

    commit: str


type RecoveryResult = Restored | Reconciled


@dataclass(frozen=True)
class Recovered:
    """Record recovery of one effect dispatch."""

    effect: str
    dispatch: int
    result: RecoveryResult


@dataclass(frozen=True)
class Completed:
    """Record completed I/O for one effect dispatch."""

    effect: str
    dispatch: int
    commit: str | None


@dataclass(frozen=True)
class Failed:
    """Record a failed effect dispatch."""

    effect: str
    dispatch: int
    reason: str


type ExecutionAnswer = Answered | Checked | Approved | Baselined | Completed | Failed
type Answer = Tick | Recovered | ExecutionAnswer


@dataclass(frozen=True)
class Receipt:
    """Record an accepted completion event."""

    effect: str
    event: Answer


type Json = bool | int | float | str | list[Json] | dict[str, Json] | None
