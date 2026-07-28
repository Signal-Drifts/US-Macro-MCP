"""
The MCP server for US-Macro-MCP - this is the file that defines the eight tools an AI assistant can call.

What this file does, in order:
1. Creates the MCP server object that Claude, Cursor or any other MCP client connects to.
2. Defines the eight tools in the order a user naturally works: see what exists, read one indicator,
   read its history, compare several, check the release calendar, take a whole-economy snapshot,
   check recession signals, and search by keyword.
3. Each tool asks the FRED client for data, then returns a plain dictionary with the numbers already
   calculated - so the AI never has to do arithmetic or guess a series ID.
4. Any failure is caught and returned as a readable "error" message rather than crashing the server.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import catalog, fomc, fred

mcp = FastMCP("US-Macro-MCP")

# Never ask FRED for more than this many series at once, to stay well inside its rate limits.
MAX_CONCURRENT_REQUESTS = 8


# Packages one indicator's numbers together with its labels, the shape every tool returns.
async def _load_indicator(item: catalog.Indicator) -> dict[str, Any]:
    points = await fred.get_observations(
        item.series_id,
        start=fred.default_start(item.frequency),
        frequency_hint=item.frequency,
    )
    result: dict[str, Any] = {
        "name": item.name,
        "title": item.title,
        "category": item.category,
        "units": item.units,
        "frequency": item.frequency,
        "series_id": item.series_id,
        "source": "Federal Reserve Economic Data (FRED), St. Louis Fed",
    }
    result.update(fred.summarize(points))
    if item.notes:
        result["how_to_read"] = item.notes
    return result


# Runs many indicator loads at once but caps the concurrency, returning an error entry for any that fail.
async def _load_many(items: tuple[catalog.Indicator, ...]) -> list[dict[str, Any]]:
    limiter = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def one(item: catalog.Indicator) -> dict[str, Any]:
        async with limiter:
            try:
                return await _load_indicator(item)
            except fred.FredError as exc:
                return {"name": item.name, "title": item.title, "error": str(exc)}

    return await asyncio.gather(*(one(item) for item in items))


# TOOL 1 - Shows the full menu of indicators available, so the assistant knows what it can ask for.
@mcp.tool()
def list_indicators(category: str | None = None) -> dict[str, Any]:
    """List every US economic indicator this server provides.

    Call this first to discover valid indicator names before using the other tools.

    Args:
        category: Optional filter. One of: inflation, employment, growth, housing,
            consumer, rates, stress, markets, fiscal. Omit to list all indicators.
    """
    items = catalog.in_category(category)
    if not items:
        return {
            "error": f"Unknown category '{category}'.",
            "valid_categories": list(catalog.CATEGORIES),
        }

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(item.category, []).append({
            "name": item.name,
            "title": item.title,
            "units": item.units,
            "frequency": item.frequency,
            "headline_indicator": item.major,
        })

    return {
        "total": len(items),
        "categories": list(catalog.CATEGORIES),
        "indicators_by_category": grouped,
    }


# TOOL 2 - Returns the current reading of a single indicator with its change since last time and last year.
@mcp.tool()
async def get_indicator(name: str) -> dict[str, Any]:
    """Get the latest value of one economic indicator, with its recent changes already calculated.

    Args:
        name: A friendly indicator name such as "cpi", "unemployment_rate",
            "jobless_claims" or "mortgage_30y". Use list_indicators to see all names.
    """
    item = catalog.find(name)
    if item is None:
        suggestions = [match.name for match in catalog.search(name, limit=5)]
        return {
            "error": f"No indicator named '{name}'.",
            "did_you_mean": suggestions or "Call list_indicators to see valid names.",
        }

    try:
        return await _load_indicator(item)
    except fred.FredError as exc:
        return {"error": str(exc)}


# TOOL 3 - Returns the full time series for one indicator, for trend questions and charting.
@mcp.tool()
async def get_history(
    name: str,
    start: str | None = None,
    end: str | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    """Get the historical time series for one indicator.

    Args:
        name: Friendly indicator name, for example "cpi" or "sp500".
        start: Optional first date as YYYY-MM-DD. Defaults to about two years ago.
        end: Optional last date as YYYY-MM-DD. Defaults to today.
        limit: Maximum number of data points to return, most recent kept. Defaults to 500.
    """
    item = catalog.find(name)
    if item is None:
        return {"error": f"No indicator named '{name}'. Call list_indicators to see valid names."}

    try:
        points = await fred.get_observations(
            item.series_id,
            start=start or fred.default_start(item.frequency),
            end=end,
            frequency_hint=item.frequency,
        )
    except fred.FredError as exc:
        return {"error": str(exc)}

    trimmed = points[-limit:] if limit and len(points) > limit else points
    return {
        "name": item.name,
        "title": item.title,
        "units": item.units,
        "frequency": item.frequency,
        "series_id": item.series_id,
        "start": trimmed[0]["date"] if trimmed else None,
        "end": trimmed[-1]["date"] if trimmed else None,
        "count": len(trimmed),
        "truncated": len(trimmed) < len(points),
        "observations": trimmed,
        "source": "Federal Reserve Economic Data (FRED), St. Louis Fed",
    }


# TOOL 4 - Puts several indicators side by side so they can be judged against each other.
@mcp.tool()
async def compare_indicators(names: list[str], period: str = "1y") -> dict[str, Any]:
    """Compare two or more indicators over the same period, for questions like
    "did wage growth beat inflation" or "how do the 2-year and 10-year yields compare".

    Args:
        names: Two or more friendly indicator names, for example ["cpi", "avg_hourly_earnings"].
        period: How far back to look - "1y", "2y", "5y" or "10y". Defaults to "1y".
    """
    if not names or len(names) < 2:
        return {"error": "Pass at least two indicator names to compare."}

    years = {"1y": 1, "2y": 2, "5y": 5, "10y": 10}.get(period.lower())
    if years is None:
        return {"error": f"Unknown period '{period}'. Use 1y, 2y, 5y or 10y."}
    start = (date.today() - timedelta(days=365 * years)).isoformat()

    resolved: list[catalog.Indicator] = []
    unknown: list[str] = []
    for name in names:
        item = catalog.find(name)
        resolved.append(item) if item else unknown.append(name)
    if unknown:
        return {"error": f"Unknown indicator names: {unknown}. Call list_indicators to see valid names."}

    limiter = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def one(item: catalog.Indicator) -> dict[str, Any]:
        async with limiter:
            try:
                points = await fred.get_observations(
                    item.series_id, start=start, frequency_hint=item.frequency
                )
            except fred.FredError as exc:
                return {"name": item.name, "error": str(exc)}

            summary = fred.summarize(points)
            first = points[0]["value"] if points else None
            # Percent change across the whole window is what makes series in different units comparable.
            summary["change_over_period_percent"] = fred.percent_change(
                summary.get("latest_value"), first
            )
            return {
                "name": item.name,
                "title": item.title,
                "units": item.units,
                "frequency": item.frequency,
                **summary,
            }

    return {
        "period": period,
        "start": start,
        "note": "Compare change_over_period_percent across indicators - raw values use different units.",
        "indicators": await asyncio.gather(*(one(item) for item in resolved)),
    }


# TOOL 5 - Lists which official economic reports are due out in the next few days.
@mcp.tool()
async def release_calendar(days_ahead: int = 14) -> dict[str, Any]:
    """Show which US economic data releases are scheduled over the coming days,
    for questions like "what economic data comes out this week".

    Args:
        days_ahead: How many days forward to look. Defaults to 14, maximum 90.
    """
    days_ahead = max(1, min(int(days_ahead), 90))
    today = date.today()

    try:
        upcoming = await fred.get_release_dates(today, today + timedelta(days=days_ahead))
    except fred.FredError as exc:
        return {"error": str(exc)}

    # Work out which FRED release publishes each headline indicator, so we can name the releases usefully.
    # Daily series are deliberately left out. Their releases - H.15 interest rates, the stock indexes,
    # the bond spread indices - republish every business day, which buries the handful of reports that
    # actually matter (CPI, the jobs report, GDP) under two dozen repeat entries in a single week.
    # Anyone who wants those daily republications can still find them in all_releases below.
    headline = tuple(item for item in catalog.CATALOG if item.major and item.frequency != "Daily")
    limiter = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def release_for(item: catalog.Indicator) -> tuple[int | None, str]:
        async with limiter:
            try:
                release = await fred.get_series_release(item.series_id)
            except fred.FredError:
                return None, item.name
            return (release or {}).get("id"), item.name

    pairs = await asyncio.gather(*(release_for(item) for item in headline))
    indicators_by_release: dict[int, list[str]] = {}
    for release_id, name in pairs:
        if release_id is not None:
            indicators_by_release.setdefault(release_id, []).append(name)

    scheduled: list[dict[str, Any]] = []
    for row in upcoming:
        release_id = row.get("release_id")
        entry = {
            "date": row.get("date"),
            "release": row.get("release_name"),
            "release_id": release_id,
        }
        if release_id in indicators_by_release:
            entry["indicators"] = indicators_by_release[release_id]
            entry["headline"] = True
        scheduled.append(entry)

    headline_only = [row for row in scheduled if row.get("headline")]
    return {
        "from": today.isoformat(),
        "to": (today + timedelta(days=days_ahead)).isoformat(),
        "headline_releases": headline_only,
        "headline_count": len(headline_only),
        "all_releases_count": len(scheduled),
        "all_releases": scheduled[:200],
        "fomc_meetings": fomc.in_window(today, today + timedelta(days=days_ahead)),
        "next_fomc_meeting": fomc.next_meeting(today),
        "fomc_schedule_valid_through": fomc.VALID_THROUGH.isoformat(),        
        "note": (
            "headline_releases are the scheduled reports that update this server's monthly and weekly "
            "indicators. Daily-republished releases such as interest rates and stock indexes are excluded "
            "from that list but still appear in all_releases. FOMC meeting dates come from the "
            "Federal Reserve's published schedule, not from FRED."
        ),
    }


# TOOL 6 - The whole-economy view: every headline indicator in one call, optionally narrowed to one category.
@mcp.tool()
async def macro_snapshot(category: str = "all") -> dict[str, Any]:
    """Get a current snapshot of the US economy in one call - the latest value and
    recent change for every headline indicator.

    Args:
        category: "all" for the headline indicators across every category, or one of
            inflation, employment, growth, housing, consumer, rates, stress, markets,
            fiscal to get every indicator in that category.
    """
    wanted = (category or "all").strip().lower()

    if wanted == "all":
        items = tuple(item for item in catalog.CATALOG if item.major)
        scope = "Headline indicators across all categories."
    else:
        items = catalog.in_category(wanted)
        scope = f"Every indicator in the {wanted} category."
        if not items:
            return {
                "error": f"Unknown category '{category}'.",
                "valid_categories": ["all", *catalog.CATEGORIES],
            }

    results = await _load_many(items)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        item = catalog.find(row["name"])
        grouped.setdefault(item.category if item else "other", []).append(row)

    return {
        "as_of": date.today().isoformat(),
        "scope": scope,
        "indicator_count": len(results),
        "by_category": grouped,
        "source": "Federal Reserve Economic Data (FRED), St. Louis Fed",
    }


# TOOL 7 - Checks the handful of series that historically warn of a downturn, and grades each one.
@mcp.tool()
async def recession_signals() -> dict[str, Any]:
    """Check the main US recession warning signals at once - the Sahm rule, the yield curve,
    credit spreads, jobless claims and financial conditions - each with a plain-English status.
    """
    watched = ("sahm_rule", "yield_curve", "high_yield_spread", "jobless_claims", "financial_conditions")
    items = tuple(catalog.BY_NAME[name] for name in watched)
    results = await _load_many(items)
    readings = {row["name"]: row for row in results}

    signals: list[dict[str, Any]] = []
    triggered = 0

    # Each rule below is the widely used threshold for that specific series.
    for name, row in readings.items():
        value = row.get("latest_value")
        if value is None:
            signals.append({"signal": name, "status": "unavailable", "detail": row.get("error", "No data.")})
            continue

        if name == "sahm_rule":
            hit = value >= 0.50
            detail = f"Sahm rule at {value}. At or above 0.50 has historically meant a recession has started."
        elif name == "yield_curve":
            hit = value < 0
            detail = f"10-year minus 2-year spread is {value} percent. Below zero is an inverted curve."
        elif name == "high_yield_spread":
            hit = value >= 5.0
            detail = f"High yield spread is {value} percent. Above about 5 percent signals credit stress."
        elif name == "jobless_claims":
            year_ago = row.get("year_over_year_percent")
            hit = year_ago is not None and year_ago >= 20
            detail = f"Initial claims at {int(value):,}, {year_ago} percent versus a year ago. A rise above 20 percent is a warning."
        else:  # financial_conditions
            hit = value > 0
            detail = f"Financial conditions index at {value}. Above zero means tighter than average."

        triggered += 1 if hit else 0
        signals.append({
            "signal": name,
            "title": row.get("title"),
            "value": value,
            "as_of": row.get("latest_date"),
            "status": "warning" if hit else "normal",
            "detail": detail,
        })

    if triggered == 0:
        overall = "No recession signals are currently triggered."
    elif triggered == 1:
        overall = "One signal is triggered. Watch, but a single signal is often a false alarm."
    elif triggered <= 3:
        overall = f"{triggered} signals are triggered. Elevated recession risk."
    else:
        overall = f"{triggered} signals are triggered. Broad-based recession warning."

    return {
        "as_of": date.today().isoformat(),
        "signals_triggered": triggered,
        "signals_checked": len(signals),
        "assessment": overall,
        "signals": signals,
        "disclaimer": "These are historical statistical indicators, not a forecast or investment advice.",
    }


# TOOL 8 - Finds the right indicator when the assistant only knows roughly what it is looking for.
@mcp.tool()
def search_indicators(query: str, limit: int = 10) -> dict[str, Any]:
    """Find indicators by keyword when you do not know the exact name -
    for example "gas prices", "wages", "mortgage" or "recession".

    Args:
        query: Free-text words to search for across indicator names, titles and descriptions.
        limit: Maximum number of matches to return. Defaults to 10.
    """
    matches = catalog.search(query, limit=max(1, min(int(limit), 25)))
    if not matches:
        return {
            "query": query,
            "matches": [],
            "hint": "No match. Call list_indicators to browse all available indicators by category.",
        }

    return {
        "query": query,
        "match_count": len(matches),
        "matches": [
            {
                "name": item.name,
                "title": item.title,
                "category": item.category,
                "units": item.units,
                "frequency": item.frequency,
            }
            for item in matches
        ],
    }


# Starts the server and speaks the MCP protocol over standard input and output.
def run() -> None:
    mcp.run()
