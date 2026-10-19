# Quality gates for building Gauntlet

Status: approved 2026-10-18.

## Intent

Gauntlet is built by agents before it can build itself. Gating is extremely strict and trust in agent-written code is low. The outcome wanted is coherent, cohesive, correct, easily testable code: no shortcuts, no patches, no workarounds. A small bug that shows a whole system is wrong leads to the system being rebuilt, not the symptom patched.

These gates go in before any product code. M1 starts under the full set.

## Principles

1. **A gate must be impossible to satisfy without the code getting better.** A gate an agent can pass by reshaping code, rather than improving it, is not included.
2. **No count caps.** Nothing triggers on a number of arguments, returns, branches, statements, lines, nesting levels, files per directory, or a complexity score. Whether a unit does too much is a question for the reviewer.
3. **No coverage threshold.** Test quality is judged by mutation testing. Coverage is measured only to find lines mutation testing cannot see.
4. **No suppressions.** No inline suppression comment, no per-file ignore, no exemption table, no baseline, no ratchet. A finding is fixed in the code.

## Gates

All gates run from one entry point, `make check`, which pre-commit invokes. Every gate applies to every Python file in the tree: `gauntlet/`, `tests/`, gate scripts, and any hook or tool script. No path is excluded. A Python file is a file whose name ends in `.py` or `.pyi`, or an extensionless file whose first line is a shebang that names python; a `.pyw` file is not one. A gate's verdict on a Python file is the same whatever other files the tree holds. Every gate is a script under `gates/` that `make check` runs; a gate whose checker is an external tool runs that tool over the tree's Python files with the settings in `pyproject.toml`, which holds those settings and nothing else does, and returns the checker's findings. A gate exits 0 with no finding, 1 with one or more findings, and 2 when its checker could not finish; it prints each finding on its own line and prints its count line on every run. A gate given no Python file prints that nothing was checked and exits 1, since an empty run proves nothing.

### Types

- mypy with `strict = true`, plus `warn_unreachable = true`, `disallow_any_explicit = true`, `disallow_any_expr = true`, and every optional error code in `enable_error_code`. `python_version = "3.12"`, `requires-python = ">=3.12"`, ruff `target-version = "py312"`.
- pyright in `strict` mode.
- `typing.cast` is banned (ruff `TID251`). The ban is on the function, not its spelling: it covers `typing.cast` under every name it is imported by, `typing_extensions.cast` included, and the banned-api table lists each such name.

### Lint and format

- ruff `select = ["ALL"]`, `preview` off.
- `ignore` holds only:
  - `C901`, `E501`, `W505`, `PLR0911`, `PLR0912`, `PLR0913`, `PLR0915`, `PLR0917`;
  - `D203`, `D213`, `COM812`, `ISC001`;
  - `S603`.

  Each ignore carries a one-line reason comment in `pyproject.toml`.
- `per-file-ignores`: `tests/**` gets `S101` only.
- ruff format in check mode.

### Suppression gate

A gate script fails on any of:

- a `noqa`, `type: ignore`, `pyright: ignore`, `pragma: no cover` or `pragma: no mutate` comment, found by tokenizing;
- a `# mypy:`, `# pyright:`, `# fmt: off` or `# fmt: skip` comment;
- a `@typing.no_type_check` decorator;
- a `per-file-ignores` entry other than `tests/** = ["S101"]`;
- an `ignore` entry not on the list above, or `preview` on;
- any mypy `[[tool.mypy.overrides]]` section, or a pyright rule downgraded from strict;
- any path excluded from a checker: ruff `exclude`/`extend-exclude`, mypy `exclude` or `follow_imports` other than `normal`, pyright `exclude`/`ignore`, coverage `omit`;
- any ignore list in another tool's config: mutmut `do_not_mutate`/`do_not_mutate_patterns`, import-linter `ignore_imports`, a filepawl exempt table or allowance baseline, a deptry ignore, a vulture whitelist, a pytest `filterwarnings` entry other than `"error"`, coverage `exclude_lines`/`exclude_also`.

### Tests

- **Mutation testing blocks.** mutmut runs over every Python file outside `tests/`, in full on every commit, with no cache. Any surviving mutant fails the gate. There is no score threshold. The fix is a test that kills the mutant, or deleting code no behavior depends on. An equivalent mutant means the code is rewritten.
- **Seams:** tests use real git and filesystem. Podman and the Claude API never run in tests; seams take their process runner as a parameter.
- **No copy:** errors are typed exceptions carrying data; tests assert the type and the values they seeded.
- **Unseen-line backstop.** A gate fails on any line in a file mutation testing covers that no test executes and on which mutmut generated no mutant, and lists each one.
- **pytest strictness:** `--strict-markers`, `--strict-config`, `filterwarnings = ["error"]`, `xfail_strict = true`, random test order (pytest-randomly), and a per-test timeout (pytest-timeout).
- **Test-shape gates**, from filepawl's suite gates and hqptuner2's `check_test_assertions.py` and `check_no_copy_assertions.py`, applied to every test file:
  - no `unittest.mock`, `patch`, `monkeypatch` or `setattr` on code under test;
  - no access to private names of the code under test;
  - one claim per test;
  - no test that asserts only absence, or only existence or type;
  - no clock reads and no sleeps;
  - no skip, skipif or xfail;
  - no test with zero assertions, no `and`/`or` at an assertion's root, no assertion in a loop or inside `all()`/`any()`, no assertion outside a test;
  - no multi-word string literal in an assertion unless the test seeded it.

  filepawl's `length`, `dircount` and `nesting` gates are off.

### Structure

- **Layering** with import-linter, exhaustive: every module under `gauntlet/` belongs to a contract. `seams` may import `core`; `core` may not import `seams`. `exclude_type_checking_imports = false`.
- **Pure core**: a `forbidden` contract stops `gauntlet.core` importing `os`, `sys`, `io`, `pathlib`, `subprocess`, `socket`, `shutil`, `tempfile`, `time`, `datetime`, `random`, `asyncio`, `threading`, `multiprocessing` or `logging`.
- **filepawl code gates**: no re-export or forwarding modules, consistent key sets for dict returns, no `dict[str, Any]` results, no sentinel return from an `except`, no import of another module's private names.
- **Dead code**: vulture over the whole tree with `min_confidence = 60`, no whitelist, no `ignore_names`, no `ignore_decorators`.

### Dependencies

- All dependencies pinned in a committed `uv.lock`; the gate fails if the lock is out of date with `pyproject.toml`.
- deptry fails on unused, missing or transitive-only dependencies.

### Gate code

- Every gate script has its own tests, under every gate above.
- A wiring check fails if a script in the gates directory is not invoked by `make check`.
- A gate reads its checker's machine-readable output where the checker offers one, and a finding carries the checker's whole message.

## Judgment layer

A reviewer agent, defined in the repository, reads each diff without being told what it is for and returns findings anchored to file and line with a failure scenario. It looks for what no program can prove: incoherence, low cohesion, a duplicated concept, logic in the wrong home, a patch where a root-cause fix belongs. A finding stands until the code is fixed or the owner rules on it.

## Non-goals

- Mechanisms that stop an agent bypassing the gates (`--no-verify`, `SKIP=`, editing gate config).
- The gate that blocks shell-command parsing in Gauntlet's own code (roadmap M1).
- Gates for any language other than Python.

## Left to the builder

- Directory and file names for gate scripts.
- The per-test timeout value.
- How the unseen-line backstop joins coverage data with mutmut's mutant list.
- Parallelism of the mutation run, within half of `nproc`.
