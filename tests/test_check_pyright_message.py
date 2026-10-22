"""Red tests for what a pyright gate finding carries.

Source: the quality gates design spec under docs/superpowers/specs/, "Gate code",
third bullet, applied to the pyright gate of "Types", second bullet.

A finding carries the checker's whole message, so text the test seeds into the
checked source, and which pyright repeats in its message, reaches the gate's
output. The documents name no stream, so stdout and stderr are read together.
"""

from pathlib import Path

import pytest

from gates.check_pyright import main

DEPRECATION_REASON = "replaced by fetch_fresh since release nine"

DEPRECATED_CALL = f'from typing_extensions import deprecated\n\n\n@deprecated("{DEPRECATION_REASON}")\ndef fetch_stale() -> None:\n    pass\n\n\nfetch_stale()\n'

FIRST_MISSING = "alpha_missing_quokka"

SECOND_MISSING = "beta_missing_pangolin"

TWO_UNDEFINED = f"print({FIRST_MISSING})\nprint({SECOND_MISSING})\n"


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "seeded.py"
    path.write_text(source, encoding="utf-8")
    return path


def _output(capsys: pytest.CaptureFixture[str]) -> str:
    captured = capsys.readouterr()
    return captured.out + captured.err


def test_carries_deprecation_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The reason pyright appends below its deprecation line is part of the whole message."""
    path = _seed(tmp_path, DEPRECATED_CALL)
    main([path])

    assert DEPRECATION_REASON in _output(capsys)


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(FIRST_MISSING, id="first"),
        pytest.param(SECOND_MISSING, id="second"),
    ],
)
def test_carries_each_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], name: str
) -> None:
    """Every undefined name pyright reports appears in the gate's output, not only the first."""
    path = _seed(tmp_path, TWO_UNDEFINED)
    main([path])

    assert name in _output(capsys)
