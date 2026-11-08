import asyncio
import contextlib
import subprocess

import pytest
from files_helpers import load, put


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def new_repo(monkeypatch, tmp_path):
    """A real repository with one commit holding base.txt and src.txt, isolated
    from the host's git configuration."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    put(tmp_path, "base.txt", "base\n")
    put(tmp_path, "src.txt", "x\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "initial")
    return tmp_path


def fence(monkeypatch, repo, write=".", hide="", commit="1"):
    return load(monkeypatch, repo, read=".", write=write, hide=hide, commit=commit)


def head_files(repo):
    return git(repo, "show", "--name-only", "--format=", "HEAD").split()


def staged(repo):
    return git(repo, "diff", "--cached", "--name-only")


def write_hook(repo, name, body):
    hook = repo / ".git/hooks" / name
    hook.write_text(f"#!/bin/sh\n{body}\n")
    hook.chmod(0o755)


def count_log(repo):
    log = repo / "hook.log"
    return len(log.read_text().splitlines()) if log.exists() else 0


def committed(repo, path):
    shown = subprocess.run(
        ["git", "-C", str(repo), "show", f"HEAD:{path}"], capture_output=True, text=True
    )
    return shown.stdout


def test_commit_holds_exactly_the_listed_paths_while_another_path_is_staged(
    monkeypatch, tmp_path
):
    repo = new_repo(monkeypatch, tmp_path)
    f = fence(monkeypatch, repo)
    f.write_file("a.txt", "a\n")
    put(repo, "b.txt")
    git(repo, "add", "b.txt")
    f.commit("add a", ["a.txt"])
    assert head_files(repo) == ["a.txt"]


def test_commit_answer_carries_exit_zero_and_the_full_hash(monkeypatch, tmp_path):
    repo = new_repo(monkeypatch, tmp_path)
    f = fence(monkeypatch, repo)
    f.write_file("a.txt", "a\n")
    answer = f.commit("add a", ["a.txt"])
    assert answer.split() == ["exit=0", f"commit={git(repo, 'rev-parse', 'HEAD').strip()}"]


@pytest.mark.parametrize(
    "record",
    [
        lambda f: f.write_file("p.txt", "new\n"),
        lambda f: f.edit_file("src.txt", "x", "y"),
        lambda f: f.copy_file("src.txt", "p.txt"),
        lambda f: f.delete_file("src.txt"),
    ],
    ids=["write", "edit", "copy-destination", "delete"],
)
def test_commit_refuses_a_recorded_changed_path_left_out(monkeypatch, tmp_path, record):
    repo = new_repo(monkeypatch, tmp_path)
    f = fence(monkeypatch, repo)
    f.write_file("keep.txt", "k\n")
    record(f)
    with pytest.raises(ValueError):
        f.commit("keep", ["keep.txt"])


def test_commit_accepts_a_recorded_path_that_did_not_change(monkeypatch, tmp_path):
    repo = new_repo(monkeypatch, tmp_path)
    f = fence(monkeypatch, repo)
    f.write_file("src.txt", "x\n")
    f.write_file("keep.txt", "k\n")
    assert f.commit("keep", ["keep.txt"]).split()[:1] == ["exit=0"]


def test_commit_leaves_out_a_listed_path_that_does_not_exist(monkeypatch, tmp_path):
    repo = new_repo(monkeypatch, tmp_path)
    f = fence(monkeypatch, repo)
    f.write_file("a.txt", "a\n")
    f.commit("add a", ["a.txt", "ghost.txt"])
    assert head_files(repo) == ["a.txt"]


def test_commit_takes_a_new_file_in_a_directory_that_does_not_exist_yet(
    monkeypatch, tmp_path
):
    repo = new_repo(monkeypatch, tmp_path)
    f = fence(monkeypatch, repo)
    f.write_file("new/dir/f.txt", "f\n")
    f.commit("add f", ["new/dir/f.txt"])
    assert head_files(repo) == ["new/dir/f.txt"]


def test_commit_with_no_changed_path_answers_exit_zero_nothing(monkeypatch, tmp_path):
    repo = new_repo(monkeypatch, tmp_path)
    f = fence(monkeypatch, repo)
    assert f.commit("none", ["base.txt"]) == "exit=0 nothing"


def test_commit_retries_once_after_a_hook_changed_files(monkeypatch, tmp_path):
    repo = new_repo(monkeypatch, tmp_path)
    write_hook(repo, "pre-commit", f'echo run >> "{repo}/hook.log"\necho more >> a.txt\nexit 1')
    f = fence(monkeypatch, repo)
    f.write_file("a.txt", "a\n")
    f.commit("add a", ["a.txt"])
    assert count_log(repo) == 2


def test_commit_keeps_what_the_hook_changed_on_the_retry(monkeypatch, tmp_path):
    repo = new_repo(monkeypatch, tmp_path)
    write_hook(
        repo,
        "pre-commit",
        f'[ -e "{repo}/fixed" ] && exit 0\necho formatted > a.txt\ntouch "{repo}/fixed"\nexit 1',
    )
    f = fence(monkeypatch, repo)
    f.write_file("a.txt", "a\n")
    f.commit("add a", ["a.txt"])
    assert committed(repo, "a.txt") == "formatted\n"


def test_commit_names_the_failing_hook_file_not_its_output(monkeypatch, tmp_path):
    repo = new_repo(monkeypatch, tmp_path)
    write_hook(repo, "pre-commit", 'echo "- hook id: ruff-check" >&2\nexit 1')
    f = fence(monkeypatch, repo)
    f.write_file("a.txt", "a\n")
    assert f.commit("add a", ["a.txt"]).split() == ["exit=1", "pre-commit"]


def test_commit_tool_is_absent_without_fence_commit(monkeypatch, tmp_path):
    repo = new_repo(monkeypatch, tmp_path)
    f = fence(monkeypatch, repo, commit="")
    names = [t.name for t in asyncio.run(f.mcp.list_tools())]
    assert "commit" not in names


def test_commit_refuses_a_hidden_path(monkeypatch, tmp_path):
    repo = new_repo(monkeypatch, tmp_path)
    put(repo, "secret/k.txt")
    f = fence(monkeypatch, repo, hide="secret")
    with pytest.raises(PermissionError, match="FENCE_HIDE"):
        f.commit("leak", ["secret/k.txt"])


def test_commit_refuses_a_path_outside_fence_write(monkeypatch, tmp_path):
    repo = new_repo(monkeypatch, tmp_path)
    put(repo, "src/a.txt")
    f = fence(monkeypatch, repo, write="out")
    with pytest.raises(PermissionError, match="FENCE_WRITE"):
        f.commit("escape", ["src/a.txt"])


@pytest.mark.parametrize("case", ["outside-write", "recorded-left-out"])
def test_a_refused_commit_stages_nothing_beyond_what_was_already_staged(monkeypatch, tmp_path, case):
    repo = new_repo(monkeypatch, tmp_path)
    f = fence(monkeypatch, repo, write="out" if case == "outside-write" else ".")
    put(repo, "pre.txt")
    git(repo, "add", "pre.txt")
    put(repo, "out/ok.txt")
    put(repo, "src/a.txt")
    f.write_file("out/rec.txt", "r\n")
    listed = {"outside-write": ["out/ok.txt", "src/a.txt"], "recorded-left-out": ["out/ok.txt"]}
    with contextlib.suppress(PermissionError, ValueError):
        f.commit("refused", listed[case])
    assert staged(repo).split() == ["pre.txt"]
