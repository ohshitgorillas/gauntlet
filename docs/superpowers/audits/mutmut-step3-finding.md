# Mutmut run design, step 3: the spike's finding

- Step 3 is stopped as UNSETTLED: mutmut's stats step collects all of `tests/` from inside `mutants/`, can't import `gates` there (`ModuleNotFoundError`), and exits 1 before checking any mutant.
- Settings that would let mutmut collect the tests are not named in the step, so that is the owner's decision to make through step 7.
- Mutmut's source treats a pytest-timeout failure as killed; this is a source-reading finding without runtime confirmation.
- Steps 4 to 7 remain pending; step 7 requires the owner's rulings on the spike findings.
