# Copyright 2026 oh shit, gorillas!
"""Hold the design record and what makes it valid."""

from collections import Counter
from collections.abc import Collection, Sequence
from dataclasses import dataclass

from gauntlet.core.verdicts import Anchor

_MAX_PATHS = 5
_MAX_CHOICES = 5


@dataclass(frozen=True)
class Stub:
    """Record one public name a design stubs."""

    name: str  # the public name, e.g. "Clock.now"
    text: str  # signature and a body that only raises


@dataclass(frozen=True)
class Module:
    """Record one module of a design."""

    path: str
    job: str  # one line
    stubs: tuple[Stub, ...]
    replaces: tuple[Anchor, ...]  # each copy this module's arrival purges


@dataclass(frozen=True)
class Home:
    """Record the one module a shared concern lives in."""

    concern: str  # e.g. "process running"
    module: str  # a Module.path of this design
    forbids: str  # what no other module writes


@dataclass(frozen=True)
class Step:
    """Record one step of a design's order."""

    name: str
    paths: tuple[str, ...]  # at most five
    implementer: str  # a role name


@dataclass(frozen=True)
class Choice:
    """Record one choice the owner rules."""

    question: str
    recommend: str
    alternative: str
    cost: str  # each side's cost; "unmeasured" where nobody measured it


@dataclass(frozen=True)
class Design:
    """Record a whole design."""

    modules: tuple[Module, ...]
    homes: tuple[Home, ...]
    order: tuple[Step, ...]
    choices: tuple[Choice, ...]  # at most five; the owner rules each before approval


def design_problems(design: Design) -> tuple[str, ...]:
    """Return every broken design rule in the prescribed check order."""
    problems: list[str] = []
    concerns = Counter(home.concern for home in design.homes)
    problems.extend(
        f"concern {concern}: {count} homes"
        for concern, count in concerns.items()
        if count > 1
    )
    modules = Counter(module.path for module in design.modules)
    problems.extend(
        f"home {home.concern}: module {home.module} not in design"
        for home in design.homes
        if home.module not in modules
    )
    problems.extend(
        f"module {path}: defined {count} times"
        for path, count in modules.items()
        if count > 1
    )
    first_writes: dict[str, tuple[int, str]] = {}
    for index, step in enumerate(design.order):
        for path in step.paths:
            first_writes.setdefault(path, (index, step.name))
    problems.extend(
        f"module {path}: no step writes it"
        for path in modules
        if path not in first_writes
    )
    problems.extend(
        f"step {step.name}: {len(step.paths)} paths, at most five"
        for step in design.order
        if len(step.paths) > _MAX_PATHS
    )
    problems.extend(
        f"step {step.name}: no implementer"
        for step in design.order
        if not step.implementer.strip()
    )
    names = Counter(step.name for step in design.order)
    problems.extend(
        f"step {name}: named {count} times"
        for name, count in names.items()
        if count > 1
    )
    ports: dict[tuple[str, str, str], str] = {}
    for module in design.modules:
        if module.path in first_writes:
            index, first_name = first_writes[module.path]
            replaced = {anchor.path for anchor in module.replaces}
            for step in design.order[:index]:
                for path in step.paths:
                    if path in replaced:
                        ports.setdefault(
                            (step.name, path, module.path),
                            f"step {step.name}: writes {path} before step {first_name} writes {module.path}",
                        )
    problems.extend(ports.values())
    if len(design.choices) > _MAX_CHOICES:
        problems.append(f"choices: {len(design.choices)}, at most five")
    for choice in design.choices:
        for field, value in (
            ("recommend", choice.recommend),
            ("alternative", choice.alternative),
            ("cost", choice.cost),
        ):
            if not value.strip():
                problems.append(f"choice {choice.question}: no {field}")
    return tuple(problems)


def home_of(design: Design, concern: str) -> Home | None:
    """Return the first home for the exact concern, if present."""
    return next((home for home in design.homes if home.concern == concern), None)


def uncovered(
    design: Design, copies: Sequence[Anchor], done: Collection[str]
) -> tuple[Anchor, ...]:
    """Return distinct copies lacking a replacement and a pending port."""
    replaced = {anchor for module in design.modules for anchor in module.replaces}
    pending_paths = {
        path for step in design.order if step.name not in done for path in step.paths
    }
    return tuple(
        copy
        for copy in dict.fromkeys(copies, False)
        if copy not in replaced or copy.path not in pending_paths
    )
