import pytest
from files_helpers import load, put


def test_write_creates_missing_parent_folders(monkeypatch, tmp_path):
    f = load(monkeypatch, tmp_path, write="out")
    f.write_file("out/a/b/c.txt", "deep")
    assert (tmp_path / "out/a/b/c.txt").read_text() == "deep"


def test_write_outside_write_folders_refused(monkeypatch, tmp_path):
    f = load(monkeypatch, tmp_path, read=".", write="out")
    with pytest.raises(PermissionError, match="FENCE_WRITE"):
        f.write_file("src/a.txt", "no")


@pytest.mark.parametrize(
    "bad", ["tests/t.py", "plans/approved/p.md", "specs/approved/s.md"]
)


def test_write_refused_inside_denied_folder(monkeypatch, tmp_path, bad):
    f = load(
        monkeypatch,
        tmp_path,
        read=".",
        write=".",
        deny="tests:plans/approved:specs/approved",
    )
    with pytest.raises(PermissionError):
        f.write_file(bad, "no")


def test_deny_does_not_cover_sibling_with_prefix_name(monkeypatch, tmp_path):
    f = load(monkeypatch, tmp_path, read=".", write=".", deny="tests")
    f.write_file("tests2/y.txt", "ok")
    assert (tmp_path / "tests2/y.txt").read_text() == "ok"


@pytest.mark.parametrize(
    "bad", [".git/hooks/pre-commit", ".archon/w.yaml", ".claude/settings.json"]
)


def test_write_refused_in_always_denied_folder(monkeypatch, tmp_path, bad):
    f = load(monkeypatch, tmp_path, read=".", write=".")
    with pytest.raises(PermissionError):
        f.write_file(bad, "no")


@pytest.mark.parametrize(
    "call",
    [
        lambda f: f.edit_file(".archon/w.yaml", "x", "y"),
        lambda f: f.delete_file(".archon/w.yaml"),
        lambda f: f.copy_file("a.txt", ".archon/w.yaml"),
    ],
    ids=["edit", "delete", "copy"],
)


def test_writing_tools_refused_in_always_denied_folder(monkeypatch, tmp_path, call):
    put(tmp_path, "a.txt")
    put(tmp_path, ".archon/w.yaml")
    f = load(monkeypatch, tmp_path, read=".", write=".")
    with pytest.raises(PermissionError):
        call(f)


def test_edit_replaces_single_occurrence(monkeypatch, tmp_path):
    put(tmp_path, "src/a.txt", "alpha beta\nbeta\n")
    f = load(monkeypatch, tmp_path, read="src", write="src")
    f.edit_file("src/a.txt", "alpha", "ALPHA")
    assert (tmp_path / "src/a.txt").read_text() == "ALPHA beta\nbeta\n"


def test_edit_replace_all_replaces_every_occurrence(monkeypatch, tmp_path):
    put(tmp_path, "src/a.txt", "alpha beta\nbeta\n")
    f = load(monkeypatch, tmp_path, read="src", write="src")
    f.edit_file("src/a.txt", "beta", "gamma", replace_all=True)
    assert (tmp_path / "src/a.txt").read_text() == "alpha gamma\ngamma\n"


@pytest.mark.parametrize("old", ["beta", "zeta"], ids=["ambiguous", "missing"])


def test_edit_refuses_old_text_not_found_exactly_once(monkeypatch, tmp_path, old):
    put(tmp_path, "src/a.txt", "alpha beta\nbeta\n")
    f = load(monkeypatch, tmp_path, read="src", write="src")
    with pytest.raises(ValueError):
        f.edit_file("src/a.txt", old, "gamma")


@pytest.mark.parametrize(
    ("read", "write", "refused"),
    [("", "src", "FENCE_READ"), ("src", "", "FENCE_WRITE")],
)


def test_edit_needs_read_and_write(monkeypatch, tmp_path, read, write, refused):
    put(tmp_path, "src/a.txt", "abc")
    f = load(monkeypatch, tmp_path, read=read, write=write)
    with pytest.raises(PermissionError, match=refused):
        f.edit_file("src/a.txt", "a", "b")


def test_copy_creates_missing_destination_folders(monkeypatch, tmp_path):
    put(tmp_path, "plans/plan.json", "first\n")
    f = load(monkeypatch, tmp_path, read="plans", write="plans/approved")
    f.copy_file("plans/plan.json", "plans/approved/round/plan.json")
    assert (tmp_path / "plans/approved/round/plan.json").read_text() == "first\n"


def test_copy_refuses_existing_destination(monkeypatch, tmp_path):
    put(tmp_path, "plans/plan.json", "second\n")
    put(tmp_path, "plans/approved/plan.json", "first\n")
    f = load(monkeypatch, tmp_path, read="plans", write="plans/approved")
    with pytest.raises(FileExistsError):
        f.copy_file("plans/plan.json", "plans/approved/plan.json")


def once_fence(monkeypatch, tmp_path):
    put(tmp_path, "reviews/old.md", "old\n")
    put(tmp_path, "src/old.md", "old\n")
    return load(
        monkeypatch, tmp_path, read=".", write="reviews:src", once="reviews"
    )


def test_write_creates_new_path_inside_once_folder(monkeypatch, tmp_path):
    f = once_fence(monkeypatch, tmp_path)
    f.write_file("reviews/new.md", "new\n")
    assert (tmp_path / "reviews/new.md").read_text() == "new\n"


def test_write_refuses_existing_path_inside_once_folder(monkeypatch, tmp_path):
    f = once_fence(monkeypatch, tmp_path)
    with pytest.raises(PermissionError, match="FENCE_ONCE"):
        f.write_file("reviews/old.md", "new\n")


def test_edit_refused_inside_once_folder(monkeypatch, tmp_path):
    f = once_fence(monkeypatch, tmp_path)
    with pytest.raises(PermissionError, match="FENCE_ONCE"):
        f.edit_file("reviews/old.md", "old", "new")


def test_delete_refused_inside_once_folder(monkeypatch, tmp_path):
    f = once_fence(monkeypatch, tmp_path)
    with pytest.raises(PermissionError, match="FENCE_ONCE"):
        f.delete_file("reviews/old.md")


def test_write_overwrites_existing_path_outside_once_folder(monkeypatch, tmp_path):
    f = once_fence(monkeypatch, tmp_path)
    f.write_file("src/old.md", "new\n")
    assert (tmp_path / "src/old.md").read_text() == "new\n"


def test_edit_changes_path_outside_once_folder(monkeypatch, tmp_path):
    f = once_fence(monkeypatch, tmp_path)
    f.edit_file("src/old.md", "old", "new")
    assert (tmp_path / "src/old.md").read_text() == "new\n"


def test_delete_removes_path_outside_once_folder(monkeypatch, tmp_path):
    put(tmp_path, "src/keep.md")
    f = once_fence(monkeypatch, tmp_path)
    f.delete_file("src/old.md")
    assert sorted(p.name for p in (tmp_path / "src").iterdir()) == ["keep.md"]


@pytest.mark.parametrize(
    ("read", "write", "refused"),
    [("out", "out", "FENCE_READ"), ("src", "", "FENCE_WRITE")],
)


def test_copy_refuses_unreadable_source_or_unwritable_destination(
    monkeypatch, tmp_path, read, write, refused
):
    put(tmp_path, "src/a.txt")
    f = load(monkeypatch, tmp_path, read=read, write=write)
    with pytest.raises(PermissionError, match=refused):
        f.copy_file("src/a.txt", "out/a.txt")


def test_copy_refuses_directory_source(monkeypatch, tmp_path):
    (tmp_path / "src/d").mkdir(parents=True)
    f = load(monkeypatch, tmp_path, read="src", write="out")
    with pytest.raises(ValueError):
        f.copy_file("src/d", "out/d")


@pytest.mark.parametrize(
    "call",
    [
        lambda f: f.write_file("cp/new.txt", "no"),
        lambda f: f.write_file("cp/old.txt", "no"),
        lambda f: f.edit_file("cp/new.txt", "x", "y"),
        lambda f: f.edit_file("cp/old.txt", "x", "y"),
    ],
    ids=["write-new", "write-existing", "edit-new", "edit-existing"],
)


def test_write_and_edit_refused_inside_copy_folder(monkeypatch, tmp_path, call):
    put(tmp_path, "cp/old.txt", "x\n")
    f = load(monkeypatch, tmp_path, read=".", write=".", copy="cp")
    with pytest.raises(PermissionError, match="FENCE_COPY"):
        call(f)


def test_copy_into_copy_folder_creates_file_with_source_content(monkeypatch, tmp_path):
    put(tmp_path, "src/a.txt", "payload\n")
    f = load(monkeypatch, tmp_path, read="src", write="cp", copy="cp")
    f.copy_file("src/a.txt", "cp/a.txt")
    assert (tmp_path / "cp/a.txt").read_text() == "payload\n"


def test_write_outside_copy_folder_still_allowed(monkeypatch, tmp_path):
    f = load(monkeypatch, tmp_path, read=".", write="cp:out", copy="cp")
    f.write_file("out/a.txt", "ok")
    assert (tmp_path / "out/a.txt").read_text() == "ok"


def test_delete_removes_file(monkeypatch, tmp_path):
    put(tmp_path, "out/a.txt")
    put(tmp_path, "out/b.txt")
    f = load(monkeypatch, tmp_path, write="out")
    f.delete_file("out/a.txt")
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["b.txt"]


def test_delete_refuses_directory(monkeypatch, tmp_path):
    (tmp_path / "out/d").mkdir(parents=True)
    f = load(monkeypatch, tmp_path, write="out")
    with pytest.raises(ValueError):
        f.delete_file("out/d")
