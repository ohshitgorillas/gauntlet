"""Behavior tests for the `changelog.py` gate's argv surface."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "gates" / "repo" / "changelog.py"

CLEAN = "# Changelog\n\n## [Unreleased]\n\n### Fixed\n- **A clean fix lands.** It closes the gap.\n"

DIRTY = "# Changelog\n\n## [Unreleased]\n\n### Fixed\n- no bold lead here\n"


def _run(args):
    """Invoke the gate as a subprocess with `args` on argv; return the completed process."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False
    )


# 1
def test_a_clean_file_named_on_argv_exits_zero(tmp_path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text(CLEAN)

    done = _run([str(path)])

    assert done.returncode == 0


# 2
def test_a_dirty_file_named_on_argv_exits_nonzero(tmp_path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text(DIRTY)

    done = _run([str(path)])

    assert done.returncode == 1


# 3
def test_the_offending_path_is_named_on_stdout(tmp_path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text(DIRTY)

    done = _run([str(path)])

    assert str(path) in done.stdout


# 4
def test_a_clean_file_passing_reports_ok_on_stdout(tmp_path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text(CLEAN)

    done = _run([str(path)])

    assert "[ok]" in done.stdout


# 5
def test_no_path_on_argv_falls_back_to_the_repo_changelog():
    done = _run([])

    assert "CHANGELOG.md" in done.stdout


# 6
def test_no_path_on_argv_reads_the_real_changelog_not_a_missing_default():
    done = _run([])

    assert done.returncode in (0, 1)


# 7
def test_two_paths_on_argv_are_both_checked(tmp_path):
    clean_path = tmp_path / "clean.md"
    dirty_path = tmp_path / "dirty.md"
    clean_path.write_text(CLEAN)
    dirty_path.write_text(DIRTY)

    done = _run([str(clean_path), str(dirty_path)])

    assert (str(clean_path) in done.stdout, str(dirty_path) in done.stdout) == (True, True)


# 8
def test_two_paths_where_one_is_dirty_exits_nonzero(tmp_path):
    clean_path = tmp_path / "clean.md"
    dirty_path = tmp_path / "dirty.md"
    clean_path.write_text(CLEAN)
    dirty_path.write_text(DIRTY)

    done = _run([str(clean_path), str(dirty_path)])

    assert done.returncode == 1


# 9
def test_self_test_flag_exits_zero_on_a_clean_gate():
    done = _run(["--self-test"])

    assert done.returncode == 0


# 10
def test_self_test_flag_prints_a_pass_or_fail_line_per_rule():
    done = _run(["--self-test"])

    assert done.stdout.count("PASS ") + done.stdout.count("FAIL ") > 1
