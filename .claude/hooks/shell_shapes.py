#!/usr/bin/env python3
"""Shell and path shapes the lane hooks share.

The lane hooks all ask the same two questions: does this path fall inside a
directory that belongs to one agent, and does this shell command write
anything. This module answers both, so that a hook is a policy over the
answers rather than a second parser.

It is deliberately standalone. These hooks travel as a unit into other repos,
where the change budget and its `free_bash` allowlist do not exist, so the
read-only judgment here is two small closed allowlists of its own, read in
this order: a redirection makes any command a write whatever it says; a
recognized runner invocation is a read, because running the suite is the job
and a head word cannot tell a suite run from an interpreter writing a file;
otherwise a command is a read only if its first word is a known reader.
Unknown command, unknown effect, treated as a write. That is the safe
direction for a lane: an over-denied read costs a message, an under-denied
write costs the lane.

The runner table is whole invocations, not head words. `pytest` is the one
head accepted with arbitrary arguments, and it was a known reader before the
table existed; every other entry names the argument that makes it a run
(`python -m pytest`, `node --test`, `npm test`, `npx vitest`, `cargo test`).
An inline-script flag (`-e`, `-c`, `-p`, `--eval`, `--print`) is never a run,
whatever the head word: that is the shape an agent reaches for to write a
file with an interpreter the lane would otherwise wave through.
"""

from __future__ import annotations

import os
import re
import shlex

#: first words of commands that only read; anything else is treated as a write
READ_ONLY = frozenset(
    {
        "basename", "cat", "cksum", "column", "comm", "cut", "diff",
        "dirname", "du", "echo", "false", "fgrep", "file", "grep",
        "head", "jq", "less", "ls", "md5sum", "nl", "od",
        "printf", "pwd", "realpath", "rg", "sha256sum", "sort",
        "stat", "tail", "test", "tr", "true", "uniq", "wc", "which", "xxd",
        "yq",
    }
)

#: an interpreter told to run a script given on the command line; never a run
#: of the suite, whatever the head word in front of it
INLINE_SCRIPT = frozenset({"-e", "-c", "-p", "--eval", "--print"})

#: packages `npx` may run as a test runner
NPX_RUNNERS = frozenset({"ava", "jest", "mocha", "playwright", "tap", "vitest"})

#: modules `python -m` may run as a test runner
PY_MODULES = frozenset({"pytest", "unittest"})

#: git subcommands that never write the working tree; a commit message or a
#: pathspec naming a lane is not a write to it
GIT_NO_WORKTREE = frozenset(
    {"add", "blame", "commit", "diff", "log", "ls-files", "rev-parse", "show", "status"}
)

#: an output redirection; `2>&1` and `>&2` are not one
REDIRECT = re.compile(r"(?:^|[^0-9<>&])>>?(?![&>])")

_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")


def strip_heredocs(command: str) -> str:
    """Drop heredoc bodies, so prose that mentions a lane is not read as a path.

    The redirection that opens the heredoc stays on its own line, so
    `cat > lane/x.txt <<EOF` is still seen as the write it is.
    """
    out: list[str] = []
    terminator: str | None = None
    for line in command.split("\n"):
        if terminator is not None:
            if line.strip() == terminator:
                terminator = None
            continue
        out.append(line)
        m = _HEREDOC.search(line)
        if m:
            terminator = m.group(2)
    return "\n".join(out)


def _split_unquoted(text: str) -> list[str]:
    """Split on `&&`, `||`, `;`, `|`, a newline and a bare `&`, outside quotes.

    A separator inside a quoted argument is part of the argument: splitting
    `node -e "a && b"` on it would leave fragments whose head word is not a
    command. A `&` next to a redirection (`2>&1`, `>&2`) is not a separator
    either — cutting there leaves a fragment ending in `2>`, which `REDIRECT`
    reads as an output redirection and every lane then reads as a write.

    An unterminated quote quotes to the end of the string, so a malformed
    command is one segment and falls to whatever its head word says.
    """
    out: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(text):
        ch = text[i]
        if quote is not None:
            buf.append(ch)
            quote = None if ch == quote else quote
            i += 1
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
        elif text.startswith("&&", i) or text.startswith("||", i):
            out.append("".join(buf))
            buf = []
            i += 2
        elif ch in ";|\n":
            out.append("".join(buf))
            buf = []
            i += 1
        elif ch == "&" and not (
            (i and text[i - 1] in ">&") or (i + 1 < len(text) and text[i + 1] in ">&")
        ):
            out.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(ch)
            i += 1
    out.append("".join(buf))
    return [s.strip() for s in out if s.strip()]


def segments(command: str) -> list[str]:
    """The pipeline stages of a command, heredoc bodies removed."""
    return _split_unquoted(strip_heredocs(command))


def is_runner(words: list[str]) -> bool:
    """Is this invocation a run of the project's suite, rather than a write?

    A closed table of whole invocations. `pytest` is the only head word
    accepted with arbitrary arguments; everything else names the argument that
    makes it a run. An inline-script flag disqualifies any of them.
    """
    if not words:
        return False
    if any(w in INLINE_SCRIPT for w in words[1:]):
        return False
    head = os.path.basename(words[0])
    rest = words[1:]
    first = rest[0] if rest else ""
    if head == "pytest":
        return True
    if head == "python" or head.startswith("python3"):
        if "-m" not in rest:
            return False
        after = rest.index("-m") + 1
        return after < len(rest) and rest[after] in PY_MODULES
    if head == "node":
        return "--test" in rest
    if head in ("npm", "pnpm", "yarn"):
        return first == "test"
    if head == "npx":
        return first in NPX_RUNNERS
    if head in ("cargo", "go"):
        return first == "test"
    return False


def is_object_restore(words: list[str]) -> bool:
    """`git restore --source <rev> -- <paths>` or `git checkout <rev> -- <paths>`.

    Both copy a named commit onto a path. Neither types content, so a lane that
    has git history can be reverted without going around its writer.
    """
    if len(words) < 4 or words[0] != "git":
        return False
    if words[1] == "restore":
        return "--source" in words[2:] or any(w.startswith("--source=") for w in words[2:])
    if words[1] == "checkout":
        return "--" in words[2:] and not words[2].startswith("-")
    return False


def words_of(segment: str) -> list[str]:
    try:
        return shlex.split(segment, comments=False, posix=True)
    except ValueError:
        return segment.split()


def segment_writes(segment: str, *, restore_ok: bool = True) -> bool:
    """Does this one pipeline stage change anything on disk?"""
    if REDIRECT.search(segment):
        return True
    words = words_of(segment)
    if not words:
        return False
    if is_runner(words):
        return False
    head = os.path.basename(words[0])
    if head == "git":
        if len(words) > 1 and words[1] in GIT_NO_WORKTREE:
            return False
        return not (restore_ok and is_object_restore(words))
    if head == "sed":
        return any(w == "-i" or w.startswith("-i") for w in words[1:])
    return head not in READ_ONLY


def command_writes(command: str, *, restore_ok: bool = True) -> bool:
    """Does any stage of this command change anything on disk?"""
    return any(segment_writes(s, restore_ok=restore_ok) for s in segments(command))


def lane_pattern(lane: str) -> re.Pattern[str]:
    """A regex matching a `<lane>` path token in a shell command, relative or absolute.

    The trailing slash is optional, because the lane is named without one every
    time a command takes the directory itself as an argument: `find tests
    -delete` and `rm -rf tests` write the whole lane and spell it `tests`. What
    follows the name must be a separator or the end of the command, so
    `tests_old.py` is not the lane.
    """
    return re.compile(
        r"(?:^|[\s\"'=(:])(?:[^\s\"']*/)?"
        + re.escape(lane)
        + r"(?:/|(?=[\s\"';|&)]|$))"
    )


def bash_touches_lane(command: str, pattern: re.Pattern[str]) -> bool:
    return bool(pattern.search(command))


def cd_target(words: list[str]) -> str | None:
    """The directory a `cd` stage moves to, or None when the stage is not a `cd`."""
    if not words or os.path.basename(words[0]) != "cd":
        return None
    args = [w for w in words[1:] if not w.startswith("-")]
    return args[0] if args else ""


def lane_write_in(command: str, pattern: re.Pattern[str], *, restore_ok: bool = True) -> bool:
    """Does any stage write to the lane, by naming it or by standing in it?

    The stages are walked in order carrying the directory a `cd` moved them
    to, because a command that never spells the lane can still write into it:
    `cd tests && rm t.py` names `tests` once, without the slash the lane
    pattern needs, and does its writing from inside.

    A `cd` whose target is absolute, `-`, `~...`, or absent moves somewhere
    this walk cannot follow, so it drops the tracking rather than guess. With
    no `cd` anywhere the walk is the old per-stage test.
    """
    here: str | None = ""
    for stage in segments(command):
        words = words_of(stage)
        target = cd_target(words)
        if target is not None:
            if here is None or target in ("", "-") or target.startswith(("/", "~")):
                here = None
            else:
                here = os.path.normpath(os.path.join(here, target))
            continue
        if not segment_writes(stage, restore_ok=restore_ok):
            continue
        if pattern.search(stage):
            return True
        if here and pattern.search(here.rstrip("/") + "/"):
            return True
    return False


def checkout_root(path: str) -> str | None:
    """The checkout (main or worktree) containing `path`, by walking up to a `.git`."""
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def root_by_name(path: str) -> str | None:
    """A checkout root read off the path alone, for trees that need not exist.

    `.claude/worktrees/<slug>-spec` and `-impl` are roots by construction; the
    directory holding `.claude/worktrees` is the main checkout.
    """
    parts = path.split(os.sep)
    for i in range(len(parts) - 1, 1, -1):
        if parts[i - 2] == ".claude" and parts[i - 1] == "worktrees":
            return os.sep.join(parts[: i + 1])
    return None


def split_root(target: str, cwd: str) -> tuple[str | None, str | None]:
    """(checkout root, path relative to it) for a write target, or (None, None)."""
    resolved = os.path.abspath(os.path.join(cwd, target))
    root = root_by_name(resolved) or checkout_root(os.path.dirname(resolved))
    if root is None:
        return None, None
    return root, os.path.relpath(resolved, root)


def under(rel: str, lane: str) -> bool:
    """Is this repo-relative path the lane directory or inside it?"""
    prefix = lane.replace("/", os.sep)
    return rel == prefix or rel.startswith(prefix + os.sep)


def path_in_lane(target: str, cwd: str, lane: str) -> bool:
    """Does the resolved target land inside a `<lane>` directory of any checkout?

    Falls back to a segment match when the path is in no checkout at all, so
    the lane holds before `git init` and outside a repo.
    """
    _, rel = split_root(target, cwd)
    if rel is not None and not rel.startswith(".."):
        return under(rel, lane)
    parts = os.path.abspath(os.path.join(cwd, target)).split(os.sep)
    lane_parts = lane.split("/")
    return any(
        parts[i : i + len(lane_parts)] == lane_parts
        for i in range(len(parts) - len(lane_parts) + 1)
    )


def deny(reason: str) -> str:
    """The PreToolUse deny payload, as a JSON string."""
    import json

    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )
