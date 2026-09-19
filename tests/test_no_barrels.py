"""Behavior tests for the no-barrels gate's argv surface."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "gates" / "no-barrels.py"

REEXPORT = "import os\nimport sys\n"
DEFINES_FUNCTION = 'import os\n\n\ndef f():\n    return os.sep + "x"\n'
FORWARDER = "class C:\n    def f(self, x):\n        return self._other.f(x)\n"
DOES_MORE = "class C:\n    def f(self, x):\n        self._log(x)\n        return self._other.f(x)\n"


def _write(root, files):
    """Write `files` under `root`, making every parent."""
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)


def _run(cwd, args):
    """Run the gate in `cwd` with `args` on argv; give its exit status and stdout."""
    done = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    return done.returncode, done.stdout


def _repo(root, files):
    """Build a git repository at `root` holding `files`, every one of them tracked."""
    _write(root, files)
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    return root


# 1
def test_a_module_of_imports_and_nothing_else_fails_on_argv(tmp_path):
    _write(tmp_path, {"hooks/barrel.py": REEXPORT})

    status, out = _run(tmp_path, ["hooks/barrel.py"])

    assert (status, "hooks/barrel.py" in out) == (1, True)


# 2
def test_a_module_that_defines_a_function_passes_on_argv(tmp_path):
    _write(tmp_path, {"hooks/good.py": DEFINES_FUNCTION})

    status, out = _run(tmp_path, ["hooks/good.py"])

    assert (status, out) == (0, "")


# 3
def test_an_init_file_of_imports_alone_passes_on_argv(tmp_path):
    _write(tmp_path, {"scripts/pair/__init__.py": REEXPORT})

    status, out = _run(tmp_path, ["scripts/pair/__init__.py"])

    assert (status, out) == (0, "")


# 4
def test_a_trivial_forwarder_fails_and_is_named_with_its_function(tmp_path):
    _write(tmp_path, {"hooks/good.py": FORWARDER})

    status, out = _run(tmp_path, ["hooks/good.py"])

    assert (status, "hooks/good.py::f" in out) == (1, True)


# 5
def test_a_method_doing_more_than_returning_the_call_passes(tmp_path):
    _write(tmp_path, {"hooks/good.py": DOES_MORE})

    status, out = _run(tmp_path, ["hooks/good.py"])

    assert (status, out) == (0, "")


# 6
def test_a_file_not_named_on_argv_is_not_checked(tmp_path):
    _write(tmp_path, {"hooks/good.py": DEFINES_FUNCTION, "hooks/barrel.py": REEXPORT})

    status, out = _run(tmp_path, ["hooks/good.py"])

    assert (status, out) == (0, "")


# 7
def test_with_no_paths_the_gate_reads_the_tracked_files_under_the_shipped_roots(tmp_path):
    _repo(tmp_path, {"hooks/barrel.py": REEXPORT})

    status, out = _run(tmp_path, [])

    assert (status, "hooks/barrel.py" in out) == (1, True)


# 8
def test_with_no_paths_a_tracked_file_outside_the_shipped_roots_is_left_alone(tmp_path):
    _repo(tmp_path, {"vendor/barrel.py": REEXPORT, "hooks/good.py": DEFINES_FUNCTION})

    status, out = _run(tmp_path, [])

    assert (status, out) == (0, "")


# 9
def test_with_no_paths_an_untracked_file_under_a_shipped_root_is_left_alone(tmp_path):
    _repo(tmp_path, {"hooks/good.py": DEFINES_FUNCTION})
    _write(tmp_path, {"hooks/barrel.py": REEXPORT})

    status, out = _run(tmp_path, [])

    assert (status, out) == (0, "")


# 10
def test_the_shipped_tree_passes_its_own_gate_with_no_paths():
    status, out = _run(REPO, [])

    assert (status, out) == (0, "")


# 11
def test_the_self_test_flag_runs_the_self_test_rather_than_the_gate():
    status, out = _run(REPO, ["--self-test"])

    assert (status, "FAIL" in out) == (0, False)
