"""
The FOMC meeting calendar for US-Macro-MCP.

What this file does, in order:
1. Holds the Federal Reserve's published FOMC meeting schedule as a plain hardcoded list, because the
   Fed publishes it as a web page and offers no API for it - not even through FRED.
2. Marks which meetings also publish the Summary of Economic Projections, the quarterly meetings where
   the Fed releases its own forecasts for rates, inflation and unemployment.
3. Answers the two questions the release calendar needs: which meetings fall inside a date window, and
   when the next one is.
4. Reports when this hardcoded list is close to running out, so the answer says so instead of going
   quietly empty.

Maintenance: the Fed publishes roughly two years ahead and revises the schedule about once a year.
Refresh this list every January from federalreserve.gov/monetarypolicy/fomccalendars.htm and move
VALID_THROUGH forward to match. See the annual checklist in README.md.
"""

from __future__ import annotations

from datetime import date

# The last date this hardcoded schedule can be trusted to be complete.
VALID_THROUGH = date(2027, 12, 31)

# Source: federalreserve.gov/monetarypolicy/fomccalendars.htm, read 27 July 2026.
# Each entry is (first day, last day, whether the Summary of Economic Projections is published).
SCHEDULE: tuple[tuple[date, date, bool], ...] = (
    (date(2026, 1, 27), date(2026, 1, 28), False),
    (date(2026, 3, 17), date(2026, 3, 18), True),
    (date(2026, 4, 28), date(2026, 4, 29), False),
    (date(2026, 6, 16), date(2026, 6, 17), True),
    (date(2026, 7, 28), date(2026, 7, 29), False),
    (date(2026, 9, 15), date(2026, 9, 16), True),
    (date(2026, 10, 27), date(2026, 10, 28), False),
    (date(2026, 12, 8), date(2026, 12, 9), True),
    (date(2027, 1, 26), date(2027, 1, 27), False),
    (date(2027, 3, 16), date(2027, 3, 17), True),
    (date(2027, 4, 27), date(2027, 4, 28), False),
    (date(2027, 6, 8), date(2027, 6, 9), True),
    (date(2027, 7, 27), date(2027, 7, 28), False),
    (date(2027, 9, 14), date(2027, 9, 15), True),
    (date(2027, 10, 26), date(2027, 10, 27), False),
    (date(2027, 12, 7), date(2027, 12, 8), True),
)


# Turns one schedule entry into the dictionary shape the tools return.
def _as_dict(start: date, end: date, projections: bool) -> dict[str, object]:
    return {
        "starts": start.isoformat(),
        "ends": end.isoformat(),
        "decision_announced": end.isoformat(),
        "economic_projections": projections,
        "note": (
            "Rate decision announced on the final day at 2pm Eastern, with the Fed's own forecasts."
            if projections
            else "Rate decision announced on the final day at 2pm Eastern."
        ),
    }


# Returns every FOMC meeting that starts inside a date window, for the release calendar.
def in_window(start: date, end: date) -> list[dict[str, object]]:
    return [_as_dict(a, b, sep) for a, b, sep in SCHEDULE if start <= a <= end]


# Returns the next meeting on or after a given day, or a warning when the schedule has run out.
def next_meeting(today: date) -> dict[str, object] | None:
    for a, b, sep in SCHEDULE:
        if b >= today:
            meeting = _as_dict(a, b, sep)
            meeting["days_away"] = (a - today).days
            return meeting
    return None


# True when the hardcoded schedule is within six months of running out and needs a refresh.
def needs_refresh(today: date) -> bool:
    return (VALID_THROUGH - today).days < 180