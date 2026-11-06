Convergence pass 3, Plan 3 Task 3: the graph check and the section A re-check, made by the executor on the designs after the pass-2 rulings (9901135, af2e0ae) and the three rulings after application (G-54/D-40, G-61/D-43, G-93/D-58) were applied. Input to REVIEW-pass3.md or REVIEW-convergence.md; not committed on its own.

## Build orders as one graph

Key and step list as `reviews/convergence-graph.md` (pass 2): 40 steps (intake 3, gauntlet 10, plan-review 4, spec-review 7, worktree-cut 3, writing 7, landing 6). Each `## Order` section was diffed against its text at e01ea0b, word by word. Changes: gauntlet step 1 adds node `env-check`; gauntlet step 10 adds node `land-4` and fixture `moved-thrice.stubs.yaml` and names landing's step 6; spec-review step 6 is renamed "Spiker's run tool" (`fence/spike.py`, `fence/test_spike.py`); writing step 6 adds the `blocked` fixtures of both writer blocks; landing step 3 adds fixtures `resumed`, `repair-uncommitted`, `repair-retry`, `repair-retry-review`; landing step 6 adds fixture `gate-moved-last`; landing's closing line reads "step 10" (finding 2.69, group G-103). No "Needs" clause changed, so the edge list of pass 2 holds.

- Cycles: none (no edge changed).
- A step needing a step ordered after it, within a design: none.
- A step needing a file no step builds: none. Every fixture file named in `gauntlet-design.md` (`gauntlet-run/fixtures/`: 10 files) and `landing-design.md` (`land/fixtures/`: 8 files; the `mend/fixtures/` names are steps 3 and 5) sits in the Order step of the design that names it.
- Step references across designs: every "design's step N" names an existing step (`landing-design.md` closing line now "step 10" of `gauntlet-design.md`, which has 10 steps).

## Section A rows a ruling changed

Rows with a changed cell since e01ea0b: A1, A9, A12, A14, A15, A19, A21, A26, A28, A29. Each verdict re-read against the form the designs now hold:

- A1 `documented` plus `probed` (P7): unchanged form (phase files carry `worktree: { enabled: false }`); the verdict stands.
- A9 `documented`: the form is now `max_parallel: 1` and a bash node `clean` ahead of the writer inside the fanned-out include; the citations (loop-nodes.md:729, workflow-language.md:2550, :2613-2614) cover `include:` with `fan_out:` in a `loop_group` and one shared checkout; the verdict stands.
- A12 `documented`, A21 `documented`, A26 `documented`, A28 `documented`: only the design lines a ruling moved changed; the form is the one the citations cover.
- A14 `documented`: intake's `put` binding takes `if_skipped: "<skipped>"`; workflow-language.md:1174-1184 shows `{ from, if_skipped }` with a value, so the string form is the documented form.
- A15 `documented`: intake's `until_bash` reads a script node with `trigger_rule: all_done`; workflow-language.md:325 says `all_done` runs whatever the dependencies' outcome, and DECISION-REVIEW.md D-49 confirmed it.
- A19 `unsupported` (the `Task` name): unchanged; the row still awaits Task 4's hash for the pass-1 ruling commit; the spiker row now says no Bash and no shell.
- A29 `documented`: four rounds (`land` to `land-4`) are four includes of one block under distinct ids at one scope, not a nested include; workflow-language.md:1588-1596 and :1735 cover them; the branch-name hash of `land__retree` stays unmeasured, guarded by `branch-check`.

No row changes verdict. No new finding from the graph.
