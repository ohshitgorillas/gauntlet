"""Finding a project's declaration, and reading it.

`blind-reads.json` carries nine keys, and they are the whole of what varies
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
"""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any


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
        raise ConfigFault(f"no declaration at {source}: run scripts/init.py to write one") from None
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
