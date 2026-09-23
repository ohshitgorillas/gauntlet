#!/usr/bin/env python3
"""Write a project's `blind-reads.json` and the lane directories it names.

The kit ships as a plugin and lives outside the checkout it runs for, so the
one thing a project has to say for itself is where its directories are. That
declaration is `<project>/.claude/blind-reads.json`, and `lane_declaration.config`
faults without it rather than falling back on the kit's defaults: a project
that never wrote the file and a project that meant the defaults are different
facts, and only one of them is safe to guess at. This script is the deliberate
step that makes them different -- one run, one file, and the guessing stops.

    scripts/init.py [--project DIR] [--force] [--print]

`--project` is the checkout to install into; the default is the checkout this
script sits in, or `$CLAUDE_PROJECT_DIR` where it is set. `--force` overwrites
a declaration that is already there, and without it an existing file is left
alone and the exit status says so: a project's word is not this script's to
replace by accident. `--print` writes nothing and prints what would be written.

The values it writes are the kit's defaults, read out of `lane_config` rather
than retyped here, so a project starts from the shipped layout and edits the
file by hand from there. All eight keys are written out, present and explicit,
because a key a project can see is a key it can change.

It also creates the skeleton under `gauntlet_dir`: the four lanes the agents
write, the two draft directories that feed them, and `red` and `merge`, which
`scripts/pair.sh` writes its evidence to. Each gets a `.gitkeep`, because an
empty directory is not a thing git tracks and a lane that vanishes on clone is
a lane the first agent recreates in the wrong place.

It writes no hook wiring. An installed plugin declares its own hooks in its
manifest, so `.claude/settings.json` is the manifest's business and not this
script's; a copy of that file written here would be a second source of truth
for what is wired, and the wrong one.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

_HOOKS = str(Path(__file__).resolve().parent / ".." / "hooks" / "lib")
sys.path.insert(0, _HOOKS)

try:
    import lane_config  # noqa: E402
    import lane_declaration  # noqa: E402
except ImportError:
    sys.exit(f"init.py: no lane_config.py in {_HOOKS}: scripts/ ships with hooks/")

#: the file a project declares itself in, relative to the checkout
DECLARATION = Path(".claude") / "blind-reads.json"

#: the skeleton under `gauntlet_dir`. The four lanes are the ones the hooks
#: guard; `plans/drafts` and `specs/drafts` are where a block is written before
#: it is approved into a lane; `red` and `merge` are `scripts/pair.sh`'s
#: evidence. The shape does not vary between projects -- only the base does.
SKELETON = (
    "plans/drafts",
    "plans/approved",
    "specs/drafts",
    "specs/approved",
    "red",
    "reviews",
    "verdicts",
    "merge",
)


def declaration() -> dict[str, Any]:
    """The eight keys and the kit's default for each, in a stable order.

    The defaults are `lane_config`'s own tables, not a copy: a second copy of
    `target_branch` here is a second answer the day the first one changes.
    """
    written: dict[str, Any] = {}
    written.update(lane_config.DEFAULT_DIRS)
    written.update(lane_config.DEFAULT_SCALARS)
    written.update(lane_config.DEFAULT_RUNNERS)
    written["extra_binds"] = list(lane_config.DEFAULT_EXTRA_BINDS)
    return written


def body(conf: dict[str, Any]) -> str:
    """The file's text: pretty JSON with a trailing newline, for hand editing."""
    return json.dumps(conf, indent=2) + "\n"


def default_project() -> Path:
    """The checkout to install into where the caller names none.

    `$CLAUDE_PROJECT_DIR` first, because a session that has one is working on
    that project. Otherwise the checkout holding this script, resolved the way
    every hook resolves it, so running the script out of a plugin directory
    does not write a declaration into the plugin.
    """
    named = os.environ.get("CLAUDE_PROJECT_DIR")
    if named:
        return Path(named)
    root = lane_declaration.project_checkout(Path.cwd().resolve())
    return root if root else Path.cwd().resolve()


def skeleton_dirs(project: Path, base: str) -> list[Path]:
    """The eight directories the skeleton is, under `base` in `project`."""
    return [project / base / suffix for suffix in SKELETON]


def install(project: Path, *, force: bool) -> tuple[int, list[str]]:
    """Write the declaration and the skeleton; the exit status and what to say.

    An existing declaration without `--force` is status 1 and nothing written,
    the skeleton included: a project that already declared itself has a base
    this script has not read, and creating the shipped one beside it would put
    eight empty directories where no lane is.
    """
    lines: list[str] = []
    target = project / DECLARATION
    conf = declaration()
    if target.exists() and not force:
        return 1, [f"EXISTS {target} -- left alone; pass --force to overwrite it"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body(conf), encoding="utf-8")
    lines.append(f"WROTE {target}")
    for path in skeleton_dirs(project, conf["gauntlet_dir"]):
        path.mkdir(parents=True, exist_ok=True)
        keep = path / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
        lines.append(f"LANE {path}")
    return 0, lines


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="init.py", description="Write a project's blind-reads.json and lane skeleton."
    )
    parser.add_argument("--project", help="the checkout to install into")
    parser.add_argument("--force", action="store_true", help="overwrite an existing declaration")
    parser.add_argument(
        "--print", dest="show", action="store_true", help="print the file; write nothing"
    )
    args = parser.parse_args(argv)

    project = Path(args.project).resolve() if args.project else default_project()
    if args.show:
        sys.stdout.write(body(declaration()))
        return 0
    if not project.is_dir():
        sys.stderr.write(f"init.py: no such directory: {project}\n")
        return 2
    status, lines = install(project, force=args.force)
    stream = sys.stdout if status == 0 else sys.stderr
    for line in lines:
        stream.write(line + "\n")
    return status


def self_test() -> int:
    """Pin what this script exists to hold, on throwaway trees."""
    rules: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        status, _ = install(project, force=False)
        target = project / DECLARATION
        rules["1 a fresh project gets a declaration and status 0"] = (
            status == 0 and target.is_file()
        )

        loaded = json.loads(target.read_text(encoding="utf-8"))
        expected = (
            set(lane_config.DEFAULT_DIRS)
            | set(lane_config.DEFAULT_SCALARS)
            | set(lane_config.DEFAULT_RUNNERS)
            | {"extra_binds"}
        )
        rules["2 it carries all eight keys, explicitly"] = (
            set(loaded) == expected and len(expected) == 8
        )

        rules["3 every value is the kit's default, not a second copy"] = loaded == declaration()

        rules["4 the file it writes is the project's word, not a fault"] = (
            _reads_back(project) == loaded
        )

        base = loaded["gauntlet_dir"]
        rules["5 the eight skeleton directories exist under gauntlet_dir"] = all(
            path.is_dir() for path in skeleton_dirs(project, base)
        )
        rules["6 each carries a .gitkeep, so a clone keeps the lane"] = all(
            (path / ".gitkeep").is_file() for path in skeleton_dirs(project, base)
        )
        rules["7 the four guarded lanes are among them"] = all(
            (project / base / suffix).is_dir()
            for suffix in ("plans/approved", "specs/approved", "reviews", "verdicts")
        )
        rules["8 it writes no hook wiring"] = not (project / ".claude" / "settings.json").exists()

        target.write_text('{"tests_dir": "spec"}\n', encoding="utf-8")
        status, lines = install(project, force=False)
        rules["9 an existing declaration is left alone, with status 1"] = (
            status == 1
            and json.loads(target.read_text(encoding="utf-8")) == {"tests_dir": "spec"}
            and lines[0].startswith("EXISTS ")
        )

        status, _ = install(project, force=True)
        rules["10 --force overwrites it"] = (
            status == 0 and json.loads(target.read_text(encoding="utf-8")) == declaration()
        )

        bare = Path(tmp) / "bare"
        bare.mkdir()
        rules["11 a project with no declaration is a fault before init runs"] = (
            _fault_of(bare) is not None
        )
        install(bare, force=False)
        rules["12 and no fault after it"] = _fault_of(bare) is None

        empty = Path(tmp) / "empty"
        (empty / ".claude").mkdir(parents=True)
        (empty / DECLARATION).write_text("{}\n", encoding="utf-8")
        rules["13 an empty object is a declaration, not a fault"] = _fault_of(empty) is None

    for label, ok in rules.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(rules.values()) else 1


def _in_project(project: Path, call: str) -> str:
    """Run `call` in a fresh interpreter with `project` as the project directory.

    A fresh interpreter, because `lane_config` caches the declaration for the
    life of a process and this self-test asks about several projects.
    """
    source = (
        f"import sys; sys.path.insert(0, {_HOOKS!r}); "
        f"import lane_config; import lane_declaration; {call}"
    )
    environment = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
    completed = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
        timeout=60,
    )
    return completed.stdout


def _fault_of(project: Path) -> str | None:
    """`lane_declaration.config_fault` for that project, or `None`."""
    printed = _in_project(project, "print(lane_declaration.config_fault() or '', end='')")
    return printed or None


def _reads_back(project: Path) -> dict[str, Any]:
    """The declaration `lane_declaration` reads back out of that project."""
    return dict(
        json.loads(
            _in_project(project, "import json; print(json.dumps(lane_declaration.config()))")
        )
    )


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else main(sys.argv[1:]))
