Status: proposed, for the owner's approval.

## Why

A red brief carries one behavior, one `view:` and an optional `replaces:`. The agents spec, the structure-first plan and the mutmut run, mutation plan and test-writer designs restate this rule.

The rule turns every Order in the tree into runs of one-behavior red steps that feed one build each, one dispatch per step. The remaining runs include:

- mutmut run design: steps 17–25, 28–33.
- mutation plan design: steps 7–8, 14–19, 22–28.

Each run's red tests already land in one commit with their build, so merging a run changes the dispatches and not the commits. No code under `gauntlet/`, `gates/` or `tests/` spells the red brief.

## Modules

### The red brief

Its job is to carry the behaviors of one run of consecutive red steps whose tests land with one build, each behavior with its own `view:` and optional `replaces:`, written by one `test-writer` dispatch as one diff under `tests/`, in brief order, no behavior started once `CHANGED` reaches 300 and the rest reported `LEFT`. Its home is `test-writer`'s row and red-brief decision in the agents spec, and `.claude/agents/test-writer.md` holds the same shape (`CLAUDE.md:45`). It replaces the one-behavior rule and its restatements, which become pointers.

```text
red
behavior: <one behavior, in the words of the owner or a document>
view: <the .pyi stubgen made from the stub module this behavior calls, in the scratchpad>
replaces: <a test id a port step reported UNMOVED for this behavior>   # optional, at most one per behavior
behavior: <the next behavior, in its design step's order>               # one group per behavior, one or more groups
view: <its .pyi; the same path as another group's where both call one stub module>
replaces: <...>                                                         # optional
# every behavior is one red step of one run: consecutive red steps of a design Order, no other step between them,
#   all named as red tests by one build step
# done: each new test red from one run with --tb=no -rA --assert=plain, as AssertionError or NotImplementedError;
#   each replaces: test removed in this dispatch; behaviors written in brief order, and no behavior started
#   once CHANGED reaches 300
# report adds: BEHAVIOR <n> | <test id>, one per new test
#   REPLACED <test id> | behavior <n>, one per replaces: line
#   CHANGED <lines added plus lines removed over the files written or changed, a new file counted whole>
#   LEFT <n> | <behavior>, one per behavior not started
```

A brief with one group is the red brief as it stands. A behavior whose own tests take `CHANGED` past 300 is written whole. Each `LEFT` behavior goes, with its `view:` and `replaces:`, into a further red brief dispatched before the build. A design's file homes still bind a merged brief, such as the one real-time test alone in its file. How many behaviors fit in 300 changed lines is unmeasured.

### Merging a run

The lead dispatches a run as one red brief, its groups in step order: the red steps a build step names as "red tests from steps <a> to <b>". Design Orders keep one red step per behavior. A `port`, `moved`, `finding` or `stub` step never joins a merged brief, and a run is never merged across one. The rule lives in the agents spec's red-brief decision; the user-scope `lead` applies unchanged (`CLAUDE.md:33`).

### The pointer

Each restatement becomes this line, in the words its section needs:

```text
A red step's shape, and the run of red steps one brief may carry: docs/superpowers/specs/agents-design.md, test-writer's red brief.
```

### The proof

Its job is to prove the merged red brief on its first live dispatch of two or more behaviors. The agents spec's **Build order** holds this requirement in its last line, and `docs/roadmap.md:23` names it among `test-writer`'s outstanding proofs.

```text
<n>. `role-author` rewrites `test-writer`'s red brief to carry a run of behaviors. Proof: the first live red dispatch of two or more behaviors, its COMMANDS showing no read under `gauntlet/` or `gates/`; each behavior's tests red as AssertionError or NotImplementedError; each replaces: test gone from the diff; CHANGED equal to the lead's count of the diff. A failed proof returns red briefs to one behavior until the role is fixed.
```

## Homes

| Concern | Its one home | What it forbids elsewhere |
|---|---|---|
| What one red brief carries | `test-writer`'s red-brief decision and row, with `.claude/agents/test-writer.md` holding the same shape | A red-brief rule restated in a plan or a design; behaviors of two builds in one brief; `port`, `moved` or `finding` work in a red brief |
| Which red steps merge | The same decision: one run, named by one build step | A design Order re-cut into merged red steps; a merge across any other step |
| The size of a red diff | The red report's `CHANGED` line, counted by `test-writer` and checked at the lead's diff read | A gate, gate threshold or reviewer finding on lines changed; a size bound on a `port`, `moved` or `finding` step |
| What proves the merged brief | The agents spec's **Build order** last line, and `docs/roadmap.md:23` | A proof dispatch on a scratch test; a second merged dispatch after a failed proof |

A lead that needs a merge these homes do not give dispatches the steps one by one. It writes no merge rule of its own.

## Order

Each step lands green under `make check` before the next starts. No lead merges a run before step 3 lands.

1. The red brief, the merge rule and the size bound into `test-writer`'s row and red-brief decision (`docs/superpowers/specs/agents-design.md:28`, `:61`); the proof as the **Build order**'s last line (`:79`); the outstanding proof at `docs/roadmap.md:23`. Agent: `general-purpose`, a change confined to `docs/` (`CLAUDE.md:33`). Paths: `docs/superpowers/specs/agents-design.md`, `docs/roadmap.md`.
2. `test-writer`'s role file to match step 1, within the role file's 16,000-byte cap (`CLAUDE.md:43`); its headroom under the cap is unmeasured. Agent: `role-author`. Paths: `.claude/agents/test-writer.md`.
3. The pointers in place of each restatement. Agent: `general-purpose`, a change confined to `docs/`. Paths: `docs/superpowers/plans/structure-first-plan.md`, `docs/superpowers/specs/mutmut-run-design.md`, `docs/superpowers/specs/mutation-plan-design.md`, `docs/superpowers/specs/test-writer-design.md`.
