#!/usr/bin/env python3
"""The `--self-test` body of `subprocess-timeout.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays readable as one
rule over two shapes, and `python3 scripts/gates/code/subprocess-timeout.py
--self-test` runs it.

Each case writes real Python source into a throwaway tree, changes into it so
the paths reaching the gate are repo-relative the way a real run passes them,
and checks the pair the gate offers a caller: the exit code, and what lands on
stdout.
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "subprocess-timeout.py"

BARE_RUN = 'import subprocess\n\nsubprocess.run(["git", "status"], check=True)\n'
TIMED_RUN = 'import subprocess\n\nsubprocess.run(["git", "status"], check=True, timeout=60)\n'
BARE_CALL = 'import subprocess\n\nsubprocess.call(["git", "status"])\n'
BARE_CHECK_CALL = 'import subprocess\n\nsubprocess.check_call(["git", "status"])\n'
BARE_CHECK_OUTPUT = 'import subprocess\n\nsubprocess.check_output(["git", "status"])\n'
ALIASED_IMPORT = 'from subprocess import run\n\nrun(["git", "status"])\n'
TIMED_ALIASED_IMPORT = 'from subprocess import run\n\nrun(["git", "status"], timeout=60)\n'
RENAMED_IMPORT = 'from subprocess import run as spawn\n\nspawn(["git", "status"])\n'
ALIASED_MODULE = 'import subprocess as sp\n\nsp.check_output(["git", "status"])\n'
POPEN_COMMUNICATE = (
    "import subprocess\n\n"
    'out = subprocess.Popen(["git", "status"], stdout=subprocess.PIPE).communicate()\n'
)
TIMED_COMMUNICATE = (
    "import subprocess\n\n"
    'proc = subprocess.Popen(["git", "status"], stdout=subprocess.PIPE)\n'
    "out = proc.communicate(timeout=60)\n"
)
OTHER_RUN = 'import mytool\n\nmytool.run(["git", "status"])\n'
NO_SUBPROCESS = '"""A module that starts nothing."""\n\nROOT = "/"\n'


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location("subprocess_timeout_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _write(root: Path, relpath: str, source: str) -> None:
    """Write `source` to `relpath` under `root`, making its parents."""
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def _run(files: dict[str, str], names: list[str] | None = None) -> tuple[int, str]:
    """Build a tree of `files`, run the gate over `names`, and return its status and stdout.

    Named no path the gate picks the file set itself, which is what the walk of
    `hooks/` and `scripts/` has to be driven through to be checked at all.
    """
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relpath, source in files.items():
            _write(root, relpath, source)
        os.chdir(root)
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                status = GATE.main(["subprocess-timeout.py", *(names or [])])
        finally:
            os.chdir(cwd)
    return status, out.getvalue()


def self_test() -> int:
    """One PASS or FAIL per rule this gate exists to hold."""
    failed = 0

    def check(rule: str, got: object, want: object) -> None:
        nonlocal failed
        if got == want:
            print(f"PASS {rule}")
        else:
            failed += 1
            print(f"FAIL {rule}: {got!r} != {want!r}")

    bad = "hooks/bad.py"
    good = "hooks/good.py"

    status, out = _run({bad: BARE_RUN}, [bad])
    check("subprocess.run without timeout= fails", status, 1)
    check("the offending call is named with its line", f"{bad}:3" in out, True)

    status, out = _run({good: TIMED_RUN}, [good])
    check("subprocess.run with timeout= passes", (status, out), (0, ""))

    status, _ = _run({bad: BARE_CALL}, [bad])
    check("subprocess.call without timeout= fails", status, 1)

    status, _ = _run({bad: BARE_CHECK_CALL}, [bad])
    check("subprocess.check_call without timeout= fails", status, 1)

    status, _ = _run({bad: BARE_CHECK_OUTPUT}, [bad])
    check("subprocess.check_output without timeout= fails", status, 1)

    status, out = _run({bad: ALIASED_IMPORT}, [bad])
    check("an imported bare run() without timeout= fails", status, 1)
    check("the imported name is named on stdout", "run carries no timeout=" in out, True)

    status, out = _run({good: TIMED_ALIASED_IMPORT}, [good])
    check("an imported bare run() with timeout= passes", (status, out), (0, ""))

    status, _ = _run({bad: RENAMED_IMPORT}, [bad])
    check("an import renamed with `as` is followed too", status, 1)

    status, _ = _run({bad: ALIASED_MODULE}, [bad])
    check("a module imported as an alias is followed too", status, 1)

    status, out = _run({bad: POPEN_COMMUNICATE}, [bad])
    check("Popen(...).communicate() without timeout= fails", status, 1)
    check("the communicate call is named on stdout", ".communicate carries no" in out, True)

    status, out = _run({good: TIMED_COMMUNICATE}, [good])
    check("communicate(timeout=...) passes", (status, out), (0, ""))

    status, out = _run({good: OTHER_RUN}, [good])
    check("a run() on some other module passes", (status, out), (0, ""))

    status, out = _run({good: NO_SUBPROCESS}, [good])
    check("a module starting no child passes", (status, out), (0, ""))

    files = {
        "hooks/one.py": TIMED_RUN,
        "hooks/two.py": BARE_RUN,
        "scripts/three.py": POPEN_COMMUNICATE,
    }
    status, out = _run(files, list(files))
    check("one offender among compliant files fails the gate", status, 1)
    check(
        "every offender is reported, not only the first",
        ("hooks/two.py" in out, "scripts/three.py" in out),
        (True, True),
    )
    check("a compliant file beside an offender is not named", "hooks/one.py" in out, False)

    status, out = _run({"hooks/two.py": BARE_RUN, "elsewhere/four.py": BARE_RUN})
    check("named no path the gate walks hooks/ and scripts/ itself", status, 1)
    check("a file outside those roots is not walked", "elsewhere/four.py" in out, False)

    check("the shipped tree passes its own gate", GATE.main(["subprocess-timeout.py"]), 0)

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
