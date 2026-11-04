# /// script
# requires-python = ">=3.12"
# dependencies = ["mcp>=1.2,<2"]
# ///
import asyncio
import os
import signal
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

MAX_LINES = 200
MAX_CHARS = 20000


def _fail(message):
    print(f"checks.py: {message}", file=sys.stderr)
    sys.exit(2)


def _load():
    project = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project:
        _fail("CLAUDE_PROJECT_DIR is required")
    root = os.path.realpath(project)
    if not os.path.isdir(root):
        _fail(f"CLAUDE_PROJECT_DIR is not a directory: {root}")
    command = os.environ.get("FENCE_TEST_COMMAND", "")
    if not command.strip():
        _fail("FENCE_TEST_COMMAND is required and must be non-empty")
    raw = os.environ.get("FENCE_TEST_TIMEOUT", "900")
    try:
        timeout = int(raw)
    except ValueError:
        _fail(f"FENCE_TEST_TIMEOUT must be a positive integer, got {raw!r}")
    if timeout <= 0:
        _fail(f"FENCE_TEST_TIMEOUT must be a positive integer, got {raw!r}")
    return root, command, timeout


ROOT, COMMAND, TIMEOUT = _load()
LOCK = asyncio.Lock()
mcp = FastMCP("fence-checks")


def _killpg(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass


def _tail(text):
    lines = text.splitlines()
    kept = "\n".join(lines[-MAX_LINES:])
    kept = kept[-MAX_CHARS:]
    cut = len(lines) - len(kept.splitlines())
    if cut > 0:
        return f"[... {cut} earlier lines cut]\n{kept}"
    return kept


@dataclass(frozen=True)
class Clock:
    monotonic: Callable[[], float] = time.monotonic
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep


async def _exits_within(proc, seconds, clock):
    """Wait for proc to exit or for clock to sleep through seconds; True if it exited."""
    exited = asyncio.ensure_future(proc.wait())
    timer = asyncio.ensure_future(clock.sleep(seconds))
    try:
        await asyncio.wait({exited, timer}, return_when=asyncio.FIRST_COMPLETED)
        return exited.done()
    finally:
        exited.cancel()
        timer.cancel()


async def run_tests_with(clock: Clock) -> str:
    """run_tests, with every wait and elapsed reading taken from clock."""
    async with LOCK:
        start = clock.monotonic()
        timed_out = False
        with tempfile.TemporaryFile() as out:
            proc = await asyncio.create_subprocess_exec(
                "bash",
                "-c",
                COMMAND,
                cwd=ROOT,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=out,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True,
            )
            pgid = proc.pid
            try:
                if not await _exits_within(proc, TIMEOUT, clock):
                    timed_out = True
                    _killpg(pgid, signal.SIGTERM)
                    await _exits_within(proc, 5, clock)
            finally:
                _killpg(pgid, signal.SIGKILL)
            await proc.wait()
            out.seek(0)
            text = out.read().decode("utf-8", errors="replace")
        seconds = clock.monotonic() - start
        head = f"exit={proc.returncode} timed_out={str(timed_out).lower()} seconds={seconds:.1f}"
        return f"{head}\n{_tail(text)}"


@mcp.tool()
async def run_tests() -> str:
    """Run the fixed test command in the project checkout and return its result."""
    return await run_tests_with(Clock())


if __name__ == "__main__":
    mcp.run()
