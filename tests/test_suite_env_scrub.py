"""Behavior tests for the child environment the suite's two subprocess helpers build.

The subject is this repository's own suite: ``hook_decision`` in
``tests/test_hook_wire.py`` and ``payload_decision`` in
``tests/test_blind_reads_declaration.py``.  Both take the script to run as an
ordinary parameter and join it onto a directory with ``pathlib``, so an absolute
path handed to that parameter is the path that runs; both return raw stdout when
stdout is not a hook answer, so a probe's own report comes back as the helper's
return value.

The probe below is written by this file, so every literal asserted here was put
on the wire by the test rather than read out of an implementation.  Every
expectation comes from the approved spec block
``gauntlet/specs/approved/suite-env-scrub.txt``.
"""

import importlib.util
from pathlib import Path

import pytest

WORKTREE_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = WORKTREE_ROOT / "tests"

# The copy label whose declaration the calls below carry.
ALLOW_LABEL = "ALLOW"

# The probe's whole source.  It reads its own environment and prints one line:
# each variable's value, or `<unset>` where the variable is absent from it.
UNSET = "<unset>"
PROBE_SOURCE = (
    "import os\n"
    "import sys\n"
    "\n"
    "sys.stdin.read()\n"
    "print(\n"
    '    "GAUNTLET={0}|PROBE_CONTROL={1}".format(\n'
    '        os.environ.get("GAUNTLET", "' + UNSET + '"),\n'
    '        os.environ.get("PROBE_CONTROL", "' + UNSET + '"),\n'
    "    )\n"
    ")\n"
)

# The caller environments driven, and the report each one must come back with:
# `GAUNTLET` scrubbed out of the child at both, `PROBE_CONTROL` carried through
# to the child at its own distinct value each time.
CALLER_SWEEP = (
    ("kept", "GAUNTLET=" + UNSET + "|PROBE_CONTROL=kept"),
    ("second", "GAUNTLET=" + UNSET + "|PROBE_CONTROL=second"),
)

# A payload shaped as the hooks' wire carries one; the probe ignores it.
PROBE_PAYLOAD = {"tool_name": "Bash", "tool_input": {"command": "true"}, "cwd": "/"}


def _load_suite_module(file_name, module_name):
    """Load one of the suite's own test modules by file path."""
    spec = importlib.util.spec_from_file_location(
        module_name, str(TESTS_DIR / file_name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def probe_path(tmp_path_factory):
    """Absolute path of the probe script, written by this file."""
    path = tmp_path_factory.mktemp("suite-env-scrub") / "env_probe.py"
    path.write_text(PROBE_SOURCE)
    return str(path)


@pytest.fixture(scope="module")
def hook_wire_module():
    return _load_suite_module("test_hook_wire.py", "suite_env_scrub_hook_wire")


@pytest.fixture(scope="module")
def blind_reads_module():
    """The declaration module, with ``_COPIES`` populated as the suite does."""
    module = _load_suite_module(
        "test_blind_reads_declaration.py", "suite_env_scrub_blind_reads"
    )
    module.setUpModule()
    yield module
    module.tearDownModule()


@pytest.mark.parametrize("control_value,expected_report", CALLER_SWEEP)
def test_hook_wire_helper_scrubs_gauntlet_and_keeps_other_caller_variables(
    monkeypatch, hook_wire_module, probe_path, control_value, expected_report
):
    monkeypatch.setenv("GAUNTLET", "off")
    monkeypatch.setenv("PROBE_CONTROL", control_value)

    assert hook_wire_module.hook_decision(probe_path, PROBE_PAYLOAD) == expected_report


@pytest.mark.parametrize("control_value,expected_report", CALLER_SWEEP)
def test_payload_decision_scrubs_gauntlet_and_keeps_other_caller_variables(
    monkeypatch, blind_reads_module, probe_path, control_value, expected_report
):
    monkeypatch.setenv("GAUNTLET", "off")
    monkeypatch.setenv("PROBE_CONTROL", control_value)

    assert (
        blind_reads_module.payload_decision(ALLOW_LABEL, probe_path, PROBE_PAYLOAD)
        == expected_report
    )
