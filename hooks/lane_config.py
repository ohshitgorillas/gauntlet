"""The keys a declaration names, and what each one is when it names none.

The three directories resolve together while the scalars and runners resolve
per key: a scalar or a runner collides with nothing, while `tests_dir` naming
`docs` is legal alone and collides the moment a malformed `docs_dir` falls back
to `docs`. Nothing else is in the file: the readable set is
`no-impl-reads.py`'s own table, and the agent names are the kit's identity.
"""

from __future__ import annotations

import functools
import os
import shlex
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lane_declaration import _declared, _under

#: the lane directories this kit's hooks guard are not literals: four of them
#: are the fixed suffixes below, under whatever `gauntlet_dir` resolves to, and
#: the fifth is `tests_dir`, which is the project's own. `lane_dirs()` is the
#: whole table, derived beside the rest of the config further down this file.
LANE_SUFFIXES = ("plans/approved", "specs/approved", "verdicts", "reviews")

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

#: the paths a project declares writable inside a wrapped shell on top of the
#: checkout itself, and the empty list a project that declares none takes. Every
#: path outside the checkout is already readable, so the key is writable-only.
DEFAULT_EXTRA_BINDS: list[str] = []

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


def _expand_home(path: str) -> str:
    """`~` and `~/...` against `HOME`, and the path unchanged where there is none.

    `os.path.expanduser` falls back to the password database, which answers a
    home directory for a process that has no `HOME` at all. A declaration read
    in that environment would bind a path the project never spelled, so the
    expansion is `HOME` or nothing and an unexpanded `~` stays relative -- which
    is what the mount table drops it for.
    """
    if path != "~" and not path.startswith("~/"):
        return path
    home = os.environ.get("HOME")
    return home + path[1:] if home else path


def extra_binds_from(conf: dict[str, Any]) -> list[str]:
    """The extra writable paths this config declares, `~` expanded.

    All or nothing, like the unwrapped commands: a value that is not a list, an
    entry that is not a string, and an empty entry each void the whole key. Half
    of a mistyped list taking effect would open a path the project never named.

    Shape and `~` only. Whether a path is absolute, whether its source is live,
    and whether it stands over something a profile protects are questions about
    a checkout and a host, and they are asked where the mount table is built.
    """
    if "extra_binds" not in conf:
        return []
    declared = conf.get("extra_binds")
    if not isinstance(declared, list):
        return []
    resolved: list[str] = []
    for entry in declared:
        if not isinstance(entry, str) or not entry:
            return []
        resolved.append(_expand_home(entry))
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


@functools.lru_cache(maxsize=1)
def extra_binds() -> list[str]:
    """The declared extra writable paths, read once per process."""
    return extra_binds_from(_declared()[0])


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


#: what `--config <key>` answers: the nine keys the file carries, and the four
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
    "extra_binds": extra_binds,
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
