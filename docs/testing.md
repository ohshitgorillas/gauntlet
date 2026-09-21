# Testing policy — binding for all contributors, human or agent

Break rule = review say no. Even if test green.

`arbiter` point at rule number. Number no change — new rule go end or get letter, never renumber.

`<...>` = you fill in for project. Swap in real name before rule bind.

## Core rules

1. **Test behavior, never implementation.** Give input/wire traffic, public API give result. Refactor keep behavior but test break = test bad. Module shape, private helper, inside state, call order, log word — no touch.

2. **One assertion per test.** Many case = framework parametrize, never assert in loop. Boolean AND = one assertion each side. `x is not None and x["k"] == v` trick fix: empty value of same type instead of null check (`(x or {})["k"] == v`), so missing key fail alone. `scripts/gates/test-assertions.py`.

3. **Public API only.** No private attribute, no monkeypatch inside.

4. **Fakes speak wire protocol; never mock our own code.** Fake server, real protocol, real transport, quirk included.

5. **Anchor on stable contract facts, never golden dumps.** Field with known meaning, never whole-blob snapshot equal.

6. **Test names state behavior**: `test_checked_checkbox_parses_true`, not `test_parse_2`.

7. **No test waits on wall clock.** Retry/poll loop judge by count and end result, never time spent. Production tick on inject clock, suite fake it.
   - Tick on project clock seam: `<name it>`. Raw sleep/monotonic call direct = review flag.
   - Autouse fixture fake both sleep and monotonic read.
   - Push clock forward; never freeze half — dead sleep + real clock read = hot spin.
   - `<any background loop that stays on real clock by design, and why>`.
   - Fake server: short poll gap on teardown, not default.
   - E2E only: fixed sleep still banned; bounded condition poll okay, timeout is a ceiling on condition, never expected duration.
   - Gated: `<gate holding suite wall time to last green run>`.

8. **New tests must bite.** Must go red on old code. Bite check: put back old implementation, keep test, run again, want red. Import/collect error ≠ bite (every new-surface test throw one no matter what assertion say). New surface with no red run possible: spec name null stub each line fail on. Characterization/refactor test exempt — say it, no assume.

9. **Assert only wire-originated strings, wire identifiers, numbers derived from wire data. Every string born in the implementation is copy.** Test: writer must read implementation to know this literal? Then copy — keep out of assertion and selector.
   - Error text is copy — match type + code, never message.
   - Rendered text is copy — assert class/attribute/`data-*`/values, text only if wire identifier or number.
   - Vendored/built data blob never give expected value — test join/lookup against owned fixtures; data well-formedness is a data gate, not a behavior test.
   - Curated count/order is copy.
   - Selector need wording → add stable test id. Nothing live through remove wording → delete via `motion: strike`, or `motion: amend` where behavior under it stay pinned. Never hand-edit `<tests dir>/`.
   - `scripts/gates/no-copy-assertions.py`.

10. **A test discriminates, or it's a tautology.** Name failing implementation and a passing one, both plausible; if failing one is only "feature absent," test pins nothing. Shapes that fail this:
    - Single input/single expected value = lookup-table entry. Need relation between two observations, or two distinct expected values on same surface.
    - Existence-only assertion (truthy/not-null/type/length/key-presence), legal only as owner-approved `EXEMPT` entry in `docs/exemptions.md`.
    - Expected value equals the absent-feature's zero value.
    - Asserting the fix's own mechanism (new flag/field/call) — that's rule 1.
    - Writer round-tripped through own reader — pin one half against fixture value.
    - Expected value computed the same way the code computes it — write the number instead.
    - Pure-math units: no repair exists — pin against external reference oracle fixtures, not a spec block.

11. **A test guards a bug, never a change of mind.** Write bug report it failure would file; if only a decision-change turns it red, reshape to invariant or delete.
    - Instance vs. invariant: assert the property (sorted, unique, one per option) at two inputs, never today's literal.
    - Styling as contract: state-carrying class/attribute (`active`, `disabled`, `data-*`, test id) is contract; stylesheet-selecting class or nesting order is design. External/upstream wire facts may be pinned.
    - Default as absolute: test the role (unset → default, set → override), not the value.
    - Sibling status code: pin only if a client branches on it or it's a documented contract; else pin code + status class.
    - Formatting (rounding, key order, number string form) not asserted unless a wire consumer demands it.
    - Tell: fixture-supplied value assertable verbatim; design-chosen value never asserted absolute. Rule 10's two distinct values = two inputs to one invariant, never two design literals.

12. **A test costs.** Test that hold nothing get delete, no coverage regression. Two tests that can't fail independently = one test. Test written to reach a line = rule 1 by another route — fix the code or the surface.

13. **Fakes answer from tables, never logic.** Fake that work out reply by code's own algorithm = second wrong implementation.

14. **Helpers return values.** No assert outside test function; fixture that must refuse to run raises. `scripts/gates/test-assertions.py`.

15. **Lowest lane.** Pure function → store/service → API → rendered component → browser. Higher-lane test a lower one already covers is deleted.

16. **No environment coupling.** No hostname/locale/timezone/cwd/home/fixed port. (Clock is rule 7.)

## Strike motions

Kill copy-pinning test (rule 9) walk the `/tests` chain as `motion: strike`, never hand edit in `<tests dir>/`:

```
N. strike <target>
   rule: docs/testing.md rule <n>
   assertion: <the offending assertion, quoted from the test file>
```

Target: `<tests dir>/<file>::<test>`, or `<tests dir>/<file>` (no `::`) for whole file. No `kills:`/`bite:`/`existing:`, four-line cap no apply. Rule number must match what quoted assertion really break.

Second citation form, for test that break no rule and still must go: behavior it pin is behavior owner dropped. `rule:` become `removed:`, carry owner's own sentence that dropped it, verbatim, same sentence block's `brief:` quote:

```
N. strike <target>
   removed: <owner's sentence that dropped the behavior, quoted>
   assertion: <the assertion that pins the dropped behavior, quoted>
```

Exactly one of `rule:` or `removed:` per line, never both, never neither. `removed:` sentence must appear in block's own `brief:` — reviewer blind to implementation, so owner's word is only fact it can check. Sentence not in `brief:` = line go. "Feature gone so test fail" is not `removed:`: failing test is finding, and dropped behavior reach here through owner, never through red suite.

Every test in file gone by single-test line, none replaced there → writer delete file, same as amend half below.

## Amend motions

Test that break rule but pin behavior worth keeping walk chain as `motion: amend`. One line carry both halves — what go, what take its place:

```
N. strike <tests dir>/<file>::<test>
   rule: docs/testing.md rule <n>
   assertion: <the offending assertion, quoted from the test file>
   replace: <behavior as the caller sees it>
   as: <tests dir>/<file>::<test_name>
   kills: <a wrong implementation a user would notice>
```

Target always `<tests dir>/<file>::<test>`. Whole-file target belong to `motion: strike` only: replacement cannot land in file strike half delete.

`as:` name test replacement must land as. May equal target — coupled test name often state behavior right (rule 6) and only assertion wrong, so rename is churn. Merge check read target as satisfied on either fact: name gone from `<tests dir>/`, or name present and quoted `assertion:` gone from that test's own body. Body, not file — same assertion text can sit in sibling test (parametrize case, shared line).

No `bite:`. Replacement pin behavior HEAD already have = characterization, rule 8 exempt it. Four-line cap count `replace:` lines only.

Strike half empty a file (every test gone, none replaced there) → writer delete file.

## Rehome motions

Test that break no rule and pin behavior worth keeping, and whose file or whose body around that assertion must change anyway, walk chain as `motion: rehome`. Assertion stay byte-identical; only what surround it move.

```
N. strike <tests dir>/<file>::<test>
   moved: <the fact outside the tests dir that moved, and what it forced>
   assertion: <the assertion, quoted verbatim from the test file>
   as: <tests dir>/<file>::<test_name>
```

Target always `<tests dir>/<file>::<test>`. Whole-file target malformed here: file that moves is every test in it, one line each.

`moved:` name fact outside `<tests dir>/` that force move — module split, source file renamed, fixture take new home. Prose, read by reviewer, never mechanically. "Tidier over there" is not `moved:`.

No `rule:`, no `removed:`, no `replace:`, no `kills:`, no `bite:`. Nothing pinned change, so no rule to cite and no wrong implementation to name. Four-line cap no apply.

`as:` name where test land. It may name target itself: assertion that survive byte-identical while body around it change for reason `moved:` name have no other route, and in-place line is that route. Test name may equal target's; name that state behavior right (rule 6) stay as it is. Barred is line that record nothing — same file, same test name, body unchanged.

Merge check split on `as:`. Where `as:` name file or test other than target's, line satisfied on two fact together: target gone from its own file (name gone, or name present and quoted `assertion:` gone from that test's body), and `as:` test exist with that same quoted text byte-identical in its own body. Where `as:` equal target, nothing leave the file, so check is other two fact together: quoted `assertion:` byte-identical in that test's body, and that body differ from its body at base. Body byte-identical on both side = `UNSATISFIED`: nothing moved. Assertion text that change under this motion = `STRICKEN`: it belong to `kind: refactor` or to `motion: amend`, where replacement is judged.

## Collateral rows

`kind:` block may carry `collateral:` section under its behavior lines, one row per test change break but no line pin. Caller-side move — renamed keyword, moved fixture, renumbered index — break test that pin nothing in block. Row is how block name it, so writer may repair what surround assertion and merge check hold assertion byte-identical.

```
collateral:
- <tests dir>/<file>::<test>
  breaks: <the fact outside the tests dir that moved, and what it forces>
  assertion: <the assertion, quoted verbatim, byte-identical after>
```

`kind:` blocks only. Motion block have no implementation phase, so it have no caller-side move to carry.

Target always `<tests dir>/<file>::<test>`. Whole-file target malformed: row's promise is about named test's own body.

Target always a test. Helper, fixture, parametrize list, import: named in `breaks:`, repaired by writer, never a target.

No `rule:`, no `removed:`, no `replace:`, no `kills:`, no `bite:`. Nothing pinned change, so no rule to cite and no wrong implementation to name.

`breaks:` name fact outside `<tests dir>/` that force repair. Prose, read by reviewer, never mechanically. "Test was stale" is not `breaks:`.

`collateral:` header with no row under it = malformed. Absent section is how block carry none.

Test named by both a row and an `existing:` clause = malformed. Clause say its assertion change, row say it do not.

Repair that must move test to another file or rename it = no row. That is `motion: rehome`'s shape, and rehome cannot ride this pair: move go as own tests-only block once pair land.

No ceiling on rows. Four-line cap count behavior lines; each row cost one reviewer check and one merge verdict.

Merge check read quoted `assertion:` in target test's own body at head. Body, not file — same text can sit in sibling. Present byte-identical = `OK`. Test no longer defined = `MISSING`. Test defined, quoted text gone from its body = `ALTERED`. Anything but `OK` stop the merge.

## Markers

- Default suite: offline, deterministic, pass with no outside service up.
- Real-system test: `<live marker>`, read only. Anything write-shape run on fake, forever.
- Browser e2e: `<path>`, `<marker>`, out of default run. Rule 2 still hold — assertion gate count framework assertion only.
- skip/xfail = gate exemption, owner say yes as `EXEMPT` entry in `docs/exemptions.md`, reason named. Shape in that file. Skip on environment/data precondition (dep missing, service down) is mechanism, not exemption.

## Mutation testing

No merge gate. `<mutation test command(s)>`. Survivor = untested line, equivalent mutant, or dead code — pick which, no chase score.

## Stack-specific addenda

Fill per project. Below core rules, out of numbering — `arbiter` never point into this part.

- Test framework(s), sweep mechanism.
- Render/harness mechanic: what fire event handler, what visible server side.
- Harness gotcha (state leak between test, escaping quirk, coverage tool footgun).
- Branch no way to reach, and where written down instead of worked around.
- Name of mechanical gate above as `<...>`.