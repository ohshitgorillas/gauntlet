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

A repo adds its own entries to that table in `blind-reads.json` beside this
file, since a repo-local script is a path rather than a name and cannot be
compiled in here. A declaration is an entry path, the fixed argument words
after it, and the prefix its one remaining argument sits under, and it is
keyed on the whole invocation and its arity like every other entry. Two
bounds on a declaration are code rather than data: a prefix resolving to or
under a lane directory is dropped, and the one argument is normalized before
it is tested against the prefix. A repo that declares nothing gets the table
above, which is the behavior it has without the file.
"""

from __future__ import annotations

import functools
import json
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
#: of the suite. Which flag means that depends on the head word in front of it,
#: so the set is read through `has_inline_script`, never against a bare word
#: list: `-c` is an inline script to `python` and a config file to `pytest`,
#: and `-p` is an inline script to `perl` and a plugin to `pytest`.
INLINE_SCRIPT = frozenset({"-e", "-c", "-p", "--eval", "--print"})

#: heads for which `-c` is an inline script rather than a configuration file
INLINE_C_HEADS = frozenset({"sh", "bash", "zsh", "ruby", "perl", "php"})
#: heads for which `-p`/`--print` is an inline script rather than an argument
INLINE_P_HEADS = frozenset({"perl", "node"})

#: `pytest` arguments that make it write somewhere of its own choosing, so the
#: invocation stops being a run of the suite and falls to the ordinary path test
PYTEST_WRITE_FLAGS = (
    "--junitxml", "--junit-xml", "--report-log", "--result-log",
    "--cov-report", "--basetemp",
)

#: git subcommands that print no file content; everything else prints some, and
#: an unrecognized subcommand is treated as content. Staging and committing
#: belong here: they print no tree, and leaving them out denies the blind test
#: writer the commit its own red run depends on. `GIT_NO_WORKTREE` below asks a
#: different question, whether a subcommand writes, not whether it prints:
#: `cat-file`, `grep` and `show` write nothing and print content, so they are
#: there and not here. The two lists share `add`, `commit`, `describe`,
#: `ls-files`, `merge-base`, `rev-list`, `rev-parse` and `status`.
GIT_METADATA = frozenset(
    {
        "status", "rev-parse", "ls-files", "branch", "describe", "remote",
        "config", "symbolic-ref", "merge-base", "rev-list", "tag",
        "add", "commit", "restore", "checkout", "switch", "worktree", "reset",
    }
)
#: flags that turn `git log` from a list of commits into a patch
GIT_PATCH_FLAGS = frozenset({"-p", "-u", "--patch", "--full-diff"})

#: packages `npx` may run as a test runner
NPX_RUNNERS = frozenset({"ava", "jest", "mocha", "playwright", "tap", "vitest"})

#: modules `python -m` may run as a test runner
PY_MODULES = frozenset({"pytest", "unittest"})

#: a slug names one path segment and carries no traversal
SLUG = r"[A-Za-z0-9][A-Za-z0-9._-]*"
#: a spec worktree is the other place a blind agent's tests live, so a declared
#: argument may carry that one prefix and no other: the writer runs the suite
#: in the tree it wrote in
TREE = rf"\.claude/worktrees/{SLUG}-spec/"

#: the lane directories this kit's hooks guard. A declared prefix resolving to
#: or under one is dropped when the config is read: a declaration naming a lane
#: would turn off the hook that guards it, and every bound on what a
#: declaration can widen is code rather than data sitting beside it.
LANE_DIRS = (
    "docs/gauntlet/plans",
    "docs/gauntlet/specs",
    "docs/gauntlet/" + "verdicts",
    "docs/gauntlet/reviews",
)

#: git subcommands that never write the working tree in their reading forms; a
#: commit message or a pathspec naming a lane is not a write to it. Membership
#: is conditional: `git_write_form` counts a member's stage as a write when it
#: carries `--output`, `grep -O` or a writing `reflog` form.
GIT_NO_WORKTREE = frozenset(
    {
        "add", "blame", "cat-file", "commit", "describe", "diff", "grep", "log",
        "ls-files", "ls-tree", "merge-base", "reflog", "rev-list", "rev-parse",
        "shortlog", "show", "status",
    }
)

#: `--output=<file>` writes a file wherever git takes its diff options
GIT_OUTPUT = "output"
#: `git grep -O[<pager>]` runs a command on the matching files
GIT_GREP_PAGER = "open-files-in-pager"
#: `git reflog` forms that change the reflog rather than print it
GIT_REFLOG_WRITES = frozenset({"write", "delete", "drop", "expire"})

#: an output redirection and the target it opens. A file-descriptor prefix
#: (`1>`, `2>`) and `&>` are redirections; `2>&1` and `>&2` duplicate a
#: descriptor and open nothing, which is what the `(?![&>])` lookahead excludes.
#: The prefix is not what tells those apart, so it is not excluded here.
REDIRECT = re.compile(r"(?:^|[^<>&])(?:\d*|&)>>?(?![&>])\s*([^\s;|&)]*)")

#: a redirection to this target changes nothing on disk
NULL_TARGET = "/dev/null"

_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([\w][\w.-]*)\1")


def redirect_writes(segment: str) -> bool:
    """Does any redirection in this stage open something other than `/dev/null`?

    Asked per redirection, not per stage. A stage carries more than one, and a
    stage-level answer would let `cat impl.py > tests/t.py 2>/dev/null` off on
    the harmless half of it.
    """
    for match in REDIRECT.finditer(segment):
        if match.group(1).strip("\"'") != NULL_TARGET:
            return True
    return False


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


def segments_with_bodies(command: str) -> list[tuple[str, str]]:
    """Each stage, paired with the heredoc body opened on that stage's line.

    `segments` drops every body before a caller sees it, which is right for a
    question about what a command *does* — the head word already answers that.
    It is wrong for a question about *which path* a stage touches, because the
    path a heredoc names lives in the body. The body attaches to the last stage
    of the line that opened it, which is the stage carrying the `<<`.

    A body is evidence about the target of a write, never evidence that a write
    happened: `lane_write_in` reads one only for a stage that already
    classifies as a write, so `cat <<EOF` carrying prose stays prose.
    """
    units: list[tuple[str, str]] = []
    lines = command.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        body: list[str] = []
        for match in _HEREDOC.finditer(line):
            terminator = match.group(2)
            #: an unterminated heredoc runs to the end of the input, as it does
            #: in the shell, so the body is whatever is left
            while i < len(lines) and lines[i].strip() != terminator:
                body.append(lines[i])
                i += 1
            i += 1 if i < len(lines) else 0
        stages = _split_unquoted(line)
        for index, stage in enumerate(stages):
            last = index == len(stages) - 1
            units.append((stage, "\n".join(body) if last else ""))
    return units


def has_inline_script(words: list[str]) -> bool:
    """Is this invocation an interpreter told to run a script given inline?

    Read against the head word. `-e` and `--eval` are that shape for every head
    that has them; `-c` only for a shell or an interpreter; `-p` and `--print`
    only for `perl` and `node`. A bare `-` is the same shape by another road —
    it is how `python3 - <<EOF` feeds a script in without a flag at all.
    """
    if not words:
        return False
    head = os.path.basename(words[0])
    for word in words[1:]:
        if word in ("-e", "--eval", "-"):
            return True
        if word == "-c" and (head.startswith("python") or head in INLINE_C_HEADS):
            return True
        if word in ("-p", "--print") and head in INLINE_P_HEADS:
            return True
    return False


def path_shape(prefix: str) -> str:
    """The regex source a declared prefix expands into.

    Repo-relative, under `prefix`, optionally inside a spec worktree. The
    trailing class admits `.` and `/`, so it admits `..` as well: the shape is
    not the whole key, and `is_declared_run` normalizes what it matches.
    """
    return rf"(?:{TREE})?{re.escape(prefix)}/[A-Za-z0-9_][A-Za-z0-9._/-]*"


#: the shape this repository's own declared entry takes, exported so that
#: `blind-bash.py` reads the same regular expression the classifier does
TESTPATH = path_shape("tests")


def config() -> dict:
    """Per-repo widening, from `blind-reads.json` beside this file.

    An unreadable or malformed file is an empty config, which is the safe
    direction for a lane: an empty config declares nothing and so denies.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blind-reads.json")
    try:
        with open(path, encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _under(path: str, parent: str) -> bool:
    """Is `path` `parent` itself, or something beneath it? Both normalized."""
    return path == parent or path.startswith(parent + "/")


def declared_runners(conf: dict) -> tuple[tuple[str, tuple[str, ...], re.Pattern[str]], ...]:
    """The repo's declared runner invocations, as (entry, argument words, shape).

    A declaration names an entry path, the fixed argument words that follow it,
    and the prefix its one remaining argument sits under. A malformed
    declaration is dropped, and so is one whose prefix resolves to or under a
    lane directory: a declaration is data, and a declaration that could name a
    lane would turn off the hook that guards it.
    """
    out = []
    for dec in conf.get("runner_invocations") or ():
        if not isinstance(dec, dict):
            continue
        entry, args, prefix = dec.get("entry"), dec.get("args") or [], dec.get("prefix")
        if not isinstance(entry, str) or not isinstance(prefix, str) or not entry or not prefix:
            continue
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            continue
        prefix = os.path.normpath(prefix)
        if os.path.isabs(prefix) or prefix == ".." or prefix.startswith("../"):
            continue
        if any(_under(prefix, lane) for lane in LANE_DIRS):
            continue
        out.append((os.path.normpath(entry), tuple(args), re.compile(path_shape(prefix) + r"\Z")))
    return tuple(out)


@functools.lru_cache(maxsize=1)
def _declared() -> tuple[tuple[str, tuple[str, ...], re.Pattern[str]], ...]:
    """The declarations, read once per process rather than once per stage."""
    return declared_runners(config())


def is_declared_run(words: list[str]) -> bool:
    """Is this whole invocation one of the repo's declared runner invocations?

    The key is the whole invocation, arity included: the head normalizes to the
    declared entry or to a path ending in it, the declared argument words come
    next, and exactly one argument follows them. That argument matches the
    declared shape both as typed and after `os.path.normpath`, so an argument
    that opens under the prefix and walks out of it is not a run.
    """
    if not words:
        return False
    head = os.path.normpath(words[0])
    rest = words[1:]
    for entry, args, shape in _declared():
        if head != entry and not head.endswith("/" + entry):
            continue
        if len(rest) != len(args) + 1 or list(rest[: len(args)]) != list(args):
            continue
        arg = rest[-1]
        if shape.match(arg) and shape.match(os.path.normpath(arg)):
            return True
    return False


def is_runner(words: list[str]) -> bool:
    """Is this invocation a run of the project's suite, rather than a write?

    A closed table of whole invocations. `pytest` is the only head word
    accepted with arbitrary arguments; everything else names the argument that
    makes it a run. An inline-script flag disqualifies any of them.

    The table the repo declares is read first and is whole invocations too: a
    repo-local script is not a head word on any list, and asking whether a head
    only ever prints is the wrong question for one that runs gates.
    """
    if not words:
        return False
    if has_inline_script(words):
        return False
    if is_declared_run(words):
        return True
    head = os.path.basename(words[0])
    rest = words[1:]
    first = rest[0] if rest else ""
    if head == "pytest":
        return not any(w.startswith(PYTEST_WRITE_FLAGS) for w in rest)
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


def _long_option(word: str, option: str, least: int) -> bool:
    """Would git read `word` as `--<option>`, spelled out or abbreviated?"""
    if not word.startswith("--"):
        return False
    name = word[2:].split("=", 1)[0]
    return len(name) >= least and option.startswith(name)


def git_write_form(words: list[str]) -> bool:
    """Does this `GIT_NO_WORKTREE` stage carry a form that writes anyway?

    Git accepts a unique prefix of a long option, so an abbreviation is read as
    the option it could spell. That over-denies one a subcommand rejects, which
    is the safe direction. Every word after the subcommand is scanned, `--` and
    pattern arguments included, because a misread there under-denies.
    """
    sub, rest = words[1], words[2:]
    if any(_long_option(w, GIT_OUTPUT, 3) for w in rest):
        return True
    if sub == "grep":
        for w in rest:
            if _long_option(w, GIT_GREP_PAGER, 2):
                return True
            if w.startswith("-") and not w.startswith("--") and "O" in w:
                return True
    return sub == "reflog" and any(w in GIT_REFLOG_WRITES for w in rest)


def segment_writes(segment: str, *, restore_ok: bool = True) -> bool:
    """Does this one pipeline stage change anything on disk?"""
    if redirect_writes(segment):
        return True
    words = words_of(segment)
    if not words:
        return False
    if is_runner(words):
        return False
    head = os.path.basename(words[0])
    if head == "git":
        if len(words) > 1 and words[1] in GIT_NO_WORKTREE:
            return git_write_form(words)
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
    for stage, body in segments_with_bodies(command):
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
        if body and pattern.search(body):
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
