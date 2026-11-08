"""Characterization of fence/checks.py as it stands (D-09): the tests pin existing behavior and are exempt from the red run (docs/testing.md rule 8)."""

import asyncio
import importlib.util
import os
from pathlib import Path

import pytest

SRC = Path(__file__).with_name("checks.py")


def load(monkeypatch, root, command="true", timeout=None):
    if root is None:
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    else:
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv("FENCE_TEST_COMMAND", command)
    if timeout is None:
        monkeypatch.delenv("FENCE_TEST_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("FENCE_TEST_TIMEOUT", timeout)
    spec = importlib.util.spec_from_file_location("fence_checks_under_test", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_normally(mod, seconds_read=(0.0, 1.0), sleeps=None):
    """Run the command with a clock whose sleep never completes, so the process exit wins. `sleeps` records each wait asked for."""
    table = iter(seconds_read)
    waits = [] if sleeps is None else sleeps

    async def never(seconds):
        waits.append(seconds)
        await asyncio.Event().wait()

    return asyncio.run(mod.run_tests_with(mod.Clock(monotonic=lambda: next(table), sleep=never)))


def run_to_timeout(mod, seconds_read=(0.0, 900.0), started=None):
    """Run the command with a clock whose sleep returns at once, so the timeout fires. With `started`, the sleep first yields until that file exists, so the command has begun."""
    table = iter(seconds_read)

    async def at_once(seconds):
        while started is not None and not started.exists():
            await asyncio.sleep(0)

    return asyncio.run(mod.run_tests_with(mod.Clock(monotonic=lambda: next(table), sleep=at_once)))


@pytest.mark.parametrize(
    "root, command, timeout",
    [
        (None, "true", None),
        ("a-file", "true", None),
        ("dir", "", None),
        ("dir", "   ", None),
        ("dir", "true", "soon"),
        ("dir", "true", "0"),
        ("dir", "true", "-5"),
    ],
)
def test_startup_refuses_with_status_2(monkeypatch, tmp_path, root, command, timeout):
    (tmp_path / "a-file").write_text("x")
    (tmp_path / "dir").mkdir()
    target = None if root is None else tmp_path / root
    with pytest.raises(SystemExit, match="^2$"):
        load(monkeypatch, target, command, timeout)


@pytest.mark.parametrize("timeout, waited", [(None, 900), ("45", 45)])
def test_the_command_waits_for_the_timeout_it_was_given(monkeypatch, tmp_path, timeout, waited):
    sleeps = []
    run_normally(load(monkeypatch, tmp_path, "true", timeout), sleeps=sleeps)
    assert sleeps[0] == waited


def test_the_result_head_carries_exit_timed_out_and_seconds(monkeypatch, tmp_path):
    mod = load(monkeypatch, tmp_path, "exit 3")
    assert run_normally(mod, (10.0, 12.5)).splitlines()[0] == "exit=3 timed_out=false seconds=2.5"


def test_the_result_body_holds_stdout_then_stderr_of_the_command(monkeypatch, tmp_path):
    mod = load(monkeypatch, tmp_path, "echo out; echo err >&2")
    assert run_normally(mod).splitlines()[1:] == ["out", "err"]


def test_the_command_runs_in_the_project_folder(monkeypatch, tmp_path):
    mod = load(monkeypatch, tmp_path, "pwd")
    assert run_normally(mod).splitlines()[1] == str(tmp_path.resolve())


def test_the_tail_keeps_the_last_200_lines(monkeypatch, tmp_path):
    mod = load(monkeypatch, tmp_path, "seq 1 250")
    assert run_normally(mod).splitlines()[-200:] == [str(n) for n in range(51, 251)]


def test_the_tail_keeps_the_last_20000_characters(monkeypatch, tmp_path):
    mod = load(monkeypatch, tmp_path, "for i in 1 2 3; do head -c 9000 /dev/zero | tr '\\0' x; echo; done")
    assert len(run_normally(mod).partition("\n")[2]) == 20000


def test_a_timeout_is_reported_in_the_head(monkeypatch, tmp_path):
    mod = load(monkeypatch, tmp_path, "sleep 20", "7")
    assert run_to_timeout(mod).splitlines()[0].split()[1] == "timed_out=true"


def test_a_timeout_reports_the_seconds_the_clock_read(monkeypatch, tmp_path):
    mod = load(monkeypatch, tmp_path, "sleep 20", "7")
    assert run_to_timeout(mod, (100.0, 107.5)).splitlines()[0].split()[2] == "seconds=7.5"


def test_a_timeout_kills_the_command(monkeypatch, tmp_path):
    pidfile = tmp_path / "pid"
    mod = load(monkeypatch, tmp_path, f"echo $$ > {pidfile}.tmp; mv {pidfile}.tmp {pidfile}; sleep 20", "7")
    run_to_timeout(mod, started=pidfile)
    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text()), 0)
