# Copyright 2026 oh shit, gorillas!
"""`startable` in `gauntlet/core/schedule.py`.

Spec: docs/superpowers/specs/structure-first-design.md, `gauntlet/core/schedule.py`.
Plan: docs/superpowers/plans/structure-first-plan.md, C2e and open question 5.
"""

from gauntlet.core.schedule import startable


def test_two_disjoint_pieces_both_start_in_order() -> None:
    """Breaks when disjoint pieces are serialized, or the result leaves input order."""
    order = [("s2", frozenset({"pkg/b.py"})), ("s1", frozenset({"pkg/a.py"}))]
    assert startable(order, (), (), ()) == ("s2", "s1")


def test_of_two_overlapping_pieces_only_the_first_starts() -> None:
    """Breaks when an earlier piece not done stops blocking a later overlapping one."""
    order = [
        ("s1", frozenset({"pkg/a.py", "pkg/c.py"})),
        ("s2", frozenset({"pkg/b.py", "pkg/c.py"})),
    ]
    assert startable(order, (), (), ()) == ("s1",)


def test_an_empty_order_gives_nothing() -> None:
    """Breaks when names are given for an empty order."""
    assert startable((), (), (), ()) == ()


def test_a_done_piece_is_not_given_and_does_not_block() -> None:
    """Breaks when done pieces are returned, or a done earlier piece still blocks."""
    order = [("s1", frozenset({"pkg/a.py"})), ("s2", frozenset({"pkg/a.py"}))]
    assert startable(order, {"s1"}, (), ()) == ("s2",)


def test_a_running_piece_is_not_given_and_blocks_overlapping_pieces() -> None:
    """Breaks when running pieces are returned, or a running piece stops blocking."""
    order = [
        ("s1", frozenset({"pkg/a.py"})),
        ("s2", frozenset({"pkg/a.py", "pkg/b.py"})),
        ("s3", frozenset({"pkg/c.py"})),
    ]
    assert startable(order, (), {"s1"}, ()) == ("s3",)


def test_a_later_running_piece_blocks_an_earlier_overlapping_one() -> None:
    """Breaks when only earlier pieces, not every running one, are checked."""
    order = [
        ("s1", frozenset({"pkg/a.py"})),
        ("s2", frozenset({"pkg/a.py"})),
        ("s3", frozenset({"pkg/b.py"})),
    ]
    assert startable(order, (), {"s2"}, ()) == ("s3",)


def test_a_held_path_stops_only_the_pieces_holding_it() -> None:
    """Breaks when held paths are ignored, or a held path stops disjoint pieces."""
    order = [
        ("s1", frozenset({"pkg/a.py"})),
        ("s2", frozenset({"pkg/b.py"})),
        ("s3", frozenset({"pkg/c.py"})),
    ]
    assert startable(order, (), (), {"pkg/b.py"}) == ("s1", "s3")


def test_a_piece_waiting_on_a_held_path_still_blocks_later_overlapping_pieces() -> None:
    """Breaks when a held earlier piece not done stops counting as an earlier piece."""
    order = [
        ("s1", frozenset({"pkg/a.py", "pkg/b.py"})),
        ("s2", frozenset({"pkg/b.py"})),
        ("s3", frozenset({"pkg/c.py"})),
    ]
    assert startable(order, (), (), {"pkg/a.py"}) == ("s3",)


def test_a_running_name_absent_from_order_adds_no_files() -> None:
    """Breaks when an unknown running name is taken as holding files or none."""
    order = [("s1", frozenset({"pkg/a.py"})), ("s2", frozenset({"pkg/b.py"}))]
    assert startable(order, (), {"ghost"}, ()) == ("s1", "s2")


def test_an_empty_piece_alone_starts() -> None:
    """Breaks when an empty file set never starts, even with nothing to overlap."""
    assert startable([("s1", frozenset[str]())], (), (), ()) == ("s1",)


def test_an_empty_piece_first_blocks_every_later_piece() -> None:
    """Breaks when an empty file set overlaps nothing."""
    order = [("s1", frozenset[str]()), ("s2", frozenset({"pkg/b.py"}))]
    assert startable(order, (), (), ()) == ("s1",)


def test_an_empty_piece_waits_on_an_earlier_piece_not_done() -> None:
    """Breaks when an empty file set is checked by plain intersection."""
    order = [("s1", frozenset({"pkg/a.py"})), ("s2", frozenset[str]())]
    assert startable(order, (), (), ()) == ("s1",)


def test_an_empty_piece_waits_on_any_held_path() -> None:
    """Breaks when an empty file set does not overlap every held path."""
    order = [("s1", frozenset[str]())]
    assert startable(order, (), (), {"pkg/z.py"}) == ()


def test_a_running_empty_piece_blocks_every_other_piece() -> None:
    """Breaks when a running piece with no declared files overlaps nothing."""
    order = [
        ("s1", frozenset({"pkg/a.py"})),
        ("s2", frozenset[str]()),
        ("s3", frozenset({"pkg/c.py"})),
    ]
    assert startable(order, (), {"s2"}, ()) == ()
