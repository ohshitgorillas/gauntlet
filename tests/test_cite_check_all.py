"""Behavior tests for the `--check-all` mode of the citation resolver CLI."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "cite.py"

FIXTURES = "tests/support/fixtures/cite"
ALPHA = FIXTURES + "/alpha.txt"
BETA = FIXTURES + "/beta.txt"


def _check_all(tmp_path, **bodies):
    """Write one document per `name: body` kwarg and run `--check-all` over
    all of them, in the order given. Gives the finished subprocess and a map
    of name to the document path written for it."""
    docs = {}
    for name, body in bodies.items():
        doc = tmp_path / (name + ".md")
        doc.write_text(body)
        docs[name] = doc
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--check-all", *[str(p) for p in docs.values()]],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    return done, docs


def test_check_all_exits_0_when_every_document_passes(tmp_path):
    done, _ = _check_all(
        tmp_path,
        one="The rule is at `" + ALPHA + ":1` today.\n",
        two="The guard is at `" + BETA + ":1` today.\n",
    )
    assert done.returncode == 0


def test_check_all_exits_1_when_any_document_fails(tmp_path):
    done, _ = _check_all(
        tmp_path,
        one="The rule is at `" + ALPHA + ":1` today.\n",
        two="The guard is at `" + ALPHA + ":9` today.\n",
    )
    assert done.returncode == 1


def test_check_all_prefixes_a_failing_row_with_its_document(tmp_path):
    done, docs = _check_all(
        tmp_path,
        one="The rule is at `" + ALPHA + ":1` today.\n",
        two="The guard is at `" + ALPHA + ":9` today.\n",
    )
    assert f'{docs["two"]}: RANGE' in done.stdout


def test_check_all_a_passing_document_contributes_no_rows(tmp_path):
    done, docs = _check_all(
        tmp_path,
        one="The rule is at `" + ALPHA + ":1` today.\n",
        two="The guard is at `" + ALPHA + ":9` today.\n",
    )
    assert str(docs["one"]) not in done.stdout


def test_check_all_resolves_a_document_against_its_own_checkout(tmp_path):
    root = tmp_path / "checkout"
    (root / ".git").mkdir(parents=True)
    (root / "target.md").write_text("only line here\n")
    doc = root / "plan.md"
    doc.write_text("The rule is at `target.md:1` today.\n")

    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--check-all", str(doc)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)

    assert done.returncode == 0


def test_check_all_resolves_a_plugin_root_citation_against_the_scripts_own_checkout(tmp_path):
    consumer = tmp_path / "consumer"
    (consumer / ".git").mkdir(parents=True)
    doc = consumer / "plan.md"
    doc.write_text("The rule shape is at `${CLAUDE_PLUGIN_ROOT}/" + ALPHA + ":1` today.\n")

    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--check-all", str(doc)],
        cwd=consumer,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)

    assert done.returncode == 0


def test_check_all_with_no_document_fails_outside_a_checkout(tmp_path):
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--check-all"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert done.returncode != 0
