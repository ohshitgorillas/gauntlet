"""The `--self-test` body of `gauntlet-off.py`, and the two helpers only it uses.

Nothing else imports this module: `python3 hooks/gauntlet-off.py --self-test` is
what runs it, importing it inside that branch so the hook's own entry points pay
nothing for it.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hook_shape  # noqa: E402

_off = importlib.import_module("gauntlet-off")

BANNER = _off.BANNER
NOTICE = _off.NOTICE
OFF = _off.OFF
SILENCED = _off.SILENCED
VAR = _off.VAR
_count_path = _off._count_path
_key = _off._key
_session = _off._session
_speaks = _off._speaks
off = _off.off
prompt = _off.prompt


def _cadence(session: str, *, every: int, turns: int) -> list[bool]:
    """What `_speaks` answers over `turns` consecutive turns of one session.

    A self-test helper, and it removes the count file it made: a self-test that
    left one behind would pass once and fail on the next run.
    """
    try:
        return [_speaks(session, every=every) for _ in range(turns)]
    finally:
        with contextlib.suppress(OSError):
            _count_path(session).unlink()


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
        with contextlib.suppress(OSError):
            _count_path(session).unlink()
    finally:
        if before is None:
            os.environ.pop(VAR, None)
        else:
            os.environ[VAR] = before
    return buffer.getvalue().strip()


def self_test() -> int:
    """Pin the switch's grammar, the two voices, and the cadence."""
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
            and _count_path(_session('{"session_id": "a/b"}')).parent == Path(tempfile.gettempdir())
        ),
        "the self-test asserts nothing on the ambient variable": (
            off("off") is True and off(os.environ.get("NONEXISTENT-BY-CONSTRUCTION")) is False
        ),
    }
    return hook_shape.report(lines)
