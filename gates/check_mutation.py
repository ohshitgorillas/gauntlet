"""Mutation gate: run mutmut over the changed functions of the given Python files that are not test files, and fail on any mutant it does not kill."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from gates.core.project import KeyRule, Project, key_findings, non_test_files
from gates.core.report import Finding, GateError, Outcome, Unfinished
from gates.core.runner import Gate, Run, run_gate
from gates.core.runner import main as run_main
from gates.core.source import pinned_version

GATE_NAME = "check_mutation"

WALL_CLOCK_SECONDS = 600

# The gate's line at the wall-clock cap, the spec's "checker that ran past its time cap"; the run still exits 1.
AT_THE_CAP = f"{GATE_NAME}: mutmut hit the wall-clock cap of {WALL_CLOCK_SECONDS} seconds; every mutant it had not checked is a finding"

# The [tool.mutmut] keys that narrow or widen what the run mutates or runs; the run never reads them.
SCOPE_KEYS = (
    "also_copy",
    "do_not_mutate",
    "do_not_mutate_patterns",
    "max_stack_depth",
    "mutate_only_covered_lines",
    "only_mutate",
    "paths_to_mutate",
    "pytest_add_cli_args",
    "pytest_add_cli_args_test_selection",
    "source_paths",
    "tests_dir",
)

# The [tool.mutmut] keys that change mutmut's own time limit; the run uses mutmut's default.
TIME_LIMIT_KEYS = ("timeout_constant", "timeout_multiplier")


def _set(value: object) -> bool:
    """Tell whether a key set to the value breaks its rule: any value does, since the run reads none of them."""
    del value
    return True


SETTINGS = (
    *(
        KeyRule(
            ("tool", "mutmut", key),
            _set,
            "narrows or widens the files mutated or the tests run; the run takes the changed functions of the given files and the given suite",
        )
        for key in SCOPE_KEYS
    ),
    *(
        KeyRule(
            ("tool", "mutmut", key),
            _set,
            "changes mutmut's own time limit; the run uses mutmut's default",
        )
        for key in TIME_LIMIT_KEYS
    ),
)


@dataclass(frozen=True)
class Mutant:
    """One mutant mutmut did not kill: the file's path as given, mutmut's name, its status and mutmut's whole diff."""

    given: str
    name: str
    status: str
    diff: str


@dataclass(frozen=True)
class Mutated:
    """What a mutmut run left: every mutant it did not kill, whether it hit the wall-clock cap, and its error when it
    left a mutant unchecked other than at the cap, with the failing test ids when the suite failed on the unmutated
    tree."""

    mutants: tuple[Mutant, ...] = ()
    at_cap: bool = False
    error: str | None = None


def setting_findings(project: Project) -> list[Finding]:
    """Return one finding per [tool.mutmut] key of the project that narrows or widens the scope or changes the time limit."""
    return key_findings(project, SETTINGS)


def mutate(run: Run, version: tuple[int, int]) -> Mutated:
    """Run mutmut over the changed functions of the run's sources, parsed under the pinned version.

    The smallest stub: the copy, git and parse steps (C7c) and the mutmut processes (C7b) replace it.
    """
    del run, version
    message = (
        f"{GATE_NAME}: running mutmut is not on the gates core yet (steps C7b and C7c)"
    )
    raise GateError(message)


def _order(mutant: Mutant) -> tuple[str, str]:
    """Give the mutant's place among the findings: by path as given, then by mutmut's name."""
    return mutant.given, mutant.name


def outcome(settings: Sequence[Finding], mutated: Mutated) -> Outcome:
    """Return the run's lines: the checker's error first when it did not finish, then the key findings, then each mutant
    not killed in order of path as given, then of name; at the cap, the gate's line naming it comes first."""
    findings = (
        *settings,
        *(
            Finding(f"{mutant.given} {mutant.name} {mutant.status}: {mutant.diff}")
            for mutant in sorted(mutated.mutants, key=_order)
        ),
    )
    error = () if mutated.error is None else (Unfinished(mutated.error),)
    return Outcome(
        lines=(*error, *findings), notes=(AT_THE_CAP,) if mutated.at_cap else ()
    )


def check(run: Run) -> Outcome:
    """Check the run's sources under the project's pin; a GateError from mutmut's run is the checker's error, and the
    key findings still print after it."""
    version = pinned_version(run.project)
    settings = setting_findings(run.project)
    try:
        mutated = mutate(run, version)
    except GateError as error:
        mutated = Mutated(error=error.report)
    return outcome(settings, mutated)


GATE = Gate(
    name=GATE_NAME,
    check=check,
    select=non_test_files,
    selects="Python file that is not a test file",
)


def main(paths: Sequence[Path]) -> int:
    """Run the gate over the paths, in the working directory's project, and return its exit code."""
    return run_gate(GATE, paths)


if __name__ == "__main__":
    run_main(GATE)
