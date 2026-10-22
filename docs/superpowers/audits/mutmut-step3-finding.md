# Mutmut run design, step 3: the spike's finding

From the C7b stream lead's report (cloud session, branch claude/c7b-build-fa1hvj, after step 2 at 788cc39):

- Step 3 (stop): the spiker answered UNSETTLED. mutmut checked no mutant at all: its stats step collects all of `tests/` from inside `mutants/`, can't import `gates` there (`ModuleNotFoundError`), and exits 1.
- Settings that would let mutmut collect the tests are not named in the step, so that is the owner's decision to make through step 7.
- The spiker also read in mutmut's source, without a run, that a pytest-timeout failure counts as killed.
- Steps 4 to 7 have not run, and step 7 needs the owner's rulings on the spike findings in any case.
