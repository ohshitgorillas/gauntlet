# Copyright 2026 oh shit, gorillas!
"""Fixed upstream and request policy for the credential proxy."""

from dataclasses import dataclass

from gauntlet.core.errors import LaunchError
from gauntlet.core.records import DEFAULT_PROXY_ROUTES, ProxyLimits, ProxyRoute

UPSTREAM_ORIGIN = "https://api.anthropic.com"


@dataclass(frozen=True)
class ProxyPolicy:
    """The routes the credential proxy allows and the limits it enforces."""

    routes: tuple[ProxyRoute, ...]
    limits: ProxyLimits


def proxy_policy(
    limits: ProxyLimits, extra_routes: tuple[ProxyRoute, ...] = ()
) -> ProxyPolicy:
    """Build the proxy policy from its limits and any extra routes."""
    merged: dict[tuple[str, str], tuple[str, ...]] = {
        (route.method, route.path): route.query_parameters
        for route in DEFAULT_PROXY_ROUTES
    }
    for extra in extra_routes:
        key = (extra.method, extra.path)
        known = merged.get(key, ())
        merged[key] = known + tuple(
            name for name in extra.query_parameters if name not in known
        )
    routes = tuple(
        ProxyRoute(method, path, names) for (method, path), names in merged.items()
    )
    return ProxyPolicy(routes, limits)


RELEASE_POLICY = proxy_policy(ProxyLimits())


def _rejected() -> LaunchError:
    """Name the refusal without echoing any part of the request."""
    return LaunchError("proxy", "request target is not permitted")


def upstream_target(method: str, target: str, policy: ProxyPolicy) -> str:
    """Return the upstream URL for a request, as the policy decides."""
    if "#" in target:
        raise _rejected()
    path, _, query = target.partition("?")
    for route in policy.routes:
        if route.method == method and route.path == path:
            allowed = [
                pair
                for pair in query.split("&")
                if pair.partition("=")[0] in route.query_parameters
            ]
            suffix = "?" + "&".join(allowed) if allowed else ""
            return UPSTREAM_ORIGIN + path + suffix
    raise _rejected()
