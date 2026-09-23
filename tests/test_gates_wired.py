"""Behavior tests for the gates-wired gate, through its `--check` surface.

Each test builds a throwaway tree — some scripts, and a `check-gates.sh` whose
`gates=(...)` array wires however many of them the case is about — and runs the
gate in it exactly as `check-gates.sh` runs a gate: as a process, in the tree's
own working directory. Nothing here imports the gate; what is pinned is the
pair a caller gets, the exit status and stdout.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "gates" / "wiring" / "gates-wired.py"
WIRING = "scripts/gates/check-gates.sh"

ENTRY = (
    "#!/usr/bin/env python3\n\n\ndef main():\n    return 0\n\n\n"
    'if __name__ == "__main__":\n    main()\n'
)
ENTRY_SELF_TEST = ENTRY.replace("def main():", "def self_test():\n    return 0\n\n\ndef main():")
SUPPORT = '"""A helper."""\n\n\ndef self_test():\n    return 0\n'
SHELL_SELF_TEST = "#!/usr/bin/env bash\n[[ $1 == --self-test ]] && exit 0\n"

GATE = "scripts/gates/shape.py"
HOOK = "hooks/lane-thing.py"


def _wiring(entries):
    """Render a check-gates.sh whose array holds exactly these lines."""
    body = "".join(f"    {entry}\n" for entry in entries)
    return (
        "#!/usr/bin/env bash\nset -u\n\ngates=(\n"
        + body
        + ')\n\nfor entry in "${gates[@]}"; do :; done\n'
    )


def _run(root, files, entries):
    """Build the tree under `root`, run the gate in it, and return the process."""
    for relpath, text in {WIRING: _wiring(entries), **files}.items():
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_wired_gate_passes(tmp_path):
    assert _run(tmp_path, {GATE: ENTRY}, [f'"shape|python3 {GATE} --check"']).returncode == 0


def test_wired_gate_prints_nothing(tmp_path):
    assert _run(tmp_path, {GATE: ENTRY}, [f'"shape|python3 {GATE} --check"']).stdout == ""


def test_unwired_gate_fails(tmp_path):
    assert _run(tmp_path, {GATE: ENTRY}, []).returncode == 1


def test_unwired_gate_is_named(tmp_path):
    assert GATE in _run(tmp_path, {GATE: ENTRY}, []).stdout


def test_failure_names_the_wiring_file(tmp_path):
    assert WIRING in _run(tmp_path, {GATE: ENTRY}, []).stdout


def test_commented_entry_wires_nothing(tmp_path):
    assert _run(tmp_path, {GATE: ENTRY}, [f'#    "shape|python3 {GATE}"']).returncode == 1


def test_unwired_hook_offering_self_test_fails(tmp_path):
    assert _run(tmp_path, {HOOK: ENTRY_SELF_TEST}, []).returncode == 1


def test_unwired_hook_is_given_the_flag_as_its_reason(tmp_path):
    assert "accepts --self-test" in _run(tmp_path, {HOOK: ENTRY_SELF_TEST}, []).stdout


def test_wired_hook_offering_self_test_passes(tmp_path):
    assert (
        _run(tmp_path, {HOOK: ENTRY_SELF_TEST}, [f'"t|python3 {HOOK} --self-test"']).returncode == 0
    )


def test_hook_offering_no_self_test_needs_no_entry(tmp_path):
    assert _run(tmp_path, {HOOK: ENTRY}, []).returncode == 0


def test_support_module_in_the_gate_directory_needs_no_entry(tmp_path):
    assert _run(tmp_path, {"scripts/gates/shape_selftest.py": SUPPORT}, []).returncode == 0


def test_module_without_a_main_guard_needs_no_entry(tmp_path):
    assert _run(tmp_path, {"scripts/pair/selftest.py": SUPPORT}, []).returncode == 0


def test_shell_script_offering_self_test_needs_an_entry(tmp_path):
    assert _run(tmp_path, {"scripts/blind.sh": SHELL_SELF_TEST}, []).returncode == 1


def test_shell_script_offering_no_self_test_needs_no_entry(tmp_path):
    assert _run(tmp_path, {"scripts/pair.sh": "#!/usr/bin/env bash\nexit 0\n"}, []).returncode == 0


def test_the_wiring_script_need_not_wire_itself(tmp_path):
    assert _run(tmp_path, {}, []).returncode == 0


def test_a_cached_copy_is_not_a_gate(tmp_path):
    assert _run(tmp_path, {"scripts/gates/__pycache__/shape.py": ENTRY}, []).returncode == 0


def test_entry_naming_no_file_fails_as_stale(tmp_path):
    assert (
        _run(tmp_path, {}, ['"ghost|python3 scripts/gates/ghost.py --self-test"']).returncode == 1
    )


def test_stale_entry_is_named(tmp_path):
    assert (
        "scripts/gates/ghost.py"
        in _run(tmp_path, {}, ['"ghost|python3 scripts/gates/ghost.py"']).stdout
    )


def test_entry_naming_no_script_path_is_not_stale(tmp_path):
    assert _run(tmp_path, {}, ['"pytest|env PYTHONPATH=$root $pytest tests -q"']).returncode == 0


def test_mention_outside_the_array_wires_nothing(tmp_path):
    files = {GATE: ENTRY, WIRING: f"# {GATE}\n" + _wiring([])}
    assert _run(tmp_path, files, []).returncode == 1


def test_a_gate_directory_script_is_reported_once(tmp_path):
    assert _run(tmp_path, {GATE: ENTRY_SELF_TEST}, []).stdout.count(GATE) == 1


def test_every_unwired_gate_is_reported(tmp_path):
    out = _run(
        tmp_path, {GATE: ENTRY, "scripts/gates/other.py": ENTRY, HOOK: ENTRY_SELF_TEST}, []
    ).stdout
    assert (GATE in out, "scripts/gates/other.py" in out, HOOK in out) == (True, True, True)


def test_a_wired_gate_beside_an_unwired_one_is_not_named(tmp_path):
    files = {GATE: ENTRY, "scripts/gates/other.py": ENTRY}
    assert GATE not in _run(tmp_path, files, [f'"shape|python3 {GATE}"']).stdout
