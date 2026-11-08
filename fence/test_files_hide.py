import pytest
from files_helpers import load, put


def hidden_tree(monkeypatch, tmp_path, hide="secret"):
    put(tmp_path, "secret/k.txt")
    put(tmp_path, "other/o.txt")
    return load(monkeypatch, tmp_path, read=".", write=".", hide=hide)


@pytest.mark.parametrize(
    "call",
    [
        lambda f: f.read_file("secret/k.txt"),
        lambda f: f.write_file("secret/k.txt", "y"),
        lambda f: f.edit_file("secret/k.txt", "x", "y"),
        lambda f: f.copy_file("secret/k.txt", "other/n.txt"),
        lambda f: f.copy_file("other/o.txt", "secret/n.txt"),
        lambda f: f.delete_file("secret/k.txt"),
        lambda f: f.list_directory("secret"),
        lambda f: f.find_files("*", "secret"),
        lambda f: f.grep("x", "secret"),
    ],
    ids=[
        "read",
        "write",
        "edit",
        "copy-source",
        "copy-destination",
        "delete",
        "list",
        "find",
        "grep",
    ],
)
def test_every_tool_refuses_a_hidden_path(monkeypatch, tmp_path, call):
    f = hidden_tree(monkeypatch, tmp_path)
    with pytest.raises(PermissionError, match="FENCE_HIDE"):
        call(f)


def test_refused_read_inside_readable_folder_names_fence_hide(monkeypatch, tmp_path):
    put(tmp_path, "docs/a.txt")
    put(tmp_path, "docs/h.txt")
    f = load(monkeypatch, tmp_path, read="docs", hide="docs/h.txt")
    with pytest.raises(PermissionError, match="FENCE_HIDE"):
        f.read_file("docs/h.txt")


def test_list_directory_omits_hidden_file_from_its_parent(monkeypatch, tmp_path):
    put(tmp_path, "docs/a.txt")
    put(tmp_path, "docs/h.txt")
    f = load(monkeypatch, tmp_path, read="docs", hide="docs/h.txt")
    assert f.list_directory("docs") == "a.txt"


def test_list_directory_omits_folder_holding_only_hidden_paths(monkeypatch, tmp_path):
    put(tmp_path, "docs/a.txt")
    put(tmp_path, "vault/k.txt")
    f = load(monkeypatch, tmp_path, read=".", hide="vault/k.txt")
    assert f.list_directory(".") == "docs/"


def test_find_files_omits_hidden_file_and_folder_holding_only_hidden_paths(
    monkeypatch, tmp_path
):
    put(tmp_path, "docs/a.txt")
    put(tmp_path, "docs/h.txt")
    put(tmp_path, "vault/k.txt")
    f = load(monkeypatch, tmp_path, read=".", hide="docs/h.txt:vault/k.txt")
    assert f.find_files("**").splitlines() == ["docs", "docs/a.txt"]


def test_grep_omits_hidden_file_hits(monkeypatch, tmp_path):
    put(tmp_path, "docs/a.txt", "needle\n")
    put(tmp_path, "docs/h.txt", "needle\n")
    put(tmp_path, "vault/k.txt", "needle\n")
    f = load(monkeypatch, tmp_path, read=".", hide="docs/h.txt:vault/k.txt")
    assert f.grep("needle").splitlines() == ["docs/a.txt:1:needle"]


def test_pattern_entry_hides_matching_file(monkeypatch, tmp_path):
    put(tmp_path, "docs/a.secret")
    f = load(monkeypatch, tmp_path, read=".", hide="docs/*.secret")
    with pytest.raises(PermissionError, match="FENCE_HIDE"):
        f.read_file("docs/a.secret")


def test_pattern_entry_star_does_not_hide_a_deeper_path(monkeypatch, tmp_path):
    put(tmp_path, "docs/sub/a.secret", "deep\n")
    f = load(monkeypatch, tmp_path, read=".", hide="docs/*.secret")
    assert f.read_file("docs/sub/a.secret").split("\t")[1] == "deep"


def test_unset_hide_hides_nothing(monkeypatch, tmp_path):
    put(tmp_path, "secret/k.txt", "open\n")
    f = load(monkeypatch, tmp_path, read=".")
    assert f.read_file("secret/k.txt").split("\t")[1] == "open"


def test_symlink_to_a_hidden_file_is_refused(monkeypatch, tmp_path):
    put(tmp_path, "vault/k.txt")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/link").symlink_to(tmp_path / "vault/k.txt")
    f = load(monkeypatch, tmp_path, read=".", hide="vault/k.txt")
    with pytest.raises(PermissionError, match="FENCE_HIDE"):
        f.read_file("docs/link")
