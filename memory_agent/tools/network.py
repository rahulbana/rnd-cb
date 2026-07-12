"""Network lookup tools (DNS resolution + IP geolocation)."""

from __future__ import annotations

import socket

import requests
from langchain_core.tools import tool

from .base import HTTP_TIMEOUT, extract_host


def make_network_tools() -> list:
    @tool
    def ip_lookup(domain_or_url: str) -> str:
        """Resolve a domain or URL to its IP address(es) and geolocation."""
        host = extract_host(domain_or_url)
        if not host:
            return f"Could not parse a host from '{domain_or_url}'."
        try:
            _, _, ips = socket.gethostbyname_ex(host)
        except Exception as exc:
            return f"DNS lookup failed for {host}: {exc}"
        if not ips:
            return f"No IP addresses found for {host}."

        primary = ips[0]
        lines = [f"Host: {host}", f"IP addresses: {', '.join(ips)}"]
        try:
            geo = requests.get(
                f"http://ip-api.com/json/{primary}", timeout=HTTP_TIMEOUT
            ).json()
            if geo.get("status") == "success":
                lines.append(
                    "Location of {ip}: {city}, {region}, {country} (ISP: {isp})".format(
                        ip=primary,
                        city=geo.get("city", "?"),
                        region=geo.get("regionName", "?"),
                        country=geo.get("country", "?"),
                        isp=geo.get("isp", "?"),
                    )
                )
        except Exception:
            pass  # geolocation is best-effort
        return "\n".join(lines)

    return [ip_lookup]
