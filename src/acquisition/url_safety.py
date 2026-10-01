"""Fetch-time guard: only public http(s) hosts may be retrieved.

Provenance validation cannot resolve DNS, so a name that resolves to a loopback,
private or link-local address must be refused here, before any request is sent,
and again for every redirect hop.
"""
from ipaddress import ip_address
import socket
from urllib.parse import urlsplit


def ensure_public_url(url: str, *, resolver=socket.getaddrinfo) -> str:
    """Return the URL when every address its host resolves to is public, else raise ValueError."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("only http(s) URLs with a host may be fetched")
    if parts.username or parts.password:
        raise ValueError("URLs must not carry credentials")
    try:
        addresses = {info[4][0] for info in resolver(parts.hostname, parts.port or 443)}
    except OSError as exc:
        raise ValueError(f"host does not resolve: {parts.hostname}") from exc
    if not addresses or any(not ip_address(address.split("%")[0]).is_global for address in addresses):
        raise ValueError(f"host resolves to a non-public address: {parts.hostname}")
    return url


def fetch_public(url: str, *, get, headers=None, timeout=10, max_hops=5, resolver=socket.getaddrinfo) -> bytes:
    """GET a public URL, re-validating every redirect hop instead of following redirects blindly."""
    from urllib.parse import urljoin
    for _ in range(max_hops + 1):
        ensure_public_url(url, resolver=resolver)
        response = get(url, headers=headers, timeout=timeout, allow_redirects=False)
        if response.is_redirect and response.headers.get("Location"):
            url = urljoin(url, response.headers["Location"])
            continue
        response.raise_for_status()
        return response.content
    raise ValueError("too many redirects")
