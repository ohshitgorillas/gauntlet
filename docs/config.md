# Configuring a repository for Gauntlet

A repository declares how its tests and gates run, what the harness must protect, and which specialist roles it brings. The mechanisms these settings feed are described in [`design.md`](design.md).

## `gauntlet.yaml`

Place it at the repository root.

```yaml
image: .gauntlet/Containerfile
tests:
  - {dir: tests/py, run: "pytest {ids}"}
  - {dir: tests/js, run: "node --test {ids}"}
gates: scripts/gate.sh make check
test_helpers: [hqptuner/clock.py, tests/support/fake_clock.py]
test_policy: docs/testing.md
protected: [conftest.py, pyproject.toml, package.json, scripts/gate.sh]
interface:
  - {lang: py, run: "stubgen -o {out} {modules}"}
  - {lang: js, run: "tsc --allowJs --declaration --emitDeclarationOnly --outDir {out} {files}"}
test_lint: "ruff check {files} && mypy {files}"
implementer_network: false
caps: {plan: 2, spec: 2, juror: 2, build: 2, review: 2, reopen: 2}
roles:
  planner: {model: claude-opus-5-5, effort: high}
  juror: {effort: medium}
```

| Key | Required | Meaning |
|---|---|---|
| `image` | yes | `Containerfile` for the repository's toolchain image. It holds the whole toolchain the tests and gates need. The harness builds the pinned image every container runs on top of it, adding the CLI at the harness's pinned version, the `socat` relay and the `gauntlet-launch` entrypoint; the `Containerfile` carries none of them. Every dependency change needs a rebuild. |
| `tests` | yes | Each test directory and the command that runs it. `{ids}` is replaced with the test ids. The red run uses every entry. |
| `gates` | yes | The command the harness runs, in its own container, after each build step and before land. |
| `test_helpers` | no | Files outside `tests/` that testers may read: fakes, clocks, fixtures. |
| `test_policy` | yes | The numbered test rules that scriveners write to, and that the bailiff and auditor rule against. |
| `protected` | no | Paths outside `tests/` that can change test outcomes. They are mounted read-only for implementers. Include the root `conftest.py`, test-runner configuration and the gate script. `pyproject.toml` holds both build and test settings: protecting it stops implementers changing dependencies, and leaving it unprotected leaves its test settings open. |
| `interface` | yes | Per language, the command that generates the signatures-only view testers see. `{out}` is the output directory; `{modules}` and `{files}` are the names the plan touches. |
| `test_lint` | no | The lint and type commands testers run on their test files. `{files}` is replaced with those files. |
| `implementer_network` | no, default `false` | Whether implementer containers may reach the network beyond the harness proxy. |
| `caps` | no, defaults as shown | Round caps per loop. |
| `roles` | no | `model` and `effort` per role, fixed or repo-defined. An unset key uses the harness default. |

## Repo roles

Gauntlet ships its fixed roles and one general implementer and one general tester. A repository adds specialists as files in `.gauntlet/roles/<name>.md`:

```markdown
---
kind: implementer
description: Timing-sensitive code; cuts clock seams into code that waits.
skills: [clock-seams]
---
Craft instructions for the role.
```

- **`kind`** is one of `implementer`, `tester` or `reviewer`. A reviewer runs as a reader and takes part in stage 11. The kind fixes what the role can see, write and run; nothing in the file can change that.
- **`description`** is one line. The planner routes work by it: plan steps go to implementers, spec lines go to testers.
- **`skills`** names skills from `.gauntlet/skills/` that the role loads.
- **The body** is the role's craft. It cannot widen the role's permissions, and it cannot override the fixed answer schema for its kind.

A specialist that both writes code and writes its own tests becomes two roles: an implementer and a tester, which share a skill.

## Skills

Each skill lives in `.gauntlet/skills/<name>/SKILL.md`, with any supporting files beside it. Skills hold craft shared across roles, such as how to cut a clock seam. They are mounted read-only into the containers of the roles that name them.

## Test policy

The file named by `test_policy` holds numbered rules, such as what a test may patch, or what an assertion must pin. Rules are cited by number in tester answers, bailiff rulings and auditor rows, so a rule keeps its number for life. A retired rule is marked retired, not renumbered.
