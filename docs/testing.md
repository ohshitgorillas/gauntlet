# Testing policy — binding for all contributors, human or agent

Break rule = review say no. Even if test green.

`gauntlet-arbiter` point at rule number. Number no change — new rule go end or get letter, never renumber.

`<...>` = you fill in for project. Swap in real name before rule bind.

## Core rules

1. **Test behavior, never implementation.** Give input/wire traffic, public
   API give result. Refactor keep behavior but test break = test bad. Module
   shape, private helper, inside state, call order, log word — no touch.

2. **One assertion per test.** Many case = framework parametrize, never
   assert in loop. Boolean AND = one assertion each side.
   `x is not None and x["k"] == v` trick fix: empty value of same type
   instead of null check (`(x or {})["k"] == v`), so missing key fail alone.
   `<gate for this>`.

3. **Public API only.** No private attribute, no monkeypatch inside.

4. **Fakes speak wire protocol; never mock our own code.** Fake server, real
   protocol, real transport, quirk included.

5. **Anchor on stable contract facts, never golden dumps.** Field with known
   meaning, never whole-blob snapshot equal.

6. **Test names state behavior**: `test_checked_checkbox_parses_true`, not
   `test_parse_2`.

7. **No test waits on wall clock.** Retry/poll loop judge by count and end
   result, never time spent. Production tick on inject clock, suite fake it.
   - Tick on project clock seam: `<name it>`. Raw sleep/monotonic call
     direct = review flag.
   - Autouse fixture fake both sleep and monotonic read.
   - Push clock forward; never freeze half — dead sleep + real clock read =
     hot spin.
   - `<any background loop that stays on real clock by design, and why>`.
   - Fake server: short poll gap on teardown, not default.
   - E2E only: fixed sleep still banned; bounded condition poll okay,
     timeout is a ceiling on condition, never expected duration.
   - Gated: `<gate holding suite wall time to last green run>`.

8. **New tests must bite.** Must go red on old code. Bite check: put back old
   implementation, keep test, run again, want red. Import/collect error ≠
   bite (every new-surface test throw one no matter what assertion say). New
   surface with no red run possible: spec name null stub each line fail on.
   Characterization/refactor test exempt — say it, no assume.

9. **Assert only wire-originated strings, wire identifiers, numbers derived
   from wire data. Every string born in the implementation is copy.** Test:
   writer must read implementation to know this literal? Then copy — keep out
   of assertion and selector.
   - Error text is copy — match type + code, never message.
   - Rendered text is copy — assert class/attribute/`data-*`/values,
     text only if wire identifier or number.
   - Vendored/built data blob never give expected value — test join/lookup
     against owned fixtures; data well-formedness is a data gate, not a
     behavior test.
   - Curated count/order is copy.
   - Selector need wording → add stable test id. Nothing live through remove
     wording → delete via `kind: excision`, never hand-edit `tests/`.
   - `<mechanical gate for this>`.

10. **A test discriminates, or it's a tautology.** Name failing
    implementation and a passing one, both plausible; if failing one is only
    "feature absent," test pins nothing. Shapes that fail this:
    - Single input/single expected value = lookup-table entry. Need relation
      between two observations, or two distinct expected values on same
      surface.
    - Existence-only assertion (truthy/not-null/type/length/key-presence),
      legal only as owner-approved `EXEMPT` entry.
    - Expected value equals the absent-feature's zero value.
    - Asserting the fix's own mechanism (new flag/field/call) — that's rule 1.
    - Writer round-tripped through own reader — pin one half against fixture
      value.
    - Expected value computed the same way the code computes it — write the
      number instead.
    - Pure-math units: no repair exists — pin against external reference
      oracle fixtures, not a spec block.

11. **A test guards a bug, never a change of mind.** Write bug report it
    failure would file; if only a decision-change turns it red, reshape to
    invariant or delete.
    - Instance vs. invariant: assert the property (sorted, unique, one per
      option) at two inputs, never today's literal.
    - Styling as contract: state-carrying class/attribute (`active`,
      `disabled`, `data-*`, test id) is contract; stylesheet-selecting class
      or nesting order is design. External/upstream wire facts may be pinned.
    - Default as absolute: test the role (unset → default, set → override),
      not the value.
    - Sibling status code: pin only if a client branches on it or it's a
      documented contract; else pin code + status class.
    - Formatting (rounding, key order, number string form) not asserted
      unless a wire consumer demands it.
    - Tell: fixture-supplied value assertable verbatim; design-chosen value
      never asserted absolute. Rule 10's two distinct values = two inputs to
      one invariant, never two design literals.

12. **A test costs.** Test that hold nothing get delete, no coverage
    regression. Two tests that can't fail independently = one test. Test
    written to reach a line = rule 1 by another route — fix the code or the
    surface.

13. **Fakes answer from tables, never logic.** Fake that work out reply by
    code's own algorithm = second wrong implementation.

14. **Helpers return values.** No assert outside test function; fixture
    that must refuse to run raises. `<gate for this>`.

15. **Lowest lane.** Pure function → store/service → API → rendered
    component → browser. Higher-lane test a lower one already covers is
    deleted.

16. **No environment coupling.** No hostname/locale/timezone/cwd/home/fixed
    port. (Clock is rule 7.)

## Excision blocks

Kill copy-pinning test (rule 9) walk the `/tests` chain as `kind: excision`,
never hand edit in `tests/`:

```
N. excise <target>
   rule: docs/testing.md rule <n>
   assertion: <the offending assertion, quoted from the test file>
```

Target: `tests/<file>::<test>`, or `tests/<file>` (no `::`) for whole file.
No `kills:`/`bite:`/`existing:`, four-line cap no apply. Rule number must
match what quoted assertion really break.

## Markers

- Default suite: offline, deterministic, pass with no outside service up.
- Real-system test: `<live marker>`, read only. Anything write-shape run on
  fake, forever.
- Browser e2e: `<path>`, `<marker>`, out of default run. Rule 2 still hold —
  assertion gate count framework assertion only.
- skip/xfail = gate exemption, owner say yes in `EXEMPT`, reason named.
  Skip on environment/data precondition (dep missing, service down) is
  mechanism, not exemption.

## Mutation testing

No merge gate. `<mutation test command(s)>`. Survivor = untested line,
equivalent mutant, or dead code — pick which, no chase score.

## Stack-specific addenda

Fill per project. Below core rules, out of numbering — `gauntlet-arbiter` never point
into this part.

- Test framework(s), sweep mechanism.
- Render/harness mechanic: what fire event handler, what visible
  server side.
- Harness gotcha (state leak between test, escaping quirk, coverage
  tool footgun).
- Branch no way to reach, and where written down instead of
  worked around.
- Name of mechanical gate above as `<...>`.