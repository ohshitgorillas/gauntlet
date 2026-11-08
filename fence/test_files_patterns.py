import pytest
from files_helpers import load, put

REVIEW = "gauntlet/mend/*.review.*.txt"


def test_write_pattern_allows_matching_file_at_same_depth(monkeypatch, tmp_path):
    f = load(monkeypatch, tmp_path, write=REVIEW)
    f.write_file("gauntlet/mend/a.review.1.txt", "ok")
    assert (tmp_path / "gauntlet/mend/a.review.1.txt").read_text() == "ok"


def test_write_pattern_star_does_not_cross_slash(monkeypatch, tmp_path):
    f = load(monkeypatch, tmp_path, write=REVIEW)
    with pytest.raises(PermissionError, match="FENCE_WRITE"):
        f.write_file("gauntlet/mend/x/a.review.1.txt", "no")


@pytest.mark.parametrize(
    ("entry", "path"),
    [("out/a?.txt", "out/ab.txt"), ("out/[ab].txt", "out/b.txt")],
    ids=["question-mark", "bracket"],
)
def test_write_pattern_recognizes_question_mark_and_bracket(
    monkeypatch, tmp_path, entry, path
):
    f = load(monkeypatch, tmp_path, write=entry)
    f.write_file(path, "ok")
    assert (tmp_path / path).read_text() == "ok"


def test_read_pattern_allows_matching_file(monkeypatch, tmp_path):
    put(tmp_path, "docs/a.md", "hi\n")
    f = load(monkeypatch, tmp_path, read="docs/*.md")
    assert f.read_file("docs/a.md").split("\t")[1] == "hi"


def test_read_pattern_star_does_not_cross_slash(monkeypatch, tmp_path):
    put(tmp_path, "docs/sub/a.md")
    f = load(monkeypatch, tmp_path, read="docs/*.md")
    with pytest.raises(PermissionError, match="FENCE_READ"):
        f.read_file("docs/sub/a.md")


def test_deny_pattern_refuses_inside_writable_folder(monkeypatch, tmp_path):
    f = load(monkeypatch, tmp_path, write=".", deny="gauntlet/*.lock")
    with pytest.raises(PermissionError):
        f.write_file("gauntlet/a.lock", "no")


def test_once_pattern_refuses_overwrite_of_matching_file(monkeypatch, tmp_path):
    put(tmp_path, "out/a.once.txt")
    f = load(monkeypatch, tmp_path, write="out", once="out/*.once.txt")
    with pytest.raises(PermissionError, match="FENCE_ONCE"):
        f.write_file("out/a.once.txt", "no")


def test_copy_pattern_refuses_write_of_matching_file(monkeypatch, tmp_path):
    f = load(monkeypatch, tmp_path, write="out", copy="out/*.copy.txt")
    with pytest.raises(PermissionError, match="FENCE_COPY"):
        f.write_file("out/a.copy.txt", "no")


def test_list_directory_shows_only_folders_holding_a_readable_file(
    monkeypatch, tmp_path
):
    put(tmp_path, "gauntlet/mend/a.review.1.txt")
    put(tmp_path, "docs/mend/a.txt")
    f = load(
        monkeypatch,
        tmp_path,
        read="gauntlet/mend/*.review.*.txt:docs/mend/*.review.*.txt",
    )
    assert f.list_directory(".") == "gauntlet/"


def test_find_files_shows_matching_files_and_no_folder_without_one(
    monkeypatch, tmp_path
):
    put(tmp_path, "docs/a.md")
    put(tmp_path, "docs/sub/c.txt")
    f = load(monkeypatch, tmp_path, read="docs/*")
    assert f.find_files("**").splitlines() == ["docs/a.md"]
