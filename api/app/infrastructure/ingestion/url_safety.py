import ipaddress
import socket
from urllib.parse import urlparse


def ensure_public_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("url must be http or https")

    hostname = parsed.hostname
    try:
        ip = ipaddress.ip_address(hostname)
        _ensure_public_ip(ip)
        return
    except ValueError:
        pass

    for address_info in socket.getaddrinfo(hostname, None):
        ip = ipaddress.ip_address(address_info[4][0])
        _ensure_public_ip(ip)


def _ensure_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise ValueError("url host must resolve to a public ip")
