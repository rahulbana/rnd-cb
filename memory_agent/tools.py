"""Extra capabilities exposed to the agent as tools.

Grouped roughly by kind:

* External APIs  - web search (Tavily), currency rates, IP geolocation.
* Local compute  - unit conversion (pint), current time by timezone/country.
* LLM sub-tasks  - email drafting, summarizing, translating (a focused,
  separate model call so the main conversation context stays clean).

Every tool is defensive: network/lookup failures return a readable message to
the model rather than raising, so one flaky tool never crashes the chat loop.
"""

from __future__ import annotations

import socket
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, available_timezones

import pytz
import requests
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from .config import Settings

HTTP_TIMEOUT = 15


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _llm_task(llm, system: str, user: str) -> str:
    """Run a one-shot, tool-free LLM sub-task and return its text."""
    try:
        resp = llm.invoke([SystemMessage(system), HumanMessage(user)])
        return resp.content
    except Exception as exc:  # pragma: no cover - network dependent
        return f"(the language model call failed: {exc})"


def _extract_host(domain_or_url: str) -> str:
    s = domain_or_url.strip()
    if "//" not in s:
        s = "//" + s  # let urlparse treat it as a netloc
    host = urlparse(s).hostname or domain_or_url.strip()
    return host


# --------------------------------------------------------------------------
# tool factory
# --------------------------------------------------------------------------

def build_extra_tools(settings: Settings, util_llm) -> list:
    """Return the list of extra tools, closing over settings and an LLM."""

    ureg = None  # lazily created pint registry (import is a little slow)

    # ---- web search (Tavily) --------------------------------------------
    @tool
    def web_search(query: str, max_results: int = 5) -> str:
        """Search the web for current, real-world information using Tavily.

        Use for recent events, facts you're unsure about, prices, docs, etc.
        """
        if not settings.tavily_api_key:
            return (
                "Web search is unavailable: TAVILY_API_KEY is not set. "
                "Ask the user to set it to enable web search."
            )
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=settings.tavily_api_key)
            data = client.search(
                query, max_results=max(1, min(max_results, 10)),
                include_answer=True,
            )
        except Exception as exc:
            return f"Web search failed: {exc}"

        lines = []
        if data.get("answer"):
            lines.append(f"Answer: {data['answer']}")
        for r in data.get("results", []):
            lines.append(f"- {r.get('title')} ({r.get('url')})\n  {r.get('content', '')[:300]}")
        return "\n".join(lines) or "No results found."

    # ---- currency converter ---------------------------------------------
    @tool
    def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
        """Convert an amount between currencies using live exchange rates.

        Currencies are ISO codes, e.g. USD, EUR, INR, JPY.
        """
        src, dst = from_currency.upper().strip(), to_currency.upper().strip()
        try:
            resp = requests.get(
                f"https://open.er-api.com/v6/latest/{src}", timeout=HTTP_TIMEOUT
            )
            data = resp.json()
        except Exception as exc:
            return f"Currency lookup failed: {exc}"

        if data.get("result") != "success":
            return f"Could not fetch rates for {src} ({data.get('error-type', 'unknown error')})."
        rate = data.get("rates", {}).get(dst)
        if rate is None:
            return f"Unknown target currency: {dst}."
        converted = amount * rate
        return f"{amount:,.2f} {src} = {converted:,.2f} {dst} (rate {rate:.4f})"

    # ---- unit converter --------------------------------------------------
    @tool
    def convert_units(value: float, from_unit: str, to_unit: str) -> str:
        """Convert a value between physical units.

        Handles length, mass, temperature, volume, speed, time, data, etc.
        Examples: (10, "km", "mi"), (72, "degF", "degC"), (5, "kg", "lb").
        """
        nonlocal ureg
        try:
            if ureg is None:
                from pint import UnitRegistry

                ureg = UnitRegistry()
            result = ureg.Quantity(value, from_unit).to(to_unit)
        except Exception as exc:
            return f"Could not convert {value} {from_unit} to {to_unit}: {exc}"
        return f"{value} {from_unit} = {result.magnitude:.6g} {to_unit}"

    # ---- current time by timezone / country -----------------------------
    @tool
    def current_time(timezone_or_place: str) -> str:
        """Get the current local time for an IANA timezone, city, or country.

        Examples: "Asia/Kolkata", "Tokyo", "Germany", "UTC".
        """
        q = timezone_or_place.strip()

        # 1) direct IANA timezone (e.g. "Asia/Kolkata", "UTC")
        try:
            tz = ZoneInfo(q)
            return _format_time(q, tz)
        except Exception:
            pass

        # 2) country name -> timezone(s) via pytz
        code = {n.lower(): c for c, n in pytz.country_names.items()}.get(q.lower())
        if code and pytz.country_timezones.get(code):
            zones = pytz.country_timezones[code]
            primary = zones[0]
            out = _format_time(primary, ZoneInfo(primary))
            if len(zones) > 1:
                out += f"\n(This country spans {len(zones)} zones: {', '.join(zones)})"
            return out

        # 3) city / fuzzy match against IANA zone names
        key = q.lower().replace(" ", "_")
        matches = [
            z for z in available_timezones()
            if key == z.split("/")[-1].lower() or key in z.lower()
        ]
        if matches:
            best = sorted(matches, key=len)[0]
            return _format_time(best, ZoneInfo(best))

        return (
            f"Couldn't resolve '{timezone_or_place}' to a timezone. "
            "Try an IANA name like 'Europe/Paris' or a country/city name."
        )

    # ---- IP lookup for a domain / url -----------------------------------
    @tool
    def ip_lookup(domain_or_url: str) -> str:
        """Resolve a domain or URL to its IP address(es) and geolocation."""
        host = _extract_host(domain_or_url)
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
                    "Location of {ip}: {city}, {region}, {country} "
                    "(ISP: {isp})".format(
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

    # ---- email drafter (LLM) --------------------------------------------
    @tool
    def draft_email(recipient: str, subject: str, key_points: str,
                    tone: str = "professional") -> str:
        """Draft an email from a recipient, subject, key points, and tone.

        `key_points` is a free-text description of what to say. Returns a ready
        subject line and body.
        """
        system = (
            "You are an expert email writer. Write a clear, well-structured "
            f"email in a {tone} tone. Return a 'Subject:' line followed by the "
            "body, with a greeting and sign-off. Do not add commentary."
        )
        user = f"Recipient: {recipient}\nSubject hint: {subject}\nKey points:\n{key_points}"
        return _llm_task(util_llm, system, user)

    # ---- summarizer (LLM) -----------------------------------------------
    @tool
    def summarize_text(text: str, style: str = "concise") -> str:
        """Summarize a block of text. `style` e.g. 'concise', 'bullets', 'tl;dr'."""
        system = (
            f"Summarize the user's text in a {style} style. Preserve key facts, "
            "names, and numbers. Output only the summary."
        )
        return _llm_task(util_llm, system, text)

    # ---- translator (LLM) -----------------------------------------------
    @tool
    def translate_text(text: str, target_language: str,
                       source_language: str = "auto") -> str:
        """Translate text into `target_language` (e.g. 'French', 'Hindi', 'ja')."""
        src = "" if source_language == "auto" else f" from {source_language}"
        system = (
            f"You are a professional translator. Translate the user's text{src} "
            f"into {target_language}. Preserve meaning, tone, and formatting. "
            "Output only the translation."
        )
        return _llm_task(util_llm, system, text)

    return [
        web_search,
        convert_currency,
        convert_units,
        current_time,
        ip_lookup,
        draft_email,
        summarize_text,
        translate_text,
    ]


def _format_time(label: str, tz: ZoneInfo) -> str:
    now = datetime.now(tz)
    return f"Current time in {label}: {now:%Y-%m-%d %H:%M:%S %Z%z} ({now:%A})"
