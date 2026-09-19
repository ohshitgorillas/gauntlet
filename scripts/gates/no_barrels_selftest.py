#!/usr/bin/env python3
"""The `--self-test` body of `no-barrels.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays readable as a
pair of rules and two tables, and `python3 scripts/gates/no-barrels.py
--self-test` runs it.

Each case writes real Python source into a throwaway tree, changes into it so
the paths reaching the gate are repo-relative the way a real run passes them,
and hands the gate its own exemption tables. What is checked is the pair the
gate offers a caller: the exit code, and what lands on stdout.
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

GATE_PATH = Path(__file__).resolve().parent / "no-barrels.py"

REEXPORT = "import os\nimport sys\n"
DEFINES_FUNCTION = 'import os\n\n\ndef f():\n    return os.sep + "x"\n'
DEFINES_CONSTANT = "import os\n\nROOT = os.sep\n"
ONLY_ALL = 'import os\n\n__all__ = ["os"]\n'
ONLY_MAIN_GUARD = 'import sys\n\nif __name__ == "__main__":\n    sys.exit(0)\n'
NO_IMPORTS = '"""A module of constants."""\n\nROOT = "/"\n'
NOTHING_AT_ALL = '"""A module that says nothing."""\n'
FORWARDER = "class C:\n    def f(self, x):\n        return self._other.f(x)\n"
AWAIT_FORWARDER = "class C:\n    async def f(self, x):\n        return await self._other.f(x)\n"
DOCSTRING_FORWARDER = (
    'class C:\n    def f(self, x):\n        """Hand it on."""\n        return self._other.f(x)\n'
)
KEYWORD_FORWARDER = "class C:\n    def f(self, x):\n        return self._other.f(x=x)\n"
REORDERED = "class C:\n    def f(self, x, y):\n        return self._other.f(y, x)\n"
DOES_MORE = "class C:\n    def f(self, x):\n        self._log(x)\n        return self._other.f(x)\n"
PLAIN_RETURN = "class C:\n    def f(self, x):\n        return x + 1\n"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location("no_barrels_under_test", GATE_PATH)
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


def _run(
    files: dict[str, str],
    names: list[str],
    exempt: dict[str, str] | None = None,
    module_exempt: dict[str, str] | None = None,
) -> tuple[int, str]:
    """Build a tree of `files`, run the gate over `names`, and return its status and stdout."""
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relpath, source in files.items():
            _write(root, relpath, source)
        os.chdir(root)
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                status = GATE.check(names, exempt or {}, module_exempt or {})
        finally:
            os.chdir(cwd)
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

    barrel = "hooks/barrel.py"
    good = "hooks/good.py"

    status, out = _run({barrel: REEXPORT}, [barrel])
    check("a module of imports and nothing else fails", status, 1)
    check("the re-export module is named on stdout", barrel in out, True)

    status, out = _run({good: DEFINES_FUNCTION}, [good])
    check("a module defining a function passes", (status, out), (0, ""))

    status, out = _run({good: DEFINES_CONSTANT}, [good])
    check("a module defining a constant passes", (status, out), (0, ""))

    status, _ = _run({barrel: ONLY_ALL}, [barrel])
    check("__all__ alone does not count as defining something", status, 1)

    status, _ = _run({barrel: ONLY_MAIN_GUARD}, [barrel])
    check("a module whose whole body sits under the main guard fails", status, 1)

    status, out = _run({good: NO_IMPORTS}, [good])
    check("a module that imports nothing is not a re-export", (status, out), (0, ""))

    status, out = _run({good: NOTHING_AT_ALL}, [good])
    check("a module of nothing but a docstring passes", (status, out), (0, ""))

    init = "scripts/pair/__init__.py"
    status, out = _run({init: REEXPORT}, [init])
    check("__init__.py re-exporting a package surface passes", (status, out), (0, ""))

    status, out = _run({good: FORWARDER}, [good])
    check("a method returning a call on its own arguments fails", status, 1)
    check("the forwarder is named with its function on stdout", f"{good}::f" in out, True)

    status, _ = _run({good: AWAIT_FORWARDER}, [good])
    check("an awaited pass-through is a forwarder too", status, 1)

    status, _ = _run({good: DOCSTRING_FORWARDER}, [good])
    check("a docstring does not save a forwarder", status, 1)

    status, out = _run({good: KEYWORD_FORWARDER}, [good])
    check("a keyword-argument pass-through is knowingly not caught", (status, out), (0, ""))

    status, out = _run({good: REORDERED}, [good])
    check("a method reordering its arguments is not a forwarder", (status, out), (0, ""))

    status, out = _run({good: DOES_MORE}, [good])
    check("a method doing more than returning the call passes", (status, out), (0, ""))

    status, out = _run({good: PLAIN_RETURN}, [good])
    check("a method returning an expression of its own passes", (status, out), (0, ""))

    status, out = _run(
        {good: FORWARDER}, [good], {f"{good}::f": "reaches the private collaborator"}
    )
    check("an exempt forwarder passes", (status, out), (0, ""))

    status, out = _run({barrel: REEXPORT}, [barrel], None, {barrel: "the surface is the point"})
    check("an exempt re-export module passes", (status, out), (0, ""))

    status, out = _run({good: DEFINES_FUNCTION}, [good], {"hooks/gone.py::f": "stale"})
    check("a forwarder exemption naming no file fails as stale", status, 1)
    check("the stale forwarder entry is named on stdout", "hooks/gone.py::f" in out, True)

    status, _ = _run({good: DEFINES_FUNCTION}, [good], {f"{good}::f": "stale"})
    check("a forwarder exemption matching no forwarder fails as stale", status, 1)

    status, out = _run({good: DEFINES_FUNCTION}, [good], None, {"hooks/gone.py": "stale"})
    check("a module exemption naming no file fails as stale", status, 1)
    check("the stale module entry is named on stdout", "hooks/gone.py" in out, True)

    status, _ = _run({good: DEFINES_FUNCTION}, [good], None, {good: "stale"})
    check("a module exemption for a module that defines something fails as stale", status, 1)

    untouched = "hooks/untouched.py"
    status, _ = _run(
        {untouched: REEXPORT, good: DEFINES_FUNCTION}, [good], None, {untouched: "live"}
    )
    check("a live module exemption for a file not on argv passes", status, 0)

    status, _ = _run(
        {untouched: DEFINES_FUNCTION, good: DEFINES_FUNCTION}, [good], None, {untouched: "stale"}
    )
    check("a stale module exemption for a file not on argv still fails", status, 1)

    status, _ = _run(
        {untouched: FORWARDER, good: DEFINES_FUNCTION}, [good], {f"{untouched}::f": "live"}
    )
    check("a live forwarder exemption for a file not on argv passes", status, 0)

    files = {
        "hooks/one.py": DEFINES_FUNCTION,
        "hooks/two.py": REEXPORT,
        "hooks/three.py": FORWARDER,
    }
    status, out = _run(files, list(files))
    check("one offender among compliant files fails the gate", status, 1)
    check(
        "every offender is reported, not only the first",
        ("hooks/two.py" in out, "hooks/three.py" in out),
        (True, True),
    )
    check("a compliant file beside an offender is not named", "hooks/one.py" in out, False)

    check("the shipped tree passes its own gate", GATE.main(["no-barrels.py"]), 0)

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
