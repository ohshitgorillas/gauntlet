Status: proposed, for the owner's approval.

## Why

M1 supplies the pure decisions and durable records needed before the launcher exists (`docs/roadmap.md:37`). Its completion check covers every structure-job decision branch and recovery to the same next action (`docs/roadmap.md:48`). The proposed interfaces below use the recommendations in Decisions for the owner; those decisions remain open until the owner rules.

- **Record definitions, three homes.** Answer primitives live at `gauntlet/core/verdicts.py:9`, design records at `gauntlet/core/design.py:15`, and cause records at `gauntlet/core/causes.py:12`. These are distinct records, not three implementations of one record. The requirement for one record-type module (`docs/superpowers/specs/gates-core-design.md:394`) conflicts with the approved homes for design and cause records (`docs/superpowers/specs/structure-first-design.md:270`, `docs/superpowers/specs/structure-first-design.md:274`). Decision 1 puts that conflict before the owner.

- **Fixture factories, four.** `tests/test_core_design.py:21` and `tests/test_core_causes.py:33` construct valid designs separately; `tests/test_core_causes.py:22` constructs findings; `tests/test_core_verdicts.py:25` constructs CoreMissing. Their field values differ and must survive the port. The prescribed shared builders have no implementation (`docs/superpowers/specs/structure-first-design.md:253`). Record-preservation cases at `tests/test_core_records.py:20` are assertions about payloads, not another factory to replace.

- **One product exception.** `UnownedPathError` and its compatibility alias are at `gauntlet/core/causes.py:37` and `gauntlet/core/causes.py:46`. It joins the required typed error family (`docs/superpowers/specs/gates-core-design.md:395`). Gate errors at `gates/core/report.py:9` and test-support errors at `tests/support/capture.py:70`, `tests/support/project.py:32` and `tests/support/scripted.py:16` belong to their existing domains and remain there.

- **One implementation of each structure decision.** `design_problems`, `home_of`, `uncovered` (`gauntlet/core/design.py:70`, `gauntlet/core/design.py:141`, `gauntlet/core/design.py:146`), the four cause functions (`gauntlet/core/causes.py:49`, `gauntlet/core/causes.py:77`, `gauntlet/core/causes.py:108`, `gauntlet/core/causes.py:145`), and `startable` (`gauntlet/core/schedule.py:17`) are reused. Their existing branch tests are at `tests/test_core_design.py:30`, `tests/test_core_causes.py:42` and `tests/test_core_schedule_startable.py:11`.

- **Records and resume have requirements but no implementation.** The state, trace and crash contract is at `docs/design.md:251`; resume is at `docs/design.md:236`. Product module placement is at `docs/design.md:275`; configuration and cap defaults are at `docs/config.md:9`. The CLI entry point names `gauntlet.seams.cli:main` at `pyproject.toml:12`. The JSON readers in `gates/check_cast.py:88`, `gates/check_mypy.py:41` and `gates/check_pyright.py:111` read checker reports, not job records. They are not product codecs.

- **The shell gate has an existing host.** `gates/core/source.py:63` owns pinned-grammar parsing; `gates/core/runner.py:259` owns gate execution; `gates/core/report.py:50` owns gate exit status. The shell gate uses these homes, as required at `docs/superpowers/specs/gates-core-design.md:400`. It enforces the product's command-parsing prohibition (`docs/design.md:18`), not a command allowlist.

The refactor-request proposal is unapproved (`docs/superpowers/specs/refactor-request-design.md:1`). Its GREEN-keeps rule conflicts with the current every-line-RED requirement (`docs/design.md:44`). M1 follows the latter; it adds no MISPLACED category, refactor flag or keeps exception. This conflict is decision 5. Feature routing, reopen, effects that launch containers, git execution and screens remain at their roadmap milestones (`docs/roadmap.md:50`, `docs/roadmap.md:59`, `docs/roadmap.md:106`, `docs/roadmap.md:126`).

## Modules

Imports run from errors and verdicts into codec, from codec into config and roles, from verdicts into design and then causes, and from these homes into decide; schedule stays independent and seams import core. Product code imports no gates. The proposed consolidation makes verdicts independent of design, causes and decide. Only the existing domain functions stay in design and causes. Every function below has a stub body of `raise NotImplementedError`; ellipses denote that body in this document, and record bodies define fields. Existing record fields below preserve the cited interfaces.

### `gauntlet/core/verdicts.py` — the one definition of every product record, answer payload and enum

It defines Anchor, Category, Finding, Candidate, CoreMissing, Survey and core_missing_problems (`gauntlet/core/verdicts.py:9` through `gauntlet/core/verdicts.py:84`). The six design records use the fields specified at `gauntlet/core/design.py:15` through `gauntlet/core/design.py:67`; the three cause records use those at `gauntlet/core/causes.py:12` through `gauntlet/core/causes.py:34`. Their behavior modules import these canonical classes and define their own decision functions.

```python
from __future__ import annotations
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
```

```python
@dataclass(frozen=True)
class Anchor:
    path: str
    line: int

class Category(StrEnum):
    DEFECT = "defect"; COPY = "copy"; OWN_CORE = "own-core"
    DRIFT = "drift"; MISSING = "missing"

@dataclass(frozen=True)
class Finding:
    anchor: Anchor
    scenario: str
    category: Category
    blocking: bool
    concern: str | None
    also: tuple[Anchor, ...] = ()

@dataclass(frozen=True)
class Candidate:
    concern: str
    payoff: str
    risk: str
    keeps: tuple[str, ...]
    why: str | None = None

@dataclass(frozen=True)
class CoreMissing:
    need: str
    candidate: Candidate
    also: tuple[Anchor, ...]

@dataclass(frozen=True)
class Survey:
    findings: tuple[Finding, ...]
    candidates: tuple[Candidate, ...]
    sound: tuple[str, ...]

def core_missing_problems(missing: CoreMissing, *,
                          blocked: bool) -> tuple[str, ...]: ...
```

```python
@dataclass(frozen=True)
class Stub:
    name: str
    text: str

@dataclass(frozen=True)
class Module:
    path: str
    job: str
    stubs: tuple[Stub, ...]
    replaces: tuple[Anchor, ...]

@dataclass(frozen=True)
class Home:
    concern: str
    module: str
    forbids: str

@dataclass(frozen=True)
class Step:
    name: str
    paths: tuple[str, ...]
    implementer: str

@dataclass(frozen=True)
class Choice:
    question: str
    recommend: str
    alternative: str
    cost: str

@dataclass(frozen=True)
class Design:
    modules: tuple[Module, ...]
    homes: tuple[Home, ...]
    order: tuple[Step, ...]
    choices: tuple[Choice, ...]
```

```python
@dataclass(frozen=True)
class Cause:
    id: str
    claim: str
    concern: str | None
    findings: tuple[Finding, ...]

@dataclass(frozen=True)
class FixStep:
    cause: Cause
    implementer: str
    paths: tuple[str, ...]

@dataclass(frozen=True)
class DesignChange:
    cause: Cause
```

```python
class Stage(StrEnum):
    BRIEF = "brief"; DISCOVERY = "discovery"; OUTLINE = "outline"
    DESIGN = "design"; PLAN = "plan"; SPEC = "spec"; STUBS = "stubs"
    TESTS = "tests"; RED_RUN = "red-run"; LOCK = "lock"; BUILD = "build"
    REVIEW = "review"; BAILIFF = "bailiff"; LAND = "land"

class Shape(StrEnum):
    JOB = "job"; TEST_AUDIT = "test-audit"; STRUCTURE = "structure"

class Verdict(StrEnum):
    PASS = "pass"; FAIL = "fail"; COULD_NOT_JUDGE = "could-not-judge"

class Loop(StrEnum):
    DESIGN = "design"; PLAN = "plan"; SPEC = "spec"; JUROR = "juror"
    BUILD = "build"; REVIEW = "review"; REOPEN = "reopen"

class Kind(StrEnum):
    JUDGE = "judge"; READER = "reader"; COORDINATOR = "coordinator"
    SCRATCH = "scratch"; TESTER = "tester"; IMPLEMENTER = "implementer"

class RedVerdict(StrEnum):
    RED = "red"; ERROR = "error"; GREEN = "green"
    INVALID = "invalid"; COULD_NOT_JUDGE = "could-not-judge"

class BuildStatus(StrEnum):
    COMPLETE = "complete"; PARTIAL = "partial"; BLOCKED = "blocked"
```

All records below are frozen dataclasses. Collections are tuples, including key/value entries; a frozen record contains no mutable dict or list. Identifiers and paths are exact strings, not normalized by core code. Anchor retains its existing constructor behavior, including preservation of supplied line values (`tests/test_core_records.py:82`); wire validation rejects an invalid incoming anchor without changing that constructor.

```python
class Brief:
    text: str

class Citation:
    claim: str
    anchor: Anchor

class Discovery:
    citations: tuple[Citation, ...]

class PlanStep:
    step: Step
    serves: tuple[str, ...]
    stubs: tuple[Stub, ...]

class Outline:
    steps: tuple[Step, ...]
    areas: tuple[str, ...]
    shared_structure: bool = False

class Plan:
    steps: tuple[PlanStep, ...]

class SpecLine:
    id: str
    claim: str
    bite: str

class Collateral:
    test_id: str
    assertion: str
    disposition: str

class Spec:
    lines: tuple[SpecLine, ...]
    collateral: tuple[Collateral, ...]

class SpecDefect:
    line: str
    claim: str
    evidence: tuple[Citation, ...]
```

PlanStep adds spec coverage and stubs around the existing Step, not another name/paths/implementer triple. SPEC validates stable unique ids, nonblank claims and bites. In a STRUCTURE job, each Candidate.keeps string appears verbatim as a claim; missing keeps fails the spec round. Its tests still need RED under the current behavior. A previously satisfied keeps claim reaches the arbiter as a spec/test conflict; no passing test silently becomes red evidence.

```python
class Check:
    id: str
    verdict: Verdict
    reason: str
    citations: tuple[Anchor, ...]

class CheckSet:
    checks: tuple[Check, ...]
    disposition: str  # continue, refuse, escalate-leave

class SpecRuling:
    line: str
    verdict: Verdict
    reason: str

class SpecJudgment:
    rulings: tuple[SpecRuling, ...]

class Evidence:
    measurements: tuple[Citation, ...]

class TestBinding:
    line: str
    ids: tuple[str, ...]

class TestAnswer:
    bindings: tuple[TestBinding, ...]
    untestable: tuple[str, ...]

class RedLine:
    line: str
    verdict: RedVerdict
    tests: tuple[str, ...]

class RedJudgment:
    lines: tuple[RedLine, ...]
```

```python
class BuildAnswer:
    step: str
    status: BuildStatus
    reason: str
    missing: CoreMissing | None = None

class ReviewAnswer:
    findings: tuple[Finding, ...]

class CausesAnswer:
    causes: tuple[Cause, ...]

class Pin:
    line: str
    verdict: str  # pin, unpinned, could-not-judge
    reason: str

class CollateralRuling:
    test_id: str
    verdict: str  # held, altered, could-not-judge
    reason: str

class BailiffAnswer:
    pins: tuple[Pin, ...]
    collateral: tuple[CollateralRuling, ...]

class AuditRow:
    test_id: str
    verdict: str  # valid, strike, amend, note, could-not-judge
    reason: str

class AuditAnswer:
    rows: tuple[AuditRow, ...]

class EpicJob:
    id: str
    brief: str
    depends: tuple[str, ...]
    areas: tuple[str, ...]

class EpicAnswer:
    jobs: tuple[EpicJob, ...]
    stop: str | None

type Payload = (Brief | Discovery | Outline | Design | Plan | Spec
    | CheckSet | SpecJudgment | Evidence | TestAnswer | RedJudgment
    | BuildAnswer | ReviewAnswer | CausesAnswer | BailiffAnswer
    | Survey | AuditAnswer | EpicAnswer)

class RoleAnswer:
    payload: Payload
    spec_defect: SpecDefect | None = None
```

Payloads for later stages define their wire contracts, not implementations of those milestones. String verdict fields above have exactly the values in their comments; codec validation rejects others. A spec_defect is accepted and recorded but stops with reopen unavailable until M8. Judge inability is always explicit; absent or duplicate required rows fail validation, and an empty answer never proves a check ran.

```python
class Caps:
    design: int = 2
    plan: int = 2
    spec: int = 2
    juror: int = 2
    build: int = 2
    review: int = 2
    reopen: int = 2

class TestCommand:
    directory: str
    run: str

class InterfaceCommand:
    language: str
    run: str

class RoleSetting:
    name: str
    model: str | None
    effort: str | None

class Config:
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

class RoleSpec:
    name: str
    kind: Kind
    schemas: tuple[str, ...]

class StageRule:
    stage: Stage
    successor: Stage | None
    loop: Loop | None
    approval: bool
```

Schema names are stable codec tags. Planner has Outline, Plan and Spec tags; no guessed superset payload with optional fields replaces these answers.

```python
class CheckRow:
    id: str
    stage: Stage
    round: int
    check: str
    verdict: Verdict
    evidence: str

class Bypass:
    stage: Stage
    reason: str  # by-rule, unavailable, or owner; detail is mandatory
    detail: str

class Amendment:
    lines: tuple[str, ...]
    reason: str

class OwnerUse:
    command: str
    stage: Stage
    detail: str

class TraceRow:
    id: str  # one dispatched launch attempt, distinct from a retry or its effect
    role: str
    model: str
    effort: str
    tokens: int | None
    cost: str | None  # decimal text, not binary float
    outcome: str  # starting, running, complete, failed, interrupted

class Round:
    loop: Loop
    used: int

class Artifact:
    name: str
    revision: int
    answer: RoleAnswer

class StepRun:
    name: str
    attempt: int
    base_commit: str
    partial_diff: str | None
    status: str  # pending, running, partial, complete, blocked

class CauseRound:
    id: str
    failures: int
```

A CheckRow has a unique run id; repeated executions of the same check have different ids and all remain in state. Trace tokens and cost are unknown until reported, never zero by inference. Each dispatched launch attempt has one TraceRow, including failed startup, interruption or an invalid answer; scheduled work not yet dispatched has none. A starting row records uncertainty about whether an external agent began, not proof that it did.

```python
class Effect:
    id: str
    stage: Stage
    operation: str  # launch, checks, commit-tests, build, owner, land, stop
    role: str | None
    step: str | None
    input: Payload | None
    inputs: tuple[Artifact, ...]

class Pending:
    effect: Effect
    status: str  # ready, started, uncertain
    launch_id: str | None

class State:
    job: str
    revision: int
    shape: Shape
    stage: Stage
    status: str  # active, waiting, stopped, landed
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

class Action:
    state: State
    effects: tuple[Effect, ...]
```

Effect ids derive only from job, persisted stage/round/step attempt and effect position; no clock, random id or global counter enters decide. State contains the complete inputs needed to reproduce pending actions, including approved artifacts, caps, running steps, cause history and owner rulings. State validation rejects duplicate ids, invalid operation/role/step combinations, contradictory step status and missing required STRUCTURE input.

Effect.inputs is the immutable artifact selection for that role, including each selected revision; input is its primary payload. Neither executor nor launcher discovers extra stage context. Answered.trace closes the matching pending launch attempt with the reported model, effort, tokens and cost; unknown metrics stay None. A trace for a different effect, role or launch id is rejected.

```python
class Tick:
    pass

class Answered:
    effect: str
    role: str
    answer: RoleAnswer
    trace: TraceRow

class Checked:
    effect: str
    rows: tuple[CheckRow, ...]

class Approved:
    effect: str
    choices: tuple[tuple[str, str], ...]
    design: Design | None = None

class Completed:
    effect: str
    commit: str | None

class Failed:
    effect: str
    reason: str

type ExecutionAnswer = Answered | Checked | Approved | Completed | Failed
type Answer = Tick | ExecutionAnswer

class Receipt:
    effect: str
    event: Answer
type Json = None | bool | int | float | str | list[Json] | dict[str, Json]
```

Events identify their pending effect; stale, duplicate, wrong-role and wrong-stage events cannot advance it. Every accepted completion has a stored Receipt. An exact duplicate completion is a no-op only when its stored receipt matches; a conflicting receipt is a state error. Completed proves an I/O operation finished, never that a role's checks passed. Owner acceptance and skip remain distinct recorded controls, added to transitions by M4 rather than interpreted as ordinary Completed events.

### `gauntlet/core/errors.py` — typed product failures carrying data

It takes the existing UnownedPathError; causes retains UnownedPath as the same class. Gate and test-support exceptions are not imported or merged.

```python
class GauntletError(Exception):
    pass

class UnownedPathError(GauntletError):
    path: str
    def __init__(self, path: str) -> None: ...

class RecordError(GauntletError):
    location: str
    reason: str
    def __init__(self, location: str, reason: str) -> None: ...

class ConfigError(GauntletError):
    key: str
    reason: str
    def __init__(self, key: str, reason: str) -> None: ...

class StateError(GauntletError):
    effect: str
    reason: str
    def __init__(self, effect: str, reason: str) -> None: ...

class StorageError(GauntletError):
    path: str
    operation: str
    errno: int | None
    def __init__(self, path: str, operation: str, errno: int | None) -> None: ...

class RecoveryError(GauntletError):
    effects: tuple[str, ...]
    reason: str
    def __init__(self, effects: tuple[str, ...], reason: str) -> None: ...

class CapabilityError(GauntletError):
    operation: str
    def __init__(self, operation: str) -> None: ...
```

An error carries its original data and chained exception where there is one. A seam catches expected parser or operating-system exceptions at its boundary; it never returns an empty record, a success sentinel or a default configuration from an exception.

### Existing pure decision homes — design, causes and schedule

`gauntlet/core/design.py` owns its three existing functions; `gauntlet/core/causes.py` owns its four functions and imports the moved exception; `gauntlet/core/schedule.py` supplies startable through its existing interface. The record declarations move to verdicts; decision functions follow their documented input and output contracts. M3f supplies outline routing.

```python
# gauntlet/core/design.py
# Imports Stub, Module, Home, Step, Choice, Design from verdicts.
def design_problems(design: Design) -> tuple[str, ...]: ...
def home_of(design: Design, concern: str) -> Home | None: ...
def uncovered(design: Design, copies: Sequence[Anchor],
              done: Collection[str]) -> tuple[Anchor, ...]: ...

# gauntlet/core/causes.py
# Imports Cause, FixStep, DesignChange from verdicts.
# Imports UnownedPathError from errors; UnownedPath = UnownedPathError.
def finding_problems(finding: Finding, design: Design | None) -> tuple[str, ...]: ...
def partition_problems(findings: Sequence[Finding],
                       causes: Sequence[Cause]) -> tuple[str, ...]: ...
def route(cause: Cause, design: Design | None,
          owners: Mapping[str, str]) -> FixStep | DesignChange: ...
def survey_problems(survey: Survey, causes: Sequence[Cause]) -> tuple[str, ...]: ...

# gauntlet/core/schedule.py: existing implementation, no write step.
def startable(order: Sequence[tuple[str, frozenset[str]]],
              done: Collection[str], running: Collection[str],
              held: Collection[str]) -> tuple[str, ...]: ...
```

### `gauntlet/core/roles.py` — the registry relating each role to its kind and answer schemas

It replaces no implementation. It centralizes the role/schema relationship required by `docs/superpowers/specs/gates-core-design.md:397`; prompts name these schemas and never define copies.

```python
ROLES: tuple[RoleSpec, ...]
def role(name: str) -> RoleSpec: ...
def registry_problems(roles: Sequence[RoleSpec]) -> tuple[str, ...]: ...
```

| Role | Kind | Payload tags |
|---|---|---|
| brief-writer | reader | brief |
| detective | reader | discovery |
| planner | reader | outline, plan, spec |
| architect | reader | design |
| prosecutor | reader | check-set |
| examiner | scratch | evidence |
| arbiter | judge | spec-judgment |
| scrivener | tester | tests |
| juror | judge | red-judgment |
| implementer | implementer | build |
| reviewer | reader | review |
| structure-reviewer | reader | review |
| grouper | judge | causes |
| bailiff | judge | bailiff |
| surveyor | reader | survey |
| auditor | judge | audit |
| coordinator | coordinator | epic |

General implementers/testers and later repository specialists select the registered implementer, scrivener or reviewer contract, not an independently defined schema. Registry validation rejects duplicate role names, empty schema sets, unknown schema tags and a fixed role's wrong kind. A contract test parameterizes every registry row: each named schema exists, accepts its documented seed, and rejects a different payload; the registry has exactly the fixed roles above. Role-setting overrides change model/effort only. roles imports SCHEMAS from codec; codec consumes RoleSpec from verdicts and never imports roles.

### `gauntlet/core/codec.py` — one pure, versioned JSON codec and schema catalog

It replaces no product codec. It encodes all the record types through one explicit schema catalog; it never imports a Python module or evaluates a class name from record text. Internal nested adapters share primitive, enum and tuple decoding; no seam builds JSON objects or reconstructs dataclasses.

```python
FORMAT: int  # 1
SCHEMAS: tuple[str, ...]
def json_value(value: object) -> Json: ...
def encode_state(state: State) -> str: ...
def decode_state(text: str) -> State: ...
def encode_trace(trace: TraceRow) -> str: ...
def decode_trace(text: str) -> TraceRow: ...
def encode_answer(answer: RoleAnswer) -> str: ...
def decode_answer(text: str, spec: RoleSpec) -> RoleAnswer: ...
def answer_schema(spec: RoleSpec) -> Json: ...
def encode_document(payload: Payload) -> str: ...
def decode_document(text: str, schema: str) -> Payload: ...
```

State and answer envelopes have exactly format, schema and data keys. State's schema is state; answer data includes payload and optional spec_defect. Trace envelopes use trace and produce one compact JSON object plus a newline. Document encoding is a Markdown fenced JSON envelope; decoding requires that exact fence and a matching tag. This is the codec M3s's design/cause/survey writers extend, rather than another serialization path (`docs/superpowers/specs/structure-first-design.md:216`).

Unknown versions, tags or fields, missing required fields, wrong enum values, bools in integer fields, invalid ids, nonfinite numbers, duplicate JSON keys and malformed JSON raise RecordError with field location and reason. Omitted fields receive only the defaults declared above or in the preserved record interfaces; required fields never default. Unicode, tuple order, exact relative path strings and decimal cost text round-trip. Encoding orders keys deterministically; readers do not require an input key order. An unknown format stops resume; M1 supplies no migration or heuristic repair.

Codec contracts precede consumer tests: all record types round-trip; each fixed role's answer schema and decoder agree; malformed wire values fail at the same field path; empty successful reviews round-trip; every declared record field survives. Tests seed expected wire values from this document and compare decoded values with supplied inputs, never with generated expected output.

### `gauntlet/core/config.py` — validation of repository configuration without I/O

It replaces no reader. Defaults live only in Config and Caps; validation reads those values, rather than restating numeric cap defaults in decide, roles or tests.

```python
def config_from_json(value: Json) -> Config: ...
def config_problems(config: Config) -> tuple[str, ...]: ...
```

The keys and defaults are those of `docs/config.md:29`. Required keys are image, tests, gates, test_policy and interface. Tests and interface have at least one entry; caps are positive integers, excluding bool; duplicate directories, languages, role overrides and YAML keys fail. Unknown keys fail with their full key path. Every missing optional field takes its record default. Commands and their placeholders remain opaque strings: no splitting, interpolation or shell inspection occurs here. M2/M3 own execution and interface expansion. Config errors identify a key, never include credentials or read environment variables.

### `gauntlet/core/decide.py` — the stage table and pure state transition

It replaces no existing decide implementation. Stage and Shape are the exact classes imported from verdicts; FIRST and SKIPPED remain here, along with the one stage table.

```python
FIRST: Mapping[Shape, Stage]  # JOB: BRIEF; TEST_AUDIT: SPEC; STRUCTURE: DESIGN
SKIPPED: Mapping[Shape, frozenset[Stage]]
# TEST_AUDIT: STUBS, BUILD, REVIEW; JOB and STRUCTURE: empty
STAGES: tuple[StageRule, ...]
def initial(job: str, shape: Shape, config: Config, *,
            candidate: Candidate | None = None,
            copies: tuple[Anchor, ...] = ()) -> State: ...
def state_problems(state: State) -> tuple[str, ...]: ...
def decide(state: State, answer: Answer) -> Action: ...
```

STAGES follows Stage's displayed order. LAND has no successor. DESIGN, PLAN, SPEC and LAND require owner approval; the JOB outline approval belongs to its later implementation. DESIGN, PLAN, SPEC, RED_RUN, BUILD and REVIEW use design, plan, spec, juror, build and review caps respectively. BAILIFF failure stops. Cap use is explicit persisted data: a failed attempt increments used; reaching the configured cap stops with the current answer and objections retained. A fresh round is a fresh effect and agent, not an agent session resumed.

M1 implements every row a STRUCTURE job walks. JOB-only BRIEF, DISCOVERY and OUTLINE and TEST_AUDIT-specific behavior have their FIRST/SKIPPED data but stop as unavailable if reached; their implementations remain M3f, M9 and M10. No unavailable row becomes PASS. M3s may request documented omissions as Bypass entries; the core records and exposes each omission, and does not invent one for itself.

- **DESIGN:** launch architect, validate design_problems, require a home for candidate.concern, and call uncovered with opened copies and done empty. Any problem fails the design round. A valid design waits for owner rulings on every choice and approval. Approval is a harness event carrying the resolved design; a nonempty choices tuple cannot advance. PLAN receives that approved design, not an absent outline.

- **PLAN and SPEC:** planner produces steps based on approved order; every plan path and implementer agrees with its design step. PLAN waits for approval after its required checks pass. SPEC preserves every candidate.keeps claim and waits after its required rulings pass. Required check ids come from the stage's requested work and must each have an explicit row. A FAIL or COULD NOT JUDGE blocks. An arbitrary empty collection is not a successful check batch.

- **STUBS, TESTS, RED_RUN and LOCK:** the first STUBS work is the approved shared design's stubs, followed by plan-step stubs; completed stub work is persisted. TESTS requires bindings for every stable spec id, with no duplicate or unknown ids and no untestable line. RED_RUN schedules every Config.tests runner and requires every line's juror verdict RED; ERROR, GREEN, INVALID, missing and COULD NOT JUDGE block. LOCK is a commit-tests effect only after that evidence is durable. Core never performs the commit.

- **BUILD:** startable selects work from plan paths, done, running and held. STRUCTURE emits every selected step; other shapes, when implemented, emit only the first. Each selected step has its own effect, attempt and base commit. Complete is accepted only after its tests and gates have explicit passing rows and its commit receipt arrives. Partial keeps its diff and schedules a fresh implementer from the recorded base/diff; it is not reapplied on top of itself. Blocked stops at M1. CoreMissing is validated with core_missing_problems and retained; its spawn/offer behavior waits for M8.

- **REVIEW:** validate findings with finding_problems, record rejected findings and their problems, then request the grouper on those that stand. Invalid partition_problems is COULD NOT JUDGE. Route each blocking cause once through route. FixSteps return to BUILD with cause identities retained. A recurrent cause id increments its review failures; a new id does not erase the round cap. A DesignChange stops with the cause until M8. An unowned route raises the typed error. The structure surveyor's current-copy findings join the same grouping. REVIEW exits only after uncovered with all plan steps done and the current surveyed copies is empty; copies at different line anchors remain distinct.

- **BAILIFF and LAND:** every spec line needs PIN and every collateral row its required HELD/ALTERED ruling; inability or missing rows blocks. LAND requests owner approval with checks, bypasses, amendments, controls and launch costs retained. Approval yields a land effect; only its successful receipt marks landed. M1 neither merges git nor fabricates that receipt.

Tick reproduces existing pending effects without allocating new ids. With no pending work it computes the next effects from persisted state. Started or uncertain effects are exposed for reconciliation, not dispatched again. An absent external capability stops with an explicit pending operation; it neither consumes a check round nor loses the pending input. No retry, acceptance, edit, skip, eject, reopen or feature-routing implementation is smuggled into Tick.

### `gauntlet/seams/config.py` — the one YAML reader

It replaces no implementation. It reads exactly the assigned root's gauntlet.yaml and feeds the core config validator; no cwd search, host defaults or second reader exists.

```python
def read_config(root: Path) -> Config: ...
```

A safe YAML loader accepts only JSON-compatible scalars and collections, rejects duplicate keys before constructing a dict, and cannot construct Python objects. It converts parser values through the codec's shared JSON-value validation before core config validation. File failures become StorageError; parse and schema failures become ConfigError. The safe loader and its typing dependency are direct pinned project/development dependencies as appropriate, added in Order before this reader; selecting their lock versions is dependency maintenance, not a second configuration design.

### `gauntlet/seams/job.py` — the only state/trace writer, lock owner and durable checkpoint boundary

It replaces no implementation. It owns each job's state.json and trace.jsonl, as required by `docs/design.md:257`. M3s's named design/cause/survey/open_structure functions are later additions to this module, not competing writers.

```python
class JobStore:
    def __init__(self, job: Path) -> None: ...
    def __enter__(self) -> JobStore: ...
    def __exit__(self, exc_type: type[BaseException] | None,
                 exc: BaseException | None,
                 traceback: TracebackType | None) -> None: ...
    def load(self) -> State: ...
    def create(self, state: State) -> None: ...
    def save(self, state: State, *, expected_revision: int) -> None: ...
    def repair_trace(self, state: State) -> None: ...
```

The host is macOS or Linux. A nonblocking advisory lock in the job folder admits one harness writer; a busy lock is StorageError with operation lock. All writes use exclusive temporary files in that folder, UTF-8, flush, fsync, atomic replace, then directory fsync. Revision mismatch fails before replacement. Create never overwrites an existing state. Save advances revision exactly once and validates the entire state before publication. A failed write preserves the previous committed snapshot or the new complete one, never a partly decoded state.

State is authoritative and includes its launch ledger. trace.jsonl is a deterministic projection of that ledger, one line per dispatched launch attempt. Save durably replaces state first, then trace; load repairs a stale or torn projection from state. Thus a death between the two replacements cannot lose a recorded launch or add another launch on recovery. A corrupt state stops; a corrupt projection is regenerated, not used to infer state. No state migration, backup fallback or guess from log text occurs.

A pending effect is saved ready before dispatch, then saved started before external work. A launch's started checkpoint includes its TraceRow. On completion, answer/check rows, trace outcome, receipt and resulting action are saved together before any successor effect starts. Abrupt death with started work leaves uncertainty: resume stops for reconciliation under decision 2. Finally removes only temporary files this invocation owns and releases the lock; process death releases the operating-system lock. Orphan temporary files never become authoritative.

### `gauntlet/seams/resume.py` — loading and dispatching persisted actions through an injected executor

It replaces no implementation. It contains no stage routing, shell/process runner, git calls or SDK calls.

```python
class Executor(Protocol):
    def __call__(self, effect: Effect) -> ExecutionAnswer: ...

def pending_action(job: Path) -> Action: ...
def resume(job: Path, *, execute: Executor) -> State: ...
```

pending_action locks, loads, repairs trace and returns decide(state, Tick()). resume holds the single-writer lock, persists each proposed action before dispatch, marks each dispatched effect started, feeds its returned event into decide and durably saves the result. It stops on owner wait, land, explicit stop, unavailable capability or uncertain work. Parallel BUILD effects remain independent pending identities; M1 dispatches them through the executor in stable order, while M3s supplies concurrent execution and serializes completions through this writer.

An interrupted pending effect that was only ready is reproducible with the same id and input. Started work raises RecoveryError with the uncertain effect ids and preserves state; no agent, check, commit or land operation is automatically repeated. M2/M3 reconciliation will supply receipts or explicit owner resolution, never assume idempotency. A dead harness does not cause a completed checkpoint to consume another round or schedule a duplicate effect.

### `gauntlet/seams/cli.py` — parsing resume arguments and translating typed failures into output/status

It fills the existing entry point (`pyproject.toml:12`) and replaces no CLI. It is M1's sole terminal writer; screens take rendering over at M3s.

```python
def render_action(action: Action) -> str: ...
def render_error(error: GauntletError) -> str: ...
def exit_code(error: GauntletError | None) -> int: ...
def main(arguments: Sequence[str] | None = None, *,
         execute: Executor | None = None) -> int: ...
```

The command is gauntlet resume <id>; id is a single job-folder component, excluding dot, dot-dot and path separators. The caller's repository root supplies .gauntlet/jobs/<id>, with no alternate job discovery. M1 main uses its explicit CLI cwd as that root; tests supply cwd through their process runner, not Path.cwd assertions. Output names the persisted stage and pending operations, or the typed failure's fields. Successful owner wait or finished work returns 0; stopped/uncertain/unavailable work and typed failures return 2. Bad CLI syntax follows argparse's status 2. A missing executor reports CapabilityError and preserves pending work; it never marks that work complete. New/run/audit/status and owner controls remain their roadmap work.

### `gates/check_shell.py` — a local AST gate against shell-parsing facilities in product code

It uses Run, source.parse and report.Outcome instead of copying gate selection, Python-file discovery, source reading, output, error or exit handling (`gates/core/runner.py:134`, `gates/core/source.py:63`, `gates/core/report.py:43`). It runs no checker or product code.

```python
def parsing_findings(parsed: Parsed) -> tuple[Finding, ...]: ...
def check(run: Run) -> Outcome: ...
GATE: Gate
def main(paths: Sequence[Path]) -> int: ...
```

Every input Python file is counted and parsed through the shared grammar home; findings apply to gauntlet/ code. A prohibited AST use is an import or from-import of shlex, bashlex, bashparser, bashparserlib or shellparse, their submodules included; an importlib.import_module or __import__ call with one of those literal module names; or shell=True passed to subprocess execution. Resolve aliases of importlib, __import__, subprocess and their directly imported names in the module's imports. One finding names the source anchor and prohibited construct. A shadowed or dynamically computed target is not falsely claimed to be resolved.

These syntactic checks are a bounded gate, not proof that arbitrary Python never interprets commands. Review still rejects hand-written command tokenizers, regex interpreters, computed imports and alternate parser packages. Configuration command strings travel verbatim to M2/M3's execution boundary; invoking a configured shell in an isolated runner is distinct from the harness parsing its text. The gate contains no shell-command parser. Tests exercise every prohibited syntax and alias form, safe opaque storage/forwarding, shadowing, malformed source and the shared empty-run/exit contract. No exception list or suppression is added.

### `tests/support/answers.py` — literal builders for records and input events

It replaces the four factory sites counted in Why. Builders construct supplied records; they never call decide, validators or codec to compute an expected answer.

```python
def anchor(path: str = "pkg/a.py", line: int = 1) -> Anchor: ...
def finding(*, anchor: Anchor = ..., scenario: str = "a call fails",
            category: Category = Category.DEFECT, blocking: bool = True,
            concern: str | None = None, also: tuple[Anchor, ...] = ()) -> Finding: ...
def design(*, modules: tuple[Module, ...] = ...,
           homes: tuple[Home, ...] = ..., order: tuple[Step, ...] = ...,
           choices: tuple[Choice, ...] = ()) -> Design: ...
def cause(*, id: str = "c1", claim: str = "one cause",
          concern: str | None = None,
          findings: tuple[Finding, ...] = ...) -> Cause: ...
def candidate(*, concern: str = "process running", payoff: str = "one runner",
              risk: str = "a caller breaks", keeps: tuple[str, ...] = (),
              why: str | None = None) -> Candidate: ...
def survey(*, findings: tuple[Finding, ...] = (),
           candidates: tuple[Candidate, ...] = (),
           sound: tuple[str, ...] = ()) -> Survey: ...
def missing(*, need: str = "one shared policy",
            candidate: Candidate = ..., also: tuple[Anchor, ...] = ()) -> CoreMissing: ...
```

Default design is Module("pkg/home.py", "one line", (), ()), Home("process running", "pkg/home.py", "running a process"), Step("s1", ("pkg/home.py",), "core-builder"), with no choices. Default cause contains the default finding. Default finding.anchor is anchor(); default missing.candidate is candidate(). Helpers' keyword overrides replace only their named field, and no default contains a mutable collection.

```python
class ConfigChanges(TypedDict, total=False):
    image: str
    tests: tuple[TestCommand, ...]
    gates: str
    test_policy: str
    interface: tuple[InterfaceCommand, ...]
    test_helpers: tuple[str, ...]
    protected: tuple[str, ...]
    test_lint: str | None
    implementer_network: bool
    caps: Caps
    roles: tuple[RoleSetting, ...]
```

```python
class StateChanges(TypedDict, total=False):
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

def config(**changes: Unpack[ConfigChanges]) -> Config: ...
def state(**changes: Unpack[StateChanges]) -> State: ...
def answer(payload: Payload = ..., *, effect: str = "e1",
           role: str = "architect",
           spec_defect: SpecDefect | None = None,
           trace: TraceRow = ...) -> Answered: ...
def seed(schema: str) -> Payload: ...
```

ConfigChanges and StateChanges are total=False TypedDict views of the exact Config and State fields above, with no added keys or object/Any fields. Config's seed is image ".gauntlet/Containerfile", one tests entry ("tests", "pytest {ids}"), gates "make check", test_policy "docs/testing.md", one interface entry ("py", "stubgen -o {out} {modules}"), and the declared optional defaults. State's seed is job "j1", revision 0, STRUCTURE/DESIGN/active, that config, candidate(), no copies and empty remaining tuples. Answer's default payload is design(). seed returns a documented, nonblank literal specimen for each registry payload tag; the helper's own test pins each specimen before codec tests use it. The seed table below fixes each specimen; nested builder calls use only the defaults above.

| Tag | Literal specimen |
|---|---|
| brief | Brief("one request") |
| discovery | Discovery((Citation("one claim", anchor()),)) |
| outline | Outline((Step("s1", ("pkg/home.py",), "core-builder"),), ("pkg",), False) |
| design | design() |
| plan | Plan((PlanStep(Step("s1", ("pkg/home.py",), "core-builder"), ("S1",), ()),)) |
| spec | Spec((SpecLine("S1", "one claim", "one measured value"),), ()) |
| check-set | CheckSet((Check("c1", Verdict.PASS, "one reason", (anchor(),)),), "continue") |
| spec-judgment | SpecJudgment((SpecRuling("S1", Verdict.PASS, "one reason"),)) |
| evidence | Evidence((Citation("one measurement", anchor()),)) |

| Tag | Literal specimen |
|---|---|
| tests | TestAnswer((TestBinding("S1", ("tests/test_a.py::test_a",)),), ()) |
| red-judgment | RedJudgment((RedLine("S1", RedVerdict.RED, ("tests/test_a.py::test_a",)),)) |
| build | BuildAnswer("s1", BuildStatus.COMPLETE, "one result") |
| review | ReviewAnswer(()) |
| causes | CausesAnswer((cause(),)) |
| bailiff | BailiffAnswer((Pin("S1", "pin", "one reason"),), ()) |
| survey | survey() |
| audit | AuditAnswer((AuditRow("tests/test_a.py::test_a", "valid", "one reason"),)) |
| epic | EpicAnswer((EpicJob("j1", "one request", (), ("pkg",)),), None) |

The port replaces _design/_finding/_missing calls with shared builders carrying the old field values explicitly. No assertion, input record value, expected problem string or test id changes. The four original local factories are removed. Tests that deliberately construct or mutate records to prove their field behavior retain those direct constructors. Answer's default trace is TraceRow("e1.launch", "architect", "model", "medium", None, None, "complete"); an explicit role/effect change requires a matching explicit trace.

### `tests/support/recovery.py` — deterministic crash probes and literal executor replies

It replaces no support module. It uses existing pipe coordination (`tests/support/lifeline.py:45`) and output capture (`tests/support/capture.py:362`), not sleeps, polling deadlines or a second child-process manager.

```python
class Replies:
    def __init__(self, values: Sequence[ExecutionAnswer]) -> None: ...
    def __call__(self, effect: Effect) -> ExecutionAnswer: ...
    @property
    def seen(self) -> tuple[Effect, ...]: ...

class RepliesExhaustedError(Exception):
    seen: tuple[Effect, ...]
    def __init__(self, seen: tuple[Effect, ...]) -> None: ...

def checkpoint_child(job: str, ready: int, release: int,
                     replies: tuple[ExecutionAnswer, ...]) -> None: ...
```

Replies records each effect and returns the next supplied literal Answer; exhausted replies raise a typed support error, never compute a production response. checkpoint_child announces the committed checkpoint over ready and waits on release at the executor boundary. The parent kills it only after the announcement, joins by process exit and reloads the real temporary job. The ordinary pytest timeout is the failure bound.

## Homes

| Shared concern | One home | Forbids elsewhere |
|---|---|---|
| Product records, enums and answer fields | core/verdicts.py | A second definition in design, causes, roles, seams or tests; proposed move of the three existing definition sites counted in Why, subject to decision 1. |
| Design validity and copy coverage | core/design.py | A second design validator or copy/port calculation in decide, job, land or survey code. |
| Finding validity, cause partition and routing | core/causes.py | A seam filtering findings, routing one instance or inventing a design-change rule. |
| File overlap and runnable work | core/schedule.py:startable | A scheduling copy in decide, resume or an executor. |
| Role/kind/schema association | core/roles.py | A launcher, prompt or CLI inventing a schema or changing a fixed role's kind. |
| JSON, Markdown record envelopes and schema export | core/codec.py | json.loads/dumps, envelope versions or record reconstruction in seams and role prompts; checker-report codecs remain in gates. |
| Typed product errors | core/errors.py | Another product exception family, bare errors crossing a seam, or success defaults after read/parse failures; replaces causes.py:37. |
| Config values and defaults | Config/Caps plus core/config.py | Cap defaults or config interpretation in another piece. |
| Config filesystem/YAML access | seams/config.py | Another gauntlet.yaml reader, cwd search or command parser. |
| Stage table, rounds and next action | core/decide.py | Stage routing, cap decisions or fabricated check success in seams. |
| Durable checkpoints, state/trace I/O, lock and temporary cleanup | seams/job.py | Another state/trace writer, a trace-derived resume, broad temp deletion or cleanup in the executor. |

| Shared concern | One home | Forbids elsewhere |
|---|---|---|
| Dispatch/recovery protocol | seams/resume.py | Automatic replay of uncertain external work or a second decide loop in CLI. |
| Product output and exit status during M1 | seams/cli.py | Terminal writes or CLI status choices in core, job, config or resume; M3s supplies screens. |
| Process execution and process cleanup | M2 process seam, not introduced here | Any product subprocess/git/container implementation in M1; an executor missing that capability reports it. |
| Shell gate execution, grammar, output/errors | existing gates/core/runner.py, source.py and report.py | Copies of gate infrastructure in check_shell or product code. |
| Shell-parsing syntactic rules | gates/check_shell.py | Parsing shell text or restating its findings in another gate; semantic command parsing remains blind review's finding. |
| Product test factories | tests/support/answers.py | Local _design, _finding and _missing factories at the four counted sites, or deriving expectations from implementation. |
| Recovery probe coordination | tests/support/recovery.py using lifeline and capture | Sleeps, host-clock reads, hand-written child reaping or a fake that calculates its answer. |

## Order

Every code chain has stubs before its red tests and builds after the recorded red run. test-writer reads only this design, behavior docs and stubgen interfaces. A red row below is one or more consecutive behavior dispatches under the current red-step limits, never permission to read implementation. Shared builders and their own tests precede consumer tests. Existing tests are ported with byte-identical assertions, never edited to pass new code. Blind reviews receive only the diff scope; the coordinator runs make check in full, unpiped before each commit and names specified gates it does not run.

Steps 1–5 wait for decision 1; every remaining step waits for owner approval of this design. A later architect rulings pass carries any approved changes required in the affected existing design documents; this dispatch writes none of them. No plan's implied acceptance of an open recommendation is an owner ruling.

| Step | Agent | Paths written | Contract / dependency |
|---|---|---|---|
| 1 port | test-writer | tests/support/answers.py, tests/test_support_answers.py | The seven existing-record builders and their pinned defaults, before consumer ports. |
| 2 port | test-writer | tests/test_core_design.py, tests/test_core_causes.py, tests/test_core_verdicts.py | Remove the four local factories; preserve every input and assertion. |
| 3 stub | core-builder | gauntlet/core/verdicts.py | Add the complete canonical design/cause record declarations before identity tests import them. |
| 4 red | test-writer | tests/test_core_record_homes.py | Every old design/cause import is the canonical verdicts class; assertions fail while the old definitions remain. |
| 5 build | core-builder | gauntlet/core/design.py, gauntlet/core/causes.py | Replace the old record definitions with canonical imports on step 4; existing decision and payload tests stay green. |
| 6 stub | core-builder | gauntlet/core/errors.py | Typed error constructors, including the existing unowned-path contract. |
| 7 red | test-writer | tests/test_core_errors.py | Every exception's exact data and hierarchy, including alias identity. |
| 8 build | core-builder | gauntlet/core/errors.py, gauntlet/core/causes.py | Error behavior and unowned-path port on step 7; no change to route outputs. |
| 9 stub | core-builder | gauntlet/core/verdicts.py | New records and enums as complete declarations, no decision behavior. |
| 10 port | test-writer | tests/support/answers.py, tests/test_support_answers.py | Config/State/Answer builders and schema seeds with pinned literal values. |
| 11 stub | core-builder | gauntlet/core/codec.py | The shared catalog, wire/JSON-value adapters and all codec interfaces. |

| Step | Agent | Paths written | Contract / dependency |
|---|---|---|---|
| 12 red | test-writer | tests/test_m1_records.py | Decoded records preserve complete payloads, frozen fields and defaults; schema export has the exact enums. |
| 13 red | test-writer | tests/test_core_codec.py | Round-trip all records; exact envelopes and every malformed value branch. |
| 14 build | core-builder | gauntlet/core/codec.py | Steps 12–13; no I/O or dynamic class import. |

| Step | Agent | Paths written | Contract / dependency |
|---|---|---|---|
| 15 stub | core-builder | gauntlet/core/roles.py | Registry and lookup/validation interfaces, using codec's schema catalog. |
| 16 red | test-writer | tests/test_core_roles.py | All fixed roles, kinds, tags, invalid registries and every role/schema codec contract. |
| 17 build | core-builder | gauntlet/core/roles.py | Step 16; no schema declarations in roles or prompts. |
| 18 stub | core-builder | gauntlet/core/config.py | Pure config reader/validator interface. |
| 19 red | test-writer | tests/test_core_config.py | Required/optional keys, all defaults, positive caps, duplicate entries, opaque commands and invalid values. |
| 20 build | core-builder | gauntlet/core/config.py | Step 19, using codec's shared JSON-value adapter. |
| 21 dependency | gatesmith | pyproject.toml, uv.lock | Safe YAML runtime dependency and required typing dependency, exactly locked. |
| 22 stub | seam-builder | gauntlet/seams/config.py | YAML reader only. |
| 23 red | test-writer | tests/test_seams_config.py | Explicit root, missing/unreadable YAML, duplicate keys, unsafe tags, non-JSON values and typed failures. |
| 24 build | seam-builder | gauntlet/seams/config.py | Step 23 on the core validator; no subprocess. |
| 25 stub | core-builder | gauntlet/core/decide.py | FIRST, SKIPPED, STAGES and initial/state_problems/decide interfaces. |
| 26 red | test-writer | tests/test_core_decide_state.py | Deterministic state/effect ids, event association, receipts, round boundaries, waits, unavailable rows and all shape data. |
| 27 build | core-builder | gauntlet/core/decide.py | Step 26; STRUCTURE stage dispatch stops at its not-yet-built row. |

| Step | Agent | Paths written | Contract / dependency |
|---|---|---|---|
| 28 red | test-writer | tests/test_core_decide_structure.py | DESIGN validity/coverage/approval, design stubs first, PLAN input and agreement, keeps at SPEC, tests/red/lock branches. |
| 29 build | core-builder | gauntlet/core/decide.py | Step 28 using existing validators; cap-1, cap-2 and COULD NOT JUDGE branches. |
| 30 red | test-writer | tests/test_core_decide_build.py | startable delegation, parallel pending identities, partial base/diff, blocked, test/gate receipts and CoreMissing validation without M8 spawn. |
| 31 build | core-builder | gauntlet/core/decide.py | Step 30; no second overlap rule or git execution. |
| 32 red | test-writer | tests/test_core_decide_review.py, tests/test_m1_contract.py | Review/bailiff/land branches and a literal STRUCTURE event walk, with missing/nonpassing evidence cases, red before their final rows are built. |
| 33 build | core-builder | gauntlet/core/decide.py | Step 32; every remaining STRUCTURE branch, including empty but explicitly executed review. |
| 34 stub | seam-builder | gauntlet/seams/job.py | JobStore interfaces and exclusive lock boundary. |
| 35 red | test-writer | tests/test_seams_job.py | Exact files, revisions, lock contention, failed publication, trace projection repair, corrupt-state rejection and owned cleanup. |
| 36 build | seam-builder | gauntlet/seams/job.py | Step 35 using only core codec for record text. |
| 37 stub | seam-builder | gauntlet/seams/resume.py | Executor, pending_action and resume interfaces. |
| 38 port | test-writer | tests/support/recovery.py, tests/test_support_recovery.py | Literal replies and event-controlled checkpoint probe, using existing lifeline/capture interfaces. |

| Step | Agent | Paths written | Contract / dependency |
|---|---|---|---|
| 39 red | test-writer | tests/test_seams_resume.py | Same next action after kill at committed ready checkpoint, no duplicate completed effect, started-effect uncertainty and repaired trace after publication failure. |
| 40 build | seam-builder | gauntlet/seams/resume.py | Step 39; real temporary files and killed child, injected executor, no real launcher. |
| 41 stub | seam-builder | gauntlet/seams/cli.py | Resume CLI and output/status interfaces. |
| 42 red | test-writer | tests/test_seams_cli_resume.py | Entry point, id validation, typed output/status, executor injection and unavailable-executor behavior. |
| 43 build | seam-builder | gauntlet/seams/cli.py | Step 42; all stage choices delegated to core/resume. |
| 44 stub | gatesmith | gates/check_shell.py | AST checker and existing gate host interfaces. |
| 45 red | test-writer | tests/test_check_shell.py, tests/test_check_shell_contract.py | Prohibited constructs and aliases, accepted opaque strings, shadowing, scope, grammar/empty-run contracts. |
| 46 build | gatesmith | gates/check_shell.py | Step 45 on shared gates core; no external checker. |
| 47 wire | gatesmith | Makefile, pyproject.toml | Add check_shell over every Python input and to the real-time import contract's explicit source-module list. |

Step 9's records have no behavioral bodies to implement. Step 12 tests their decoded values and exported schemas against the codec stub, so its red proof comes before codec behavior. Steps 9–14 share a commit chain rather than landing unused declarations. Codec precedes registry and pure configuration. Steps 21–24 share a chain so the YAML dependency has its importing consumer before deptry runs. Other stub/red/build groups land once their full red set is green. Steps 3–5 share a stub/red/build chain; temporary duplicate declarations never land. Step 32's event-walk contract is red before step 33 builds its missing final rows.

After the common record/codec base, config, decide, persistence and the gate are independent until their stated consumers need them. Work may use separate worktrees, but this design authorizes no extra writes or agent dispatches in the current design-only task. Existing gauntlet/core/schedule.py and gate infrastructure supply their documented interfaces to these pieces.

M1 is complete only after all named structure branches have their red-to-green proof and the killed-harness probe recovers the identical ready action with the same id, inputs, rounds, check rows and trace ledger. A second probe proves uncertain started work is retained and stopped, not silently repeated. Missing external executors stay visible as unavailable work; no fixture substitutes an actual agent/container launch.

## Decisions for the owner

1. **How does one record-type module fit the approved record homes?** Recommend moving the design/cause record declarations and stage/shape enum declarations into verdicts, keeping the old behavior modules and import identities. The existing approved design needs a focused rulings pass for those homes before the move. Alternative: retain domain-local records and have one codec catalog over them, revising the gates-core requirement for one record-type module instead. The recommendation moves declarations and preserves callers; the alternative preserves placement but relaxes that stated requirement. Implementation and maintenance costs on both sides are unmeasured.

2. **What is authoritative across a crash, and may started work replay?** Recommend atomic state snapshots containing launch rows, a repairable trace projection, and stopping on started/uncertain effects until reconciliation exists. Alternative: an append-only transactional event journal with state and trace as projections, plus effect-specific reconciliation before replay. The recommendation rewrites a growing snapshot and can stop after ambiguous work; the alternative adds a journal/replayer and still cannot promise exactly-once external effects without reconciliation. Space, time and recovery costs for both are unmeasured.

3. **How far does resume run before M2's executor exists?** Recommend the injected Executor contract and a working crash-recovery probe now, with the public CLI reporting unavailable execution when no executor is installed. Alternative: make M1 depend on the M2 launcher and M3s runner so the default CLI can dispatch real work immediately. The recommendation leaves a visible capability stop; the alternative moves those dependencies ahead of the roadmap's core-before-seams boundary. Effort and delay on both sides are unmeasured.

4. **What can the shell gate establish mechanically?** Recommend the exact AST prohibition listed above, plus blind review for command interpretation outside those forms. Alternative: a conservative whole-product data-flow checker rejecting any transformation of configured command strings. The recommendation cannot prove the semantic prohibition for arbitrary Python; the alternative needs a specified alias/flow model and rejects safe transformations when it cannot prove them safe. Detection coverage and maintenance costs for both are unmeasured. Neither option provides a suppression path.

5. **Which red-run rule holds for existing behaviors a structure job keeps?** Recommend retaining the current every-line-RED rule in this dispatch and ruling on the separate refactor-request proposal before a real structure pilot needs GREEN-keeps behavior. Alternative: approve that proposal first and return here on a rulings pass to add its SpecLine mark, red checks and examiner-bypass records. The recommendation leaves a real compatibility stop when a keeps claim already passes; the alternative expands M1 beyond the current approved roadmap behavior. Effort and pilot impact for both are unmeasured.

