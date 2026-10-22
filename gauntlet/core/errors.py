# Copyright 2026 oh shit, gorillas!
"""Define typed product failures and their original data."""


class GauntletError(Exception):
    """Represent a product failure."""


class UnownedPathError(GauntletError):
    """Report a path without a designated owner."""

    path: str

    def __init__(self, path: str) -> None:
        """Keep the exact path without an owner."""
        super().__init__(path)
        self.path = path


class RecordError(GauntletError):
    """Report invalid record data at its location."""

    location: str
    reason: str

    def __init__(self, location: str, reason: str) -> None:
        """Keep the invalid record location and explanation."""
        super().__init__(location, reason)
        self.location = location
        self.reason = reason


class ConfigError(GauntletError):
    """Report an invalid configuration key."""

    key: str
    reason: str

    def __init__(self, key: str, reason: str) -> None:
        """Keep the invalid key and explanation."""
        super().__init__(key, reason)
        self.key = key
        self.reason = reason


class StateError(GauntletError):
    """Report invalid state for an effect."""

    effect: str
    reason: str

    def __init__(self, effect: str, reason: str) -> None:
        """Keep the affected operation and explanation."""
        super().__init__(effect, reason)
        self.effect = effect
        self.reason = reason


class StorageError(GauntletError):
    """Report a failed storage operation."""

    path: str
    operation: str
    errno: int | None

    def __init__(self, path: str, operation: str, errno: int | None) -> None:
        """Keep the failed storage request and original error number."""
        super().__init__(path, operation, errno)
        self.path = path
        self.operation = operation
        self.errno = errno


class RecoveryError(GauntletError):
    """Report contradictory recovery evidence for effects."""

    effects: tuple[str, ...]
    reason: str

    def __init__(self, effects: tuple[str, ...], reason: str) -> None:
        """Keep the ordered recovery effects and explanation."""
        super().__init__(effects, reason)
        self.effects = effects
        self.reason = reason


class CapabilityError(GauntletError):
    """Report an unavailable operation."""

    operation: str

    def __init__(self, operation: str) -> None:
        """Keep the unavailable operation."""
        super().__init__(operation)
        self.operation = operation
