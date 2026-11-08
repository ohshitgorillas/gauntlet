import hashlib

import pytest
from rounds_helpers import LEAD, PASS, READY, build, leading, profile, run_main
from shared_helpers import load

rounds = load("rounds")

SLUG = "item"
V1 = hashlib.sha256(b"item v1\n").hexdigest()
V2 = hashlib.sha256(b"item v2\n").hexdigest()
BENCH = "Verdict: APPROACH THE BENCH"
NONRESP = "Verdict: OBJECTION: NON-RESPONSIVE"

ENDED = [("round", 1), ("review", 1, READY), ("ruling", 1, "review", "approve")]

# Named file sets and what they leave owed. Nothing sets an item hash, so each run writes it.
SCENARIOS = {
    "empty": [],
    "filed": [("round", 1)],
    "passed": [("round", 1), ("review", 1, PASS)],
    "refiled": [("round", 1), ("review", 1, PASS), ("round", 2)],
    "ready": [("round", 1), ("review", 1, READY)],
    "revised": [("round", 1), ("review", 1, READY), ("ruling", 1, "review", "revise")],
    "ended": ENDED,
    "approved-over-ended": ENDED + [("approved",)],
    "ended-over-owner": ENDED + [("idle", 1)],
    "owner-over-reviewer": [("round", 1), ("idle", 1)],
    "twelve-leading-after-guard": leading(12) + [("guard", 5)],
}


@pytest.fixture
def hearing(tmp_path):
    item = tmp_path / "item.md"
    item.write_text("item v1\n")
    return tmp_path / "specs", item


NO_OVER = {}


def read_state(hearing, files, over=NO_OVER, **inputs):
    folder, item = hearing
    build(folder, SLUG, files)
    inputs = {"mode": "state", **inputs}
    return run_main(rounds, profile(rounds, folder, **over), items=item, **inputs)[2]


def field(hearing, files, name, over=NO_OVER, **inputs):
    return read_state(hearing, files, over, **inputs).get(name)


@pytest.mark.parametrize(
    "scenario, owed",
    [
        ("empty", "speccer"),
        ("filed", "arbiter"),
        ("passed", "speccer"),
        ("refiled", "arbiter"),
        ("ready", "owner"),
        ("revised", "speccer"),
        ("ended", "ended"),
        ("approved-over-ended", "approved"),
        ("ended-over-owner", "ended"),
        ("owner-over-reviewer", "owner"),
        ("twelve-leading-after-guard", "speccer"),
    ],
)
def test_owed_names_who_owes_the_round(hearing, scenario, owed):
    assert field(hearing, SCENARIOS[scenario], "owed") == owed


@pytest.mark.parametrize(
    "scenario, round_",
    [("empty", 1), ("filed", 1), ("passed", 2), ("refiled", 2), ("ready", 2), ("revised", 2)],
)
def test_round_is_the_latest_untried_round_or_the_next(hearing, scenario, round_):
    assert field(hearing, SCENARIOS[scenario], "round") == round_


def test_file_is_the_round_file_in_the_folder(hearing):
    assert field(hearing, SCENARIOS["passed"], "file") == f"{hearing[0]}/item.2.txt"


def test_slug_comes_from_the_item_file(hearing):
    assert field(hearing, [], "slug") == "item"


def test_uncited_plan_is_owed_to_the_author(hearing):
    assert field(hearing, [("round", 1), ("cite", 1, [["a | q | r"]])], "owed", over={"filed": rounds.cited, "author": "defense"}) == "defense"


def test_cited_plan_is_owed_to_the_reviewer(hearing):
    assert field(hearing, [("round", 1), ("cite", 1, [[]])], "owed", over={"filed": rounds.cited, "reviewer": "prosecutor"}) == "prosecutor"


@pytest.mark.parametrize(
    "files, start, expected",
    [
        (leading(3) + [("round", 4)], None, "a4"),
        (leading(11) + [("round", 12)], None, "a12"),
        (leading(2), None, "speccer"),
        (leading(12) + [("guard", 5)], None, "vacant"),
        (leading(12) + [("round", 13), ("guard", 5)], None, "vacant"),
        (leading(12) + [("guard", 5)], 10, "speccer"),
    ],
)
def test_next_names_the_author_a_slot_or_vacant(hearing, files, start, expected):
    inputs = {} if start is None else {"start": start}
    assert field(hearing, files, "next", **inputs) == expected


def test_next_is_never_vacant_without_a_retiring_verdict(hearing):
    assert field(hearing, leading(12) + [("guard", 5)], "next", over={"retire": None}) == "speccer"


@pytest.mark.parametrize(
    "files, name, expected",
    [
        ([], "start", 0),
        (SCENARIOS["passed"], "start", 1),
        ([("round", 1), ("review", 1, PASS), ("round", 2), ("review", 2, PASS)], "start", 2),
        ([], "base", 0),
        ([("iter", 3)], "base", 3),
        ([], "since", 0),
        ([("round", 1), ("review", 1, PASS), ("ruling", 1)], "since", 1),
        ([("ruling", 1), ("ruling", 4)], "since", 4),
    ],
)
def test_state_reads_start_base_and_since_from_the_files(hearing, files, name, expected):
    assert field(hearing, files, name) == expected


def test_start_is_echoed_inside_the_loop(hearing):
    assert field(hearing, SCENARIOS["passed"], "start", start=7) == 7


@pytest.mark.parametrize(
    "files, name, expected",
    [
        ([("round", 1), ("review", 1, PASS), ("round", 2), ("review", 2, BENCH)], "attempts", 2),
        ([("round", 1), ("review", 1, READY)], "attempts", 0),
        ([("round", 1), ("review", 1, PASS), ("round", 2), ("review", 2, PASS), ("ruling", 2), ("round", 3), ("review", 3, PASS)], "attempts", 1),
        ([("round", 1), ("review", 1, NONRESP), ("round", 2), ("review", 2, PASS)], "non_responsive", 1),
        ([("round", 1), ("review", 1, NONRESP), ("ruling", 1)], "non_responsive", 0),
    ],
)
def test_attempts_and_non_responsive_count_reviews_since_the_ruling(hearing, files, name, expected):
    assert field(hearing, files, name) == expected


TRIED_THREE = [("round", 1), ("review", 1, PASS), ("round", 2), ("review", 2, PASS), ("round", 3), ("review", 3, PASS)]


@pytest.mark.parametrize(
    "files, expected",
    [
        (TRIED_THREE, 3),
        (TRIED_THREE + [("guard", 2)], 2),
        (TRIED_THREE + [("ruling", 2)], 1),
        ([("round", 1), ("cite", 1, [["m"], ["m"]])], 2),
        (TRIED_THREE + [("round", 4), ("cite", 4, [["m"]])], 4),
    ],
)
def test_stretch_counts_tried_rounds_since_the_ruling_and_guard_plus_repairs(hearing, files, expected):
    assert field(hearing, files, "stretch") == expected


@pytest.mark.parametrize(
    "files, expected",
    [
        ([("round", 1)], 0),
        ([("round", 1), ("cite", 1, [["m"], [], ["m"], ["m"]])], 3),
        ([("round", 1), ("cite", 1, [["m"], ["m"], ["m"], ["m"]]), ("guard", 1, 3)], 1),
    ],
)
def test_repairs_count_marker_lines_past_the_last_guard_entry(hearing, files, expected):
    assert field(hearing, files, "repairs") == expected


def test_rulings_list_guard_files_before_the_ruling_of_the_same_round(hearing):
    folder = hearing[0]
    files = [("ruling", 2), ("guard", 2), ("ruling", 1), ("guard", 1)]
    expected = [f"{folder}/item.guard.1.txt", f"{folder}/item.ruling.1.txt", f"{folder}/item.guard.2.txt", f"{folder}/item.ruling.2.txt"]
    assert field(hearing, files, "rulings") == expected


def test_review_is_the_path_of_the_latest_review(hearing):
    files = [("round", 1), ("review", 1, PASS), ("round", 2), ("review", 2, READY)]
    assert field(hearing, files, "review") == f"{hearing[0]}/item.review.2.txt"


@pytest.mark.parametrize("name, expected", [("review", ""), ("verdict", "")])
def test_review_and_verdict_are_empty_without_a_review(hearing, name, expected):
    assert field(hearing, [("round", 1)], name) == expected


@pytest.mark.parametrize(
    "line, extra, expected",
    [
        ("Verdict: READY", (), "READY"),
        ("**Verdict:** READY", (), "READY"),
        ("# _Verdict_: `READY`", (), "READY"),
        ("verdict: ready", (), "READY"),
        ("Verdict: ANOTHER PASS - repair the quoted text", (), "ANOTHER PASS"),
        ("Verdict: OBJECTION: LEADING", (), "OBJECTION: LEADING"),
        ("Verdict: READY WITH NOTES", ("READY WITH NOTES",), "READY WITH NOTES"),
        ("Verdict: READY WITH NOTES", (), "READY"),
        ("Verdict: MAYBE", (), ""),
        ("READY", (), ""),
    ],
)
def test_verdict_is_the_longest_known_name_after_verdict(hearing, line, extra, expected):
    over = {"verdicts": profile(rounds, ".").verdicts + extra}
    assert field(hearing, [("round", 1), ("review", 1, line)], "verdict", over=over) == expected


# first: several hearings share one folder
EARLIER = [("round", n) for n in (1, 2, 3)] + [("review", n, PASS) for n in (1, 2, 3)] + [("ruling", 3, "review", "approve")]


def hear_from(hearing, files, first):
    folder, item = hearing
    build(folder, SLUG, files)
    return rounds.state(profile(rounds, folder), SLUG, None, first=first)


@pytest.mark.parametrize(
    "name, expected",
    [("round", 4), ("owed", "speccer"), ("attempts", 0), ("since", 0), ("stretch", 0), ("start", 0)],
)
def test_first_ignores_the_earlier_hearings_files(hearing, name, expected):
    assert hear_from(hearing, EARLIER, 4).get(name) == expected


def test_first_hears_the_later_hearing_in_the_same_folder(hearing):
    later = EARLIER + [("round", 4), ("review", 4, READY)]
    assert hear_from(hearing, later, 4).get("owed") == "owner"


def test_first_counts_attempts_from_the_later_hearing_only(hearing):
    later = EARLIER + [("round", 4), ("review", 4, PASS)]
    assert hear_from(hearing, later, 4).get("attempts") == 1


# the item hash and the set-aside
def lines(path):
    return path.read_text().splitlines()


def test_first_run_writes_the_item_hash(hearing):
    read_state(hearing, [])
    assert (hearing[0] / "item.items.sha256").read_text().strip() == V1


def test_unchanged_item_keeps_every_file_in_place(hearing):
    read_state(hearing, [("hash", V1), ("round", 1)])
    assert (hearing[0] / "item.1.txt").exists()


def test_the_hash_is_left_alone_inside_the_loop(hearing):
    read_state(hearing, [("hash", V2)], start=0)
    assert (hearing[0] / "item.items.sha256").read_text().strip() == V2


@pytest.fixture
def changed(hearing):
    folder, item = hearing
    build(
        folder,
        SLUG,
        [("hash", V2), ("round", 1), ("review", 1), ("approved",), ("put", "approved/item.rev2.txt"), ("summary", 1), ("put", "approved/item-summary.md"), ("put", "item-two.1.txt")],
    )
    run_main(rounds, profile(rounds, folder), mode="state", items=item)
    return folder, item


@pytest.mark.parametrize(
    "relative",
    ["item.1.txt", "item.review.1.txt", "item-summary.1.md", "approved/item.txt", "approved/item.rev2.txt", "approved/item-summary.md"],
)
def test_changed_item_sets_the_slugs_files_aside_keeping_the_layout(changed, relative):
    assert (changed[0] / "stale" / "item.1" / relative).exists()


def test_changed_item_leaves_only_other_slugs_files_and_the_new_hash_in_place(changed):
    folder = changed[0]
    left = sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file() and "stale" not in p.parts)
    assert left == ["item-two.1.txt", "item.items.sha256"]


def test_changed_item_writes_the_new_hash(changed):
    assert (changed[0] / "item.items.sha256").read_text().strip() == V1


def test_changed_item_is_heard_from_round_one(hearing):
    folder, item = hearing
    build(folder, SLUG, [("hash", V2), ("round", 1), ("review", 1, READY)])
    assert run_main(rounds, profile(rounds, folder), mode="state", items=item)[2].get("round") == 1


def test_a_second_change_takes_the_next_free_stale_number(changed):
    folder, item = changed
    build(folder, SLUG, [("round", 1)])
    item.write_text("item v3\n")
    run_main(rounds, profile(rounds, folder), mode="state", items=item)
    assert (folder / "stale" / "item.2" / "item.1.txt").exists()


# filing
def test_filing_appends_one_iteration_line(hearing):
    read_state(hearing, [("iter", 2)], mode="filing", start=0)
    assert len(lines(hearing[0] / "item.iter.txt")) == 3


def test_filing_starts_the_iteration_file(hearing):
    folder, item = hearing
    build(folder, SLUG, [])
    run_main(rounds, profile(rounds, folder), mode="filing", items=item, start=0)
    assert len(lines(folder / "item.iter.txt")) == 1


def test_state_appends_no_iteration_line(hearing):
    read_state(hearing, [("iter", 2)], start=0)
    assert len(lines(hearing[0] / "item.iter.txt")) == 2


def test_filing_prints_the_state(hearing):
    folder, item = hearing
    build(folder, SLUG, SCENARIOS["passed"])
    assert run_main(rounds, profile(rounds, folder), mode="filing", items=item, start=0)[2].get("owed") == "speccer"


# cited
@pytest.mark.parametrize(
    "cite_lines, expected",
    [
        (None, False),
        ([[]], True),
        ([["a | q | r"]], False),
        ([[], ["a | q | r"]], False),
        ([["a | q | r"], []], True),
    ],
)
def test_cited_reads_the_latest_cite_line(tmp_path, cite_lines, expected):
    if cite_lines is not None:
        build(tmp_path, SLUG, [("cite", 1, cite_lines)])
    assert rounds.cited(str(tmp_path), SLUG, 1) is expected
