# Copyright 2026 oh shit, gorillas!
"""The one gauntlet.yaml reader from m1-core-records-design.md, seams/config."""

from collections.abc import Callable
from errno import EACCES, EISDIR, ELOOP, ENOENT
from pathlib import Path
from typing import NamedTuple, Protocol, runtime_checkable

import pytest

from gauntlet.seams import config as seams_config

_DOCUMENTED = """\
image: .gauntlet/Containerfile
tests:
  - {dir: tests/py, run: "pytest {ids}"}
  - {dir: tests/js, run: "node --test {ids}"}
gates: scripts/gate.sh
test_helpers: [hqptuner/clock.py, tests/support/fake_clock.py]
test_policy: docs/testing.md
protected: [conftest.py, pyproject.toml, package.json, scripts/gate.sh]
interface:
  - {lang: py, run: "stubgen -o {out} {modules}"}
  - {lang: js, run: "tsc --allowJs --declaration --emitDeclarationOnly --outDir {out} {files}"}
test_lint: "ruff check {files} && mypy {files}"
implementer_network: false
caps: {design: 2, plan: 2, spec: 2, juror: 2, build: 2, review: 2, reopen: 2}
roles:
  planner: {model: claude-opus-5-5, effort: high}
  juror: {effort: medium}
"""

_REQUIRED = {
    "image": "image: .gauntlet/Containerfile\n",
    "tests": 'tests:\n  - {dir: tests/py, run: "pytest {ids}"}\n',
    "gates": "gates: scripts/gate.sh\n",
    "test_policy": "test_policy: docs/testing.md\n",
    "interface": 'interface:\n  - {lang: py, run: "stubgen -o {out} {modules}"}\n',
}


@runtime_checkable
class _Keyed(Protocol):
    key: str
    reason: str


@runtime_checkable
class _Stored(Protocol):
    path: str
    operation: str
    errno: int | None


def _document(**lines: str) -> str:
    """Join the required key lines, replacing or adding the named ones."""
    return "".join({**_REQUIRED, **lines}.values())


def _write(root: Path, text: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "gauntlet.yaml").write_text(text, encoding="utf-8")
    return root


def _failure(root: Path) -> BaseException:
    try:
        seams_config.read_config(root)
    except Exception as error:
        if type(error).__module__ != "gauntlet.core.errors":
            raise AssertionError from error
        return error
    pytest.fail("read_config returned a configuration instead of failing")


def _typed(error: BaseException, name: str) -> None:
    kind = type(error)
    assert kind.__name__ == name
    assert kind.__module__ == "gauntlet.core.errors"
    assert "GauntletError" in [base.__name__ for base in kind.__mro__]


def _config_failure(root: Path) -> _Keyed:
    error = _failure(root)
    _typed(error, "ConfigError")
    assert isinstance(error, _Keyed)
    assert error.reason.strip()
    return error


def _storage_failure(root: Path, number: int) -> None:
    error = _failure(root)
    _typed(error, "StorageError")
    assert isinstance(error, _Stored)
    assert error.path == str(root / "gauntlet.yaml")
    assert error.operation.strip()
    assert error.errno == number
    assert isinstance(error.__cause__, OSError)
    assert error.__cause__.errno == number


# Dropping, renaming or reordering any documented value while reading breaks this.
def test_example_read(tmp_path: Path) -> None:
    """Read the config.md example from the assigned root into its record."""
    result = seams_config.read_config(_write(tmp_path / "repo", _DOCUMENTED))
    assert result.image == ".gauntlet/Containerfile"
    assert [(entry.directory, entry.run) for entry in result.tests] == [
        ("tests/py", "pytest {ids}"),
        ("tests/js", "node --test {ids}"),
    ]
    assert result.gates == "scripts/gate.sh"
    assert result.test_helpers == ("hqptuner/clock.py", "tests/support/fake_clock.py")
    assert result.test_policy == "docs/testing.md"
    assert result.protected == (
        "conftest.py",
        "pyproject.toml",
        "package.json",
        "scripts/gate.sh",
    )
    assert [(entry.language, entry.run) for entry in result.interface] == [
        ("py", "stubgen -o {out} {modules}"),
        (
            "js",
            "tsc --allowJs --declaration --emitDeclarationOnly --outDir {out} {files}",
        ),
    ]
    assert result.test_lint == "ruff check {files} && mypy {files}"
    assert result.implementer_network is False
    caps = result.caps
    assert (
        caps.design,
        caps.plan,
        caps.spec,
        caps.juror,
        caps.build,
        caps.review,
        caps.reopen,
    ) == (2, 2, 2, 2, 2, 2, 2)
    assert [(role.name, role.model, role.effort) for role in result.roles] == [
        ("planner", "claude-opus-5-5", "high"),
        ("juror", None, "medium"),
    ]


# Supplying host defaults or the reader's own values for omitted keys breaks this.
def test_defaults(tmp_path: Path) -> None:
    """Fill every omitted optional key from Config and Caps, not the reader."""
    result = seams_config.read_config(_write(tmp_path / "repo", _document()))
    assert result.image == ".gauntlet/Containerfile"
    assert result.test_helpers == ()
    assert result.protected == ()
    assert result.test_lint is None
    assert result.implementer_network is False
    assert result.caps == type(result.caps)()
    assert result.roles == ()


# Opening gauntlet.yaml relative to the process cwd instead of the root breaks this.
def test_explicit_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Take the file from the explicit root while cwd holds another one."""
    root = _write(tmp_path / "repo", _DOCUMENTED)
    elsewhere = _write(
        tmp_path / "elsewhere", _document(image="image: decoy/Containerfile\n")
    )
    monkeypatch.chdir(elsewhere)
    assert seams_config.read_config(root).image == ".gauntlet/Containerfile"


# Searching cwd or parent folders when the root lacks the file breaks this.
def test_no_search(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail on the root's absent file even when its parent and cwd have one."""
    parent = _write(tmp_path / "parent", _DOCUMENTED)
    root = parent / "repo"
    root.mkdir()
    monkeypatch.chdir(parent)
    _storage_failure(root, ENOENT)


def _no_root(root: Path) -> None:
    assert not root.exists()


def _no_file(root: Path) -> None:
    root.mkdir()


def _directory(root: Path) -> None:
    (root / "gauntlet.yaml").mkdir(parents=True)


def _loop(root: Path) -> None:
    root.mkdir()
    (root / "gauntlet.yaml").symlink_to("gauntlet.yaml")


# Returning a default Config, or raising a bare OSError, on a file failure breaks this.
@pytest.mark.parametrize(
    ("arrange", "number"),
    [(_no_root, ENOENT), (_no_file, ENOENT), (_directory, EISDIR), (_loop, ELOOP)],
    ids=["no-root", "no-file", "directory", "loop"],
)
def test_unread(tmp_path: Path, arrange: Callable[[Path], None], number: int) -> None:
    """Report each failure to read the file with its path, errno and cause."""
    root = tmp_path / "repo"
    arrange(root)
    _storage_failure(root, number)


# Treating an unreadable file as absent config or a parse failure breaks this.
def test_no_permission(tmp_path: Path) -> None:
    """Report a permission failure as storage, not configuration."""
    root = _write(tmp_path / "repo", _DOCUMENTED)
    target = root / "gauntlet.yaml"
    target.chmod(0)
    try:
        _storage_failure(root, EACCES)
    finally:
        target.chmod(0o600)


# Loading into a dict first, so the last duplicate silently wins, breaks this.
@pytest.mark.parametrize(
    ("text", "key"),
    [
        (_document() + "image: .gauntlet/Containerfile\n", "image"),
        (_document() + "gates: other/gate.sh\n", "gates"),
        (_document(caps="caps: {design: 2, design: 2}\n"), "design"),
        (
            _document(
                roles="roles:\n  planner: {effort: high}\n  planner: {effort: high}\n"
            ),
            "planner",
        ),
        (
            _document(
                tests='tests:\n  - {dir: tests/py, dir: tests/py, run: "pytest {ids}"}\n'
            ),
            "dir",
        ),
    ],
    ids=["same", "differ", "caps", "roles", "entry"],
)
def test_dup_key(tmp_path: Path, text: str, key: str) -> None:
    """Reject a repeated key at any depth, even when both values agree."""
    error = _config_failure(_write(tmp_path / "repo", text))
    assert key in error.key


# Echoing the duplicated value or the parser's source snippet leaks a credential.
def test_dup_secret(tmp_path: Path) -> None:
    """Name the repeated key without disclosing either supplied value."""
    private_value = "credential-private-73"
    text = _document(gates=f"gates: {private_value}\ngates: {private_value}\n")
    error = _config_failure(_write(tmp_path / "repo", text))
    assert "gates" in error.key
    for surface in (error.key, error.reason, str(error), repr(error)):
        assert private_value not in surface


# Using a full or unsafe loader that resolves Python or local tags breaks this.
@pytest.mark.parametrize(
    "line",
    [
        'image: !!python/object/apply:os.mkdir ["MARKER"]\n',
        "image: !!python/name:os.getcwd ''\n",
        "image: !!python/object/new:types.SimpleNamespace {}\n",
        "image: !local opaque\n",
    ],
    ids=["apply", "name", "new", "local"],
)
def test_unsafe_tag(tmp_path: Path, line: str) -> None:
    """Reject every non-JSON tag before any constructor runs."""
    marker = tmp_path / "constructed"
    text = _document(image=line.replace("MARKER", str(marker)))
    error = _config_failure(_write(tmp_path / "repo", text))
    assert "image" in error.key
    assert not marker.exists()


# Passing parser scalars straight to the core validator skips JSON-value checks.
@pytest.mark.parametrize(
    ("key", "line"),
    [
        ("image", "image: !!binary aGVsbG8=\n"),
        ("image", "image: !!timestamp 2026-10-22\n"),
        ("protected", "protected: !!set {conftest.py: null}\n"),
        ("test_helpers", "test_helpers: [!!binary aGVsbG8=]\n"),
        ("caps", "caps: {review: .nan}\n"),
        ("caps", "caps: {review: .inf}\n"),
        ("caps", "caps: {review: -.inf}\n"),
        ("caps", "caps: {1: 2}\n"),
        ("roles", "roles: {planner: {model: !!binary aGVsbG8=}}\n"),
    ],
    ids=["bytes", "date", "set", "list", "nan", "inf", "ninf", "intkey", "role"],
)
def test_non_json(tmp_path: Path, key: str, line: str) -> None:
    """Reject bytes, dates, sets, nonfinite floats and non-text mapping keys."""
    error = _config_failure(_write(tmp_path / "repo", _document(**{key: line})))
    assert key in error.key


# Returning an empty or default Config for a document with no mapping breaks this.
@pytest.mark.parametrize(
    "text",
    ["", "# only a comment\n", "[]\n", "image\n"],
    ids=["empty", "comment", "list", "scalar"],
)
def test_not_map(tmp_path: Path, text: str) -> None:
    """Fail an empty or non-mapping document instead of defaulting it."""
    error = _config_failure(_write(tmp_path / "repo", text))
    assert error.key.strip()


# Letting the parser exception escape, or dropping it as the cause, breaks this.
def test_malformed(tmp_path: Path) -> None:
    """Wrap a parse failure with its cause and without the source text."""
    private_value = "credential-private-91"
    text = _document(gates=f'gates: "{private_value}\n')
    error = _config_failure(_write(tmp_path / "repo", text))
    assert isinstance(error, BaseException)
    assert error.__cause__ is not None
    for surface in (error.key, error.reason, str(error), repr(error)):
        assert private_value not in surface


# Skipping the core validator after parsing accepts incomplete or extra keys.
@pytest.mark.parametrize(
    ("text", "key"),
    [
        (_document(interface=""), "interface"),
        (_document(test_policy=""), "test_policy"),
        (_document() + "unexpected: 1\n", "unexpected"),
        (_document(caps="caps: {review: 0}\n"), "caps"),
    ],
    ids=["interface", "policy", "unknown", "cap"],
)
def test_schema(tmp_path: Path, text: str, key: str) -> None:
    """Carry the core validator's located failure out of the reader."""
    error = _config_failure(_write(tmp_path / "repo", text))
    assert key in error.key


# Startup, proxy-limit and route settings from m2-launcher-kinds-design.md.

_TEN_SECONDS = 10
_SET_SECONDS = 25
_SHORT_SECONDS = 3


class _Settings(NamedTuple):
    readiness: int
    limits: tuple[int, int, int]
    routes: list[tuple[str, str, tuple[str, ...]]]


def _read(root: Path) -> _Settings:
    """Read the new settings; a typed rejection of accepted keys is a failure."""
    try:
        result = seams_config.read_config(root)
    except Exception as error:
        if type(error).__module__ != "gauntlet.core.errors":
            raise
        message = f"read_config rejected an accepted setting: {type(error).__name__}"
        raise AssertionError(message) from error
    limits = result.proxy_limits
    return _Settings(
        result.readiness_timeout_seconds,
        (limits.header_bytes, limits.body_bytes, limits.connections),
        [
            (route.method, route.path, route.query_parameters)
            for route in result.proxy_extra_routes
        ],
    )


def _rejected(root: Path) -> _Keyed:
    """Return the located ConfigError; accepting the document is a failure."""
    caught: BaseException | None = None
    try:
        seams_config.read_config(root)
    except Exception as error:
        if type(error).__module__ != "gauntlet.core.errors":
            raise AssertionError from error
        caught = error
    if caught is None:
        message = "read_config accepted an invalid setting"
        raise AssertionError(message)
    _typed(caught, "ConfigError")
    assert isinstance(caught, _Keyed)
    return caught


# Dropping or replacing a supplied readiness_timeout_seconds breaks this.
def test_readiness_read(tmp_path: Path) -> None:
    """Carry readiness_timeout_seconds from gauntlet.yaml into the record."""
    text = _document() + "readiness_timeout_seconds: 25\n"
    result = _read(_write(tmp_path / "repo", text))
    assert result.readiness == _SET_SECONDS


# Rejecting the key, or defaulting the omitted members to anything but 64 KiB,
# 32 MiB and eight, breaks this.
def test_readiness_keeps_limits(tmp_path: Path) -> None:
    """Keep every canonical proxy limit when only readiness is supplied."""
    text = _document() + "readiness_timeout_seconds: 3\n"
    result = _read(_write(tmp_path / "repo", text))
    assert result.readiness == _SHORT_SECONDS
    assert result.limits == (65536, 33554432, 8)


# Ignoring one supplied limit, or losing a default for an omitted member, breaks this.
@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("proxy_limits: {header_bytes: 1024}\n", (1024, 33554432, 8)),
        ("proxy_limits: {body_bytes: 2048}\n", (65536, 2048, 8)),
        ("proxy_limits: {connections: 3}\n", (65536, 33554432, 3)),
        (
            "proxy_limits: {header_bytes: 100, body_bytes: 200, connections: 2}\n",
            (100, 200, 2),
        ),
    ],
    ids=["headers", "body", "connections", "all"],
)
def test_limits_partial(
    tmp_path: Path, line: str, expected: tuple[int, int, int]
) -> None:
    """Adjust each limit independently; missing members keep their defaults."""
    result = _read(_write(tmp_path / "repo", _document() + line))
    assert result.limits == expected
    assert result.readiness == _TEN_SECONDS


# Accepting a non-positive, fractional, boolean or unknown limit member breaks this.
@pytest.mark.parametrize(
    ("line", "field"),
    [
        ("proxy_limits: {header_bytes: 0}\n", "header_bytes"),
        ("proxy_limits: {body_bytes: -1}\n", "body_bytes"),
        ("proxy_limits: {connections: 1.5}\n", "connections"),
        ("proxy_limits: {connections: true}\n", "connections"),
        ("proxy_limits: {streams: 4}\n", "streams"),
    ],
    ids=["zero", "negative", "fraction", "bool", "unknown"],
)
def test_limits_invalid(tmp_path: Path, line: str, field: str) -> None:
    """Locate a rejected limit member at $.proxy_limits.<field>."""
    error = _rejected(_write(tmp_path / "repo", _document() + line))
    assert f"proxy_limits.{field}" in error.key


# Treating omitted routes as the default routes, or rejecting the other new
# settings, breaks this.
def test_routes_omitted(tmp_path: Path) -> None:
    """Add no routes when proxy_extra_routes is omitted."""
    text = _document() + "proxy_limits: {connections: 4}\n"
    result = _read(_write(tmp_path / "repo", text))
    assert result.routes == []
    assert result.limits == (65536, 33554432, 4)


# Dropping, reordering or merging defaults into the supplied routes breaks this.
def test_routes_read(tmp_path: Path) -> None:
    """Carry each route object in order, query_parameters defaulting to none."""
    text = _document() + (
        "proxy_extra_routes:\n"
        "  - {method: GET, path: /v1/models}\n"
        "  - {method: POST, path: /v1/files, query_parameters: [beta, purpose]}\n"
        "  - {method: POST, path: /v1/messages, query_parameters: [trace]}\n"
    )
    result = _read(_write(tmp_path / "repo", text))
    assert result.routes == [
        ("GET", "/v1/models", ()),
        ("POST", "/v1/files", ("beta", "purpose")),
        ("POST", "/v1/messages", ("trace",)),
    ]
    assert result.readiness == _TEN_SECONDS
    assert result.limits == (65536, 33554432, 8)


# Accepting a route without its required fields, or with a malformed or
# unknown field, breaks this.
@pytest.mark.parametrize(
    ("entry", "field"),
    [
        ("{path: /v1/files}", "method"),
        ("{method: POST}", "path"),
        ("{method: post, path: /v1/files}", "method"),
        ("{method: POST, path: '/v1/files?purpose=x'}", "path"),
        ("{method: POST, path: /v1/files, query_parameters: beta}", "query_parameters"),
        ("{method: POST, path: /v1/files, origin: example.com}", "origin"),
    ],
    ids=["no-method", "no-path", "lower", "query", "params", "unknown"],
)
def test_routes_invalid(tmp_path: Path, entry: str, field: str) -> None:
    """Locate a rejected route at $.proxy_extra_routes[index].<field>."""
    text = _document() + (
        f"proxy_extra_routes:\n  - {{method: GET, path: /v1/models}}\n  - {entry}\n"
    )
    error = _rejected(_write(tmp_path / "repo", text))
    assert "proxy_extra_routes[1]" in error.key
    assert field in error.key


# Accepting the same method/path twice in the extension list breaks this.
def test_routes_duplicate(tmp_path: Path) -> None:
    """Reject a repeated method/path pair at an indexed route location."""
    text = _document() + (
        "proxy_extra_routes:\n"
        "  - {method: POST, path: /v1/files}\n"
        "  - {method: POST, path: /v1/files, query_parameters: [beta]}\n"
    )
    error = _rejected(_write(tmp_path / "repo", text))
    assert "proxy_extra_routes[" in error.key
