"""How a server of this kit starts a script: an argv, no shell, both streams byte-faithful.

`subprocess.run` in text mode folds a `\\r\\n` and refuses a byte that is not
UTF-8, and `newline=""` is not an argument it takes. So both streams are
captured as bytes and decoded by `rpc.text`, which keeps every byte: a `\\r\\n`
stays two characters and an undecodable byte stays a surrogate, which
`json.dumps` carries as a `\\udcXX` escape.

`CLAUDE_PROJECT_DIR` names the checkout the call runs from only where the host
set it. Where the host set none, none is invented, and the script's own git
fallback finds the checkout it runs from.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import rpc


def child_env(cwd: Path) -> dict[str, str]:
    """The environment a script runs under, `CLAUDE_PROJECT_DIR` naming `cwd` if set."""
    env = dict(os.environ)
    if "CLAUDE_PROJECT_DIR" in env:
        env["CLAUDE_PROJECT_DIR"] = str(cwd)
    return env


def run(argv: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    """`argv` from `cwd`, no shell, its streams decoded by `rpc.text`."""
    done = subprocess.run(
        argv, cwd=cwd, env=child_env(cwd), capture_output=True, check=False, timeout=timeout
    )
    return subprocess.CompletedProcess(
        done.args, done.returncode, rpc.text(done.stdout), rpc.text(done.stderr)
    )
