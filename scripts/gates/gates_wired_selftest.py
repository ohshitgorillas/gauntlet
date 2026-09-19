#!/usr/bin/env python3
"""The `--self-test` body of `gates-wired.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays readable as a
pair of rules and a sweep, and `python3 scripts/gates/gates-wired.py --self-test`
runs it.

Each case writes a real tree — real scripts, a real `check-gates.sh` with a real
`gates=(...)` array — into a throwaway directory, changes into it so the paths
reaching the gate are repo-relative the way a real run passes them, and reads
back the pair the gate offers a caller: the exit code, and what lands on stdout.
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

GATE_PATH = Path(__file__).resolve().parent / "gates-wired.py"

#: A `*.py` entry point: an underscore-free name with a `__main__` guard.
ENTRY = (
    "#!/usr/bin/env python3\n\n\ndef main():\n    return 0\n\n\n"
    'if __name__ == "__main__":\n    main()\n'
)

#: The same, offering `--self-test`.
ENTRY_SELF_TEST = ENTRY.replace("def main():", "def self_test():\n    return 0\n\n\ndef main():")

#: A support module: no `__main__` guard, so nothing invokes it directly.
SUPPORT = '"""A helper."""\n\n\ndef self_test():\n    return 0\n'

#: A shell gate that answers to the flag.
SHELL_SELF_TEST = "#!/usr/bin/env bash\n[[ $1 == --self-test ]] && exit 0\n"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location("gates_wired_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _wiring(entries: list[str]) -> str:
    """Render a `check-gates.sh` whose array holds exactly these lines."""
    body = "".join(f"    {entry}\n" for entry in entries)
    return (
        "#!/usr/bin/env bash\nset -u\n\ngates=(\n"
        + body
        + ')\n\nfor entry in "${gates[@]}"; do :; done\n'
    )


def _run(files: dict[str, str], entries: list[str]) -> tuple[int, str]:
    """Build a tree of `files` wired by `entries`, run the gate in it, and report."""
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relpath, text in {GATE.WIRING: _wiring(entries), **files}.items():
            path = root / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        os.chdir(root)
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                status = GATE.check()
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

    gate = "scripts/gates/shape.py"
    hook = "hooks/lane-thing.py"

    status, out = _run({gate: ENTRY}, [f'"shape|python3 {gate} --check"'])
    check("a wired gate script passes", (status, out), (0, ""))

    status, out = _run({gate: ENTRY}, [])
    check("a gate script named by no entry fails", status, 1)
    check("the unwired gate script is named on stdout", gate in out, True)
    check("the wiring file is named in the failure", GATE.WIRING in out, True)

    status, _ = _run({gate: ENTRY}, [f'#    "shape|python3 {gate} --check"'])
    check("a commented-out entry wires nothing", status, 1)

    status, out = _run({hook: ENTRY_SELF_TEST}, [])
    check("a hook offering --self-test and named by no entry fails", status, 1)
    check("the reason given for a hook is the flag it offers", "accepts --self-test" in out, True)

    status, out = _run({hook: ENTRY_SELF_TEST}, [f'"lane-thing|python3 {hook} --self-test"'])
    check("a wired hook offering --self-test passes", (status, out), (0, ""))

    status, _ = _run({hook: ENTRY}, [])
    check("a hook offering no --self-test needs no entry", status, 0)

    status, _ = _run(
        {"hooks/lanes.py": ENTRY.replace("main()", "hook_shape.entry(self_test, main)", 1)}, []
    )
    check("a hook routing the flag through hook_shape.entry needs an entry", status, 1)

    status, _ = _run({"scripts/gates/shape_selftest.py": SUPPORT}, [])
    check("an underscore-named support module in the gate directory needs no entry", status, 0)

    status, _ = _run({"hooks/lane_config.py": SUPPORT}, [])
    check("an underscore-named support module offering self_test needs no entry", status, 0)

    status, _ = _run({"scripts/pair/selftest.py": SUPPORT}, [])
    check("a module with no __main__ guard needs no entry", status, 0)

    status, out = _run({"scripts/blind.sh": SHELL_SELF_TEST}, [])
    check("a shell script offering --self-test needs an entry", status, 1)
    check("the unwired shell script is named on stdout", "scripts/blind.sh" in out, True)

    status, _ = _run({"scripts/pair.sh": "#!/usr/bin/env bash\nexit 0\n"}, [])
    check("a shell script offering no --self-test needs no entry", status, 0)

    status, _ = _run({}, [])
    check("the wiring script does not have to wire itself", status, 0)

    status, _ = _run({"scripts/gates/__pycache__/shape.py": ENTRY}, [])
    check("a cached copy under __pycache__ is not a gate", status, 0)

    status, out = _run({}, ['"ghost|python3 scripts/gates/ghost.py --self-test"'])
    check("an entry naming no file fails as stale", status, 1)
    check("the stale entry is named on stdout", "scripts/gates/ghost.py" in out, True)

    status, _ = _run(
        {gate: ENTRY},
        ['"pytest|env PYTHONPATH=$root $pytest tests -q"', f'"shape|python3 {gate}"'],
    )
    check("an entry that names no script path is no stale entry", status, 0)

    text = f"# {gate}\n" + _wiring([])
    status, _ = _run({gate: ENTRY, GATE.WIRING: text}, [])
    check("a mention outside the gates array wires nothing", status, 1)

    both = {gate: ENTRY_SELF_TEST}
    status, out = _run(both, [])
    check("a gate directory script is reported once, not twice", out.count(gate), 1)

    many = {gate: ENTRY, "scripts/gates/other.py": ENTRY, hook: ENTRY_SELF_TEST}
    status, out = _run(many, [])
    check(
        "every unwired gate is reported, not only the first",
        (gate in out, "other.py" in out, hook in out),
        (True, True, True),
    )

    status, out = _run(many, [f'"shape|python3 {gate}"'])
    check("a wired gate beside an unwired one is not named", gate in out, False)

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
