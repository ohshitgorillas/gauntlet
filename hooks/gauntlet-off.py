#!/usr/bin/env python3
"""The owner's off switch, in its three voices.

`GAUNTLET=off claude` starts a session with the lane hook, the two blind-agent
hooks and the `Stop` gate silent. The switch itself is `bypassed()` in `shell_shapes.py`, read
at the top of each hook's `main()`; this file is what the switch says out loud
and what keeps it out of the hands of the session it governs.

One file rather than three, because all three behaviours are the same one-line
question asked of the same variable, and splitting them would put three copies
of that question in the tree.

  * `--session-start`  silent when the gauntlet is on; a banner when it is off,
    naming the three hooks, the `Stop` gate, and the plain statement that
    nothing in `gauntlet/` is protected from any hand.
  * `--prompt`         silent when the gauntlet is on. When it is off, the
    standing notice that the chain is not running, on the session's first turn
    and every `EVERY`th turn after it. The never-propose rule is not spoken
    here. `gauntlet/CLAUDE.md` states it once in a file loaded once per session,
    and a per-turn copy is paid for again in every turn that follows it.
    The cadence is what holds that state in view thirty turns deep,
    past the point where the session-start banner has left the context window,
    and it is spaced because a line still in context is already doing its work.
    The turn is counted in a file under the system temporary directory, named
    for the session, so each session counts its own turns and the count lives
    where temporary files live. A payload carrying no readable `session_id`
    falls back to its `transcript_path`, and then to the id of the process that
    spawned the hook: each is stable across the turns of one session and
    distinct between two, which is all a count file's name has to be. Only a
    count that cannot be read or written speaks unconditionally -- a voice on
    every turn is paid for in every turn after it, so the fallback is a key and
    not a shrug.
  * `--bash`           a `PreToolUse` hook, live only when the gauntlet is on
    and silent when it is off. It denies a `GAUNTLET=` assignment and a nested
    `claude` invocation. The bypass belongs to the hand that launches the
    session and to no hand inside it.

Neither `--bash` test is a substring search over the command text. The
assignment test is for a `GAUNTLET=` *word*: a leading assignment on a segment,
or an argument to `export`, `set` or `env`. The `claude` test is on the *head
word* of a segment, after any leading assignments and any wrapper (`env`,
`nohup`, `timeout`, `xargs`) are stepped over. A head-word test rather than a
text match because the commands this repository documents carry the string
`claude` inside a path: `python3 hooks/<name>.py --self-test` is nine
lines of `README.md`. Matching text would deny the repository's own documented
commands; matching the head word denies `claude -p ...`, `env GAUNTLET=off
claude` and `nohup claude` and lets every `.claude/` path through. The reading
it gives up is a `claude` reached through a shell it cannot see into --
`bash -c 'claude'`, a wrapper script named something else -- which is the same
bound every shape test read off a command string carries.

Both halves of the denial are needed and neither is redundant. A bare
`GAUNTLET=off` prefix on a shell command does not in fact disarm anything:
hooks run in the Claude Code process's environment, not in the environment of a
`Bash` tool call. It is denied because the combination that does work is
`GAUNTLET=off claude`, and denying the two halves separately means no spelling
of the pair gets through -- an `export` on one line and a bare `claude` on the
next, an `env GAUNTLET=off`, a `claude` behind `nohup` or `timeout`.

The `--self-test` sets the value it is testing explicitly for each case and
never reads the ambient variable to decide what to assert, so a developer
running it under `GAUNTLET=off` gets the same output as one running it with the
variable unset. That property is itself one of the lines it pins, and it is
`docs/testing.md:67` rule 16 being obeyed rather than bent.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shell_shapes as sh  # noqa: E402

VAR = "GAUNTLET"
OFF = "off"

#: commands that carry another command as their argument. The head word we want
#: is the first word that is not one of these and not an assignment.
WRAPPERS = ("env", "nohup", "timeout", "xargs")

#: `timeout` takes a duration before the command it wraps, and every wrapper
#: takes options of its own. Neither is the head word we are after.
_DURATION = re.compile(r"\A[0-9]+(?:\.[0-9]+)?[smhd]?\Z")

#: how many turns apart the `--prompt` voice speaks. One is a voice on every
#: turn; a large number is a voice the session loses. Ten is a context window's
#: worth of turns, near enough.
EVERY = 10

#: the characters that survive into the name of a count file. A session id
#: arrives in a payload, so it is spelled into a flat name before it is a path.
_TAME = re.compile(r"[^A-Za-z0-9_-]")

#: the three hooks the switch silences, by the name a reader sees in the tree
SILENCED = (
    "lanes.py",
    "no-impl-reads.py",
    "blind-bash.py",
)

BANNER = (
    "GAUNTLET=off -- the chain is not running in this session.\n"
    "Silent: " + ", ".join(SILENCED) + ", and the `Stop` gate "
    "(`lanes.py --stop`), which no longer holds a turn open for an "
    "unruled red run.\n"
    "Nothing under `gauntlet/` is protected from any hand, this agent's "
    "included. A blind subagent spawned in this session is not blind: it can "
    "read the implementation and run any shell command.\n"
    "The chain is for work done under the chain. A session with the gauntlet "
    "off should not run it: an approved spec block written here was reviewed "
    "by an agent that could read the code, and it lands in a tracked file "
    "indistinguishable from one produced under the chain."
)

NOTICE = (
    "GAUNTLET=off is in force: the three hooks and the `Stop` gate are "
    "silent this session -- the chain is not running. Any write into `gauntlet/` "
    "will be allowed whoever "
    "makes it, and no blind agent is blind. Artifacts produced here are not "
    "evidence of anything."
)

_WHY_ASSIGN = (
    "This command carries a `" + VAR + "=` assignment. That variable is the owner's "
    "gauntlet switch, set on the shell that launches `claude` and nowhere else. An "
    "agent inside a running session does not reach it. (hooks/gauntlet-off.py)"
)
_WHY_NESTED = (
    "This command invokes `claude`. A nested session is the one place the gauntlet "
    "switch could be set from inside a session that has it on, so the invocation is "
    "denied by name. Paths under `.claude/` are unaffected -- what is matched is the "
    "head word of a command, not the text. (hooks/gauntlet-off.py)"
)


def off(value: str | None) -> bool:
    """Whether this value of the variable means off.

    Pure, and the switch's whole grammar: the exact value `off` after strip and
    lowercase. Unset, empty or misspelled leaves the gauntlet on, which is the
    safe direction. `sh.bypassed()` is this predicate over `os.environ`; this
    one takes its value as an argument so the self-test never has to touch the
    ambient environment to assert on it.
    """
    return (value or "").strip().lower() == OFF


#: The two shapes this file needs off a command string, kept here rather than
#: in `shell_shapes.py`. That module read commands for the lane hooks once, and
#: the lane hooks do not read commands any more; this guard still has to, because
#: the thing it denies is a spelling rather than a path, and no mount table
#: reaches a spelling. So the reading lives with its one caller.


_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([\w][\w.-]*)\1")


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
        #: a one-character separator, and the bare `&` that is one: next to a
        #: redirection (`2>&1`, `>&2`) it duplicates a descriptor instead
        elif ch in ";|\n" or (
            ch == "&"
            and not ((i and text[i - 1] in ">&") or (i + 1 < len(text) and text[i + 1] in ">&"))
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


def words_of(segment: str) -> list[str]:
    try:
        return shlex.split(segment, comments=False, posix=True)
    except ValueError:
        return segment.split()


def _head(segment: str) -> str:
    """The command word of a segment, past assignments and wrappers.

    An empty string where the segment carries no command word at all.
    """
    words = words_of(segment)
    i = 0
    wrapped = False
    while i < len(words):
        word = words[i]
        if "=" in word and not word.startswith("=") and "/" not in word.split("=", 1)[0]:
            i += 1  # a leading assignment, not the command
            continue
        if Path(word).name in WRAPPERS:
            wrapped = True
            i += 1  # a wrapper carries the command we want in its arguments
            continue
        if wrapped and (word.startswith("-") or _DURATION.match(word)):
            i += 1  # a wrapper's own option or `timeout`'s duration
            continue
        return Path(word).name
    return ""


def _assignment_words(segment: str) -> list[str]:
    """The words of a segment that could carry a `VAR=` assignment.

    Leading assignments, and the arguments of `export`, `set` and `env`. A word
    inside a longer string is not one of these, which is what keeps the test off
    a substring search.
    """
    words = words_of(segment)
    out: list[str] = []
    i = 0
    while i < len(words) and "=" in words[i] and not words[i].startswith("="):
        out.append(words[i])
        i += 1
    while i < len(words):
        if Path(words[i]).name in ("export", "set", "env"):
            out.extend(words[i + 1 :])
            break
        if Path(words[i]).name in WRAPPERS:
            i += 1
            continue
        break
    return out


def sets_var(command: str) -> bool:
    """Whether the command assigns the gauntlet variable, in any spelling."""
    for segment in segments(command):
        for word in _assignment_words(segment):
            if word.split("=", 1)[0] == VAR:
                return True
    return False


def invokes_claude(command: str) -> bool:
    """Whether any segment's head word is `claude`."""
    return any(_head(segment) == "claude" for segment in segments(command))


def _verdict(name: str, tool_input: sh.ToolInput) -> str | None:
    """Why this call is refused, or None to let it through."""
    if name != "Bash":
        return None
    command = sh.command_of(tool_input)
    if sets_var(command):
        return _WHY_ASSIGN
    if invokes_claude(command):
        return _WHY_NESTED
    return None


def session_start() -> None:
    if sh.bypassed():
        print(BANNER)


def _stdin() -> str:
    """The payload on standard input, or an empty string where there is none.

    A hook that only speaks must not die reading its own input: a closed or
    absent stdin reads as no session, and `_speaks` answers that by speaking.
    """
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return ""
        return sys.stdin.read()
    except (OSError, ValueError):
        return ""


def _session(text: str) -> str:
    """The session id in a hook payload, tamed to a filename, or an empty string.

    Every shape that is not a JSON object with a string `session_id` reads as no
    session at all, which `_key` answers with a fallback name.
    """
    return _string_field(text, "session_id")


def _string_field(text: str, field: str) -> str:
    """One string field of a hook payload, tamed to a filename.

    Every shape that is not a JSON object with that field a string reads as an
    empty string.
    """
    try:
        payload = json.loads(text or "{}")
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    value = payload.get(field)
    if not isinstance(value, str):
        return ""
    return _TAME.sub("", value)[:64]


def _key(text: str) -> str:
    """The name this session's count file takes, and never an empty string.

    `session_id` where the payload carries one, its `transcript_path` where it
    does not, and the spawning process where it carries neither. A hook is a
    child of the session that runs it, so that id is stable across the turns of
    one session and distinct between two -- which is the whole of what the name
    has to be.
    """
    return _session(text) or _string_field(text, "transcript_path") or ("ppid-" + str(os.getppid()))


def _count_path(session: str) -> Path:
    return Path(tempfile.gettempdir()) / ("gauntlet-off." + session)


def _speaks(session: str, *, every: int = EVERY) -> bool:
    """Whether this turn is one the voice speaks on, and count the turn.

    True on the first turn of a session and every `every`th turn after it. A
    count file that cannot be read or written is True: a voice lost costs the
    rule it carries. The caller passes a name from `_key`, which is never empty,
    so an unnameable session no longer reads as a first turn on every turn.
    """
    if not session or every < 1:
        return True
    path = _count_path(session)
    try:
        seen = int(path.read_text())
    except (OSError, ValueError):
        seen = 0
    try:
        path.write_text(str(seen + 1))
    except OSError:
        return True
    return seen % every == 0


def prompt(stdin: str = "") -> None:
    if sh.bypassed() and _speaks(_key(stdin)):
        print(NOTICE)


def bash() -> None:
    #: this hook guards one tool, so a payload naming any other is not its call
    #: to refuse however malformed it is
    sh.hook_main(lambda name, tool_input, _payload: _verdict(name, tool_input), guards=("Bash",))


def _cadence(session: str, *, every: int, turns: int) -> list[bool]:
    """What `_speaks` answers over `turns` consecutive turns of one session.

    A self-test helper, and it removes the count file it made: a self-test that
    left one behind would pass once and fail on the next run.
    """
    try:
        return [_speaks(session, every=every) for _ in range(turns)]
    finally:
        try:
            _count_path(session).unlink()
        except OSError:
            pass


def _spoken(*, value: str | None) -> str:
    """What one `--prompt` turn prints with the variable set to `value`.

    A self-test helper. The value is set explicitly and restored, so the
    assertion never depends on the variable the developer is running under, and
    the session id is one no real session collides with.
    """
    before = os.environ.get(VAR)
    buffer = io.StringIO()
    try:
        if value is None:
            os.environ.pop(VAR, None)
        else:
            os.environ[VAR] = value
        session = "spoken-" + str(os.getpid())
        with contextlib.redirect_stdout(buffer):
            prompt(json.dumps({"session_id": session}))
        try:
            _count_path(session).unlink()
        except OSError:
            pass
    finally:
        if before is None:
            os.environ.pop(VAR, None)
        else:
            os.environ[VAR] = before
    return buffer.getvalue().strip()


def self_test() -> int:
    """Pin the switch's grammar, the two voices, the cadence, and the two denials."""
    lines = {
        "off() is the exact value `off`, after strip and lowercase": (
            off("off")
            and off("OFF")
            and off("  off\n")
            and not off(None)
            and not off("")
            and not off("offf")
            and not off("0")
            and not off("false")
        ),
        "a GAUNTLET= assignment is denied, in every spelling": all(
            _verdict("Bash", {"command": c}) == _WHY_ASSIGN
            for c in (
                "GAUNTLET=off claude",
                "GAUNTLET=off echo hi",
                "export GAUNTLET=off",
                "env GAUNTLET=off claude -p x",
                "echo hi; export GAUNTLET=off",
                "set GAUNTLET=off",
            )
        ),
        "a claude head word is denied, past wrappers and assignments": all(
            _verdict("Bash", {"command": c}) == _WHY_NESTED
            for c in (
                "claude",
                "claude -p 'do a thing'",
                "nohup claude &",
                "timeout 60 claude -p x",
                "FOO=1 claude",
                "ls; claude -p x",
                "/usr/local/bin/claude -p x",
            )
        ),
        "a .claude/ path is not a claude invocation": all(
            _verdict("Bash", {"command": c}) is None
            for c in (
                "python3 hooks/lanes.py --self-test",
                "python3 hooks/gauntlet-off.py --self-test",
                "cat .claude/settings.json",
                "ls .claude/worktrees",
                "grep -rn claude docs/",
                "scripts/gates/check-gates.sh",
            )
        ),
        "a tool that is not Bash is not this hook's business": (
            _verdict("Write", {"command": "claude"}) is None
            and _verdict("Read", {"file_path": "GAUNTLET=off"}) is None
        ),
        "the two voices differ, and each says what it is for": (
            VAR + "=" + OFF in BANNER
            and "Stop" in BANNER
            and all(h in BANNER for h in SILENCED)
            and "not running" in NOTICE
            and BANNER != NOTICE
        ),
        #: a gauntlet-on session pays nothing per turn. The `--prompt` voice
        #: carries the off-switch notice and nothing else.
        "the prompt voice speaks only when the gauntlet is off": (
            _spoken(value="off") == NOTICE and _spoken(value=None) == ""
        ),
        #: the cadence, on a session id no real session can collide with, and
        #: removed after so a second run of the self-test starts from zero.
        "the voice speaks on the first turn and every EVERY-th turn after": (
            _cadence("cadence-" + str(os.getpid()), every=3, turns=7)
            == [True, False, False, True, False, False, True]
        ),
        "a turn with an unreadable session id is still counted, not spoken on": (
            _session("") == ""
            and _session("not json at all") == ""
            and _session("[]") == ""
            and _session('{"session_id": 7}') == ""
            and _key('{"transcript_path": "/x/y/z.jsonl"}') == "xyzjsonl"
            and _key("[]") == "ppid-" + str(os.getppid())
            and _key('{"session_id": "s"}') == "s"
            and _cadence(_key("not json at all"), every=3, turns=7)
            == [True, False, False, True, False, False, True]
        ),
        "a session id is tamed to a filename directly under the temp directory": (
            _session('{"session_id": "../../etc/passwd"}') == "etcpasswd"
            and _count_path(_session('{"session_id": "a/b"}')).parent
            == Path(tempfile.gettempdir())
        ),
        "the self-test asserts nothing on the ambient variable": (
            off("off") is True and off(os.environ.get("NONEXISTENT-BY-CONSTRUCTION")) is False
        ),
        #: a hook decides a tool call, so its own crash is a denial -- and a
        #: payload it cannot read is a call it cannot decide, which is a refusal.
        #: `--bash` is the entry point that decides one; the other two only speak.
        "every payload shape is answered, and an unreadable one is refused": (
            sh.survives_hostile_payloads(__file__, "--bash", guards=("Bash",))
        ),
    }
    return sh.report(lines)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--session-start" in sys.argv:
        session_start()
    elif "--prompt" in sys.argv:
        prompt(_stdin())
    elif "--bash" in sys.argv:
        bash()
