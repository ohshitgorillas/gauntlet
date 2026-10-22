# Copyright 2026 oh shit, gorillas!
"""The suppression gate's findings for one file, as a test reads them: the file parsed by the core under a pin.

The pin is the repository's own pyright `pythonVersion` unless the test gives one. A file the core could not parse
fails the test with the core's report, so a test that wants one calls `gates.core.source.parse` itself.
"""

from pathlib import Path

from gates.check_suppressions import Suppression
from gates.check_suppressions import find_suppressions as gate_findings
from gates.core.project import Project, Source
from gates.core.report import Unfinished
from gates.core.source import parse, pinned_version
from tests.support.project import OWN_CONFIG


def find_suppressions(
    path: Path, version: tuple[int, int] | None = None
) -> list[Suppression]:
    """Return the gate's findings in the file at `path`; raise AssertionError with the core's report when it is unfinished."""
    pinned = pinned_version(Project(OWN_CONFIG.parent)) if version is None else version
    parsed = parse(Source(given=path, absolute=path.absolute()), pinned)
    match parsed:
        case Unfinished(text=report):
            raise AssertionError(report)
        case _:
            return gate_findings(parsed)
