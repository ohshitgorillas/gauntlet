"""Behavior tests for the nesting-depth gate's argv surface.

``scripts/gates/nesting.py`` takes Python file paths on argv and refuses a
tree where any function nests blocks deeper than ``MAX_DEPTH``. Each case
writes real source into ``tmp_path``, changes into it so the paths handed to
the gate are repo-relative the way a real invocation passes them, and calls
``check`` directly — the same seam ``nesting_selftest.py`` exercises. One
assertion per test.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

GATE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "gates" / "nesting.py"


def _load_gate() -> ModuleType:
    spec = importlib.util.spec_from_file_location("nesting_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()
CHECK = GATE.check

FLAT = "def f(level):\n    return level + 1\n"

DEPTH_FOUR = (
    "def f():\n    if a:\n        if b:\n            if c:\n                if d:\n                    pass\n"
)

DEPTH_FIVE = (
    "def f():\n"
    "    if a:\n"
    "        if b:\n"
    "            if c:\n"
    "                if d:\n"
    "                    if e:\n"
    "                        pass\n"
)

ELIF_CHAIN = (
    "def f():\n"
    "    if a:\n"
    "        if b:\n"
    "            if c:\n"
    "                pass\n"
    "            elif d:\n"
    "                pass\n"
    "            elif e:\n"
    "                pass\n"
)

NESTED_DEF_OVER_LIMIT = (
    "def outer():\n"
    "    if a:\n"
    "        def inner():\n"
    "            if a:\n"
    "                if b:\n"
    "                    if c:\n"
    "                        if d:\n"
    "                            if e:\n"
    "                                pass\n"
)


def _write(tmp_path: Path, relpath: str, source: str) -> str:
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    return relpath


def test_a_function_at_the_limit_passes(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/deep.py", DEPTH_FOUR)
    assert CHECK([path], {}) == 0


def test_a_function_one_past_the_limit_fails(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/deep.py", DEPTH_FIVE)
    assert CHECK([path], {}) == 1


def test_a_flat_function_passes(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/flat.py", FLAT)
    assert CHECK([path], {}) == 0


def test_a_function_over_the_limit_is_named_on_stdout(tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/deep.py", DEPTH_FIVE)
    CHECK([path], {})
    assert path in capsys.readouterr().out


def test_a_function_over_the_limit_reports_its_measured_depth(tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/deep.py", DEPTH_FIVE)
    CHECK([path], {})
    assert "5 deep (max 4)" in capsys.readouterr().out


def test_a_passing_run_prints_nothing(tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/flat.py", FLAT)
    CHECK([path], {})
    assert capsys.readouterr().out == ""


def test_an_elif_chain_shares_its_ifs_level(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/chain.py", ELIF_CHAIN)
    assert CHECK([path], {}) == 0


def test_a_nested_def_over_the_limit_is_reported_under_its_dotted_name(
    tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/inner.py", NESTED_DEF_OVER_LIMIT)
    CHECK([path], {})
    assert "outer.inner()" in capsys.readouterr().out


def test_an_exempt_function_passes(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/deep.py", DEPTH_FIVE)
    assert CHECK([path], {f"{path}::f": "measured on purpose"}) == 0


def test_a_stale_exemption_for_a_now_shallow_function_fails(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/deep.py", DEPTH_FOUR)
    assert CHECK([path], {f"{path}::f": "no longer needed"}) == 1


def test_a_stale_exemption_is_named_on_stdout(tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/deep.py", DEPTH_FOUR)
    CHECK([path], {f"{path}::f": "no longer needed"})
    assert f"{path}::f" in capsys.readouterr().out


def test_an_exemption_naming_no_file_fails_as_stale(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/flat.py", FLAT)
    assert CHECK([path], {"hooks/missing.py::f": "long gone"}) == 1


def test_an_exemption_for_a_file_not_on_argv_still_audits(tmp_path: Path, monkeypatch: Any) -> None:
    """Staleness is judged against the filesystem, not against the subset on argv."""
    monkeypatch.chdir(tmp_path)
    untouched = _write(tmp_path, "hooks/untouched.py", DEPTH_FOUR)
    committed = _write(tmp_path, "hooks/committed.py", FLAT)
    assert CHECK([committed], {f"{untouched}::f": "excused long ago"}) == 1


def test_one_offender_among_compliant_files_fails_the_gate(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    good = _write(tmp_path, "hooks/good.py", FLAT)
    bad = _write(tmp_path, "hooks/bad.py", DEPTH_FIVE)
    assert CHECK([good, bad], {}) == 1


def test_a_compliant_file_beside_an_offender_is_not_named(tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.chdir(tmp_path)
    good = _write(tmp_path, "hooks/good.py", FLAT)
    bad = _write(tmp_path, "hooks/bad.py", DEPTH_FIVE)
    CHECK([good, bad], {})
    assert good not in capsys.readouterr().out


def test_omitting_the_exemption_mapping_falls_back_to_the_shipped_one(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    path = _write(tmp_path, "hooks/deep.py", DEPTH_FIVE)
    monkeypatch.setattr(GATE, "EXEMPT", {f"{path}::f": "measured on purpose"})
    assert CHECK([path]) == 0


def test_main_with_no_argv_falls_back_to_tracked_files(tmp_path: Path, monkeypatch: Any) -> None:
    """With no paths on argv, the gate reads `git ls-files` — the shipped tree passes its own gate."""
    assert GATE.main(["nesting.py"]) == 0
