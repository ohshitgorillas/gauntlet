"""Whether `bwrap` can be used on this host, and the prose for when it cannot.

Installed is not working. The binary is on `PATH` and the kernel still refuses
the user namespace, so the probe below runs the smallest profile that does what
every real profile does and reports what `bwrap` said. The hook that wraps a
command fails closed on a fault rather than running the command unconfined.
"""

from __future__ import annotations

import functools
import shutil
import subprocess

_NO_BWRAP = (
    "This kit runs every Bash command inside `bwrap`, and `bwrap` is not on this host. "
    "Install `bubblewrap` (Fedora/RHEL: `sudo dnf install bubblewrap`; Debian/Ubuntu: "
    "`sudo apt install bubblewrap`). The hook fails closed rather than running the "
    "command unconfined. (hooks/bwrap-wrap.py)"
)


_BWRAP_BROKEN = (
    "This kit runs every Bash command inside `bwrap`. `bwrap` is installed on this host "
    "but will not run here, so every wrapped command would die at exec. `bwrap` said: "
    "{said}. Usual causes: unprivileged user namespaces off "
    "(`sysctl kernel.unprivileged_userns_clone`, `user.max_user_namespaces`), or a "
    "seccomp/LSM policy refusing the setup. The hook fails closed rather than running "
    "the command unconfined. (hooks/bwrap-wrap.py)"
)

#: the smallest profile that still does what every real profile does: make a
#: user namespace, bind a root, mount `/dev` and `/proc`, unshare the pid
#: namespace. A host that refuses any of those refuses every profile here.
_PROBE = (
    "--ro-bind",
    "/",
    "/",
    "--dev",
    "/dev",
    "--proc",
    "/proc",
    "--unshare-pid",
    "--die-with-parent",
    "--",
    "true",
)


def _first_line(text: str) -> str:
    return (text or "").strip().split("\n")[0].strip()


@functools.lru_cache(maxsize=1)
def bwrap_fault() -> str | None:
    """Why `bwrap` cannot be used on this host right now, or None if it can.

    Installed is not the same as working: user namespaces can be off and a
    seccomp policy can refuse the setup, and both leave a binary on `PATH` that
    dies at exec. Nothing but running it answers that, so it is run -- once per
    process, on `true`, which costs one process for the first `Bash` call of a
    session and nothing for the rest.
    """
    if shutil.which("bwrap") is None:
        return _NO_BWRAP
    try:
        done = subprocess.run(
            ["bwrap", *_PROBE], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError) as error:
        return _BWRAP_BROKEN.format(said=_first_line(str(error)) or type(error).__name__)
    if done.returncode == 0:
        return None
    said = _first_line(done.stderr) or f"exit status {done.returncode}"
    return _BWRAP_BROKEN.format(said=said)
