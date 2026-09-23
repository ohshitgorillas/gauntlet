#!/usr/bin/env python3
"""The `--self-test` body of `changelog.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays readable as a
set of rules over a small parse, and `python3 scripts/gates/repo/changelog.py
--self-test` runs it.

Each case writes a whole changelog into a throwaway file and hands it to the
gate's own `check`. What is checked is the pair the gate offers a caller: the
exit code, and what lands on stdout.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "changelog.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name would otherwise shadow the stdlib-adjacent module."""
    spec = importlib.util.spec_from_file_location("changelog_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

HEADER = "# Changelog\n\nFormat: Keep a Changelog.\n\n"


def _run(body: str) -> tuple[int, str]:
    """Write `body` to a throwaway CHANGELOG.md, run the gate over it, and return
    its status and stdout."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "CHANGELOG.md"
        path.write_text(HEADER + body, encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            status = GATE.check(path)
    return status, out.getvalue()


def self_test() -> int:  # noqa: PLR0915
    """One PASS or FAIL per rule this gate exists to hold."""
    failed = 0

    def check(rule: str, got: object, want: object) -> None:
        nonlocal failed
        if got == want:
            print(f"PASS {rule}")
        else:
            failed += 1
            print(f"FAIL {rule}: {got!r} != {want!r}")

    status, out = _run("## [Unreleased]\n\n## [0.1.0] - 2026-01-01\n\n### Added\n- first release\n")
    check("a changelog with no unreleased entries passes", status, 0)

    status, out = _run("## [Unreleased]\n\n- **A short bullet.** Fixed the thing.\n")
    check("a bullet outside a heading still passes on its own bar", status, 0)

    long_clause = " ".join(f"word{n}" for n in range(GATE.WORD_CAP + 1))
    status, out = _run(f"## [Unreleased]\n\n### Fixed\n- **{long_clause}.**\n")
    check("a bullet over the word cap fails", status, 1)
    check("the word count is named on stdout", f"{GATE.WORD_CAP + 1} words" in out, True)

    status, out = _run("## [Unreleased]\n\n### Fixed\n- The fix landed without a bold lead.\n")
    check("a bullet with no bold lead fails", status, 1)
    check("the missing lead is named on stdout", "bold lead" in out, True)

    status, out = _run(
        "## [Unreleased]\n\n### Fixed\n- **Your setting now applies.** "
        "It reads the file at startup.\n"
    )
    check("a bullet in second person fails", status, 1)
    check("the second-person word is named on stdout", "second person" in out, True)

    status, out = _run(
        "## [Unreleased]\n\n### Fixed\n- **The fix is seamless now.** It applies at startup.\n"
    )
    check("a bullet using hype register fails", status, 1)
    check("marketing register is named on stdout", "marketing register" in out, True)

    status, out = _run(
        "## [Unreleased]\n\n### Fixed\n- **The old path is untouched.** "
        "Only the new path changed.\n"
    )
    check("a bullet narrating by negation fails", status, 1)
    check("narration by negation is named on stdout", "narrates by negation" in out, True)

    status, out = _run(
        "## [Unreleased]\n\n### Added\n- **A new test suite covers the parser.** "
        "It replaces the old fixture.\n"
    )
    check("a bullet naming a test fails", status, 1)
    check("the test mention is named on stdout", "names tests or test policy" in out, True)

    status, out = _run(
        "## [Unreleased]\n\n### Added\n- **The fake backend is gone.** "
        "Callers hit the real one now.\n"
    )
    check("a bullet naming a fake fails", status, 1)

    status, out = _run(
        "## [Unreleased]\n\n### Added\n- **One entry lands.** It does the thing.\n"
        "\n### Added\n- **A second entry lands.** It does another thing.\n"
    )
    check("a second heading of the same kind under Unreleased fails", status, 1)
    check("the duplicate heading is named on stdout", "second '### Added'" in out, True)

    status, out = _run(
        "## [0.1.0] - 2026-01-01\n\n### Fixed\n- fixed one thing\n\n### Fixed\n- fixed another\n"
    )
    check("a second heading of the same kind under a released version fails", status, 1)
    check("the released version is named on stdout", "second '### Fixed'" in out, True)

    status, out = _run(
        "## [Unreleased]\n\n### Changed\n- changed one thing\n\n### Added\n- added a thing\n"
    )
    check("headings out of Keep a Changelog order fail", status, 1)
    check("the out-of-order heading is named on stdout", "out of order" in out, True)

    status, out = _run("## [Unreleased]\n\n### Miscellany\n- something happened\n")
    check("an unknown heading kind fails", status, 1)
    check("the unknown heading is named on stdout", "unknown section" in out, True)

    status, out = _run(
        "## [Unreleased]\n\n### Fixed\n- **A fix that spans two lines.**\n"
        "  A continuation line follows it.\n"
    )
    check("a bullet running to a second line fails", status, 1)
    check("the second paragraph is named on stdout", "second paragraph" in out, True)

    status, out = _run(
        "## [Unreleased]\n\n### Fixed\n- **A clean fix lands.** It closes the gap cleanly.\n"
    )
    check("a clean unreleased entry passes", status, 0)

    status, _ = _run(
        "## [Unreleased]\n\n"
        "## [0.2.0] - 2026-01-02\n\n### Added\n- shipped a thing\n\n"
        "## [0.1.0] - 2026-01-01\n\n### Fixed\n- fixed a thing\n"
    )
    check("released sections are never rewritten by the fuller bar", status, 0)

    check("the shipped changelog passes its own gate", GATE.check(GATE.ROOT / "CHANGELOG.md"), 0)

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
