#!/usr/bin/env python3
"""Shell and path shapes the lane hooks share.

The lane hooks all ask the same question: does this path fall inside a
directory that belongs to one agent. This module answers it, so that a hook is
a policy over the answer rather than a second parser.

It holds the shape of a lane hook too, at the end: the dispatch from a tool
call to the handler for its kind, the entry point that reads a payload and
prints a denial, the sentence a write into a lane is refused with, and the
whole policy of a lane one named agent writes. Those were the same text in
five files, which is the arrangement where one hook gets a fix and four keep
the defect.

No shell command is read here. This module carried a classifier once -- a
reader allowlist, a runner table, a redirection scanner, a git form test --
and every lane hook decided a `Bash` call through it. That half is gone with
the hooks' `Bash` matchers: what holds a shell out of a lane is the mount
table `bwrap-wrap.py` builds, which binds every lane directory read-only
inside every wrapped profile. A command that names a lane is not parsed for
the name any more; it fails in the kernel or it does not touch the lane.

What is left of the shell side is `TESTPATH`, the shape of the one argument
`blind-bash.py` admits after `scripts/blind.sh test`. It is a path shape, not
a command shape: the test directory as configured, optionally under one spec
worktree, matched whole and matched again after `os.path.normpath`, so an
argument that opens under the lane and walks out of it is not that shape.

It is deliberately standalone. These hooks travel as a unit into other repos,
where the change budget and its `free_bash` allowlist do not exist.

`blind-reads.json` carries eight keys, and they are the whole
of what varies between the projects this kit is copied into. It is read from
`$CLAUDE_PROJECT_DIR/.claude/blind-reads.json`, and from beside this file when
the project names no file at all: the config belongs to the project, not to
wherever the hook file happens to sit, so a kit installed once outside the
checkout still reads each project's own declaration.

The file is required. A declaration that is there and parses is the project's
word, and `{}` is a word like any other -- it asks for the kit's defaults and
gets them. Absent, unreadable, not JSON and not a JSON object are faults, and
a fault is a denial out of every hook and a non-zero exit out of `--config`,
naming the path. They answered as an empty config once, alongside "declares
nothing", which made a typo in the file a merge onto the wrong branch and a
red run with its deselection dropped, silently. `scripts/init.py` writes the
file, so an install has one deliberate step instead of a quiet wrong answer.

The fault is held rather than raised at import: seven hooks build their lane
constants at module level, and a hook that raises there takes the session with
it and prints no denial at all. Three name
directories. `tests_dir` is the blind writer's lane, `tests` by default, and what
the agent definitions and the docs mean by `<tests dir>`. `gauntlet_dir` is where
the chain's artifacts live, `gauntlet` by default. `docs_dir` is the prose a
blind agent may read, `docs` by default. The structure under `gauntlet_dir` does
not move: the four lanes are always `plans/approved`, `specs/approved`,
`verdicts` and `reviews` beneath it, because that shape is the kit's identity
rather than a project's layout.

The other two are what `scripts/pair.sh merge` converges onto, and they are
scalars rather than paths. `target_branch` is the branch a finished pair lands
on, `main` by default. `gate_command` is the command that has to pass in the
combined tree before it lands, `make check` by default. They validate
independently of the three directories and of each other: a name a project
cannot use falls back on its own, because neither one can collide with a lane
the way two directories can. The default gate is a command most projects either
have or notice the absence of at once, which is the safe direction -- a gate
that cannot run holds the pair in its worktrees rather than landing it unchecked.

The last two are the runner invocations `scripts/blind.sh test` and
`scripts/pair.sh red` type. `pytest_command` is `.venv/bin/pytest` by default,
`node_command` is `node --test`, and a project that has to deselect a marker or
import a loader names the whole invocation once here instead of editing the two
scripts by hand. Each is a command line split the way a shell splits it, and
`--config` prints one word per line, so an argument carrying a space survives
the trip into a shell array. They resolve per key like the scalars, for the same
reason: a runner collides with nothing. The callers add the test path and their
own trailing flags after the configured words, and a configured word carrying a
slash is a path in the checkout while a bare word is on `PATH`. A runner is
configuration and never agent input: `blind-bash.py` admits `scripts/blind.sh
test <path>` and no runner argument beside it, so no shape here widens the one
command a blind agent has.

No lane is a literal any more, so the bound on this file is no longer that a
lane is code a data file cannot reach. The bound is that the three names must
be usable and pairwise disjoint: each a repo-relative normalized path, none of
them the root, absolute or walking out, and none equal to, under, or over
another. A set failing any of those is not partly honoured -- every key falls
back to its default together. Per-key fallback is unsound once the lanes are
data: `tests_dir` naming `docs` is legal alone and collides the moment a
malformed `docs_dir` falls back to `docs`, which would hand the blind writer a
lane over the prose it reads.

Nothing else is in the file. The readable set is `no-impl-reads.py`'s own
table, and the agent names are the kit's identity, copied verbatim.

The owner's off switch lives here too, as `bypassed()`. This module is the one
place all seven hooks already share, so the switch is defined once and each
hook reads it rather than each hook parsing an environment of its own. It reads
`os.environ` and never a hook payload: the payload is the one input an agent
controls, and a switch honouring a payload key would be a bypass any subagent
could forge in a tool call.
"""

from __future__ import annotations

import functools
import json
import os
import re
import shlex
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

#: one payload as a hook reads it: whatever JSON carried, decided at runtime by
#: `payload_fault` rather than trusted by its static shape
Payload = dict[str, Any]
#: the `tool_input` of one payload, on the same terms: a hook reads the keys it
#: needs through `command_of` and `write_target`, which answer for a missing key
ToolInput = dict[str, Any]
#: the three arguments every lane verdict takes, and the refusal or None it gives
Verdict = Callable[[str, ToolInput, Payload], str | None]

#: a slug names one path segment and carries no traversal
SLUG = r"[A-Za-z0-9][A-Za-z0-9._-]*"
#: a spec worktree is the other place a blind agent's tests live, so the blind
#: runner's argument may carry that one prefix and no other: the writer runs
#: the suite in the tree it wrote in
TREE = rf"\.claude/worktrees/{SLUG}-spec/"

#: the lane directories this kit's hooks guard are not literals: four of them
#: are the fixed suffixes below, under whatever `gauntlet_dir` resolves to, and
#: the fifth is `tests_dir`, which is the project's own. `lane_dirs()` is the
#: whole table, derived beside the rest of the config further down this file.
LANE_SUFFIXES = ("plans/approved", "specs/approved", "verdicts", "reviews")

def path_shape(prefix: str) -> str:
    """The regex source a path prefix expands into.

    Repo-relative, under `prefix`, optionally inside a spec worktree. The
    trailing class admits `.` and `/`, so it admits `..` as well: the shape is
    not the whole key, and `is_blind_run` normalizes what it matches.
    """
    return rf"(?:{TREE})?{re.escape(prefix)}/[A-Za-z0-9_][A-Za-z0-9._/-]*"


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


#: the shape the blind runner's one argument takes, exported so that
#: `blind-bash.py` reads the same regular expression the classifier does
TESTPATH = path_shape(tests_dir())


_TESTPATH_WHOLE = re.compile(TESTPATH + r"\Z")


#: a write stage whose targets this parser cannot name. `STAGE` is an
#: interpreter handed a script: the paths are computed inside the script, so
#: there is no target to test and the stage is denied. `STDIN` is `xargs`: the
#: paths were produced upstream, so the evidence is the whole command and not
#: this stage.
STAGE, STDIN = "stage", "stdin"


def checkout_root(path: str) -> str | None:
    """The checkout (main or worktree) containing `path`, by walking up to a `.git`."""
    while True:
        if Path(path, ".git").exists():
            return path
        parent = str(Path(path).parent)
        if parent == path:
            return None
        path = parent


def root_by_name(path: str) -> str | None:
    """A checkout root read off the path alone, for trees that need not exist.

    `.claude/worktrees/<slug>-spec` and `-impl` are roots by construction; the
    directory holding `.claude/worktrees` is the main checkout.
    """
    parts = Path(path).parts
    for i in range(len(parts) - 1, 1, -1):
        if parts[i - 2] == ".claude" and parts[i - 1] == "worktrees":
            return str(Path(*parts[: i + 1]))
    return None


def real_path(target: str, cwd: str) -> str:
    """One absolute path for `target`, with every symlink on it followed.

    Both sides of every lane comparison come through here, so a symlinked
    file, a symlinked parent directory, a relative spelling and a `..` walk all
    collapse onto the one name the kernel will open. A lexical answer is a
    different answer for each of those spellings, and a lane that admits one
    spelling of a file and refuses another guards nothing.

    `os.path.realpath` resolves the longest prefix that exists and rejoins the
    tail lexically, which is what a write to a file whose parent does not exist
    yet needs: the nearest existing ancestor is resolved and the rest is
    carried.

    LIMIT, left open on purpose: `realpath` does not resolve a hardlink, and
    cannot -- a hardlink is a second name of equal standing, not a pointer. A
    second name for a lane file, made under another directory, resolves to
    itself and is admitted. Closing it means comparing `st_dev`/`st_ino`
    against the lane's contents, which costs a `stat` per call and per lane
    file; the owner decides whether the lane is worth that, and until then the
    hole is here rather than hidden.
    """
    return os.path.realpath(os.path.join(cwd, target))  # noqa: PTH118


def split_root(target: str, cwd: str) -> tuple[str | None, str | None]:
    """(checkout root, path relative to it) for a write target, or (None, None).

    The target is resolved first, so the root is the checkout the write really
    lands in rather than the one its spelling suggests. Every ancestor of a
    resolved path is itself resolved, so the root needs no second pass.
    """
    real = real_path(target, cwd)
    root = root_by_name(real) or checkout_root(str(Path(real).parent))
    if root is None:
        return None, None
    return root, os.path.relpath(real, root)


def under(rel: str, lane: str) -> bool:
    """Is this path the lane directory or inside it? Both sides spelled alike.

    Two repo-relative paths, or two resolved absolute ones. Never one of each.
    """
    prefix = lane.replace("/", os.sep)
    return rel == prefix or rel.startswith(prefix + os.sep)


def path_in_lane(target: str, cwd: str, lane: str) -> bool:
    """Does the resolved target land inside a `<lane>` directory of any checkout?

    Both sides are resolved. Resolving the target alone answers a symlink that
    points into the lane; resolving the lane root as well answers the other
    direction, a lane directory that is itself a symlink and whose contents
    therefore sit somewhere the repo-relative path never shows.

    Falls back to a segment match when the path is in no checkout at all, so
    the lane holds before `git init` and outside a repo.
    """
    real = real_path(target, cwd)
    root, rel = split_root(target, cwd)
    if root is not None and under(real, real_path(lane, root)):
        return True
    if rel is not None and not rel.startswith(".."):
        return under(rel, lane)
    parts = list(Path(real).parts)
    lane_parts = lane.split("/")
    return any(
        parts[i : i + len(lane_parts)] == lane_parts
        for i in range(len(parts) - len(lane_parts) + 1)
    )


def bypassed() -> bool:
    """Whether the owner started this session with the gauntlet off.

    `GAUNTLET=off claude`, and nothing else. The comparison is against the
    exact value `off` after strip and lowercase, so an unset, empty or
    misspelled variable leaves the gauntlet on, which is the safe direction.

    Read only at the top of a hook's `main()`, never inside a `_verdict()`: a
    self-test calls `_verdict()` directly, and a switch reachable from there
    would make the self-tests pass vacuously in a bypassed environment.
    """
    return os.environ.get("GAUNTLET", "").strip().lower() == "off"


def deny(reason: str) -> str:
    """The PreToolUse deny payload, as a JSON string."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def command_of(tool_input: dict[str, Any] | None) -> str:
    """The `command` field of a tool input, as a string, whatever it holds.

    A hook reads this field and hands it to a classifier that splits it. The
    field is whatever the payload carried, so a number or a list there reaches
    the classifier as one and raises -- and a hook that raises exits non-zero,
    which is read as a denial of the call it was deciding. Anything that is not
    a string is no command, and an empty string is the shape the classifier
    already answers for.
    """
    command = (tool_input or {}).get("command")
    return command if isinstance(command, str) else ""


def cwd_of(payload: Payload | None) -> str:
    """The `cwd` a payload names, as a path, or this process's own.

    Same boundary as `command_of`: the field is whatever the payload carried,
    and a hook that hands a number to `os.path` raises, which denies the call.
    """
    cwd = (payload or {}).get("cwd")
    return cwd if isinstance(cwd, str) and cwd else str(Path.cwd())


def agent_of(payload: Payload | None) -> str:
    """Who is running this call, as a bare agent name, or `""` for the main agent.

    Installed as a plugin, the harness spells a subagent's `agent_type` with
    the plugin it came from in front of it -- `gauntlet:prosecutor`
    where a loose copy of the same kit sends `prosecutor`. Every hook
    here compares the name against a bare one, so the namespace has to come off
    before the comparison or the same agent matches nothing it should: a lane
    denies its own writer, and a blind agent's guard finds no subject and lets
    the call through unblinded.

    An agent name carries no `:`, so everything up to the last one is the
    namespace and the tail is the name. Which plugin the namespace names
    is not checked: a foreign plugin shipping an agent named `arbiter`
    is treated as this kit's, exactly as an unnamespaced agent of that name in
    the host project already is.
    """
    agent = (payload or {}).get("agent_type") or ""
    if not isinstance(agent, str):
        return ""
    return agent.rsplit(":", 1)[-1] if ":" in agent else agent


#: payloads a hook must answer without dying, each with the tool it names --
#: `None` for a payload that names nothing readable at all -- and whether the
#: fields a hook has to read are usable. Not a guess at what Claude Code sends:
#: each one is a shape some hook here has assumed away -- a missing field, a
#: field of the wrong type, a `cwd` naming a tree that was cut, a path that is
#: not a path. A hook that raises on any of them exits non-zero, and a non-zero
#: `PreToolUse` blocks the call; a hook that shrugs at one of the unusable ones
#: runs the call it was put there to decide.
HOSTILE_PAYLOADS = (
    ("", None, False),
    ("not json at all", None, False),
    ("null", None, False),
    ("[]", None, False),
    #: an object naming no tool names no call this hook guards
    ("{}", "", True),
    ('{"tool_name": "Bash"}', "Bash", False),
    ('{"tool_name": "Bash", "tool_input": null, "cwd": null}', "Bash", False),
    ('{"tool_name": "Bash", "tool_input": {"command": 17}, "cwd": 17}', "Bash", False),
    #: an empty command and an empty cwd are readable: the command runs nothing
    #: and the cwd falls back to this process's own, which is what `cwd_of` says
    ('{"tool_name": "Bash", "tool_input": {"command": ""}, "cwd": ""}', "Bash", True),
    ('{"tool_name": "Edit", "tool_input": {"file_path": null}}', "Edit", False),
    #: a NUL in a path is a string, so it is readable here and raises deeper in
    ('{"tool_name": "Edit", "tool_input": {"file_path": "\\u0000"}}', "Edit", True),
    (
        '{"tool_name": "Bash", "tool_input": {"command": "echo hi"},'
        ' "cwd": "/nonexistent-by-construction/deeper"}',
        "Bash",
        True,
    ),
    (
        '{"tool_name": "Bash", "tool_input": {"command": "echo hi"}, "cwd": "/etc/hostname"}',
        "Bash",
        True,
    ),
    (
        '{"tool_name": "Bash", "tool_input": {"command": "echo hi"},'
        ' "agent_type": 3, "cwd": "/"}',
        "Bash",
        False,
    ),
)

#: the field a call of this tool must carry as a string before a hook can
#: decide it. `Bash` carries the command; a write carries its target.
REQUIRED_FIELD = {
    "Write": "file_path",
    "Edit": "file_path",
    "NotebookEdit": "notebook_path",
    "Read": "file_path",
    "Bash": "command",
}

#: a field a call may omit, but may not carry as something other than a string
OPTIONAL_FIELD = {"Grep": "path", "Glob": "path"}


def payload_fault(name: str, tool_input: Any, payload: Any, guarded: tuple[str, ...]) -> str | None:
    """Why this hook cannot decide the call it was handed, or None to decide it.

    A guard reads three things: which tool, what it names, and who is running
    it. Where one of them is missing or is not the type it has to be, the hook
    has not been handed a call it can evaluate -- and the answer to a call a
    guard cannot evaluate is no, never silence. Coercing the field to a benign
    default instead (an absent command, an empty path, an anonymous agent) is
    the shape that lets exactly the malformed call through the gate.

    Only a call of a tool in `guarded` is faulted. Every other tool is somebody
    else's to decide, and a hook that refuses a call outside its own subject
    would deny half the session over a field it never reads.
    """
    if name not in guarded:
        return None
    for field in ("cwd", "agent_type"):
        value = (payload or {}).get(field)
        if value is not None and not isinstance(value, str):
            return f"the payload carries {field} as {type(value).__name__}, not a string"
    if not isinstance(tool_input, dict):
        return f"the {name} call carries no tool_input object"
    required = REQUIRED_FIELD.get(name)
    if required is not None:
        value = tool_input.get(required)
        if not isinstance(value, str):
            return f"the {name} call carries {required} as {type(value).__name__}, not a string"
        if not value and name != "Bash":
            return f"the {name} call carries an empty {required}"
    optional = OPTIONAL_FIELD.get(name)
    if optional is not None:
        value = tool_input.get(optional)
        if value is not None and not isinstance(value, str):
            return f"the {name} call carries {optional} as {type(value).__name__}, not a string"
    return None


def undecidable(why: str) -> str:
    """The refusal a hook gives for a call it could not decide.

    Names the hook, so the denial that reaches the agent says which gate spoke
    and what it could not read, rather than arriving as an unexplained no.
    """
    hook = Path(sys.argv[0]).name or "a gauntlet hook"
    return (
        f"{hook} could not decide this call, so it refuses it: {why}. A gate that "
        "cannot read the call it was handed does not let the call through -- the "
        "malformed payload is the one that most needs deciding. Reissue the call "
        f"with the field it is missing. (hooks/{hook})"
    )


def misconfigured(fault: str) -> str:
    """The refusal a hook gives while the project's declaration is a fault.

    A lane is a configured directory, so a hook whose config will not load
    does not know where any lane is. It refuses rather than deciding against
    the kit's defaults: defaults that are not the project's are a lane in the
    wrong place, and a lane in the wrong place guards nothing.
    """
    hook = Path(sys.argv[0]).name or "a gauntlet hook"
    return (
        f"{hook} refuses this call: {fault}. The lanes are configured "
        "directories, so a gate that cannot read the declaration does not know "
        "which directory it guards, and it will not fall back on the kit's "
        "defaults and guard the wrong one. Fix the file, or write one with "
        f"`python3 scripts/init.py`. (hooks/{hook})"
    )


def is_denial(answer: str) -> bool:
    """Whether a hook's stdout is a `PreToolUse` denial."""
    try:
        parsed = json.loads(answer)
    except ValueError:
        return False
    if not isinstance(parsed, dict):
        return False
    specific = parsed.get("hookSpecificOutput")
    return isinstance(specific, dict) and specific.get("permissionDecision") == "deny"


def survives_hostile_payloads(
    hook_path: str,
    *argv: str,
    guards: tuple[str, ...] = ("Write", "Edit", "NotebookEdit", "Bash"),
    refuses_undecidable: bool = True,
) -> bool:
    """That this hook answers every `HOSTILE_PAYLOADS` shape, and answers no.

    Two failures, not one. A hook decides a tool call, so its own crash is a
    denial of whatever it was deciding: it is run the way Claude Code runs it,
    one JSON object on stdin, and must exit 0 and write either nothing or a
    parsable answer, whatever it is handed. And a hook that stays alive by
    treating every payload it cannot read as an allow has moved the defect
    rather than fixed it, so each payload whose fields this hook needs and
    cannot read must come back a denial. `guards` is the set of tools this hook
    decides; a payload naming any other tool is not its call to refuse.

    `refuses_undecidable` is false for an entry point that decides no tool call
    -- a `Stop` gate reads no payload and has no permission to withhold -- and
    there the older contract is the whole contract: stay alive, answer parsably.

    `GAUNTLET` is cleared for the run. Under `GAUNTLET=off` a hook returns at
    its first line, and every payload would pass without touching the code the
    check exists to exercise.
    """
    import subprocess

    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    for payload, tool, usable in HOSTILE_PAYLOADS:
        done = subprocess.run(
            [sys.executable, hook_path, *argv],
            input=payload,
            capture_output=True,
            text=True,
            env=environment,
            timeout=60,
            check=False,
        )
        if done.returncode != 0:
            return False
        out = done.stdout.strip()
        if out:
            try:
                json.loads(out)
            except ValueError:
                return False
        if not refuses_undecidable:
            continue
        #: a payload naming no readable tool at all is undecidable for every
        #: hook; one naming a guarded tool is undecidable when its fields are not
        if (tool is None or (tool in guards and not usable)) and not is_denial(out):
            return False
    return True


# --- the shape a lane hook is ------------------------------------------------
#
# Five hooks here guard a directory that one named agent writes. They differ in
# the lane, the agent and the prose of the refusal; everything around those
# three was the same text copied five times, which is the shape where one hook
# gets a fix and four keep the defect. The dispatch, the entry point and the
# denial sentence live here now, and a lane hook is its constants plus whatever
# it does that the others do not.

#: tools that write a file. `NotebookEdit` names its target `notebook_path`.
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")


def write_target(tool_input: dict[str, Any] | None) -> str:
    """The path a write tool names, or the empty string for no target."""
    tool_input = tool_input or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    return target if isinstance(target, str) else ""


def dispatch(
    name: str,
    tool_input: dict[str, Any],
    payload: Payload,
    *,
    on_write: Callable[[str, str, str], str | None],
    on_bash: Callable[[str, str], str | None] | None = None,
    on_read: Callable[[dict[str, Any], str, str], str | None] | None = None,
    read_tools: tuple[str, ...] = (),
) -> str | None:
    """Route one tool call to the handler for its kind; None lets it through.

    `on_write(target, cwd, agent)` is called only for a write that names a
    target, since a write with no path denies nothing. `on_read(tool_input,
    cwd, agent)` sees the whole input, because a read names its target under
    three different keys. `on_bash(command, agent)` is optional and no lane
    passes one: a lane's shell half is held by the mount table now, not by a
    reading of the command text.
    """
    cwd = cwd_of(payload)
    agent = agent_of(payload)
    if name in WRITE_TOOLS:
        target = write_target(tool_input)
        return on_write(target, cwd, agent) if target else None
    if on_read is not None and name in read_tools:
        return on_read(tool_input, cwd, agent)
    if on_bash is not None and name == "Bash":
        return on_bash(command_of(tool_input), agent)
    return None


def lane_denial(lane: str, noun: str, lane_msg: str, *, restore: bool = True) -> str:
    """The refusal a shell write into `lane` gets.

    `restore` is false for a lane with no restore escape, where the sentence
    ends at the reason.
    """
    denial = f"A shell write naming a {lane}/ path is denied: " + lane_msg
    if not restore:
        return denial
    return (
        denial + f" Restoring {noun} from a git object is the one shell shape "
        f"that passes: `git restore --source <rev> -- {lane}/<file>`."
    )


def sole_writer_lane(lane: str, writer: str, lane_msg: str) -> Verdict:
    """The verdict function of a lane one named agent writes and nobody else.

    Returns a `_verdict(name, tool_input, payload)`. A write whose target is in
    the lane passes for `writer` and is refused with `lane_msg` for every other
    hand, the main agent included; everything else passes.

    `Bash` is not this function's business and no lane hook is wired on it any
    more. A shell that writes into the lane is stopped by the mount table --
    the lane directories are bound read-only inside every wrapped profile --
    rather than by reading the command, which is the question no string
    answers.
    """

    def on_write(target: str, cwd: str, agent: str) -> str | None:
        if not path_in_lane(target, cwd, lane):
            return None
        return None if agent == writer else lane_msg

    def verdict(name: str, tool_input: dict[str, Any], payload: Payload) -> str | None:
        return dispatch(name, tool_input, payload, on_write=on_write)

    return verdict


def read_payload(guards: tuple[str, ...]) -> tuple[Payload | None, str | None]:
    """One payload from stdin as `(payload, refusal)`; exactly one is not None.

    Every way the payload can fail to be a call this hook can decide ends in a
    refusal, never in silence. The three the old entry point swallowed -- stdin
    that will not read, text that is not JSON, JSON that is not an object --
    are each a case where the hook has no idea what it was asked to decide, and
    no idea is not consent.
    """
    try:
        raw = sys.stdin.read()
    except OSError as exc:
        return None, undecidable(f"its payload could not be read from stdin ({exc})")
    try:
        data = json.loads(raw)
    except ValueError:
        return None, undecidable("its payload is not JSON")
    if not isinstance(data, dict):
        return None, undecidable("its payload is not a JSON object")
    if not isinstance(data.get("tool_name", ""), str):
        return None, undecidable("its payload carries tool_name as something other than a string")
    fault = payload_fault(data.get("tool_name", ""), data.get("tool_input"), data, guards)
    return (None, undecidable(fault)) if fault is not None else (data, None)


def hook_main(verdict: Verdict, *, guards: tuple[str, ...] = WRITE_TOOLS + ("Bash",)) -> None:
    """Read one payload from stdin and print a denial if `verdict` names one.

    `guards` is the set of tools this hook decides, and it is what makes a
    malformed payload refusable: a call of a tool outside the set is not this
    hook's to refuse however broken it is.

    A `verdict` that raises is a denial too. It is the same failure as a
    payload that will not parse -- the hook does not know whether the call is
    allowed -- and the same answer follows, with the exception named in it so
    the defect is visible rather than absorbed. `except Exception` is wide on
    purpose: what is caught is not a known-harmless class but every way this
    hook can fail, and none of them ends in the call being run.

    The switch is read here and nowhere else: a self-test calls `verdict`
    directly, so a bypass reachable from inside it would make every self-test
    pass vacuously under `GAUNTLET=off`.
    """
    if bypassed():
        return  # GAUNTLET=off: the owner's switch, read at the entry point only
    data, refusal = read_payload(guards)
    if refusal is not None or data is None:
        print(deny(refusal or undecidable("its payload named no call")))
        return
    fault = config_fault()
    if fault is not None:
        print(deny(misconfigured(fault)))
        return
    try:
        reason = verdict(data.get("tool_name", ""), data.get("tool_input") or {}, data)
    except Exception as exc:  # noqa: BLE001 -- see the docstring: a crash is a denial
        print(deny(undecidable(f"deciding it raised {type(exc).__name__}: {exc}")))
        return
    if reason is not None:
        print(deny(reason))


def answer_main(
    answer_of: Callable[[Payload], dict[str, Any] | None],
    *,
    guards: tuple[str, ...] = ("Bash",),
) -> None:
    """`hook_main` for a hook whose answer is not a denial.

    `bwrap-wrap.py` rewrites the command rather than refusing it, so its answer
    is a whole `hookSpecificOutput` object. Every failure path is the same as
    `hook_main`'s and ends the same way: a hook that cannot build the sandbox a
    command was going to run inside refuses the command, because the fallback
    it would otherwise take is running that command unsandboxed.
    """
    if bypassed():
        return  # GAUNTLET=off: the owner's switch, read at the entry point only
    data, refusal = read_payload(guards)
    if refusal is not None or data is None:
        print(deny(refusal or undecidable("its payload named no call")))
        return
    fault = config_fault()
    if fault is not None:
        print(deny(misconfigured(fault)))
        return
    try:
        answer = answer_of(data)
    except Exception as exc:  # noqa: BLE001 -- see `hook_main`: a crash is a denial
        print(deny(undecidable(f"answering it raised {type(exc).__name__}: {exc}")))
        return
    if answer is not None:
        print(json.dumps(answer))


def entry(self_test_fn: Callable[[], int], main_fn: Callable[[], None]) -> None:
    """The `__main__` of a hook with one gate mode and one wire mode."""
    sys.exit(self_test_fn()) if "--self-test" in sys.argv else main_fn()


# --- the shape a self-test is ------------------------------------------------


def denied(verdict: str | None) -> bool:
    """That a verdict refused the call: a refusal is its own reason."""
    return isinstance(verdict, str)


def allowed(verdict: str | None) -> bool:
    """That a verdict let the call through."""
    return verdict is None


def probe(
    verdict: Verdict,
    root: str,
    tool: str,
    key: str = "file_path",
    *,
    agent: str | None = None,
) -> Callable[..., str | None]:
    """A closure that calls `verdict` for one tool the way the wire does.

    `key` is the field that tool carries its target in. `agent` is the default
    `agent_type` the closure sends, overridden per call; `None` is the main
    agent, whose payload carries no such key at all.
    """

    def call(value: Any, who: str | None = agent) -> str | None:
        payload: Payload = {"cwd": root}
        if who is not None:
            payload["agent_type"] = who
        return verdict(tool, {key: value}, payload)

    return call


#: one of the three default directory names as a whole path segment, for
#: `rebased`. The bounds are not `\b`: a name is a segment when nothing joins it
#: on either side, and `\b` would take the `gauntlet` of `arbiter` and
#: rename the agent. A trailing `/` is left to the text, so `find tests -delete`
#: and `cd tests && rm t.py` -- a lane named with no slash at all -- respell too.
_DEFAULT_SEGMENT = re.compile(
    r"(?<![\w.-])(" + "|".join(sorted(set(DEFAULT_DIRS.values()))) + r")(?![\w.-])"
)


def respell(target: str) -> str:
    """One self-test path or command, at the configured directories.

    Exactly one pass, and never applied twice to the same string: the three
    names are disjoint from each other but a configured name may still contain
    a default one as a segment -- `gauntlet_dir` of `work/tests` is a legal set
    beside `tests_dir` -- and a second pass would rewrite what the first wrote.
    """
    by_default = dict(zip(DEFAULT_DIRS.values(), dirs().values(), strict=True))
    if all(default == configured for default, configured in by_default.items()):
        return target
    return _DEFAULT_SEGMENT.sub(lambda m: by_default[m.group(1)], target)


def rebased(one_probe: Callable[..., str | None]) -> Callable[..., str | None]:
    """A probe that respells the kit's default directories at the configured ones.

    Every self-test writes its paths at `tests/`, `docs/` and `gauntlet/`, which
    is what the kit ships and what the prose around each line says. Under a
    project that moved one of them those literals name nothing any hook guards,
    so the lines would pass by naming paths outside the lane and prove nothing.
    Rewriting the segment here means one set of lines holds at any base, and the
    lane each line is about is the lane the hook actually resolved.

    One pass, not three: with `tests_dir` at `docs` and `docs_dir` elsewhere,
    replacing one name after another would rewrite what the previous pass had
    just written. The names are disjoint, so a single alternation is exact.
    """

    def at_configured_dirs(target: str, *rest: Any) -> str | None:
        return one_probe(respell(target), *rest)

    return at_configured_dirs


def probes(
    verdict: Verdict, root: str = "/repo", *, agent: str | None = None
) -> tuple[Callable[..., str | None], Callable[..., str | None]]:
    """The `(write, bash)` pair every lane self-test drives its lane through."""
    return (
        rebased(probe(verdict, root, "Edit", agent=agent)),
        rebased(probe(verdict, root, "Bash", "command", agent=agent)),
    )


def report(lines: dict[str, bool]) -> int:
    """Print one PASS or FAIL per spec line; 0 if every line held."""
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    #: `shell_shapes.py --config tests_dir` prints the one config value for a
    #: shell script; `scripts/blind.sh` and `scripts/pair.sh` read it through
    #: here so one reader serves the hooks and the scripts alike
    if len(sys.argv) == 3 and sys.argv[1] == "--config":
        #: a fault is the exit status and a line on stderr, never a value on
        #: stdout: the shell reading this substitutes what it is given, and a
        #: default printed here is the wrong branch or the wrong lane, silently
        fault = config_fault()
        if fault is not None:
            sys.stderr.write(f"shell_shapes.py: {fault}\n")
            sys.exit(2)
        sys.stdout.write("".join(line + "\n" for line in config_lines(sys.argv[2])))
        sys.exit(0)
    sys.stderr.write("usage: shell_shapes.py --config <key>\n")
    sys.exit(2)
