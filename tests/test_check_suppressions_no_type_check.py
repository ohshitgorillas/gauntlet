# Copyright 2026 oh shit, gorillas!
"""Red tests for the suppression gate's ban on `typing.no_type_check` and `typing.no_type_check_decorator`.

Sources: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item (a `@typing.no_type_check` decorator; the ban is on the function, not its
spelling: it covers `typing.no_type_check` and `typing.no_type_check_decorator` under
every name they are imported by, `typing_extensions` included, whether used as a
decorator or called; a file the gate can tokenize but `ast.parse` under the pinned
Python cannot parse is a file the gate did not finish, and the gate exits 2) and
"Gates" (exit 1 with one or more findings, 2 when the checker could not finish,
whatever it found in the other files).
"""

from pathlib import Path

import pytest

from gates.check_suppressions import main
from gates.core.project import Source
from gates.core.report import Unfinished
from gates.core.source import parse
from tests.support.suppressions import find_suppressions

FINDINGS_STATUS = 1
PINNED = (3, 12)

UNFINISHED_STATUS = 2

DECORATED_SOURCES = [
    (
        "from typing import no_type_check\n\n\n@no_type_check\ndef seeded() -> None:\n    pass\n",
        4,
    ),
    (
        "from typing import no_type_check as unchecked\n\n\n@unchecked\ndef seeded() -> None:\n    pass\n",
        4,
    ),
    ("import typing as t\n\n\n@t.no_type_check\ndef seeded() -> None:\n    pass\n", 4),
    ("from typing import *\n\n\n@no_type_check\ndef seeded() -> None:\n    pass\n", 4),
    ("import typing\n\n\n@typing.no_type_check\nclass Seeded:\n    pass\n", 4),
    (
        "from typing import no_type_check\n\n\nclass Seeded:\n    @no_type_check\n    def run(self) -> None:\n        pass\n",
        5,
    ),
]

EXTENSIONS_SOURCES = [
    (
        "import typing_extensions\n\n\n@typing_extensions.no_type_check\ndef seeded() -> None:\n    pass\n",
        4,
    ),
    (
        "from typing_extensions import no_type_check as loose\n\n\n@loose\ndef seeded() -> None:\n    pass\n",
        4,
    ),
    (
        "import typing_extensions as te\n\n\n@te.no_type_check\ndef seeded() -> None:\n    pass\n",
        4,
    ),
]

DECORATOR_FACTORY_SOURCES = [
    (
        "import typing\n\n\n@typing.no_type_check_decorator\ndef wrap(func):\n    return func\n",
        4,
    ),
    (
        "from typing import no_type_check_decorator as nocheck\n\n\n@nocheck\ndef wrap(func):\n    return func\n",
        4,
    ),
    (
        "import typing_extensions as te\n\n\n@te.no_type_check_decorator\ndef wrap(func):\n    return func\n",
        4,
    ),
]

CALLED_SOURCES = [
    (
        "import typing\n\n\ndef seeded() -> None:\n    pass\n\n\nunchecked = typing.no_type_check(seeded)\n",
        8,
    ),
    (
        "from typing import no_type_check as loose\n\n\ndef seeded() -> None:\n    pass\n\n\nunchecked = loose(seeded)\n",
        8,
    ),
    (
        "import typing_extensions\n\n\ndef wrap(func):\n    return func\n\n\nnocheck = typing_extensions.no_type_check_decorator(wrap)\n",
        8,
    ),
    (
        "from typing import no_type_check_decorator\n\n\ndef wrap(func):\n    return func\n\n\nnocheck = no_type_check_decorator(wrap)\n",
        8,
    ),
]

LOOKALIKE_SOURCES = [
    "value = 1  # fmt: skip\n\n\ndef no_type_check(func):\n    return func\n\n\n@no_type_check\ndef seeded() -> None:\n    pass\n",
    "value = 1  # fmt: skip\nfrom helpers import no_type_check\n\n\n@no_type_check\ndef seeded() -> None:\n    pass\n",
    "value = 1  # fmt: skip\nimport helpers\n\n\n@helpers.no_type_check\ndef seeded() -> None:\n    pass\n",
    "value = 1  # fmt: skip\nimport typing\n\n\n@typing.final\nclass Seeded:\n    pass\n",
    'value = 1  # fmt: skip\n\n\ndef seeded() -> None:\n    """Unlike typing.no_type_check, keep every check."""\n',
]

UNPARSEABLE_SOURCES = [
    "value = = 1\n",
    "class = 1\n",
    "print 'legacy'\n",
    "value = = 1  # fmt: skip\n",
]

FINDING_SOURCE = (
    "import typing\n\n\n@typing.no_type_check\ndef seeded() -> None:\n    pass\n"
)


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "use_line"), DECORATED_SOURCES)
def test_gate_flags_no_type_check_under_any_imported_name(
    tmp_path: Path, source: str, use_line: int
) -> None:
    """Exit with the findings status on typing.no_type_check decorating a def, class or method, whatever name it was imported by, and report the decorator line."""
    path = _seed(tmp_path, "decorated.py", source)

    assert (
        main([path]),
        use_line in [finding.line for finding in find_suppressions(path)],
    ) == (FINDINGS_STATUS, True)


@pytest.mark.parametrize(("source", "use_line"), EXTENSIONS_SOURCES)
def test_gate_flags_no_type_check_from_typing_extensions(
    tmp_path: Path, source: str, use_line: int
) -> None:
    """Exit with the findings status on typing_extensions.no_type_check, whatever name it was imported by, and report the decorator line."""
    path = _seed(tmp_path, "extensions.py", source)

    assert (
        main([path]),
        use_line in [finding.line for finding in find_suppressions(path)],
    ) == (FINDINGS_STATUS, True)


@pytest.mark.parametrize(("source", "use_line"), DECORATOR_FACTORY_SOURCES)
def test_gate_flags_no_type_check_decorator(
    tmp_path: Path, source: str, use_line: int
) -> None:
    """Exit with the findings status on no_type_check_decorator from typing or typing_extensions, and report the decorator line."""
    path = _seed(tmp_path, "factory.py", source)

    assert (
        main([path]),
        use_line in [finding.line for finding in find_suppressions(path)],
    ) == (FINDINGS_STATUS, True)


@pytest.mark.parametrize(("source", "use_line"), CALLED_SOURCES)
def test_gate_flags_no_type_check_called_as_a_function(
    tmp_path: Path, source: str, use_line: int
) -> None:
    """Exit with the findings status on no_type_check or no_type_check_decorator called rather than used as a decorator, and report the call line."""
    path = _seed(tmp_path, "called.py", source)

    assert (
        main([path]),
        use_line in [finding.line for finding in find_suppressions(path)],
    ) == (FINDINGS_STATUS, True)


@pytest.mark.parametrize("source", LOOKALIKE_SOURCES)
def test_name_that_is_not_the_typing_function_is_no_finding(
    tmp_path: Path, source: str
) -> None:
    """Report only the seeded comment, not a decorator spelled no_type_check that is not the typing function, nor a mention in a string."""
    path = _seed(tmp_path, "lookalike.py", source)

    assert [finding.line for finding in find_suppressions(path)] == [1]


@pytest.mark.parametrize("source", UNPARSEABLE_SOURCES)
def test_gate_exits_unfinished_on_file_it_cannot_parse(
    tmp_path: Path, source: str
) -> None:
    """Exit with the unfinished status on a file that tokenizes but does not parse, a comment marker in it included."""
    path = _seed(tmp_path, "broken.py", source)

    assert main([path]) == UNFINISHED_STATUS


@pytest.mark.parametrize("broken_first", [True, False])
def test_gate_exits_unfinished_whatever_it_found_in_other_files(
    tmp_path: Path, *, broken_first: bool
) -> None:
    """Exit with the unfinished status when one file does not parse and another carries a finding."""
    broken = _seed(tmp_path, "broken.py", "value = = 1\n")
    flagged = _seed(tmp_path, "flagged.py", FINDING_SOURCE)
    paths = [broken, flagged] if broken_first else [flagged, broken]

    assert main(paths) == UNFINISHED_STATUS


def test_parse_names_the_file_it_cannot_parse_as_unfinished(tmp_path: Path) -> None:
    """Return the file that does not parse as unfinished, naming its path."""
    path = _seed(tmp_path, "broken.py", "value = = 1  # fmt: skip\n")
    result = parse(Source(given=path, absolute=path), PINNED)

    assert isinstance(result, Unfinished)
    assert result.text.startswith(f"{path}: ")
