import pytest
from shared_helpers import load

red = load("red")

OK = "exit=0 timed_out=false\n"
FAIL = "exit=1 timed_out=false\n"
TIMEOUT = "exit=1 timed_out=true\n"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("FAILED t::a - assert 1 == 2\nPASSED t::b", "FAILED t::a\nPASSED t::b"),
        ("no separator here", "no separator here"),
        ("a - b - c", "a"),
    ],
)
def test_cut_drops_each_line_from_its_first_separator(text, expected):
    assert red.cut(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        (OK + "PASSED t::a\nFAILED t::b - boom\nERROR t::c", {"t::a": "PASSED", "t::b": "FAILED", "t::c": "ERROR"}),
        (OK + "collected 3 items\n3 passed in 0.1s\nPASSED t::a", {"t::a": "PASSED"}),
        (OK + "  FAILED t::a\nxFAILED t::b\nFAILED t::c", {"t::c": "FAILED"}),
        (OK + "FAILED t::a - FAILED t::z - x", {"t::a": "FAILED"}),
    ],
)
def test_listing_reads_only_result_lines_at_line_start(text, expected):
    assert red.listing(text) == expected


@pytest.mark.parametrize(
    "run, brief, head, expected",
    [
        (FAIL + "FAILED t::a", OK + "PASSED t::a", "", True),
        (FAIL + "FAILED t::a", OK + "PASSED t::a", OK + "PASSED t::a", True),
        (FAIL + "ERROR t::a", OK + "PASSED t::a", "", True),
        (FAIL + "FAILED t::a", FAIL + "FAILED t::a", "", False),
        (FAIL + "FAILED t::a", OK + "PASSED t::a", FAIL + "FAILED t::a", False),
        (FAIL + "FAILED t::a - boom", FAIL + "FAILED t::a - other message", "", False),
        (FAIL + "ERROR t::a", FAIL + "FAILED t::a", "", False),
        (OK + "PASSED t::a", FAIL + "FAILED t::a", "", False),
    ],
)
def test_red_compares_failing_tests_against_both_baselines(run, brief, head, expected):
    assert red.red(run, brief, head) is expected


@pytest.mark.parametrize(
    "run, brief, head, expected",
    [
        (TIMEOUT, FAIL, "", True),
        (TIMEOUT, FAIL, FAIL, True),
        (TIMEOUT, TIMEOUT, "", False),
        (TIMEOUT, FAIL, TIMEOUT, False),
    ],
)
def test_red_run_timeout_is_red_unless_a_baseline_timed_out(run, brief, head, expected):
    assert red.red(run, brief, head) is expected


@pytest.mark.parametrize(
    "run, brief, head, expected",
    [
        (FAIL, OK, "", True),
        (FAIL, OK, OK, True),
        (FAIL, FAIL, "", False),
        (FAIL, OK, FAIL, False),
        (OK, OK, OK, False),
    ],
)
def test_red_nonzero_exit_without_failing_line_is_red_when_baselines_exited_zero(run, brief, head, expected):
    assert red.red(run, brief, head) is expected
