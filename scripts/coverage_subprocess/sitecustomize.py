"""Start the tracer in a subprocess the suite launches.

`site` imports `sitecustomize` at interpreter startup from anything on
`sys.path`, so putting this directory on `PYTHONPATH` reaches a process the
suite starts through `scripts/pair.sh`, through a hook, or through `python3`
directly. Almost everything this repository ships runs in such a process, and a
tracer that does not follow one reports it as never run: the figure then falls
as the kit grows, which is the opposite of what a coverage floor is for.

`coverage.process_startup()` does nothing unless `COVERAGE_PROCESS_START` names
a configuration file, so this directory on `PYTHONPATH` outside the gate run
costs an import and changes nothing. `scripts/gates/check-gates.sh` sets that
variable, and `COVERAGE_FILE` with it, because a subprocess run from a
throwaway checkout would otherwise write its data beside that checkout and be
lost at `coverage combine`.

This file is not imported by name anywhere. Deleting it does not fail a build;
it drops the figure, which the floor in `pyproject.toml` then catches.
"""

try:
    import coverage
except ImportError:  # pragma: no cover - a tree whose interpreter has no tracer
    pass
else:
    coverage.process_startup()
