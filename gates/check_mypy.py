"""mypy gate: type-check every Python file under the settings in `pyproject.toml`."""

import os
import sys
from pathlib import Path

from mypy import api

from gates.check_suppressions import is_python_source

CONFIG = Path(__file__).resolve().parent.parent / "pyproject.toml"

FINISHED = frozenset({0, 1})


def main(paths: list[Path]) -> int:
    """Type-check the Python files among `paths` and print the findings located in them.

    mypy follows their imports and checks what they import, but a finding is reported only
    when it lies in one of the given files. Exit 1 on any such finding and 0 on none; when
    mypy does not finish a check, print its whole output and return its exit status.

    mypy runs without its cache: a cached module replays its findings under the path it had
    when cached, so a file moved with unchanged content would report under a path no longer
    given, and its findings would be dropped.
    """
    sources = [os.path.abspath(path) for path in paths if is_python_source(path)]
    arguments = ["--config-file", str(CONFIG), "--cache-dir", os.devnull, "--show-absolute-path", "--no-error-summary", *sources]
    report, errors, status = api.run(arguments)
    sys.stderr.write(errors)
    if status not in FINISHED:
        sys.stdout.write(report)
        return status
    located = tuple(f"{source}:" for source in sources)
    findings = [line for line in report.splitlines() if line.startswith(located)]
    for finding in findings:
        sys.stdout.write(f"{finding}\n")
    sys.stdout.write(f"check_mypy: {len(findings)} finding line(s) in {len(sources)} Python file(s)\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
