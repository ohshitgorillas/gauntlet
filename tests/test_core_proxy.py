# Copyright 2026 oh shit, gorillas!
"""Fixed-upstream route policy from m2-launcher-kinds-design.md, core/proxy.py."""

import pytest

from gauntlet.core import proxy
from gauntlet.core.errors import LaunchError
from gauntlet.core.proxy import ProxyPolicy, proxy_policy, upstream_target
from gauntlet.core.records import ProxyLimits, ProxyRoute

_MESSAGES = ProxyRoute("POST", "/v1/messages", ("beta",))
_COUNT_TOKENS = ProxyRoute("POST", "/v1/messages/count_tokens", ("beta",))
_DEFAULT_LIMITS = ProxyLimits(65536, 33554432, 8)
_DEFAULT_POLICY = ProxyPolicy((_MESSAGES, _COUNT_TOKENS), _DEFAULT_LIMITS)
_MODELS = ProxyRoute("GET", "/v1/models", ("limit",))


def _unordered(routes: tuple[ProxyRoute, ...]) -> list[str]:
    """Each route once per occurrence, independent of route order."""
    return sorted(repr(route) for route in routes)


def test_release_policy_holds_the_literal_default_routes_and_limits() -> None:
    """Breaks when a default route, its query names or a canonical limit changes."""
    assert hasattr(proxy, "RELEASE_POLICY")
    assert proxy.RELEASE_POLICY == _DEFAULT_POLICY


def test_proxy_policy_without_extra_routes_keeps_exactly_the_defaults() -> None:
    """Breaks when defaults are dropped or routes are added without an extension."""
    policy = proxy_policy(ProxyLimits())
    assert policy == _DEFAULT_POLICY


def test_proxy_policy_new_method_path_adds_a_route_and_keeps_defaults() -> None:
    """Breaks when an extension replaces the defaults or is not added as a route."""
    policy = proxy_policy(ProxyLimits(), (_MODELS,))
    assert _unordered(policy.routes) == _unordered((_MESSAGES, _COUNT_TOKENS, _MODELS))
    assert policy.limits == _DEFAULT_LIMITS


def test_proxy_policy_same_method_new_path_is_a_separate_route() -> None:
    """Breaks when routes merge by method alone instead of the exact method/path pair."""
    extra = ProxyRoute("POST", "/v1/messages/batches", ("trace",))
    policy = proxy_policy(ProxyLimits(), (extra,))
    assert _unordered(policy.routes) == _unordered((_MESSAGES, _COUNT_TOKENS, extra))


def test_proxy_policy_existing_pair_unions_query_names_in_declaration_order() -> None:
    """Breaks when an existing pair gains a second route, loses or reorders a name."""
    extra = ProxyRoute("POST", "/v1/messages", ("trace", "beta", "model"))
    policy = proxy_policy(ProxyLimits(), (extra,))
    merged = ProxyRoute("POST", "/v1/messages", ("beta", "trace", "model"))
    assert _unordered(policy.routes) == _unordered((merged, _COUNT_TOKENS))


def test_proxy_policy_existing_pair_without_query_names_keeps_the_route() -> None:
    """Breaks when an extension with no query names erases a default route's names."""
    extra = ProxyRoute("POST", "/v1/messages/count_tokens")
    policy = proxy_policy(ProxyLimits(), (extra,))
    assert _unordered(policy.routes) == _unordered((_MESSAGES, _COUNT_TOKENS))


def test_proxy_policy_uses_the_supplied_limit_overrides() -> None:
    """Breaks when supplied limits are replaced by the canonical defaults."""
    limits = ProxyLimits(header_bytes=1024, body_bytes=2048, connections=2)
    policy = proxy_policy(limits, (_MODELS,))
    assert policy.limits == ProxyLimits(1024, 2048, 2)


def test_proxy_policy_single_limit_override_keeps_other_limits() -> None:
    """Breaks when one adjusted limit resets or alters the others."""
    policy = proxy_policy(ProxyLimits(connections=3))
    assert policy.limits == ProxyLimits(65536, 33554432, 3)


def test_upstream_target_default_route_goes_to_the_fixed_origin() -> None:
    """Breaks when the returned target leaves the fixed origin or alters the path."""
    target = upstream_target("POST", "/v1/messages", _DEFAULT_POLICY)
    assert target == "https://api.anthropic.com/v1/messages"


def test_upstream_target_second_default_route_is_accepted() -> None:
    """Breaks when the count_tokens default route is not permitted."""
    target = upstream_target("POST", "/v1/messages/count_tokens", _DEFAULT_POLICY)
    assert target == "https://api.anthropic.com/v1/messages/count_tokens"


def test_upstream_target_preserves_an_allowed_query_parameter() -> None:
    """Breaks when an allowed query parameter is dropped or rewritten."""
    target = upstream_target("POST", "/v1/messages?beta=true", _DEFAULT_POLICY)
    assert target == "https://api.anthropic.com/v1/messages?beta=true"


def test_upstream_target_drops_query_parameters_the_route_does_not_allow() -> None:
    """Breaks when a disallowed query parameter is forwarded upstream."""
    target = upstream_target("POST", "/v1/messages?beta=true&model=x", _DEFAULT_POLICY)
    assert target == "https://api.anthropic.com/v1/messages?beta=true"


def test_upstream_target_only_disallowed_query_leaves_no_query() -> None:
    """Breaks when a disallowed-only query is forwarded or leaves a residue."""
    target = upstream_target("POST", "/v1/messages?model=x", _DEFAULT_POLICY)
    assert target == "https://api.anthropic.com/v1/messages"


def test_upstream_target_accepts_an_extended_route_with_its_query() -> None:
    """Breaks when an added route or its own query names are not honoured."""
    policy = ProxyPolicy((_MESSAGES, _COUNT_TOKENS, _MODELS), _DEFAULT_LIMITS)
    target = upstream_target("GET", "/v1/models?limit=5", policy)
    assert target == "https://api.anthropic.com/v1/models?limit=5"


def test_upstream_target_preserves_a_unioned_query_name() -> None:
    """Breaks when a query name added to an existing route is still dropped."""
    route = ProxyRoute("POST", "/v1/messages", ("beta", "trace"))
    policy = ProxyPolicy((route, _COUNT_TOKENS), _DEFAULT_LIMITS)
    target = upstream_target("POST", "/v1/messages?trace=1", policy)
    assert target == "https://api.anthropic.com/v1/messages?trace=1"


def test_upstream_target_query_names_are_per_route() -> None:
    """Breaks when one route's query names are allowed on another route."""
    policy = ProxyPolicy((_MESSAGES, _COUNT_TOKENS, _MODELS), _DEFAULT_LIMITS)
    target = upstream_target("POST", "/v1/messages?limit=5", policy)
    assert target == "https://api.anthropic.com/v1/messages"


_MALICIOUS_TARGETS = [
    "https://evil.example/v1/messages",
    "http://evil.example/v1/messages",
    "https://api.anthropic.com/v1/messages",
    "//evil.example/v1/messages",
    "api.anthropic.com:443",
    "https://user:secret@api.anthropic.com/v1/messages",
    "//user:secret@evil.example/v1/messages",
    "/v1/messages#fragment",
    "/v1/messages?beta=true#fragment",
    "/v1/../v1/messages",
    "/v1/models/../messages",
    "/v1/./messages",
    "/v1/messages/count_tokens/..",
    "/v1/%2e%2e/v1/messages",
    "/v1/%2E%2E/v1/messages",
    "/v1/%6dessages",
    "/v1/messages%2Fcount_tokens",
    "/v1/messages%3Fbeta=true",
    "/v1/messages%23fragment",
    "/v1/messages%",
    "/v1/messages%zz",
]


@pytest.mark.parametrize("target", _MALICIOUS_TARGETS)
def test_upstream_target_rejects_malicious_targets(target: str) -> None:
    """Breaks when an authority, credential, fragment, traversal or ambiguous encoding passes."""
    policy = ProxyPolicy((_MESSAGES, _COUNT_TOKENS, _MODELS), _DEFAULT_LIMITS)
    with pytest.raises(LaunchError):
        upstream_target("POST", target, policy)


def test_upstream_target_rejection_does_not_carry_the_credential() -> None:
    """Breaks when a rejected credential is copied into the error."""
    target = "https://user:hunter2-secret@api.anthropic.com/v1/messages"
    with pytest.raises(LaunchError) as caught:
        upstream_target("POST", target, _DEFAULT_POLICY)
    assert "hunter2-secret" not in caught.value.component
    assert "hunter2-secret" not in caught.value.reason
    assert "hunter2-secret" not in str(caught.value)


@pytest.mark.parametrize(
    ("method", "target"),
    [
        ("GET", "/v1/messages"),
        ("post", "/v1/messages"),
        ("PUT", "/v1/messages/count_tokens"),
        ("POST", "/v1/messages/"),
        ("POST", "/v1/message"),
        ("POST", "/v1/messages/extra"),
        ("POST", "/V1/messages"),
        ("GET", "/v1/models"),
        ("POST", "/"),
    ],
)
def test_upstream_target_unpermitted_method_or_path_fails_closed(
    method: str, target: str
) -> None:
    """Breaks when a request with no exact method/path permission is forwarded."""
    with pytest.raises(LaunchError):
        upstream_target(method, target, _DEFAULT_POLICY)


def test_upstream_target_empty_policy_fails_closed() -> None:
    """Breaks when a policy without routes permits any request."""
    policy = ProxyPolicy((), _DEFAULT_LIMITS)
    with pytest.raises(LaunchError):
        upstream_target("POST", "/v1/messages", policy)
