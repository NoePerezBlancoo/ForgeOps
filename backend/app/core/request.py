from ipaddress import ip_address

from fastapi import Request

from app.core.config import settings


def get_client_ip(request: Request) -> str | None:
    direct_address = request.client.host if request.client else None
    if settings.client_ip_source != "x-real-ip":
        return direct_address

    forwarded_address = request.headers.get("x-real-ip", "").strip()
    try:
        return str(ip_address(forwarded_address))
    except ValueError:
        return direct_address
