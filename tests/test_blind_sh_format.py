"""The writing verb of the blind agents' one shell, over a real lane file.

The surface is ``scripts/blind.sh`` as a blind agent runs it: a subcommand and a
path under the lane, on the shell, against a file that exists.  What is observed
is the file's own bytes afterwards and the status the script exits with -- the
two things a writer who cannot see the gates' output has to go by.

The expected bytes are ruff's and black's, not this repo's: a lane file whose
only faults are an unused import and a missing space is a file those two tools
rewrite, and the rewrite is the upstream fact pinned here.
"""

import os
import subprocess
import unittest
import uuid
from pathlib import Path

WORKTREE_ROOT = Path(__file__).resolve().parents[1]
BLIND_SH = WORKTREE_ROOT / "scripts" / "blind.sh"
LANE_DIR = Path(__file__).resolve().parent

#: a lane file whose two faults -- an unused import and a missing space after a
#: comma -- are both ones the gates repair on their own
FIXABLE = "import os\n\nx = [1,2]\n"

#: the same file once ruff has taken the import out and black has spaced the
#: list, which is what the two tools leave behind at those bytes
FORMATTED = "x = [1, 2]\n"

#: the same file with an undefined name added: one fault the gates repair and
#: one they can only report
UNREPAIRABLE = "import os\n\nx = [1,2]\ny = undefined_name\n"


def _environment():
    """The caller's environment with ``GAUNTLET`` cleared and the tree named.

    Under ``GAUNTLET=off`` the kit's scripts and hooks return at their first
    line, so a suite run from such a session would be measuring nothing.
    ``CLAUDE_PROJECT_DIR`` names this worktree, so the declaration the script
    reads is this tree's own rather than one found by walking up from wherever
    pytest was started.
    """
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    environment["CLAUDE_PROJECT_DIR"] = str(WORKTREE_ROOT)
    return environment


def _blind_sh(verb, path):
    """Run one subcommand of the script over one path; return its exit status."""
    completed = subprocess.run(
        [str(BLIND_SH), verb, str(path.relative_to(WORKTREE_ROOT))],
        cwd=str(WORKTREE_ROOT),
        capture_output=True,
        text=True,
        env=_environment(),
        check=False,
    )
    return completed.returncode


def _status_class(status):
    """A status as a caller branches on it, rather than as a number to pin."""
    return "zero" if status == 0 else "non-zero"


class TheWritingVerbRepairsTheLaneFile(unittest.TestCase):
    """``format`` leaves the file repaired; ``test`` leaves it exactly as it was."""

    def lane_file(self, content):
        """A file of those bytes inside the lane, removed again when the test ends."""
        path = LANE_DIR / f"_fmt_probe_{uuid.uuid4().hex}.py"
        path.write_text(content)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_format_rewrites_the_file_where_test_leaves_the_same_bytes(self):
        # The two verbs over one file is the whole of it: a `format` that runs
        # the same gates in check mode and prints their complaint leaves the
        # writer exactly where `test` already left it, with the faults still in
        # the file and another round trip to the owner to get them out.
        under_format = self.lane_file(FIXABLE)
        under_test = self.lane_file(FIXABLE)
        _blind_sh("format", under_format)
        _blind_sh("test", under_test)
        observed = {"format": under_format.read_text(), "test": under_test.read_text()}
        assert observed == {"format": FORMATTED, "test": FIXABLE}

    def test_the_status_reports_what_the_gates_still_find_after_the_repair(self):
        # The status is the writer's only reading of whether it is done, so it
        # has to come from the gates rather than from the rewrite: a file that
        # still carries an undefined name after every repair is not a clean
        # file, however cleanly the last write of it went.
        unrepairable = _blind_sh("format", self.lane_file(UNREPAIRABLE))
        repaired = _blind_sh("format", self.lane_file(FIXABLE))
        observed = {
            "a fault the gates cannot repair": _status_class(unrepairable),
            "nothing left to find": _status_class(repaired),
        }
        assert observed == {
            "a fault the gates cannot repair": "non-zero",
            "nothing left to find": "zero",
        }


if __name__ == "__main__":
    unittest.main()
