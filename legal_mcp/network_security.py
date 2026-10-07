from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from urllib.parse import urlparse


class NetworkSafetyError(RuntimeError):
    """Base error for outbound research-network safety checks."""


class UnsafeNetworkTarget(NetworkSafetyError):
    pass


Resolver = Callable[..., list[tuple]]


def validate_https_allowlisted_url(
    url: str,
    allowed_hosts: Iterable[str],
    *,
    error_cls: type[Exception] = UnsafeNetworkTarget,
    label: str = "research",
) -> str:
    """Validate a strict HTTPS URL against an exact hostname allowlist.

    Userinfo, non-standard ports, scheme downgrades and lookalike/subdomain hosts are
    rejected. The returned string is the stripped original URL so callers retain the
    exact path/query they intended to request.
    """
    candidate = (url or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme.lower() != "https":
        raise error_cls(f"Only HTTPS {label} URLs are allowed.")
    host = (parsed.hostname or "").lower().rstrip(".")
    normalized_hosts = {str(value).lower().rstrip(".") for value in allowed_hosts}
    if host not in normalized_hosts:
        raise error_cls(f"{label.capitalize()} URL host is not in the approved allowlist.")
    if parsed.username or parsed.password:
        raise error_cls(f"Credentials in {label} URLs are not allowed.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise error_cls(f"Invalid port in {label} URL.") from exc
    if port not in (None, 443):
        raise error_cls(f"Non-standard HTTPS ports are not allowed for {label} retrieval.")
    return candidate


def _is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    return bool(address.is_global)


def assert_public_dns_for_url(
    url: str,
    *,
    resolver: Resolver | None = None,
    error_cls: type[Exception] = UnsafeNetworkTarget,
    label: str = "research",
) -> tuple[str, ...]:
    """Resolve the URL host and reject any non-global address.

    Exact host allowlists prevent arbitrary-host SSRF. This DNS guard adds protection
    against an allowlisted hostname resolving to loopback, private, link-local,
    multicast, unspecified, reserved or otherwise non-global addresses. It is applied
    immediately before every outbound request/redirect hop.
    """
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise error_cls(f"{label.capitalize()} URL has no hostname.")
    resolver_fn = resolver or socket.getaddrinfo
    try:
        infos = resolver_fn(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise error_cls(f"{label.capitalize()} hostname could not be resolved safely.") from exc

    addresses: list[str] = []
    for info in infos:
        try:
            sockaddr = info[4]
            raw = sockaddr[0]
        except Exception:
            continue
        if raw not in addresses:
            addresses.append(raw)

    if not addresses:
        raise error_cls(f"{label.capitalize()} hostname resolved to no usable address.")
    unsafe = [value for value in addresses if not _is_public_ip(value)]
    if unsafe:
        raise error_cls(f"{label.capitalize()} hostname resolved to a non-public network address.")
    return tuple(addresses)


def normalized_media_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def media_type_allowed(media_type: str, allowed_media_types: Iterable[str]) -> bool:
    allowed = {str(value).strip().lower() for value in allowed_media_types}
    return media_type.strip().lower() in allowed
