"""The declaration a project makes, and the directories it names.

`blind-reads.json` carries eight keys, and they are the whole of what varies
between the projects this kit is copied into. It is read from
`$CLAUDE_PROJECT_DIR/.claude/blind-reads.json`, and from beside this file when
the project names none: the config belongs to the project, not to wherever the
hook file happens to sit.

The file is required. A declaration that is there and parses is the project's
word, and `{}` is a word like any other -- it asks for the kit's defaults and
gets them. Absent, unreadable, not JSON and not a JSON object are faults, and a
fault is a denial out of every hook and a non-zero exit out of `--config`,
naming the path. They answered as an empty config once, which made a typo in
the file a merge onto the wrong branch and a red run with its deselection
dropped, silently. The fault is held rather than raised at import: seven hooks
build their lane constants at module level, and a hook that raises there takes
the session with it and prints no denial at all.

The three directories resolve together while the scalars and runners resolve
per key: a scalar or a runner collides with nothing, while `tests_dir` naming
`docs` is legal alone and collides the moment a malformed `docs_dir` falls back
to `docs`. Nothing else is in the file: the readable set is
`no-impl-reads.py`'s own table, and the agent names are the kit's identity.
"""

from __future__ import annotations

import functools
import json
import os
import shlex
from collections.abc import Callable
from pathlib import Path
from typing import Any

#: the lane directories this kit's hooks guard are not literals: four of them
#: are the fixed suffixes below, under whatever `gauntlet_dir` resolves to, and
#: the fifth is `tests_dir`, which is the project's own. `lane_dirs()` is the
#: whole table, derived beside the rest of the config further down this file.
LANE_SUFFIXES = ("plans/approved", "specs/approved", "verdicts", "reviews")

def project_checkout(start: Path) -> Path | None:
    """The main checkout holding `start`, following a worktree's pointer file.

    A worktree's `.git` is a file reading `gitdir: <main>/.git/worktrees/<name>`
    rather than a directory, so a walk that stops at the first `.git` stops in
    the worktree. The declaration lives in the main checkout, and a worktree
    that carries no copy of it would otherwise read as a project declaring
    nothing. The pointer names the main checkout's `.git`, whose parent is the
    checkout.

    Anything else a pointer file names -- a submodule's `<super>/.git/modules/`,
    an unreadable file, a spelling this does not know -- is the directory
    holding it, which is what the walk answered before.
    """
    for candidate in (start, *start.parents):
        dot_git = candidate / ".git"
        if dot_git.is_dir():
            return candidate
        if dot_git.is_file():
            try:
                pointer = dot_git.read_text(encoding="utf-8").strip()
            except OSError:
                return candidate
            if not pointer.startswith("gitdir:"):
                return candidate
            gitdir = Path(pointer[len("gitdir:") :].strip())
            if not gitdir.is_absolute():
                gitdir = (candidate / gitdir).resolve()
            common = gitdir.parent.parent
            if gitdir.parent.name == "worktrees" and common.name == ".git":
                return common.parent
            return candidate
    return None


class ConfigFault(Exception):
    """The project's declaration is absent or will not parse.

    Not a default. A project that declares nothing and a project whose
    declaration is a typo are both faults, and the empty object is the only
    way to ask for the kit's defaults and mean it.
    """


def config_path() -> Path:
    """The file this project's declaration is read from, present or not.

    `$CLAUDE_PROJECT_DIR/.claude/blind-reads.json` is the declaration. The
    project path wins because the config is the project's: the kit ships as a
    plugin and lives outside the checkout entirely, shared by every project it
    runs for, and only the project path distinguishes them.

    That variable is set for a hook and is not promised to a script, so where
    it is unset the checkout holding the working directory stands in as the
    project. `${CLAUDE_PLUGIN_ROOT}/scripts/pair.sh` and
    `${CLAUDE_PLUGIN_ROOT}/scripts/blind.sh` run with the checkout as their
    working directory and would otherwise read a project's declaration as
    absent. Both scripts resolve the checkout at entry and export the
    variable, so the walk is the last fallback rather than the usual path;
    where it does run it follows a worktree's pointer file to the main
    checkout, because that is where the declaration is.

    The copy beside this file is the last fallback, for a kit copied into a
    tree rather than installed. The kit itself ships none, and the fallback is
    reached only where the project names no file at all: a project path that
    exists is the declaration whatever it holds, so a malformed project file
    never half-applies by falling through to a second source. Where neither
    file is there the path named is the project's, because that is the one to
    write.
    """
    beside = Path(__file__).resolve().parent / "blind-reads.json"
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project:
        root = project_checkout(Path.cwd().resolve())
        project = str(root) if root else None
    if not project:
        return beside
    candidate = Path(project) / ".claude" / "blind-reads.json"
    return beside if not candidate.is_file() and beside.is_file() else candidate


def config() -> dict[str, Any]:
    """The project's declaration, or a `ConfigFault` naming the file.

    A file that is there and parses is the project's word, and `{}` is a word
    like any other: it asks for the kit's defaults and gets them. Absent,
    unreadable, not JSON, and not a JSON object are the four faults. They were
    one answer with "declares nothing" once -- all five came back `{}` -- which
    meant a typo in the file moved `scripts/pair.sh merge` onto whatever
    `target_branch` defaults to and dropped a runner's deselection, with
    nothing said to anyone.

    The fault is raised rather than printed. `hook_main` turns it into a
    denial and the `--config` reader turns it into a non-zero exit naming the
    path, so an operator reads the path instead of a traceback out of a hook.
    """
    source = config_path()
    try:
        with source.open(encoding="utf-8") as fh:
            loaded = json.load(fh)
    except FileNotFoundError:
        raise ConfigFault(
            f"no declaration at {source}: run scripts/init.py to write one"
        ) from None
    except OSError as exc:
        raise ConfigFault(f"the declaration at {source} cannot be read ({exc})") from None
    except ValueError as exc:
        raise ConfigFault(f"the declaration at {source} is not valid JSON ({exc})") from None
    if not isinstance(loaded, dict):
        raise ConfigFault(f"the declaration at {source} is not a JSON object")
    return loaded


@functools.lru_cache(maxsize=1)
def _declared() -> tuple[dict[str, Any], str | None]:
    """The declaration and the fault it is, read once per process.

    The fault is held here rather than raised because the callers are
    module-level constants in seven hooks and in this file: a hook that raises
    while importing takes the whole session with it, and the denial it owed
    the operator is never printed. So the resolved values stay the kit's
    defaults and the fault waits at the entry point, which is the one place
    that can shape it.
    """
    try:
        return config(), None
    except ConfigFault as exc:
        return {}, str(exc)


def config_fault() -> str | None:
    """The fault this project's declaration is, or `None` when it is its word."""
    return _declared()[1]


def _under(path: str, parent: str) -> bool:
    """Is `path` `parent` itself, or something beneath it? Both normalized."""
    return path == parent or path.startswith(parent + "/")


# --- the three directories a project names, and what they are when it does not


#: the directory keys `blind-reads.json` carries, and the value each takes when
#: the file is absent, malformed, or names a set that cannot be used. There is no
#: fourth directory: see the module docstring for what stays in code and why.
DEFAULT_DIRS = {
    "tests_dir": "tests",
    "gauntlet_dir": "gauntlet",
    "docs_dir": "docs",
}

#: the two scalar keys, and the value each takes when the file names none. They
#: are what `scripts/pair.sh merge` converges onto: the branch a finished pair
#: lands on, and the command that has to pass before it does.
DEFAULT_SCALARS = {
    "target_branch": "main",
    "gate_command": "make check",
}

#: the commands a project declares run outside the sandbox, and the paths each
#: of them reads. The key is the command text exactly as it is typed, and the
#: default is the empty mapping: a project that declares none unwraps none.
DEFAULT_UNWRAPPED: dict[str, list[str]] = {}

#: the two runner keys, and the invocation each takes when the file names none.
#: They are what `scripts/blind.sh test` and `scripts/pair.sh red` run, without
#: the test path and the trailing flags a caller adds after them.
DEFAULT_RUNNERS = {
    "pytest_command": ".venv/bin/pytest",
    "node_command": "node --test",
}


def _clean(name: object) -> str | None:
    """One repo-relative directory, or `None` when the name cannot be one.

    Normalized, so a traversal is judged by where it lands rather than by how
    it is spelled. The root, an absolute path and a name walking out of the
    checkout are all `None`: none of them names a directory inside the repo.
    """
    if not isinstance(name, str) or not name:
        return None
    #: lexical: `Path` has no normalization that collapses `..` without
    #: resolving symlinks, and where a name lands is the whole question here
    name = os.path.normpath(name).replace(os.sep, "/")
    if Path(name).is_absolute() or name in (".", "..") or name.startswith("../"):
        return None
    return name


def _scalar(value: object) -> str | None:
    """One configured scalar, or `None` when the value cannot be one.

    A scalar is a single non-empty line with no leading or trailing blanks left
    on it. A newline inside it is what separates a branch name from a second
    command smuggled after it, so a multi-line value is not a scalar at all.
    """
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or "\n" in value or "\r" in value:
        return None
    return value


def _words(value: object) -> list[str] | None:
    """One runner invocation as words, or `None` when the value cannot be one.

    A command line, split the way a shell splits it, so a marker expression
    stays one word. An unparsable line, an empty one, and anything that is not
    a string are all `None`: none of them names a command to run.
    """
    if not isinstance(value, str):
        return None
    try:
        words = shlex.split(value, comments=False, posix=True)
    except ValueError:
        return None
    return words or None


def runners_from(conf: dict[str, Any]) -> dict[str, list[str]]:
    """The two runner invocations this config resolves to, defaults filled in.

    Per key, like the scalars: a runner overlaps no lane and no other runner, so
    an unusable `pytest_command` leaves the node one standing.
    """
    resolved: dict[str, list[str]] = {}
    for key, default in DEFAULT_RUNNERS.items():
        words = _words(conf.get(key)) if key in conf else None
        resolved[key] = words if words is not None else shlex.split(default)
    return resolved


def unwrapped_from(conf: dict[str, Any]) -> dict[str, list[str]]:
    """The commands this config declares unwrapped, and the paths each reads.

    All or nothing, like the directories. A key that is not a command text, a
    value that is not an object, a `reads` that is not a list of paths: any one
    of them voids the whole mapping. Per-entry fallback would leave a project
    unwrapping the neighbours of the entry it got wrong, which is the one place
    in this design where a command runs outside the sandbox.

    The paths are carried as the project spelled them. Whether one resolves is a
    question about a checkout rather than about the declaration, and it is asked
    where the checkout is known.
    """
    if "unwrapped_commands" not in conf:
        return {}
    declared = conf.get("unwrapped_commands")
    if not isinstance(declared, dict):
        return {}
    resolved: dict[str, list[str]] = {}
    for command, value in declared.items():
        if not isinstance(command, str) or not command.strip():
            return {}
        if not isinstance(value, dict):
            return {}
        reads = value.get("reads", [])
        if not isinstance(reads, list):
            return {}
        if any(not isinstance(one, str) or not one for one in reads):
            return {}
        resolved[command] = list(reads)
    return resolved


def scalars_from(conf: dict[str, Any]) -> dict[str, str]:
    """The two scalars this config resolves to, defaults filled in.

    Per key, unlike the directories: a scalar cannot overlap a lane or another
    scalar, so an unusable branch name has nothing to take down with it and the
    gate keeps whatever the project named.
    """
    resolved: dict[str, str] = {}
    for key, default in DEFAULT_SCALARS.items():
        name = _scalar(conf.get(key)) if key in conf else None
        resolved[key] = name if name is not None else default
    return resolved


def dirs_from(conf: dict[str, Any]) -> dict[str, str]:
    """The three directories this config resolves to, defaults filled in.

    All or nothing. A key that cannot be a directory, or any pair that overlaps
    -- equal, under, or over -- voids the whole set and every key takes its
    default. A key the file omits takes its default and is still checked against
    the rest, so naming `tests_dir` as `docs` collides with the default
    `docs_dir` exactly as it would with a declared one.
    """
    resolved: dict[str, str] = {}
    for key, default in DEFAULT_DIRS.items():
        if key not in conf:
            resolved[key] = default
            continue
        name = _clean(conf.get(key))
        if name is None:
            return dict(DEFAULT_DIRS)
        resolved[key] = name
    names = list(resolved.values())
    for position, one in enumerate(names):
        for other in names[position + 1 :]:
            if _under(one, other) or _under(other, one):
                return dict(DEFAULT_DIRS)
    return resolved


@functools.lru_cache(maxsize=1)
def dirs() -> dict[str, str]:
    """The resolved set, read once per process."""
    return dirs_from(_declared()[0])


@functools.lru_cache(maxsize=1)
def scalars() -> dict[str, str]:
    """The resolved scalars, read once per process."""
    return scalars_from(_declared()[0])


@functools.lru_cache(maxsize=1)
def runners() -> dict[str, list[str]]:
    """The resolved runner invocations, read once per process."""
    return runners_from(_declared()[0])


@functools.lru_cache(maxsize=1)
def unwrapped_commands() -> dict[str, list[str]]:
    """The declared unwrapped commands, read once per process."""
    return unwrapped_from(_declared()[0])


def unwrapped_command_texts() -> list[str]:
    """One declared command per line, in the order the declaration gives them."""
    return list(unwrapped_commands())


def pytest_command() -> list[str]:
    """The python runner, without the test path a caller adds after it."""
    return list(runners()["pytest_command"])


def node_command() -> list[str]:
    """The javascript runner, without the test path a caller adds after it."""
    return list(runners()["node_command"])


def target_branch() -> str:
    """The branch a finished pair lands on."""
    return scalars()["target_branch"]


def gate_command() -> str:
    """The command that has to pass in the combined tree before it lands."""
    return scalars()["gate_command"]


def tests_dir() -> str:
    """The blind writer's lane."""
    return dirs()["tests_dir"]


def gauntlet_dir() -> str:
    """The base every lane sits under."""
    return dirs()["gauntlet_dir"]


def docs_dir() -> str:
    """The prose a blind agent may read."""
    return dirs()["docs_dir"]


def lane(suffix: str) -> str:
    """One of the four fixed lane suffixes, under the configured base."""
    return gauntlet_dir() + "/" + suffix


def plans_lane() -> str:
    """The prosecutor's lane."""
    return lane("plans/approved")


def specs_lane() -> str:
    """The arbiter's lane."""
    return lane("specs/approved")


def verdicts_lane() -> str:
    """The juror's lane."""
    return lane("verdicts")


def reviews_lane() -> str:
    """The reviewers' lane."""
    return lane("reviews")


def lane_dirs() -> dict[str, str]:
    """Every lane directory this kit guards, by the name its row carries.

    One table with two consumers, which must not drift apart: `lanes.py` builds
    its rows from this, and `bwrap-wrap.py` binds each of these read-only
    inside every wrapped profile. A lane the write tools hold and the mount
    table leaves writable -- or the reverse -- is a hook and a sandbox that
    disagree about the same directory, and a shell reaches the lane the write
    tools were guarding. `lanes.py --self-test` asserts the two sets are equal,
    so an edit to one that misses the other fails a gate.

    Four are the fixed suffixes under `gauntlet_dir`, because that shape is the
    kit's identity rather than a project's layout; `tests_dir` is the project's
    own directory and is read from the declaration like any other.
    """
    return {
        "specs": specs_lane(),
        "plans": plans_lane(),
        "tests": tests_dir(),
        "reviews": reviews_lane(),
        "verdicts": verdicts_lane(),
    }


#: the lane directories, as the tuple the mount table binds
LANE_DIRS = tuple(lane_dirs().values())


#: what `--config <key>` answers: the eight keys the file carries, and the four
#: derived lanes, so a shell script asks for a lane rather than rebuilding one
#: out of the base and a suffix it would have to hardcode. A runner answers one
#: word per line; every other key answers one line.
CONFIG_READERS: dict[str, Callable[[], str | list[str]]] = {
    "tests_dir": tests_dir,
    "gauntlet_dir": gauntlet_dir,
    "docs_dir": docs_dir,
    "target_branch": target_branch,
    "gate_command": gate_command,
    "pytest_command": pytest_command,
    "node_command": node_command,
    "unwrapped_commands": unwrapped_command_texts,
    "plans_lane": plans_lane,
    "specs_lane": specs_lane,
    "verdicts_lane": verdicts_lane,
    "reviews_lane": reviews_lane,
}


def config_lines(key: str) -> list[str]:
    """One config value as lines a shell reads with `read`.

    A known key is one line, except a runner invocation, which is one word per
    line: a word carrying a space is one word to the shell that reads it back.
    An unknown key is no lines.
    """
    reader = CONFIG_READERS.get(key)
    if not reader:
        return []
    value = reader()
    return list(value) if isinstance(value, list) else [value]
