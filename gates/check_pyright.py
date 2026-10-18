"""pyright gate: type-check every Python file in strict mode under the settings in `pyproject.toml`."""

import subprocess
import sys
from pathlib import Path

from gates.check_suppressions import is_python_source

CONFIG = Path(__file__).resolve().parent.parent / "pyproject.toml"

FINISHED = frozenset({0, 1})

DIAGNOSTIC = "  "

CONTINUATION = 4


def main(paths: list[Path]) -> int:
    """Type-check the Python files among `paths` and print the findings located in them.

    pyright follows their imports to resolve types, but a finding is reported only when it
    lies in one of the given files, each printed with the continuation lines pyright indents
    under it. Exit 1 on any such finding, and 1 when no path is a
    Python file, since pyright handed no file checks the whole project instead. Exit 0 on
    none; when pyright does not finish a check, print its whole output and return its exit
    status.
    """
    sources = [str(path.resolve()) for path in paths if is_python_source(path)]
    if not sources:
        sys.stdout.write(f"check_pyright: no Python file among {len(paths)} path(s); nothing was checked\n")
        return 1
    command = [sys.executable, "-m", "pyright", "--project", str(CONFIG), "--pythonpath", sys.executable, *sources]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    sys.stderr.write(completed.stderr)
    if completed.returncode not in FINISHED:
        sys.stdout.write(completed.stdout)
        return completed.returncode
    located = tuple(f"{DIAGNOSTIC}{source}:" for source in sources)
    findings = 0
    keeping = False
    for line in completed.stdout.splitlines():
        if not line[:CONTINUATION].isspace():
            keeping = line.startswith(located)
            findings += 1 if keeping else 0
        if keeping:
            sys.stdout.write(f"{line.removeprefix(DIAGNOSTIC)}\n")
    sys.stdout.write(f"check_pyright: {findings} finding(s) in {len(sources)} Python file(s)\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
