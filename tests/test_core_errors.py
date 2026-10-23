# Copyright 2026 oh shit, gorillas!
"""Typed failure data from m1-core-records-design.md, typed product failures."""

import pytest

from gauntlet.core.causes import UnownedPath
from gauntlet.core.causes import UnownedPathError as CauseUnownedPathError
from gauntlet.core.errors import (
    CapabilityError,
    ConfigError,
    GauntletError,
    RecordError,
    RecoveryError,
    StateError,
    StorageError,
    UnownedPathError,
)


def test_unowned_path_preserves_path_and_product_hierarchy() -> None:
    """Breaks when the path changes or the product exception parent is lost."""
    path = " ./módules/worker.py "
    error = UnownedPathError(path)
    assert error.path == path
    assert isinstance(error, GauntletError)
    assert issubclass(GauntletError, Exception)


def test_record_error_preserves_location_reason_and_product_hierarchy() -> None:
    """Breaks when record failures alter data or leave the product hierarchy."""
    location = "state.pending[2].dispatch"
    reason = " supplied reason\nwith detail "
    error = RecordError(location, reason)
    assert (error.location, error.reason) == (location, reason)
    assert isinstance(error, GauntletError)


def test_config_error_preserves_key_reason_and_product_hierarchy() -> None:
    """Breaks when configuration failures alter data or lose their parent."""
    key = " roles.réviewer.command "
    reason = " supplied configuration reason "
    error = ConfigError(key, reason)
    assert (error.key, error.reason) == (key, reason)
    assert isinstance(error, GauntletError)


def test_state_error_preserves_effect_reason_and_product_hierarchy() -> None:
    """Breaks when state failures alter data or lose their product parent."""
    effect = "effect-17"
    reason = " supplied state reason\n "
    error = StateError(effect, reason)
    assert (error.effect, error.reason) == (effect, reason)
    assert isinstance(error, GauntletError)


@pytest.mark.parametrize("number", [None, 13])
def test_storage_error_preserves_path_operation_errno_and_hierarchy(
    number: int | None,
) -> None:
    """Breaks when storage failures default errno, alter data or lose parent."""
    path = " .gauntlet/jobs/étude/state.json "
    operation = " supplied operation "
    error = StorageError(path, operation, number)
    assert (error.path, error.operation, error.errno) == (path, operation, number)
    assert isinstance(error, GauntletError)


@pytest.mark.parametrize("effects", [(), ("effect-z", "effect-a", "effect-z")])
def test_recovery_error_preserves_effects_reason_and_product_hierarchy(
    effects: tuple[str, ...],
) -> None:
    """Breaks when recovery sorts or deduplicates effects, or alters its data."""
    reason = " supplied recovery reason "
    error = RecoveryError(effects, reason)
    assert (error.effects, error.reason) == (effects, reason)
    assert isinstance(error, GauntletError)


def test_capability_error_preserves_operation_and_product_hierarchy() -> None:
    """Breaks when capability failures alter operation or lose product parent."""
    operation = " supplied capability "
    error = CapabilityError(operation)
    assert error.operation == operation
    assert isinstance(error, GauntletError)


def test_causes_unowned_path_names_are_the_product_error_class() -> None:
    """Breaks when causes keeps a distinct exception or a subclass alias."""
    aliases: tuple[type[Exception], ...] = (UnownedPath, CauseUnownedPathError)
    for alias in aliases:
        assert alias is UnownedPathError
