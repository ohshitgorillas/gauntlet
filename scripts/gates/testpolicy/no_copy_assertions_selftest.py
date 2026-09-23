"""The `--self-test` body of `no-copy-assertions.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays readable as a
definition of seeded, and `python3 scripts/gates/testpolicy/no-copy-assertions.py
--self-test` runs it.

Each case writes a real suite into a throwaway tree — a module, and where the
rule needs one a `tests/support/` fake or fixture — changes into it so the paths
reaching the gate are repo-relative the way a real run passes them, and reads
back the pair the gate offers a caller: the exit code, and what lands on stdout.
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "no-copy-assertions.py"
MODULE = "tests/test_sample.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location("no_copy_assertions_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _run(source: str, extra: dict[str, str] | None = None, listed: bool = False) -> tuple[int, str]:
    """Write a suite into a throwaway tree, run the gate over its module, and
    return status and stdout. With `listed` the tree is a git checkout the suite
    sits in untracked, and the gate picks its own file set."""
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        for relpath, text in {MODULE: source, **(extra or {})}.items():
            path = Path(tmp) / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        if listed:
            subprocess.run(["git", "init", "-q", tmp], check=True, capture_output=True, timeout=60)
        os.chdir(tmp)
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                status = GATE.check(GATE.tracked_tests() if listed else [MODULE])
        finally:
            os.chdir(cwd)
    return status, out.getvalue()


SENTENCE = "the widget was refused"
COPY = f"def test_copy():\n    assert reply() == '{SENTENCE}'\n"
SEEDED = f"def test_seeded():\n    sent = '{SENTENCE}'\n    assert reply(sent) == '{SENTENCE}'\n"
COMPOSED = (
    f"def test_composed():\n    sent = '{SENTENCE}'\n"
    f"    assert reply(sent) == '{SENTENCE}, {SENTENCE}'\n"
)
HANDED = f"def test_handed():\n    assert words('{SENTENCE}') == 4\n"
METHOD = f"def test_method():\n    assert body().count('{SENTENCE}') == 1\n"
RAISES = (
    "import pytest\n\n\ndef test_raises():\n"
    f"    with pytest.raises(ValueError, match='{SENTENCE}'):\n        reply()\n"
)
FRAMEWORK_COPY = (
    "import unittest\n\n\n"
    "class Suite(unittest.TestCase):\n"
    "    def test_copy(self):\n"
    f"        self.assertEqual(reply(), '{SENTENCE}')\n"
)
ONE_WORD = "def test_word():\n    assert reply() == 'refused'\n"
WIRE_SHAPED = "def test_wire():\n    assert reply() == '<widget state=refused>'\n"
FAKE = f"REPLY = '{SENTENCE}'\n"
SKELETON = "def reply(name):\n    return f'the {name} was refused'\n"
FIXTURE = f"a header line\n{SENTENCE}\n"


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

    status, out = _run(COPY)
    check("a prose literal the tests never seeded fails", status, 1)
    check("the copy site is named with its line", f"{MODULE}:2" in out, True)
    check("the copied sentence is quoted on stdout", SENTENCE in out, True)

    status, out = _run(SEEDED)
    check("a literal the test itself put on the wire passes", (status, out), (0, ""))

    status, out = _run(COMPOSED)
    check("a literal composed of seeded pieces passes", (status, out), (0, ""))

    status, out = _run(HANDED)
    check("a sentence handed to a plain function passes", (status, out), (0, ""))

    status, _ = _run(METHOD)
    check("a sentence handed to a method on the value under test fails", status, 1)

    status, out = _run(RAISES)
    check("a raises match= pattern is read as an assertion", status, 1)
    check("the match category is named on stdout", "raises-match" in out, True)

    status, _ = _run(FRAMEWORK_COPY)
    check("a framework assertion's literal is read as copy", status, 1)

    status, out = _run(ONE_WORD)
    check("a one-word literal is an identifier and passes", (status, out), (0, ""))

    status, out = _run(WIRE_SHAPED)
    check("a wire-shaped literal passes", (status, out), (0, ""))

    status, out = _run(COPY, {"tests/support/fake.py": FAKE})
    check("a literal a support fake wrote passes", (status, out), (0, ""))

    status, out = _run(COPY, {"tests/support/fake.py": SKELETON})
    check("a literal matching a fake's f-string passes", (status, out), (0, ""))

    status, out = _run(COPY, {"tests/support/fixtures/reply.txt": FIXTURE})
    check("a literal lying inside a fixture file passes", (status, out), (0, ""))

    status, out = _run(COPY, listed=True)
    check("with no paths an untracked test module is read", (status, MODULE in out), (1, True))

    check("the shipped suite passes its own gate", GATE.main(["no-copy-assertions.py"]), 0)

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
