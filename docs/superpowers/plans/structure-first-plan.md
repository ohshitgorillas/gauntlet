# Structure-first build plan

Builds [`../specs/2026-10-20-structure-first-design.md`](../specs/2026-10-20-structure-first-design.md) (the spec). Its Decisions taken are final; this plan adds no behavior. Where the spec names a step (D1, C1…, R1…, S1…), this plan keeps the id and splits it.

## Open questions for the owner

Each step that depends on a question says so and is built on the recommendation unless the owner rules otherwise.

1. **`needs_design` before `Outline` exists.** The spec puts it in C1, but `Outline` is M1's type and no module defines it yet. Recommend: C1 stubs `design.py` without it; C4s adds it once M1's design names `Outline`.
2. **CoreMissing's schema check has no function.** The spec says a CoreMissing with the wrong `why` "fails its schema" and names no check. Recommend `core_missing_problems(missing: CoreMissing, blocked: bool) -> tuple[str, ...]` in `verdicts.py`. Alternative: leave it to M1's schema machinery.
3. **"A concern with no home" cannot occur.** A `Design` names concerns only in its homes. Recommend: `design_problems` checks only "a concern with two homes"; C4b makes a STRUCTURE job's DESIGN a failed round when `home_of(design, candidate.concern)` is `None`.
4. **Duplicate step names.** `uncovered` and `startable` key on step names, and the spec does not forbid two steps with one name. Recommend adding the problem `step <s>: named <n> times`.
5. **A piece with no declared files.** `docs/design.md` §5 runs such a job alone; `startable` as written would run it beside anything. Recommend: an empty file set overlaps every piece and every held path.
6. **`route` with a path `owners` lacks.** Recommend a typed error `UnownedPath(path: str)` in `causes.py`, moved into M1's error family when M1's design names it.
7. **Where `survey.md` lives.** `write_survey` takes an audit folder that `docs/design.md` §7 lacks. Recommend `.gauntlet/audits/<id>/survey.md`, added to §7 by D1.
8. **role-author against the one schema home.** role-author's description and its agents-spec row say a `roles/` role is written "with its answer schema", and the four roles have no agents-spec row. Recommend: before R1, the owner amends the row to "naming its answer schema in `gauntlet/core/verdicts.py`", and R briefs give the role's line from the spec's `roles/` block and the paragraph under it as its row.

## When steps may start

- D0 and D1 are docs only and may start now.
- Every code step waits on the roadmap's **Gates** milestone ("before any product code"), so on gates-core B4 and B5 and on the steps after them through C7, where the mutation gate lands. No step reads B4 or B5's code (`gauntlet` never imports `gates`). The wait matters because the mutation gate mutates only functions a commit changes: code committed before it exists is never judged.
- C1-C3 also wait on M1's design step (gates-core spec §5), which takes these modules as given and places C1-C3 in its chunk order. C4s-C7 and S1-S6 need names M1's and M3's designs fix (`Outline`, `State`, `Answer`, `Action`, the record codec, `Screen`, `Section`); each such step says which.

## Rules for every step

- **Chain.** stub, then red tests from `test-writer` against the `stubgen` `.pyi` of one stub module, then build. A `test-writer` brief carries one behavior: a test step listing several behaviors is several dispatches, run in the order listed, all writing the step's files. The `.pyi` of support helpers is never a brief: `tests/support/answers.py` is written in C2a beside its own tests, which pass at once.
- **One commit per chain**, after the last build: `diff-reviewer` and `test-reviewer` on the chain's diff (bare briefs), then `make check` in full, unpiped. Until then `make check` is red on the chain's other red tests; a builder's red `make check` on those alone is expected. Chains: C1-C3, C4s-C5, S1-S3, C6-C7, S4-S6; each R step and each D step is its own commit.
- **Blank** means empty after `str.strip()`. Paths are compared as exact strings. Every returned tuple keeps input order. Problem strings below are exact; `<x>` is the field's value and `<cat>` the `Category` value (`own-core`).

## Steps

### D0. Record the approval

- **Role:** `architect`, `rulings` brief: the spec and the ruling "approved as written, 2026-10-20". **Writes:** the spec's Status line. **Inputs:** none. **Done:** the Status line reads approved.

### D1. Documents

- **Role:** `general-purpose`, docs only, no red test. **Writes:** `docs/design.md`, `docs/roadmap.md`, `docs/config.md`. **Inputs:** none; ∥ D0.
- Everything the spec's D1 paragraph and milestone table say.
- Also, by the spec's Homes ("citing a stage by number in any document"): drop the `#` column of §2's table; name stages, never number them, at `design.md:52`-`75`, `:57`, `:62`, `:189`, `:209` and `config.md:56`; replace the finding shape on the Review row (`:46`) with a pointer to `Finding` in `core/verdicts.py`; add "or CoreMissing" to the Build row's returns.
- Also Q7's `.gauntlet/audits/<id>/survey.md` in §7, and `design: 2` in `config.md`'s example `caps`. No version bump.
- **Done:** `grep -nE "stages? [0-9]|\([0-9]+\)\.\*\*"` over the three files prints nothing, and each change listed in the spec's D1 paragraph is in place.

### C1. Stubs (`core-builder`, `stub`)

- **Inputs:** Gates milestone, M1 design. **Writes:** `gauntlet/core/verdicts.py`, `design.py`, `causes.py`, `schedule.py`.
- `verdicts.py`: `Anchor`, `Category`, `Finding`, `Candidate`, `CoreMissing`, `Survey` exactly as the spec, complete (records have no body to raise); plus `core_missing_problems` (Q2).
- `design.py`: `Stub`, `Module`, `Home`, `Step`, `Choice`, `Design` complete; `design_problems`, `home_of`, `uncovered` raise. No `needs_design` (Q1).
- `causes.py`: `Cause`, `FixStep`, `DesignChange` complete; `UnownedPath(Exception)` with `__init__(self, path: str)` keeping `.path` (Q6); `finding_problems`, `partition_problems`, `route`, `survey_problems` raise.
- `schedule.py`: `startable` raises.
- Types from `collections.abc` (`Sequence`, `Collection`, `Mapping`). **Done:** each module imports; every function body is `raise NotImplementedError`.

### C2a. Builders (`test-writer`, one dispatch per `.pyi`: verdicts, design, causes)

- **Inputs:** C1; ∥ C2e. **Writes:** `tests/support/answers.py`, `tests/test_support_answers.py`.
- The spec's six builder signatures, keyword-only after `anchor`. Defaults: `anchor()` is `Anchor("pkg/a.py", 1)`. `finding()` is `Finding(anchor(), "a call fails", Category.DEFECT, True, None, ())`. `design()` is one `Module("pkg/home.py", "one line", (), ())`, one `Home("process running", "pkg/home.py", "running a process")`, one `Step("s1", ("pkg/home.py",), "core-builder")`, no choices. `cause()` is `Cause("c1", "one cause", None, (finding(),))`. `candidate()` is `Candidate("process running", "one runner", "a caller breaks", (), None)`. `survey()` has no findings, candidates or sound lines.
- **Proves:** each builder called bare returns exactly its default record, and each keyword replaces only its own field.

### C2b. `tests/test_core_verdicts.py` (`test-writer`, `.pyi` of verdicts)

- **Inputs:** C2a; ∥ C2c-e.
- `Category`'s values are exactly `defect`, `copy`, `own-core`, `drift`, `missing`.
- `core_missing_problems` (Q2): blocked with a non-blank `why` gives nothing; blocked with a blank or absent `why` gives `blocked with no why`; not blocked with a `why` gives `why set on a step not blocked`; not blocked without one gives nothing.

### C2c. `tests/test_core_design.py` (`test-writer`, `.pyi` of design)

- **Inputs:** C2a.
- `design_problems` gives nothing for `design()`, and exactly one problem for a design breaking one rule, in this order of checks: `concern <c>: <n> homes` (once per concern, Q3); `home <c>: module <m> not in design`; `module <p>: defined <n> times`; `module <p>: no step writes it` (a step writes a module when its paths hold the module's path); `step <s>: <n> paths, at most five`; `step <s>: no implementer` (blank); `step <s>: named <n> times` (Q4); `step <s>: writes <p> before step <t> writes <m>`, where `t` is the first step writing replacing module `m`, one per distinct triple; `choices: <n>, at most five`; `choice <q>: no recommend`, `no alternative`, `no cost` (blank). A design breaking two rules gives both, in that order.
- `home_of` gives the first home whose concern equals the one asked, and `None` when none does.
- `uncovered` gives each copy, once, unless some module's `replaces` holds it and a step not in `done` has its path; with every step done it gives every copy.

### C2d. `tests/test_core_causes.py` (`test-writer`, `.pyi` of causes)

- **Inputs:** C2a.
- `finding_problems`, checks in order, each a string: `no scenario`; `<cat> with no also` (COPY, MISSING); `<cat> not blocking` (not DEFECT); `defect with a concern`, or `<cat> with no concern`; for OWN_CORE and DRIFT, `<cat> with no design`, or `<cat>: no home for <c>`. A COPY with a concern, `also` and blocking stands with or without a design.
- `partition_problems`: `finding <path>:<line>: in no cause`; `finding <path>:<line>: in <n> causes`; `cause <id>: no finding`; `cause <id>: finding <path>:<line> breaks <c>, not <own>`, with `none` for a `None` concern, for non-DEFECT findings only. Findings first, then causes.
- `route`, first rule that fits: no concern → FixStep to `owners` of the first instance's path, paths every instance's path once; the design homes the concern → FixStep to the implementer of the first step writing the home's module, paths the module then every other instance path; a design exists and every `also` path is in `owners` → `DesignChange`; else as no concern. Instance means a finding's own anchor, never its `also`. A path `owners` lacks raises `UnownedPath` with that path (Q6).
- `survey_problems`: `cause <id>: no candidate for <c>`; `candidate <c>: no cause`; `candidate <c>: named twice` for each later duplicate; `candidate <c>: no payoff`, `no risk` (blank). Causes first, then candidates.

### C2e. `tests/test_core_schedule_startable.py` (`test-writer`, `.pyi` of schedule)

- **Inputs:** C1; ∥ C2a-d.
- Gives, in order, each piece not done and not running whose files overlap no running piece, no earlier piece not done (running ones included) and no held path. Two disjoint pieces both start; of two overlapping pieces only the first; a held path stops only the pieces holding it; a running name absent from `order` adds no files; an empty file set overlaps everything (Q5).

### C3a-d. Build (`core-builder`, one step per module)

- C3a `verdicts.py` on C2b; C3b `design.py` on C2c; C3c `causes.py` on C2d; C3d `schedule.py` on C2e. Each is a build brief: its C2 step as text, its test file, its one module in scope.
- **Order:** C3a ∥ C3d; C3b after C3a; C3c after C3b (`route` calls `home_of`).
- **Done:** every C2 test green, then the chain's reviews, `make check` and one commit.

### C4s. Stubs for `decide` (`core-builder`, `stub`)

- **Inputs:** C3 committed; M1's design approved, naming `Outline`, `State`, `Answer`, `Action`. **Writes:** `gauntlet/core/design.py` (adds `needs_design`), `gauntlet/core/decide.py`.
- `decide.py`: `Stage`, `Shape`, `FIRST`, `SKIPPED` as the spec, complete; `decide` stub with M1's signature.

### C4a, C4b. Red (`test-writer`) ∥

- C4a `tests/test_core_design_needs_design.py`: `needs_design` is the outline's shared-structure flag, true and false.
- C4b `tests/test_core_decide_structure.py`, one behavior per spec `decide` bullet, CoreMissing bullets aside: `Stage` and `Shape` values; `FIRST` and `SKIPPED`; OUTLINE → DESIGN or PLAN with DESIGN skipped by rule; DESIGN problems or an uncovered copy fail a round under `caps.design`; Q3's unhomed concern fails a round; STUBS takes the design's stubs first; REVIEW grouping, routing, `COULD NOT JUDGE`, held cause ids against `caps.review`; a STRUCTURE job's SPEC carries each `keeps` line; its REVIEW leaves only when `uncovered` is empty; its BUILD starts every startable step, any other job's the first.

### C5. Build (`core-builder`)

- `design.py` on C4a, `decide.py` on C4b. **Done:** C4 tests green; reviews, `make check`, one commit.

### R1. `roles/architect.md` (`role-author`, M3)

- **Inputs:** Q8; C3. ∥ S1-S3. Answer `Design`, reader kind. **Done:** its proof passes.

### S1. Stubs (`seam-builder`, `stub`, M3)

- **Inputs:** C5; M1's record codec; M3's `Screen` and `Section`. **Writes:** `gauntlet/seams/job.py`, `gauntlet/seams/screens.py`, signatures as the spec.

### S2a, S2b. Red (`test-writer`) ∥

- S2a `tests/test_seams_job_design.py`: each writer writes its spec-named file in the job folder, `design.N.md`, `causes.N.md`, `offers.md`, and returns its path; `read_design` reads back what `write_design` gave `design.md`, and `None` with no `design.md`; `open_structure` makes a job folder whose first stage is DESIGN, carrying the candidate and copies; `write_survey` writes `survey.md` in the audit folder (Q7).
- S2b `tests/test_seams_screens_design.py`: `design_screen` shows each module, home, step and choice and the objections; `causes_section` each claim with every instance anchor; `structure_section` each spawn's `why` and each offer's payoff and risk; `survey_screen` candidates in rank order with payoff, risk and anchors, then the sound lines.

### S3a, S3b. Build (`seam-builder`) ∥

- S3a `job.py` on S2a; S3b `screens.py` on S2b. **Done:** S2 tests green; reviews, `make check`, one commit.

### R2a, R2b. Roles (`role-author`, M6) ∥

- R2a `roles/structure-reviewer.md` (reader; COPY, OWN_CORE, DRIFT with a design, COPY alone without). R2b `roles/grouper.md` (judge; `tuple[Cause, ...]`). **Inputs:** Q8, C5.

### C6. `tests/test_core_decide_core_missing.py` (`test-writer`, M8)

- **Inputs:** C5. One behavior per spec bullet: `complete` or `partial` with CoreMissing → an offer, the step on its usual course; `blocked` → a STRUCTURE job opened at once; BUILD starts only `startable` steps under the held paths of decision 13; a landed STRUCTURE job empties `held` and the waiting steps rerun from STUBS; a merge conflict or a stopped STRUCTURE job stops the feature job once no step is startable; until M12 the STRUCTURE job starts when no step is startable; a `DesignChange` reopens DESIGN on the change alone.

### C7. Build (`core-builder`, M8)

- `decide.py` on C6. **Done:** C6 green; reviews, `make check`, one commit.

### R3. `roles/surveyor.md` (`role-author`, M8)

- Reader; `Survey`, findings COPY and MISSING. **Inputs:** Q8, C5; ∥ C6-C7.

### S4-S6. `gauntlet audit --structure` (M10)

- **Inputs:** C7, S3, R3. S4 `seam-builder` `stub`: `audit` in `gauntlet/seams/cli.py`. S5 `test-writer` `tests/test_seams_cli_audit.py`: `--structure` opens one STRUCTURE job through `open_structure` per selected candidate, none for an unselected one, run one after another; without `--structure` the test-audit shape runs. S6 `seam-builder` build on S5; reviews, `make check`, one commit.

## Parallel sets

D0 ∥ D1. C2a ∥ C2e, then C2b ∥ C2c ∥ C2d. C3a ∥ C3d, then C3b, then C3c. C4a ∥ C4b. R1 ∥ S1-S3. S2a ∥ S2b. S3a ∥ S3b. R2a ∥ R2b. R3 ∥ C6-C7.
