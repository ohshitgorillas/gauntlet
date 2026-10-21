# Structure first in the harness

Status: approved.

## Why

Gauntlet builds structure first for itself, not for the repositories it builds in. The four pieces of this design (a design stage, review against the design, fixing by cause, and a structure audit) share one design record, one finding shape and one grouping of findings into causes. No product code exists yet, so every copy below is in the documents the code will be built from.

- **No design stage.** The stage table has no step between the outline and the plan that fixes the shared core (`docs/design.md:34`-`48`). Stubs come from each plan step (`docs/design.md:41`, `:57`, `:62`), so two steps needing one helper each stub their own.
- **Stages cited by number, 4 copies.** `docs/design.md:84`, `docs/design.md:93`, `docs/roadmap.md:95` and `docs/roadmap.md:107` repeat stage numbers from the table at `docs/design.md:34`. A new stage renumbers all of them.
- **The finding shape and its drop rule, 3 copies.** `docs/design.md:46`, `docs/design.md:74` and `docs/roadmap.md:81` each state it. None has a category, so a copied helper and a wrong boolean are one kind of finding.
- **Fixes routed one finding at a time, 2 copies.** `docs/design.md:74` and `docs/roadmap.md:81` send each blocking finding to the implementer of the step it cites, so three copies of one helper become three fixes.
- **Answer schemas with two homes.** `docs/design.md:271` puts them in `core/verdicts.py`; `docs/design.md:284` puts them in `roles/` with the prompts.
- **Audit covers tests only.** `gauntlet audit` judges tests against the test policy (`docs/design.md:93`, `docs/roadmap.md:107`, `docs/config.md:35`, `:69`). Nothing surveys for a missing core or a duplicated concern.
- **Round caps have no named reader.** `caps` is a `gauntlet.yaml` key (`docs/config.md:23`, `:40`), but no module in `docs/design.md` §8 (`:265`-`286`) reads the configuration.

The vocabulary below is the product form of rules that already bind Gauntlet's own build: the judgment layer's "duplicated concept, logic in the wrong home, a patch where a root-cause fix belongs" (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:158`), `diff-reviewer`'s categories (`docs/superpowers/specs/2026-10-18-agents-design.md:34`), and the design step that each milestone takes (`docs/superpowers/specs/2026-10-20-gates-core-design.md:364`-`372`). Those stay as rules for building Gauntlet; this design does not replace them.

## Modules

Core imports run in one chain: `verdicts` ← `design` ← `causes` ← `decide`, and `decide` also imports `schedule`, which imports none of them. `Outline`, `State`, `Answer` and `Action` are M1's types (`docs/design.md:270`-`271`); `Screen` and `Section` are M3's (`docs/superpowers/specs/2026-10-20-gates-core-design.md:391`). The codec that turns a record into job-folder text is M1's record codec (`docs/superpowers/specs/2026-10-20-gates-core-design.md:377`).

**`gauntlet/core/verdicts.py`.** The records every role's answer is built from: anchors, findings and their categories, the candidate structure job put to the owner, the survey, and an implementer's report that the core is missing something. It is the one home of answer schemas: `roles/` holds prompts that name a schema and never define one, replacing the second home at `docs/design.md:284`. One record, `Candidate`, carries every structure job to the owner, whether a survey ranks it or an implementer reports it. A CoreMissing on `blocked` with no `why`, or on `complete` or `partial` with one, fails its schema (decision 8).

```python
@dataclass(frozen=True)
class Anchor:                      # one place in the job tree
    path: str                      # relative to the tree root
    line: int                      # 1-based

class Category(StrEnum):
    DEFECT = "defect"              # wrong behavior, no design concern
    COPY = "copy"                  # the same logic in two or more places
    OWN_CORE = "own-core"          # a piece writes what a design home holds
    DRIFT = "drift"                # code departs from a design stub or home
    MISSING = "missing"            # audit only: a shared concern with no home

@dataclass(frozen=True)
class Finding:
    anchor: Anchor
    scenario: str                  # the failure scenario
    category: Category
    blocking: bool
    concern: str | None            # the shared concern it breaks; None only for DEFECT
    also: tuple[Anchor, ...] = ()  # every other place the logic sits, for COPY and MISSING

@dataclass(frozen=True)
class Candidate:                   # one structure job put to the owner
    concern: str
    payoff: str                    # what the core saves, one sentence
    risk: str                      # what porting the copies could break, one sentence
    keeps: tuple[str, ...]         # hard-won behaviors the copies carry, one line each, for the spec (decision 9)
    why: str | None = None         # set only when the request cannot be done correctly without it (decision 8)

@dataclass(frozen=True)
class CoreMissing:                 # carried by an implementer's `blocked`, `complete` or `partial`
    need: str                      # what the step needs from the core, one sentence
    candidate: Candidate           # its why set on `blocked` and only there
    also: tuple[Anchor, ...]       # every copy or caller of the concern the implementer found

@dataclass(frozen=True)
class Survey:                      # the surveyor's answer
    findings: tuple[Finding, ...]  # categories COPY and MISSING
    candidates: tuple[Candidate, ...]  # one per concern, ranked best payoff for its risk first (decision 9)
    sound: tuple[str, ...]         # what is sound enough to keep as it is, one line each
```

**`gauntlet/core/design.py`.** The design record and its validity checks: one home per concern, every home in a module, steps of at most five paths, a home landing before the copies it replaces are purged, and no copy left unported. It also reads whether a job needs a design from the planner's flag on the outline (decision 1). It replaces nothing. Records:

```python
@dataclass(frozen=True)
class Stub:
    name: str                      # the public name, e.g. "Clock.now"
    text: str                      # signature and a body that only raises

@dataclass(frozen=True)
class Module:
    path: str
    job: str                       # one line
    stubs: tuple[Stub, ...]
    replaces: tuple[Anchor, ...]   # each copy this module's arrival purges

@dataclass(frozen=True)
class Home:
    concern: str                   # e.g. "process running"
    module: str                    # a Module.path of this design
    forbids: str                   # what no other module writes

@dataclass(frozen=True)
class Step:
    name: str
    paths: tuple[str, ...]         # at most five
    implementer: str               # a role name

@dataclass(frozen=True)
class Choice:
    question: str
    recommend: str
    alternative: str
    cost: str                      # each side's cost; "unmeasured" where nobody measured it

@dataclass(frozen=True)
class Design:
    modules: tuple[Module, ...]
    homes: tuple[Home, ...]
    order: tuple[Step, ...]
    choices: tuple[Choice, ...]    # at most five; the owner rules each before approval
```

Its functions:

```python
def needs_design(outline: Outline) -> bool   # decision 1: the outline's shared-structure flag
def design_problems(design: Design) -> tuple[str, ...]
def home_of(design: Design, concern: str) -> Home | None
def uncovered(design: Design, copies: Sequence[Anchor], done: Collection[str]) -> tuple[Anchor, ...]  # copies no step outside done ports
```

`design_problems` returns nothing for a valid design. It returns one problem for each of: a concern with no home or with two; a home whose module is not a module of the design; two modules with one path; a module no step writes; a step with more than five paths or no implementer; the path of a replaced anchor written in a step earlier than the step that writes its replacing module; more than five choices; and a choice missing its recommendation, alternative or cost.

`needs_design` returns the flag the planner sets on its outline answer when the job creates or changes shared structure (decision 1). The flag is a field of M1's `Outline`, beside the steps, implementers and areas it already returns (`docs/design.md:38`). A bug fix or an ordinary feature leaves it unset and skips DESIGN, but the structure reviewer still runs in its REVIEW (decision 1).

`uncovered` returns each copy that no step still to run ports. A copy counts as ported only while some `Module.replaces` names it and a step whose name is not in `done` writes its path. It is the one check behind "a structure job lands only when no copy remains" (decision 7), run twice. At DESIGN, with `done` empty and the copies the STRUCTURE job knows, it names each copy the design leaves unported. At the end of the job's REVIEW, with every step done and the copies the surveyor finds in the job tree, it names each copy that remains; the job lands only when that call returns nothing.

**`gauntlet/core/causes.py`.** Findings that stand, grouped into causes, and each cause routed to one fix. It replaces the per-finding routing at `docs/design.md:74` and `docs/roadmap.md:81`, and it owns the drop rule that those two lines and `docs/design.md:46` state. It also checks a survey's candidates against the causes grouped from its findings.

```python
@dataclass(frozen=True)
class Cause:
    id: str                        # stable across rounds; the grouper reuses it
    claim: str                     # the underlying cause, one sentence
    concern: str | None            # None for a cause outside every shared concern
    findings: tuple[Finding, ...]  # every instance

@dataclass(frozen=True)
class FixStep:
    cause: Cause
    implementer: str
    paths: tuple[str, ...]         # the home's module, then every instance's path

@dataclass(frozen=True)
class DesignChange:                # the fix needs a home the design lacks
    cause: Cause

def finding_problems(finding: Finding, design: Design | None) -> tuple[str, ...]
def partition_problems(findings: Sequence[Finding], causes: Sequence[Cause]) -> tuple[str, ...]
def route(cause: Cause, design: Design | None, owners: Mapping[str, str]) -> FixStep | DesignChange
def survey_problems(survey: Survey, causes: Sequence[Cause]) -> tuple[str, ...]
```

- `finding_problems` drops a finding that has no scenario. It also drops a COPY or MISSING finding with no `also`, a non-DEFECT finding that is not blocking, a DEFECT finding with a concern or any other finding without one, and an OWN_CORE or DRIFT finding when the job has no design or the design does not home its concern. A COPY finding stands either way, so a job without a design is still checked for copying (decision 1).
- `partition_problems` names each finding that is in no cause or in two, each cause with no finding, and each cause whose non-DEFECT findings break a concern other than the cause's own.
- `owners` maps each path the job wrote to the implementer of the step whose commit wrote it, as the harness records it (`docs/design.md:73`).
- `route` sends a cause whose concern has a home to one FixStep. That step goes to the implementer of the step that writes the home's module, and its paths are the module and every instance. A cause with no concern goes to the owner of its first instance's path, with every instance as its paths. A cause whose concern has no home becomes a DesignChange when the job has a design and every `also` anchor lies in a path the job wrote, since the gap is then in the job's own structure. Otherwise it is routed as a cause with no concern, and the fix reuses the existing code its `also` anchors name. A fixer that cannot reuse that code without a home the core lacks returns `blocked` with CoreMissing.
- `survey_problems` names each cause whose concern no candidate names, each candidate whose concern no cause has or another candidate shares, and each candidate missing its payoff or risk. A survey that fails it is `COULD NOT JUDGE`.

**`gauntlet/core/schedule.py`.** Which work may run beside which, by the files each piece declares. It is the epic module of `docs/design.md` §8, and this design adds the one function that a job's steps and structure jobs both run on (decision 6). M12's epic rule, parallel only on declared files that do not overlap (`docs/design.md:211`), is built on it.

```python
def startable(order: Sequence[tuple[str, frozenset[str]]], done: Collection[str], running: Collection[str], held: Collection[str]) -> tuple[str, ...]
```

- `startable` returns, in order, each piece that is neither done nor running and whose declared files overlap no running piece, no earlier piece not yet done, and no held path. A piece is a plan step inside a job, or a STRUCTURE job among structure jobs.
- In a feature job with an open STRUCTURE job, `held` is the blocked step's files plus the STRUCTURE job's: the CoreMissing's `also` paths until the STRUCTURE job's plan is approved, and that plan's declared files after. So the blocked step waits, and so does every step that touches a held path or a waiting step's files, while every other step runs.
- Among STRUCTURE jobs under M12, each piece's files are its approved plan's. Jobs on disjoint files run in parallel, and a job whose files overlap an earlier one's runs after that one lands. Until M12 they run one after another (decision 5).

**`gauntlet/core/decide.py`.** These are the rows this design adds to M1's stage table (`docs/design.md:270`). Stages are named, never numbered: the `Stage` member is the one identity of a stage.

```python
class Stage(StrEnum):
    BRIEF = "brief"; DISCOVERY = "discovery"; OUTLINE = "outline"; DESIGN = "design"
    PLAN = "plan"; SPEC = "spec"; STUBS = "stubs"; TESTS = "tests"; RED_RUN = "red-run"
    LOCK = "lock"; BUILD = "build"; REVIEW = "review"; BAILIFF = "bailiff"; LAND = "land"

class Shape(StrEnum):
    JOB = "job"
    TEST_AUDIT = "test-audit"      # starts at SPEC; skips STUBS, BUILD, REVIEW
    STRUCTURE = "structure"        # one job per candidate, an audit pick or a CoreMissing; starts at DESIGN, skips nothing

FIRST: Mapping[Shape, Stage]                # JOB: BRIEF; TEST_AUDIT: SPEC; STRUCTURE: DESIGN
SKIPPED: Mapping[Shape, frozenset[Stage]]   # TEST_AUDIT: STUBS, BUILD, REVIEW; JOB and STRUCTURE: none
def decide(state: State, answer: Answer) -> Action
```

- After OUTLINE comes DESIGN when `needs_design` holds, that is, when the planner flagged shared structure. Otherwise PLAN comes next, with a row that records DESIGN as skipped by rule, and the land screen shows it. JOB's DESIGN skip is this rule, never a `SKIPPED` entry.
- A DESIGN answer with any `design_problems` is a failed round under `caps.design`. A STRUCTURE job's DESIGN answer is also a failed round while `uncovered` with `done` empty names one of the copies it opened with: its audit cause's anchors, or its CoreMissing's `also` (decision 7). A valid one goes to the owner, who rules each choice and approves.
- STUBS writes the approved design's stubs before any plan step's own.
- A job delivers its request at the size asked (decision 8). A BUILD answer of `complete` or `partial` carrying CoreMissing leaves the step to its usual course, and its candidate becomes an offer on the land screen with its payoff and risk. The owner accepts it, which opens a STRUCTURE job, or declines it, and the ruling is recorded; the feature job lands either way.
- A BUILD answer of `blocked` carrying CoreMissing means the request cannot be done correctly without the core, and its candidate's `why` says so in a sentence on the status and land screens. The harness opens a STRUCTURE job for that candidate without waiting for the owner, who still approves its design (decision 6).
- Meanwhile the feature job keeps building: BUILD starts only the steps `startable` returns, with the held paths of `core/schedule.py`, so only the blocked step and steps touching its files or the STRUCTURE job's wait. When the STRUCTURE job lands, the harness merges `main` into the feature branch, `held` empties, and the waiting steps run from STUBS. A merge conflict, or a STRUCTURE job that stops without landing, stops the feature job at its stop screen once no step is startable. Until M12 the STRUCTURE job starts when the feature job has no startable step left; under M12 it starts at once, beside it.
- A STRUCTURE job, whether an audit pick or a spawn, opens at DESIGN with its candidate and the copies as its brief. Its approved order becomes its plan's steps: those that write the new home, then port steps, each moving one group of callers onto the home and deleting their copies (decision 7). Its BUILD starts every step `startable` returns, so port steps on disjoint files run in parallel, each in its own worktree (decision 20); any other job's BUILD starts the first startable step, one at a time. Its PLAN reads the design in the outline's place (decision 18).
- A STRUCTURE job's SPEC carries each of its candidate's `keeps` lines as a spec line, and the arbiter rejects a spec that drops one, so every hard-won behavior is locked at LOCK before any port step purges a copy (decision 9).
- REVIEW's findings, the structure reviewer's on every job among them (decision 1), pass `finding_problems` and then go to the grouper. Its causes pass `partition_problems`, and a grouping that fails is `COULD NOT JUDGE`. Each cause takes `route`: a FixStep goes to BUILD and a DesignChange reopens DESIGN on the change alone, then the owner approves it and the touched steps rerun from STUBS; until M8 builds reopen, a DesignChange stops the job instead (decision 19). A cause id the next round still holds counts against `caps.review`.
- In a STRUCTURE job's REVIEW the surveyor also surveys the job tree for the job's concern. Each copy it finds is a COPY finding, grouped and routed like any other, and the job leaves REVIEW only when `uncovered` with every step done returns none of them (decision 7).

**`gauntlet/seams/job.py`.** Writes and reads the new records in the job folder: `design.N.md`, `design.N.objections.md`, `design.md`, `causes.N.md`, `offers.md` (each spawned or offered candidate and the owner's ruling on an offer), and for a structure audit `survey.md`. Nothing else writes them. It is also the one opener of a STRUCTURE job, for an audit pick and a spawn alike. It replaces nothing; the list at `docs/design.md:248`-`261` gains these files.

```python
def write_design(job: Path, n: int, design: Design) -> Path
def read_design(job: Path) -> Design | None        # the approved design.md, None if the job has none
def write_causes(job: Path, n: int, causes: Sequence[Cause]) -> Path
def write_offers(job: Path, spawned: Sequence[Candidate], offered: Sequence[Candidate]) -> Path
def write_survey(audit: Path, survey: Survey, causes: Sequence[Cause]) -> Path
def open_structure(root: Path, candidate: Candidate, copies: Sequence[Anchor]) -> Path   # a STRUCTURE job folder, first stage DESIGN
```

**`gauntlet/seams/screens.py`.** Shows the owner the design, the causes, the structure jobs a job spawns or offers, and the survey. It replaces nothing.

```python
def design_screen(design: Design, objections: Sequence[str]) -> Screen   # approve, rule each choice, or edit
def causes_section(causes: Sequence[Cause]) -> Section                   # stop and land screens: claim, every instance anchor
def structure_section(spawned: Sequence[Candidate], offered: Sequence[Candidate]) -> Section   # status and land screens: each spawn's why; each offer's payoff and risk, to accept or decline
def survey_screen(survey: Survey, causes: Sequence[Cause]) -> Screen     # candidates in rank order with payoff, risk and anchors, then what is sound; the owner selects
```

**`gauntlet/seams/cli.py`.** Gives `gauntlet audit` its second shape. A structure audit opens one STRUCTURE job through `open_structure` for each candidate the owner selects, never one job for several (decision 5). Until M12's epics exist, those jobs run one after another, each starting when the one before ends; under M12, `startable` runs them, in parallel on disjoint files and in sequence on overlapping ones (decision 6). The test-audit shape (`docs/design.md:93`) stays; until M10 a bare `audit` refuses (decision 21).

```python
def audit(scope: Path, *, structure: bool = False) -> int   # gauntlet audit <scope> [--structure]
```

**`roles/`.** Four fixed roles. Each runs in an existing kind (`docs/design.md:103`-`104`), so no kind is added. They replace nothing.

```text
roles/architect.md            reader   answer: Design
roles/structure-reviewer.md   reader   answer: tuple[Finding, ...], categories COPY, OWN_CORE, DRIFT with a design, COPY alone without one   (decisions 1, 3)
roles/grouper.md              judge    answer: tuple[Cause, ...]   (decision 4)
roles/surveyor.md             reader   answer: Survey, findings in categories COPY, MISSING   (decision 9)
```

The structure reviewer runs in every job's REVIEW. On a job with a design it gets the diff and the approved design's modules and homes; on a job without one it gets the diff and reads the tree for code the diff repeats. It never gets the brief or plan. The surveyor runs in a structure audit over its scope, and in a STRUCTURE job's REVIEW over the job tree for the job's concern.

**`tests/support/answers.py`.** Builders for the records above. It is the home for the State and Answer builders that M1's design names (`docs/superpowers/specs/2026-10-20-gates-core-design.md:381`), and M1's design may rename the file. It replaces nothing.

```python
def anchor(path: str = ..., line: int = ...) -> Anchor
def finding(*, category: Category = ..., concern: str | None = ..., also: tuple[Anchor, ...] = ...) -> Finding
def design(*, modules: tuple[Module, ...] = ..., homes: tuple[Home, ...] = ..., order: tuple[Step, ...] = ...) -> Design
def cause(*, findings: tuple[Finding, ...] = ..., concern: str | None = ...) -> Cause
def candidate(*, concern: str = ..., keeps: tuple[str, ...] = ..., why: str | None = ...) -> Candidate
def survey(*, findings: tuple[Finding, ...] = ..., candidates: tuple[Candidate, ...] = ...) -> Survey
```

## Homes

| Concern | Home | Forbids elsewhere |
|---|---|---|
| Stage identity and order, including DESIGN, the test-audit shape and the STRUCTURE shape | `Stage`, `Shape`, `FIRST` and `SKIPPED` in `gauntlet/core/decide.py` | Citing a stage by number in any document or prompt. A stage order held in a seam or a role. A second shape for a structure job spawned by a feature job. |
| Answer schemas and the anchor type | `gauntlet/core/verdicts.py` | A schema defined in a role prompt (`docs/design.md:284`). A second path-and-line type for discovery (`docs/design.md:37`), citations (`docs/design.md:53`), findings or designs. |
| The design record and what makes it valid | `gauntlet/core/design.py` | Stubs or homes that a plan step, role or seam defines for itself. A plan step writing a module that the design homes in another step. |
| Whether a job needs a design | the planner's shared-structure flag on the outline answer, read only by `needs_design` | Any other role, seam or screen deciding it. DESIGN running on a JOB-shape job whose outline does not carry the flag; a STRUCTURE job runs DESIGN because `FIRST` starts it there. |
| Whether a diff copies what the core already has | the structure reviewer, in every job's REVIEW | A job skipping the check because it has no design. A repo reviewer or other role holding the check as its own. |
| Whether a finding stands | `finding_problems` | The drop rule restated at `docs/design.md:46`, `docs/design.md:74` and `docs/roadmap.md:81`. A role filtering its own findings. |
| Grouping findings into causes, and routing a cause to one fix | `gauntlet/core/causes.py`, fed by the grouper | Routing a single finding to an implementer (`docs/design.md:74`, `docs/roadmap.md:81`). A fix step for part of a cause. A fixer that adds a home the design lacks; that becomes a DesignChange, or a CoreMissing when the home is outside the job's own structure. |
| A structure job put to the owner, with its payoff, risk and the behaviors it keeps | `Candidate` in `gauntlet/core/verdicts.py` | A second record for an audit pick, a spawn or an offer. |
| Whether missing structure is required or optional | the `why` of a CoreMissing's candidate, set only on `blocked`, read only by `decide` | A STRUCTURE job opened without the owner's accept and without a `why`. A request widened into a refactor it does not need. Any seam or role deciding it. |
| Which steps and structure jobs may run beside which | `startable` in `gauntlet/core/schedule.py` | A waiting rule or parallel rule held in `decide`, a seam or a role. A feature job held whole while one step waits on a STRUCTURE job. |
| Whether a copy remains unported | `uncovered`, at DESIGN and at the end of a STRUCTURE job's REVIEW | An audit, design or land check that compares copies by its own rule. A STRUCTURE job landing while a copy remains. |
| Whether a survey stands, and its ranking | `survey_problems` and `Survey.candidates` order | A ranking held in a screen or seam. |
| Behaviors a purge must keep | each `Candidate.keeps` line, a spec line of its STRUCTURE job, locked before BUILD | A port step deleting a copy whose behavior no locked spec line holds. |
| Opening a STRUCTURE job | `open_structure` in `gauntlet/seams/job.py` | A second opener in `cli`, `decide` or any other seam. |
| Job-folder files for designs, causes, offers and surveys | `gauntlet/seams/job.py` | Any other writer of those files. |
| What the owner sees of designs, causes, spawns, offers and surveys | `gauntlet/seams/screens.py` | A seam or core module that writes them to the terminal. |
| Role craft for the four new roles | their files in `roles/` | Role rules held anywhere else (`docs/design.md:288`). |
| Round caps, `caps.design` included | `caps` in `gauntlet.yaml` (`docs/config.md:23`), read by the configuration reader M1's design names | A piece that reads `gauntlet.yaml` itself. Until the reader exists, a piece that needs a cap stops and reports it. |
| Test builders for these records | `tests/support/answers.py` | A builder or seed helper inside a test file. |

## Order

Each core step follows the repository's chain: stub, then red tests from `test-writer` against the `stubgen` view, then build, blind reviews and `make check`, with one commit. The C and S steps fold into the chunks of each milestone's own design step (`docs/superpowers/specs/2026-10-20-gates-core-design.md:366`), which takes these modules as given.

| Step | Milestone | Agent | Writes |
|---|---|---|---|
| D1 | before M1 | `general-purpose` (docs only, no red test) | `docs/design.md`, `docs/roadmap.md`, `docs/config.md` |
| C1 stub | M1 | `core-builder` | `gauntlet/core/verdicts.py`, `gauntlet/core/design.py`, `gauntlet/core/causes.py`, `gauntlet/core/schedule.py` |
| C2 red | M1 | `test-writer` | `tests/support/answers.py`, `tests/test_core_verdicts.py`, `tests/test_core_design.py`, `tests/test_core_causes.py`, `tests/test_core_schedule_startable.py` |
| C3 build | M1 | `core-builder` | `gauntlet/core/verdicts.py`, `gauntlet/core/design.py`, `gauntlet/core/causes.py`, `gauntlet/core/schedule.py` |
| C4 red | M1 | `test-writer` | `tests/test_core_decide_structure.py` |
| C5 build | M1 | `core-builder` | `gauntlet/core/decide.py` |
| R1 | M3 | `role-author` | `roles/architect.md` |
| S1 stub | M3 | `seam-builder` | `gauntlet/seams/job.py`, `gauntlet/seams/screens.py` |
| S2 red | M3 | `test-writer` | `tests/test_seams_job_design.py`, `tests/test_seams_screens_design.py` |
| S3 build | M3 | `seam-builder` | `gauntlet/seams/job.py`, `gauntlet/seams/screens.py` |
| R2 | M6 | `role-author` | `roles/structure-reviewer.md`, `roles/grouper.md` |
| C6 red | M8 | `test-writer` | `tests/test_core_decide_core_missing.py` |
| C7 build | M8 | `core-builder` | `gauntlet/core/decide.py` |
| R3 | M8 | `role-author` | `roles/surveyor.md` |
| S4 stub | M10 | `seam-builder` | `gauntlet/seams/cli.py` |
| S5 red | M10 | `test-writer` | `tests/test_seams_cli_audit.py` |
| S6 build | M10 | `seam-builder` | `gauntlet/seams/cli.py` |

D1 writes the approved design into the documents. In `docs/design.md`, it adds the DESIGN row and note to §2, the shared-structure flag to the Outline row's returns at `:38`, stage names in place of numbers at `:84` and `:93`, rewrites the Review note at `:74` to say "by cause" and to run the structure reviewer on every job, gives Audit jobs their STRUCTURE shape, adds to "Reopening the spec" the STRUCTURE job a CoreMissing opens or offers, the four roles to the §3 Roles column, the new files to §7, and the modules and `startable` to §8, dropping "with their answer schemas" at `:284`. In `docs/config.md`, it adds `design` to `caps`. In `docs/roadmap.md`, it makes the changes below.

Changes to roadmap milestones:

| Milestone | Change |
|---|---|
| M1 | Builds `core/design.py`, `core/causes.py`, the records in `core/verdicts.py`, `startable` in `core/schedule.py`, and the DESIGN, review-by-cause and STRUCTURE-shape rows of `decide`. Done when every branch of `design_problems`, `uncovered`, `finding_problems`, `partition_problems`, `route`, `survey_problems` and `startable` also has a unit test. |
| M3 | The planner's outline carries the shared-structure flag. The thin job runs DESIGN between OUTLINE and PLAN with one architect and no rounds when the flag is set, and STUBS writes the design's stubs first. Done when a fixture brief whose outline flags shared structure shows a design screen and leaves `design.md`, and a bug-fix fixture brief whose outline leaves the flag unset shows DESIGN skipped by rule on the land screen. |
| M4 | Adds prosecutor rounds on the design under `caps.design` (decision 2). Done when a design citing a copy anchor that does not resolve fails a round. |
| M6 | The structure reviewer joins every job's REVIEW, with the design on a job that has one and for COPY alone on a job that does not (decision 1), and the grouper and fixing by cause replace per-finding routing; the M6 line at `docs/roadmap.md:81` is rewritten. Done when a planted copy of a design home's logic yields one COPY finding anchored at both places, one cause and one fix step whose diff removes the copy, and the next round holds no instance of it; and when a job without a design that copies a function already in the tree yields one COPY finding and a fix step whose diff calls the existing function. |
| M8 | Reopen covers DESIGN: a DesignChange amends the job's own design and reruns the touched steps. A CoreMissing on `blocked` opens a STRUCTURE job, shows its `why`, and holds only the steps `startable` withholds; one on `complete` or `partial` becomes an offer on the land screen. A STRUCTURE job ports every copy and lands only when `uncovered` is empty at the end of its REVIEW. Until M12 it starts when the feature job has no startable step left. Done when a DesignChange on one step reruns only the steps it touches; when a three-step fixture job whose second step is blocked on CoreMissing builds its disjoint third step, opens one STRUCTURE job, then runs the second step from STUBS and lands; and when a fixture job whose step offers a candidate lands, with no STRUCTURE job opened, once the owner declines. |
| M10 | `gauntlet audit <scope> --structure`: the surveyor, the grouper, the survey screen with candidates ranked by payoff and risk and what is sound listed, owner selection, and one STRUCTURE job per selected candidate, run as separate jobs one after another. Done when a fixture repository with one concern copied in three files and no core yields three anchors in one cause and one candidate with its payoff, risk and keeps; a design whose `uncovered` is empty at DESIGN; spec lines for the keeps locked before any port step; and a landed job that adds the home, ports every caller and leaves `uncovered` empty at the end of REVIEW; and when a fixture with two such concerns, both selected, yields two jobs, the second starting when the first ends. |
| M12 | STRUCTURE jobs, audit picks and spawns alike, run under `startable`: one job per candidate, in parallel on disjoint declared files and in sequence on overlapping ones (decisions 5, 6), and a spawned STRUCTURE job starts at once beside its feature job. Until M12 lands, M8 and M10 run them as separate sequential jobs. Done when two selected candidates on disjoint files run in parallel and two on overlapping files run in sequence. |

M0, Agents, Gates, M2, M5, M7, M9, M11 and M13 do not change.

## Decisions taken

Each decision names the question put to the owner, then the owner's ruling, which holds. Decisions 18 to 21 settle questions the build plan raised, within 1 to 17.

1. **When DESIGN runs.** Design runs only when the planner flags that the job creates or changes shared structure. Bug fixes and ordinary features skip it but are still checked for copying what the core already has.
   - Written in: Modules (`core/design.py`, `core/causes.py`, `core/decide.py`, `roles/`), Homes ("Whether a job needs a design", "Whether a diff copies what the core already has"), Order (D1, M3, M6).
2. **Adversarial rounds on the design.** Prosecutor review rounds on the design (`caps.design`, default 2), with every copy anchor resolved against the tree as plan citations are (`docs/design.md:53`), then owner approval.
3. **Who checks diffs against the design.** One dedicated structure-reviewer that sees the diff plus the design, never the brief or plan. Repo reviewers stay unchanged.
4. **Who groups findings into causes.** A grouper agent groups findings by cause, with the findings, the design and the previous round's causes in its prompt, checked by `partition_problems`.
5. **What a structure audit becomes.** Not one big job. Each audit pick becomes its own job, for context management. If the epic feature isn't ready, run them as separate sequential jobs.
   - Written in: Modules (`core/schedule.py`, `core/decide.py`, `seams/cli.py`), Order (M10, M12).
6. **What a feature job does when it finds missing shared core.** It spawns a STRUCTURE job, the one job kind an audit pick also becomes. The feature job keeps running steps that do not depend on that core; only dependent steps wait for the STRUCTURE job to land. Independent STRUCTURE jobs on disjoint files run in parallel, dependent ones in sequence.
   - Written in: Modules (`core/schedule.py`, `core/decide.py`, `seams/job.py`, `seams/cli.py`), Homes ("Which steps and structure jobs may run beside which", "Opening a STRUCTURE job"), Order (C1 to C3, C6, C7, M1, M8, M12).
7. **What a STRUCTURE job includes.** Porting every copy or caller onto the new core and deleting the copies, in small port steps, one caller group each, parallel where disjoint. It lands only when no copy remains.
   - Written in: Modules (`core/design.py` `uncovered`, `core/decide.py`), Homes ("Whether a copy remains unported"), Order (M8, M10).
8. **How far a job grows past its request.** Gauntlet delivers the request at the size asked. Missing structure it spots is offered as a separate, optional STRUCTURE job with its payoff and risk. It is required only when the request cannot be done correctly without it, and then Gauntlet says why in a sentence.
   - Written in: Modules (`core/verdicts.py` `Candidate` and `CoreMissing`, `core/decide.py`, `seams/screens.py`), Homes ("Whether missing structure is required or optional"), Order (M8).
9. **What a structure audit reports.** It ranks candidates by payoff and risk, lists what is sound enough to keep, and records hard-won behaviors into the spec before any purge.
   - Written in: Modules (`core/verdicts.py` `Survey`, `core/causes.py` `survey_problems`, `core/decide.py`, `seams/screens.py`), Homes ("Whether a survey stands, and its ranking", "Behaviors a purge must keep"), Order (M10).
10. **How a CoreMissing is treated.** On a blocked step it means the structure is required: it carries a one-sentence `why` and spawns a STRUCTURE job at once. On a complete or partial step it is an optional offer on the land screen.
   - Written in: Modules (`core/verdicts.py` `CoreMissing`, `core/decide.py`, the BUILD answer of `blocked`), Homes ("Whether missing structure is required or optional"), Order (M8).
11. **When a spawned STRUCTURE job starts.** Until M12 it starts when the feature job has no startable step left; under M12 it runs beside it.
   - Written in: Modules (`core/schedule.py`, the feature job's meanwhile bullet), Order (M8, M12).
12. **What dependent means.** Dependent means overlapping declared files, the epic rule (`docs/design.md:211`); `startable` is built at M1.
   - Written in: Modules (`core/schedule.py`), Homes ("Which steps and structure jobs may run beside which"), Order (M1).
13. **What a feature job holds and how it lands.** The held paths are the blocked step's files plus the CoreMissing's `also` paths, then the STRUCTURE plan's files. On land, `main` is merged into the feature branch, and a conflict stops the feature job.
   - Written in: Modules (`core/schedule.py` `startable`, the feature job's meanwhile bullet), Order (M8).
14. **When a DesignChange applies.** A DesignChange applies only to a gap inside the job's own paths. Any other gap goes the CoreMissing route.
   - Written in: Modules (`core/causes.py` `route`), Homes ("Grouping findings into causes, and routing a cause to one fix"), Order (M8).
15. **Where the surveyor also runs.** The surveyor also runs in a STRUCTURE job's REVIEW, so R3 moves to M8.
   - Written in: Modules (the STRUCTURE job's REVIEW bullet, `roles/surveyor.md`), Order (R3, M8).
16. **What the arbiter rejects.** The arbiter rejects a STRUCTURE spec that drops a `keeps` line.
   - Written in: Modules (the STRUCTURE job's SPEC bullet), Homes ("Behaviors a purge must keep"), Order (M10).
17. **Where BUILD runs in parallel.** Parallel BUILD happens only in STRUCTURE jobs; any other job's BUILD starts one startable step at a time.
   - Written in: Modules (the STRUCTURE job's BUILD bullet), Order (M8, M12).
18. **What a STRUCTURE job's PLAN reads.** A STRUCTURE job has no outline and no discovery table. Its planner reads the brief (candidate and copies), the approved design in the outline's place, and the prosecutor's objections. The plan keeps the design's steps one for one, with their names, implementers and paths, and adds to each the spec lines it serves and the stubs it needs; the prosecutor fails a plan that adds, drops or reorders a design step.
   - Written in: Modules (the STRUCTURE job's opening bullet), plan Q9.
19. **What a DesignChange does before M8.** Until M8 builds reopen, a DesignChange stops the job with its cause, as a reached round cap does: a stop row in `state.json` before M4, the stop screen from M4. M8 replaces the stop with the reopen of DESIGN.
   - Written in: Modules (the REVIEW bullet), plan Q10, C4b, C6.
20. **How parallel BUILD steps commit.** Each running step of a STRUCTURE job's BUILD gets its own worktree and branch from the job branch head, mounted at `/work`, where its tests and gates run. When it finishes, the harness commits it and merges it into the job branch; a later step branches from the merged head. `startable` keeps running steps on disjoint declared files, so a merge conflict means a step wrote outside its files, and that step fails its gate.
   - Written in: Modules (the STRUCTURE job's BUILD bullet), plan Q11, roadmap M3s.
21. **What a bare `audit` does before M10.** Until M10 builds the test audit, `gauntlet audit <scope>` without `--structure` opens no job and returns a nonzero code, saying the test audit is not built: a check that did not run never passes. M10 replaces the refusal.
   - Written in: Modules (`seams/cli.py`), plan S5.
