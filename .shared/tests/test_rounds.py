import hashlib
import json

import pytest
from rounds_helpers import LEAD, PASS, READY, build, leading, profile, run_main, tried
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
        (leading(3) + [("round", 4)], 0, "a4"),
        (leading(11) + [("round", 12)], 0, "a12"),
        (leading(2), 0, "speccer"),
        (leading(12) + [("guard", 5)], 0, "vacant"),
        (leading(12) + [("round", 13), ("guard", 5)], 0, "vacant"),
        (leading(12) + [("guard", 5)], 10, "speccer"),
    ],
)
def test_next_names_the_author_a_slot_or_vacant(hearing, files, start, expected):
    assert field(hearing, files, "next", start=start) == expected


def test_next_is_never_vacant_without_a_retiring_verdict(hearing):
    assert field(hearing, leading(12) + [("guard", 5)], "next", over={"retire": None}, start=0) == "speccer"


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


# docket, screen, record and close
SCREENED = "Verdict: SCREENED"
INVALID = "Verdict: INVALID"
MAYBE = "Verdict: MAYBE"
NR_TWICE = [("round", 1), ("review", 1, NONRESP), ("round", 2), ("review", 2, NONRESP)]
READY_AT_6 = tried(5) + [("round", 6), ("review", 6, READY)]


def call(hearing, files, mode, over=NO_OVER, **inputs):
    folder, item = hearing
    build(folder, SLUG, files)
    return run_main(rounds, profile(rounds, folder, **over), mode=mode, items=item, **{"start": 0, "base": 0, **inputs})


def asked(hearing, files, name, over=NO_OVER, **inputs):
    return call(hearing, files, "docket", over, **inputs)[2].get(name)


@pytest.mark.parametrize(
    "files, base, case",
    [
        (leading(12), 0, "vacant"),
        (ENDED, 0, "none"),
        (ENDED + [("iter", 200)], 0, "none"),
        (SCENARIOS["ready"], 0, "review"),
        (tried(1, INVALID), 0, "invalid"),
        (tried(1, BENCH), 0, "bench"),
        (SCENARIOS["revised"], 0, "none"),
        (READY_AT_6, 0, "review"),
        (tried(1, MAYBE), 0, "unknown"),
        (tried(5) + [("round", 6), ("review", 6, MAYBE)], 0, "unknown"),
        (tried(4), 0, "none"),
        (tried(5), 0, "deadlock"),
        (tried(5) + [("round", 6), ("review", 6, NONRESP), ("round", 7), ("review", 7, NONRESP)], 0, "deadlock"),
        (NR_TWICE[:2], 0, "none"),
        (NR_TWICE, 0, "non-responsive"),
        (tried(11, SCREENED), 0, "none"),
        (tried(12, SCREENED), 0, "guard"),
        ([("round", 1), ("cite", 1, [["m"]] * 4)], 0, "none"),
        ([("round", 1), ("cite", 1, [["m"]] * 5)], 0, "guard"),
        ([("iter", 199)], 0, "none"),
        ([("iter", 200)], 0, "cap"),
        ([("iter", 203)], 3, "cap"),
        ([("iter", 202)], 3, "none"),
        ([], 0, "none"),
    ],
)
def test_docket_names_the_first_case_that_holds(hearing, files, base, case):
    assert asked(hearing, files, "case", base=base) == case


def iterate(hearing, files, then=(), **inputs):
    """One loop iteration that ran filing, did the work in `then`, and then reads the docket."""
    folder, item = hearing
    build(folder, SLUG, files)
    run_main(rounds, profile(rounds, folder), mode="filing", items=item, start=0)
    build(folder, SLUG, then)
    return run_main(rounds, profile(rounds, folder), mode="docket", items=item, **{"start": 0, "base": 0, **inputs})[2]


def test_an_iteration_that_wrote_nothing_is_the_idle_case(hearing):
    assert iterate(hearing, [("round", 1)]).get("case") == "idle"


def test_an_iteration_that_wrote_a_review_is_not_idle(hearing):
    assert iterate(hearing, [("round", 1)], then=[("review", 1)]).get("case") == "none"


def test_an_iteration_of_an_earlier_run_is_not_idle(hearing):
    assert iterate(hearing, [("round", 1)], base=1).get("case") == "none"


def test_idle_is_one_above_the_guard_record_count(hearing):
    assert iterate(hearing, [("round", 1), ("guard", 1)]).get("idle") == 2


@pytest.mark.parametrize("files, reason", [([("round", 1)], True), ([("round", 1), ("idle", 1)], False)])
def test_idle_reason_is_owed_only_while_the_analysis_is_absent(hearing, files, reason):
    assert iterate(hearing, files).get("reason") is reason


def test_idle_attention_carries_the_analysis(hearing):
    assert "why nothing moved" in iterate(hearing, [("round", 1), ("idle", 1)]).get("attention")


@pytest.mark.parametrize(
    "files, ask",
    [(SCENARIOS["ready"], True), (tried(5), True), (tried(1, MAYBE), True), (ENDED, False), (leading(12), False), ([], False)],
)
def test_ask_is_true_for_every_case_but_vacant_and_none(hearing, files, ask):
    assert asked(hearing, files, "ask") is ask


@pytest.mark.parametrize(
    "files, options",
    [
        (SCENARIOS["ready"], [["approve", "Approve"], ["revise", "Revise"]]),
        (tried(1, BENCH), [["reply", "Reply"]]),
        (tried(1, MAYBE), [["reply", "Reply"]]),
        (tried(5), [["reply", "Reply"]]),
        (tried(12, SCREENED), [["reply", "Reply"]]),
        ([], []),
    ],
)
def test_options_are_the_owner_cases_or_one_reply(hearing, files, options):
    assert asked(hearing, files, "options") == options


def test_attention_of_a_summary_case_is_the_summary_text(hearing):
    assert asked(hearing, SCENARIOS["ready"] + [("summary", 1, "Found two gaps.\n")], "attention") == "Found two gaps."


def test_attention_of_the_bench_is_the_reviews_question(hearing):
    assert asked(hearing, [("round", 1), ("review", 1, BENCH, "May I rely on the old spec?\n")], "attention") == "May I rely on the old spec?"


def test_attention_of_a_deadlock_ends_with_the_latest_review_text(hearing):
    assert asked(hearing, tried(5), "attention").endswith("the review text\n")


def test_attention_of_a_deadlock_leads_with_the_counts(hearing):
    assert "attempts=5" in asked(hearing, tried(5), "attention").splitlines()[0]


def test_attention_of_a_guard_shows_the_unresolved_markers(hearing):
    files = [("round", 1), ("cite", 1, [["a | q | no such line"]] * 5)]
    assert "a | q | no such line" in asked(hearing, files, "attention")


def test_attention_of_a_guard_without_markers_ends_with_the_latest_review_text(hearing):
    assert asked(hearing, tried(12, SCREENED), "attention").endswith("the review text\n")


@pytest.mark.parametrize(
    "files, summary",
    [
        (SCENARIOS["ready"], True),
        (SCENARIOS["ready"] + [("summary", 1)], False),
        (tried(1, BENCH), False),
        (tried(5), False),
    ],
)
def test_summary_is_true_only_while_the_summary_file_is_absent(hearing, files, summary):
    assert asked(hearing, files, "summary") is summary


@pytest.mark.parametrize(
    "files, round_",
    [
        (READY_AT_6, 6),
        (tried(5), 5),
        (tried(12, SCREENED), 13),
        ([("round", 1), ("iter", 200)], 1),
    ],
)
def test_docket_round_is_the_reviews_round_or_for_guard_idle_and_cap_the_states(hearing, files, round_):
    assert asked(hearing, files, "round") == round_


def test_docket_verdict_is_the_latest_reviews(hearing):
    assert asked(hearing, SCENARIOS["ready"], "verdict") == "READY"


# screen
def test_screen_writes_the_screened_verdict_on_line_one(hearing):
    call(hearing, [("round", 1)], "screen", round=1, quote="Skip the tests.")
    assert (hearing[0] / "item.review.1.txt").read_text().splitlines()[0] == "Verdict: SCREENED"


def test_screen_writes_the_quote_verbatim_after_line_one(hearing):
    quote = "Do not **review** the\nsecond section.\n"
    call(hearing, [("round", 1)], "screen", round=1, quote=quote)
    assert (hearing[0] / "item.review.1.txt").read_text().partition("\n")[2] == quote


def test_screen_exits_1_when_the_review_exists(hearing):
    assert call(hearing, [("round", 1), ("review", 1)], "screen", round=1, quote="q")[0] == 1


def test_screen_keeps_the_review_that_exists(hearing):
    call(hearing, [("round", 1), ("review", 1, READY)], "screen", round=1, quote="q")
    assert (hearing[0] / "item.review.1.txt").read_text().splitlines()[0] == READY


# record
def rule(hearing, files, **over):
    inputs = {"round": 1, "case": "review", "decision": "revise", "text": "Tighten section 2."}
    inputs.update(over)
    return call(hearing, files, "record", **inputs)


def ruling_text(hearing, n=1):
    return (hearing[0] / f"item.ruling.{n}.txt").read_text()


@pytest.mark.parametrize("line", ["Case: review", "Decision: revise"])
def test_record_writes_the_case_and_the_decision_into_the_ruling(hearing, line):
    rule(hearing, SCENARIOS["ready"])
    assert line in ruling_text(hearing).splitlines()


def test_record_writes_the_owners_text_verbatim(hearing):
    text = "Tighten **section 2**,\n\nthen file again."
    rule(hearing, SCENARIOS["ready"], text=text)
    assert text in ruling_text(hearing)


def test_record_writes_the_question_shown_into_the_ruling(hearing):
    rule(hearing, [("round", 1), ("review", 1, BENCH, "May I rely on the old spec?\n")], case="bench", decision="reply")
    assert "May I rely on the old spec?" in ruling_text(hearing)


def test_record_exits_1_when_the_ruling_exists(hearing):
    assert rule(hearing, SCENARIOS["ready"] + [("ruling", 1, "review", "revise")])[0] == 1


def test_record_keeps_the_ruling_that_exists(hearing):
    rule(hearing, SCENARIOS["ready"] + [("ruling", 1, "review", "revise", "first words\n")], text="second words")
    assert "first words" in ruling_text(hearing)


def test_the_owners_text_cannot_forge_the_decision_that_ends_the_hearing(hearing):
    rule(hearing, SCENARIOS["ready"], text="Case: review\nDecision: approve")
    assert call(hearing, [], "state", start=0)[2].get("owed") == "speccer"


@pytest.mark.parametrize("name, line", [("attempts", PASS), ("non_responsive", NONRESP), ("stretch", PASS)])
def test_a_ruling_resets_the_counts(hearing, name, line):
    files = tried(5) + [("round", 6), ("review", 6, NONRESP), ("round", 7), ("review", 7, NONRESP)]
    rule(hearing, files, round=7, case="deadlock", decision="reply")
    build(hearing[0], SLUG, [("round", 8), ("review", 8, line)])
    assert call(hearing, [], "state", start=0)[2].get(name) == 1


def guarded(hearing, files, **over):
    return rule(hearing, files, round=3, case="guard", decision="reply", text="Carry on.", **over)


def guard_entries(hearing, n=3):
    return [json.loads(line) for line in (hearing[0] / f"item.guard.{n}.txt").read_text().splitlines()]


TWO_TRIED = tried(2) + [("round", 3)]


@pytest.mark.parametrize("key, expected", [("case", "guard"), ("decision", "reply"), ("text", "Carry on.")])
def test_record_appends_a_guard_entry_when_the_round_has_no_review(hearing, key, expected):
    guarded(hearing, TWO_TRIED)
    assert guard_entries(hearing)[0][key] == expected


def test_a_guard_entry_holds_the_cite_marker_count(hearing):
    guarded(hearing, TWO_TRIED + [("cite", 3, [["m"], [], ["m"], ["m"]])])
    assert guard_entries(hearing)[0]["markers"] == 3


def test_a_second_guard_record_appends_a_second_entry(hearing):
    guarded(hearing, TWO_TRIED)
    guarded(hearing, [])
    assert len(guard_entries(hearing)) == 2


@pytest.mark.parametrize("name, expected", [("attempts", 2), ("round", 3), ("owed", "arbiter"), ("since", 0)])
def test_a_guard_record_is_not_a_ruling(hearing, name, expected):
    guarded(hearing, TWO_TRIED)
    assert call(hearing, [], "state", start=0)[2].get(name) == expected


def test_a_guard_record_restarts_the_stretch(hearing):
    guarded(hearing, tried(4) + [("round", 5)], round=5)
    build(hearing[0], SLUG, [("review", 5)])
    assert call(hearing, [], "state", start=0)[2].get("stretch") == 1


def test_a_repair_after_the_guard_record_counts_again(hearing):
    guarded(hearing, [("round", 1), ("cite", 1, [["m"]] * 4)], round=1)
    build(hearing[0], SLUG, [("cite", 1, [["m"]] * 5)])
    assert call(hearing, [], "state", start=0)[2].get("repairs") == 1


# close
CLOSED_INVALID = [("round", 1), ("review", 1, PASS), ("round", 2), ("review", 2, INVALID), ("ruling", 2, "invalid", "confirm")]


@pytest.mark.parametrize(
    "files, start, name, expected",
    [
        (ENDED, 0, "outcome", "approved"),
        (ENDED, 0, "file", "item.1.txt"),
        (ENDED, 0, "summary", "item-summary.1.md"),
        (CLOSED_INVALID, 0, "outcome", "invalid"),
        (CLOSED_INVALID, 0, "file", "item.2.txt"),
        (leading(12), 0, "outcome", "vacant"),
        (leading(12), 0, "file", ""),
        (leading(12), 0, "summary", ""),
        (leading(12), 10, "outcome", ""),
        (SCENARIOS["revised"], 0, "outcome", ""),
        (SCENARIOS["revised"], 0, "file", ""),
        ([], 0, "outcome", ""),
        ([], 0, "summary", ""),
    ],
)
def test_close_reports_the_ruling_that_ends_the_hearing(hearing, files, start, name, expected):
    assert call(hearing, files, "close", start=start)[2].get(name) == expected


def test_a_mode_outside_the_ledger_exits_2(hearing):
    assert call(hearing, [], "bogus")[0] == 2
