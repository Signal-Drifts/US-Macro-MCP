"""
The FRED data client for US-Macro-MCP.

What this file does, in order:
1. Reads the FRED API key from the environment, falling back to a .env file next to the project.
2. Sends read-only HTTP requests to the FRED API and raises a clear error if the key is missing or rejected.
3. Keeps every answer in a memory cache for a while, so repeated questions do not re-hit FRED - fast-moving
   daily series are cached for an hour, monthly series for half a day.
4. Converts the raw list of dated numbers FRED returns into a summary: the latest value, the value before it,
   the value one year earlier, and the changes between them.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

FRED_BASE_URL = "https://api.stlouisfed.org/fred"


# Our own log channel. Everything logged here goes to stderr, which MCP clients capture into their
# own log files, so nothing written through it may ever contain the API key.
log = logging.getLogger("us_macro_mcp")

# httpx logs every request as a complete URL, and a FRED URL carries the API key in plain sight.
# Turning its logger down to WARNING is what stops the key from being written into a client's logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Why this server caches at all: one tool call is not one network call. A single macro_snapshot()
# fetches 19 indicators, and a normal conversation asks for the same series more than once - "what is
# CPI" followed by "compare CPI to wages" hits CPI twice. Without a cache the client repeats every
# round trip to St. Louis on every question, spending network time and eating into FRED's limit of
# 120 requests per minute per key.
#
# How long an answer is held is decided by how often the number can actually change, not by how often
# it is asked for. CPI is published once a month, so holding it for half a day risks nothing except
# being a few hours late on release morning. A Treasury yield moves every business day, so one hour
# keeps it current. Weekly series sit in between.
#
# These values are a starting point, not a rule. Anyone running this server can raise them to cut
# network calls further, or lower them to get data the moment it is published. The cache is held in
# memory only and is thrown away when the server process exits.
CACHE_SECONDS = {
    "Daily": 60 * 60,
    "Weekly": 60 * 60 * 6,
    "Monthly": 60 * 60 * 12,
    "Quarterly": 60 * 60 * 12,
    "Annual": 60 * 60 * 24,
    "metadata": 60 * 60 * 24,
}


# Raised whenever we cannot get usable data out of FRED, with a message safe to show the user.
class FredError(RuntimeError):
    pass


# Reads KEY=VALUE lines out of a .env file and puts them into the environment if not already set.
def _load_env_file() -> None:
    for folder in (Path.cwd(), *Path(__file__).resolve().parents):
        env_path = folder / ".env"
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
        return


# Returns the FRED API key, or explains exactly how to get one if it is not configured.
def get_api_key() -> str:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        _load_env_file()
        key = os.environ.get("FRED_API_KEY")
    if not key:
        raise FredError(
            "No FRED API key found. Request a free key at "
            "https://fredaccount.stlouisfed.org/apikeys and set it as the "
            "FRED_API_KEY environment variable."
        )
    return key.strip()


# The in-memory cache: maps a request signature to the answer and the moment it expires.
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = asyncio.Lock()


# Returns a cached answer if it has not expired yet, otherwise None.
async def _cache_get(key: str) -> Any | None:
    async with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            _cache.pop(key, None)
            return None
        return value


# Stores an answer in the cache with the time-to-live that suits how often the data updates.
async def _cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    async with _cache_lock:
        _cache[key] = (time.monotonic() + ttl_seconds, value)


# Removes the API key from any text before it is logged or shown, so it can never escape into a log file.
def _redact(text: str) -> str:
    key = os.environ.get("FRED_API_KEY", "")
    cleaned = text.replace(key, "***REDACTED***") if key else text
    return re.sub(r"(api_key=)[^&\s]+", r"\1***REDACTED***", cleaned)


# Performs one GET request against a FRED endpoint, attaching the API key and asking for JSON.
# On success it logs only the endpoint, the series asked for, and the status code - never the URL or key.
# On failure it logs what actually went wrong, still with the key stripped out, and turns FRED's own
# words into an error the user can act on - including the rate limit message, passed through as-is.
async def _get(path: str, params: dict[str, Any], ttl_seconds: int) -> dict[str, Any]:
    query = {k: v for k, v in params.items() if v is not None}
    cache_key = f"{path}?{sorted(query.items())}"

    cached = await _cache_get(cache_key)
    if cached is not None:
        log.debug("cache hit: %s %s", path, query.get("series_id", ""))
        return cached

    label = query.get("series_id") or query.get("release_id") or ""

    query["api_key"] = get_api_key()
    query["file_type"] = "json"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{FRED_BASE_URL}/{path}", params=query)
    except httpx.TimeoutException as exc:
        log.error("FRED timeout: %s %s", path, label)
        raise FredError(f"FRED did not respond within 30 seconds for {path} {label}.") from exc
    except httpx.HTTPError as exc:
        log.error("FRED connection failed: %s %s: %s", path, label, _redact(str(exc)))
        raise FredError(f"Could not reach the FRED API for {path} {label}: {_redact(str(exc))}") from exc

    # A successful call logs the bare minimum: which endpoint, which series, which status code.
    if response.status_code == 200:
        log.info("FRED %s %s -> %s", path, label, response.status_code)
        payload = response.json()
        await _cache_set(cache_key, payload, ttl_seconds)
        return payload

    # Everything below is a failure, so we log the detail FRED sent back - always redacted first.
    detail = _redact(response.text.strip()[:300]) or "no detail returned"
    log.error("FRED %s %s -> %s: %s", path, label, response.status_code, detail)

    # FRED answers 429 once a key passes 120 requests per minute. Pass its own wording through
    # unchanged, so the user knows this is a rate limit and not a broken key or a bad series.
    if response.status_code == 429:
        raise FredError(
            f"FRED rate limit reached (HTTP 429). FRED says: {detail} "
            "Wait about a minute before asking again, or request fewer indicators at once."
        )
    # FRED answers 400 with a plain explanation when the key is missing, malformed or the series is unknown.
    if response.status_code == 400:
        raise FredError(f"FRED rejected the request (HTTP 400). FRED says: {detail}")
    if response.status_code in (401, 403):
        raise FredError(f"FRED refused the API key (HTTP {response.status_code}). FRED says: {detail}")
    if response.status_code >= 500:
        raise FredError(
            f"FRED is having server trouble (HTTP {response.status_code}) for {path} {label}. "
            "This is on their end - try again shortly."
        )
    raise FredError(f"FRED returned HTTP {response.status_code} for {path} {label}: {detail}")

# Fetches the official FRED description of a series: its title, units, frequency and last update time.
async def get_series_meta(series_id: str) -> dict[str, Any]:
    payload = await _get("series", {"series_id": series_id}, CACHE_SECONDS["metadata"])
    items = payload.get("seriess") or []
    if not items:
        raise FredError(f"FRED has no series called {series_id}.")
    return items[0]


# Fetches the dated numbers for a series, dropping the placeholder rows FRED uses for missing data.
async def get_observations(
    series_id: str,
    start: str | None = None,
    end: str | None = None,
    frequency_hint: str = "Monthly",
) -> list[dict[str, Any]]:
    ttl = CACHE_SECONDS.get(frequency_hint, CACHE_SECONDS["Monthly"])
    payload = await _get(
        "series/observations",
        {"series_id": series_id, "observation_start": start, "observation_end": end},
        ttl,
    )

    points: list[dict[str, Any]] = []
    for row in payload.get("observations", []):
        raw = row.get("value")
        if raw in (None, "", "."):
            continue                       # FRED writes "." for holidays and missing readings
        try:
            points.append({"date": row["date"], "value": float(raw)})
        except (TypeError, ValueError):
            continue
    return points


# Looks up which FRED release publishes a series, so we know when its next update is due.
async def get_series_release(series_id: str) -> dict[str, Any] | None:
    payload = await _get("series/release", {"series_id": series_id}, CACHE_SECONDS["metadata"])
    releases = payload.get("releases") or []
    return releases[0] if releases else None


# Fetches every scheduled FRED release date between two dates, for the release calendar tool.
async def get_release_dates(start: date, end: date) -> list[dict[str, Any]]:
    payload = await _get(
        "releases/dates",
        {
            "realtime_start": start.isoformat(),
            "realtime_end": end.isoformat(),
            "include_release_dates_with_no_data": "true",
            "sort_order": "asc",
            "limit": 1000,
        },
        CACHE_SECONDS["Daily"],
    )
    return payload.get("release_dates", [])


# Picks the observation closest to a target date, so we can compare against roughly one year ago.
def _nearest_observation(points: list[dict[str, Any]], target: date, tolerance_days: int) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_gap = tolerance_days + 1
    for point in points:
        gap = abs((datetime.strptime(point["date"], "%Y-%m-%d").date() - target).days)
        if gap < best_gap:
            best, best_gap = point, gap
    return best


# Divides safely so a zero or missing baseline returns None instead of crashing the tool.
def percent_change(new: float | None, old: float | None) -> float | None:
    if new is None or old in (None, 0):
        return None
    return round((new - old) / abs(old) * 100, 2)


# Turns a list of dated numbers into the headline summary: latest, previous, year-ago and the changes between.
def summarize(points: list[dict[str, Any]]) -> dict[str, Any]:
    if not points:
        return {"latest": None, "note": "No observations returned for this period."}

    ordered = sorted(points, key=lambda p: p["date"])
    latest = ordered[-1]
    previous = ordered[-2] if len(ordered) > 1 else None

    latest_date = datetime.strptime(latest["date"], "%Y-%m-%d").date()
    year_ago = _nearest_observation(ordered[:-1], latest_date - timedelta(days=365), tolerance_days=45)

    change = round(latest["value"] - previous["value"], 4) if previous else None
    yoy_change = round(latest["value"] - year_ago["value"], 4) if year_ago else None

    return {
        "latest_value": latest["value"],
        "latest_date": latest["date"],
        "previous_value": previous["value"] if previous else None,
        "previous_date": previous["date"] if previous else None,
        "change": change,
        "percent_change": percent_change(latest["value"], previous["value"] if previous else None),
        "year_ago_value": year_ago["value"] if year_ago else None,
        "year_ago_date": year_ago["date"] if year_ago else None,
        "year_over_year_change": yoy_change,
        "year_over_year_percent": percent_change(latest["value"], year_ago["value"] if year_ago else None),
        "observation_count": len(ordered),
    }


# Chooses how far back to fetch so there is always at least one full year of history to compare against.
def default_start(frequency: str) -> str:
    years = 3 if frequency in ("Quarterly", "Annual") else 2
    return (date.today() - timedelta(days=365 * years + 30)).isoformat()
