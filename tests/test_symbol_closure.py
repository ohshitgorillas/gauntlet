"""Behavior tests for the symbol-closure fact reporter CLI."""

import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent / "scripts" / "gates" / "symbol-closure.py"
)

IMPORTS_AND_CALLS_ALPHA = "from pkg import alpha\n\n\ndef test_it():\n    alpha()\n"


def _tree(root, files):
    """Write `files` under `root` beside an empty anchor; give the anchor path."""
    anchor = root / "tests" / "__init__.py"
    anchor.parent.mkdir(parents=True, exist_ok=True)
    anchor.write_text("")
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return anchor


def _closure(anchor, symbols):
    """The stdout path list of one run over the tree `anchor` sits in."""
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--symbols-stdin", str(anchor)],
        input="".join(symbol + "\n" for symbol in symbols),
        capture_output=True,
        text=True,
    )
    sys.stderr.write(done.stderr)
    return done.stdout.splitlines()


# 1
def test_a_bare_reference_with_no_import_of_its_own_reaches_the_closure(tmp_path):
    anchor = _tree(tmp_path, {"tests/test_one.py": IMPORTS_AND_CALLS_ALPHA})
    other = tmp_path / "tests" / "test_two.py"

    other.write_text("import beta\n\n\ndef test_two():\n    beta()\n")
    other_names_another_symbol = _closure(anchor, ["alpha"])

    other.write_text("def test_two():\n    alpha()\n")
    other_calls_the_symbol_unimported = _closure(anchor, ["alpha"])

    assert (other_names_another_symbol, other_calls_the_symbol_unimported) == (
        ["tests/test_one.py"],
        ["tests/test_one.py", "tests/test_two.py"],
    )


# 2
def test_the_closure_takes_one_hop_through_support_and_stops(tmp_path):
    anchor = _tree(
        tmp_path,
        {
            "tests/support/helper.py": (
                "from pkg import alpha\n"
                "\n"
                "\n"
                "def build_thing():\n"
                "    return alpha()\n"
            ),
            "tests/test_uses_helper.py": (
                "from support.helper import build_thing\n"
                "\n"
                "\n"
                "def test_uses_helper():\n"
                "    build_thing()\n"
            ),
        },
    )
    far = tmp_path / "tests" / "test_far.py"

    far.write_text(
        "from test_uses_helper import other_thing\n"
        "\n"
        "\n"
        "def test_far():\n"
        "    other_thing()\n"
    )
    far_ties_to_a_test_file = _closure(anchor, ["alpha"])

    far.write_text(
        "from support.helper import build_thing\n"
        "\n"
        "\n"
        "def test_far():\n"
        "    build_thing()\n"
    )
    far_ties_to_the_helper = _closure(anchor, ["alpha"])

    assert (far_ties_to_a_test_file, far_ties_to_the_helper) == (
        ["tests/support/helper.py", "tests/test_uses_helper.py"],
        [
            "tests/support/helper.py",
            "tests/test_far.py",
            "tests/test_uses_helper.py",
        ],
    )


# 3
def test_a_file_binding_the_name_itself_is_still_reported(tmp_path):
    anchor = _tree(tmp_path, {"tests/test_one.py": IMPORTS_AND_CALLS_ALPHA})
    collide = tmp_path / "tests" / "test_collide.py"

    collide.write_text(
        "def alpha(x, y):\n"
        "    return x + y\n"
        "\n"
        "\n"
        "def test_collide():\n"
        "    alpha(1, 2, 3)\n"
    )
    collide_binds_the_symbols_name = _closure(anchor, ["alpha"])

    collide.write_text(
        "def gamma(x, y):\n"
        "    return x + y\n"
        "\n"
        "\n"
        "def test_collide():\n"
        "    gamma(1, 2, 3)\n"
    )
    collide_binds_another_name = _closure(anchor, ["alpha"])

    assert (collide_binds_the_symbols_name, collide_binds_another_name) == (
        ["tests/test_collide.py", "tests/test_one.py"],
        ["tests/test_one.py"],
    )


# 4
def test_an_unparseable_file_costs_only_itself(tmp_path):
    anchor = _tree(tmp_path, {"tests/test_good.py": IMPORTS_AND_CALLS_ALPHA})
    broken = tmp_path / "tests" / "test_broken.py"

    broken.write_text("def f(:\n")
    the_file_does_not_parse = _closure(anchor, ["alpha"])

    broken.write_text(IMPORTS_AND_CALLS_ALPHA)
    the_file_parses_and_uses_the_symbol = _closure(anchor, ["alpha"])

    assert (the_file_does_not_parse, the_file_parses_and_uses_the_symbol) == (
        ["tests/test_good.py"],
        ["tests/test_broken.py", "tests/test_good.py"],
    )
