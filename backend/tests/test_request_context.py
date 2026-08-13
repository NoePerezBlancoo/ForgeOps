from starlette.requests import Request

from app.core.config import settings
from app.core.request import get_client_ip


def build_request(*, client: str | None, real_ip: str | None = None) -> Request:
    headers = [] if real_ip is None else [(b"x-real-ip", real_ip.encode("ascii"))]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "client": None if client is None else (client, 12345),
    }
    return Request(scope)


def test_client_ip_uses_direct_peer_by_default():
    previous = settings.client_ip_source
    settings.client_ip_source = "direct"
    try:
        request = build_request(client="10.0.0.7", real_ip="203.0.113.8")
        assert get_client_ip(request) == "10.0.0.7"
    finally:
        settings.client_ip_source = previous


def test_client_ip_uses_valid_railway_real_ip_when_configured():
    previous = settings.client_ip_source
    settings.client_ip_source = "x-real-ip"
    try:
        ipv4_request = build_request(client="10.0.0.7", real_ip="203.0.113.8")
        ipv6_request = build_request(client="10.0.0.7", real_ip="2001:db8::8")
        assert get_client_ip(ipv4_request) == "203.0.113.8"
        assert get_client_ip(ipv6_request) == "2001:db8::8"
    finally:
        settings.client_ip_source = previous


def test_client_ip_rejects_malformed_forwarded_value():
    previous = settings.client_ip_source
    settings.client_ip_source = "x-real-ip"
    try:
        invalid_ips = ["not-an-ip", "256.0.0.1", "203.0.113.8, 198.51.100.2"]
        for invalid_ip in invalid_ips:
            request = build_request(client="10.0.0.7", real_ip=invalid_ip)
            assert get_client_ip(request) == "10.0.0.7"
    finally:
        settings.client_ip_source = previous


def test_client_ip_falls_back_to_direct_when_header_is_missing():
    previous = settings.client_ip_source
    settings.client_ip_source = "x-real-ip"
    try:
        request = build_request(client="10.0.0.7", real_ip=None)
        assert get_client_ip(request) == "10.0.0.7"
    finally:
        settings.client_ip_source = previous


def test_client_ip_returns_none_when_both_addresses_missing():
    previous = settings.client_ip_source
    settings.client_ip_source = "x-real-ip"
    try:
        request = build_request(client=None, real_ip=None)
        assert get_client_ip(request) is None
    finally:
        settings.client_ip_source = previous


def test_client_ip_strips_forwarded_address_whitespace():
    previous = settings.client_ip_source
    settings.client_ip_source = "x-real-ip"
    try:
        request = build_request(client="10.0.0.7", real_ip=" 203.0.113.8 ")
        assert get_client_ip(request) == "203.0.113.8"
    finally:
        settings.client_ip_source = previous
