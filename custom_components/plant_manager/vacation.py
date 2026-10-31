"""Vacation planning. Pure functions, no Home Assistant state.

Every plant's water balance is projected through the time away, with the
climate it has now and the season in the middle of the trip:

- plants that last until you are back need nothing,
- plants that would run dry are watered right before leaving,
- if that is not enough, simple measures stretch the interval (out of direct
  sun, a cachepot around a porous pot),
- whatever still runs dry gets visits from a plant sitter. Visits are shared:
  when one plant needs water, the sitter also waters the others that are dry
  enough and would not last until you are back.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, tzinfo
from typing import Any

from .care import compute_interval, growth_level

LEAVE_HOUR = 8  # you leave in the morning of the first day
BACK_HOUR = 18  # and are back in the evening of the last day
VISIT_HOUR = 12

PREP_MIN_DRYNESS = 0.3  # watering a plant that is still this moist risks rot
VISIT_MIN_DRYNESS = 0.6  # on a visit, the sitter also waters plants at least this dry

RISK_OK = "ok"
RISK_MEASURES = "measures"
RISK_SITTER = "sitter"

TIP_TEXT = {
    "shade": "Move it out of direct sun, a few metres from the window",
    "cachepot": "Put the pot in a plastic or glazed cachepot so the walls don't dry it out",
    "sensor": "The soil moisture sensor shows when it really needs water",
}


def trip_times(start: date, end: date, tz: tzinfo) -> tuple[datetime, datetime]:
    """When you leave and when you are back."""
    return (
        datetime.combine(start, time(LEAVE_HOUR), tz),
        datetime.combine(end, time(BACK_HOUR), tz),
    )


def _days(delta: timedelta) -> float:
    return delta.total_seconds() / 86400


def _measures(plant: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """Measures that slow down drying, and the plant as it would be with them."""
    codes: list[str] = []
    changes: dict[str, Any] = {}
    if plant.get("light") in ("direct", "bright_indirect"):
        codes.append("shade")
        changes["light"] = "medium"
    if plant.get("pot_material") in ("terracotta", "fabric"):
        codes.append("cachepot")
        changes["pot_material"] = "plastic"
    return codes, {**plant, **changes}


def _checkpoints(start: datetime, back: datetime, tz: tzinfo) -> list[datetime]:
    """Times the sitter could come: now or the moment you leave, then noon every day."""
    times = [start]
    day = start.astimezone(tz).date()
    while (noon := datetime.combine(day, time(VISIT_HOUR), tz)) < back:
        if noon > start:
            times.append(noon)
        day += timedelta(days=1)
    return [*times, back]


def plan(
    plants: list[dict[str, Any]],
    statuses: dict[str, dict[str, Any]],
    leave: datetime,
    back: datetime,
    now: datetime,
    latitude: float,
) -> dict[str, Any]:
    """Plan the plants' care for a trip from ``leave`` to ``back``.

    Before the trip, plants are assumed to be watered when they are due as
    usual. During the trip (``now`` after ``leave``), the plan starts from the
    current water balance, so it follows the sitter's waterings.
    """
    tz = leave.tzinfo or now.tzinfo
    active = now >= leave
    start = max(now, leave)
    away_days = _days(back - start)
    growth = growth_level(leave + (back - leave) / 2, latitude)

    def interval(p: dict[str, Any]) -> float:
        return compute_interval(
            p, temperature=p.get("temp_ema"), humidity=p.get("humidity_ema"), growth=growth
        )[0]

    entries: list[dict[str, Any]] = []
    for plant in plants:
        status = statuses.get(plant["id"])
        if status is None:
            continue
        trip_interval = interval(plant)
        dryness = float(plant.get("dryness") or status["dryness"] or 0.0)
        prepare = False
        if not active:
            dryness += _days(leave - now) / status["interval_days"]
            # Until you leave, it is watered whenever it is due.
            dryness %= 1.0
            if dryness + away_days / trip_interval >= 1 and dryness >= PREP_MIN_DRYNESS:
                prepare, dryness = True, 0.0

        codes, measured = _measures(plant)
        stretched = interval(measured) if codes else trip_interval
        back_dryness = dryness + away_days / trip_interval
        if back_dryness < 1:
            risk, codes = RISK_OK, []
        elif (with_measures := dryness + away_days / stretched) < 1:
            risk, back_dryness = RISK_MEASURES, with_measures
        else:
            risk = RISK_SITTER
            if plant.get("moisture_sensor"):
                codes = [*codes, "sensor"]
        entries.append(
            {
                "plant_id": plant["id"],
                "name": plant["name"],
                "area_id": plant.get("area_id"),
                "interval_days": round(trip_interval, 2),
                "prepare": prepare,
                "risk": risk,
                "tips": codes,
                "lasts_days": round(max(0.0, 1 - dryness) * trip_interval, 1),
                "lasts_with_measures_days": round(max(0.0, 1 - dryness) * stretched, 1),
                "visits": [],
                "back_dryness": back_dryness,
                "_dryness": dryness,
                "_rate": 1 / trip_interval,
            }
        )

    sitter = [e for e in entries if e["risk"] == RISK_SITTER]
    visits = _plan_visits(sitter, start, back, tz)
    for entry in entries:
        dryness = entry.pop("_dryness")
        entry.pop("_rate")
        if entry["risk"] == RISK_SITTER:
            entry["back_dryness"] = dryness
        entry["back_dryness"] = round(entry["back_dryness"], 2)
    entries.sort(key=lambda e: (e["risk"] != RISK_SITTER, e["risk"] != RISK_MEASURES, e["name"]))
    return {
        "leave": leave.isoformat(),
        "back": back.isoformat(),
        "days": round(_days(back - leave), 1),
        "active": active,
        "prepare": [e["plant_id"] for e in entries if e["prepare"]],
        "visits": visits,
        "plants": entries,
    }


def _plan_visits(
    entries: list[dict[str, Any]], start: datetime, back: datetime, tz: tzinfo
) -> list[dict[str, Any]]:
    """Sitter visits, as few as possible. Updates each entry's dryness to when you are back."""
    if not entries:
        return []
    times = _checkpoints(start, back, tz)
    visits: dict[str, list[str]] = {}
    previous = start
    for index, when in enumerate(times[:-1]):
        for entry in entries:
            entry["_dryness"] += _days(when - previous) * entry["_rate"]
        previous = when
        following = times[index + 1]
        due = [e for e in entries if e["_dryness"] + _days(following - when) * e["_rate"] >= 1]
        if not due:
            continue
        due_ids = {e["plant_id"] for e in due}
        water = [
            e
            for e in entries
            if e["plant_id"] in due_ids
            or (
                e["_dryness"] >= VISIT_MIN_DRYNESS
                and e["_dryness"] + _days(back - when) * e["_rate"] >= 1
            )
        ]
        day = when.astimezone(tz).date().isoformat()
        for entry in water:
            entry["_dryness"] = 0.0
            if day not in entry["visits"]:
                entry["visits"].append(day)
            visits.setdefault(day, [])
            if entry["plant_id"] not in visits[day]:
                visits[day].append(entry["plant_id"])
    for entry in entries:
        entry["_dryness"] += _days(back - previous) * entry["_rate"]
    return [{"date": day, "plant_ids": ids} for day, ids in sorted(visits.items())]


def _day(value: str) -> str:
    return date.fromisoformat(value).strftime("%a %d %b").replace(" 0", " ")


def plan_text(
    vacation: dict[str, Any],
    trip: dict[str, Any],
    label: dict[str, str],
) -> str:
    """The sitter's plan as plain text. ``label`` maps plant ids to "Name (Area)"."""
    leave = datetime.fromisoformat(trip["leave"]).date().isoformat()
    back = datetime.fromisoformat(trip["back"]).date().isoformat()
    lines = [f"🪴 Plant care from {_day(leave)} to {_day(back)}"]
    if vacation.get("sitter"):
        lines.append(f"Thank you, {vacation['sitter']}!")
    lines.append("")
    if trip["visits"]:
        lines.append("Please water on these days:")
        for visit in trip["visits"]:
            names = ", ".join(label.get(pid, pid) for pid in visit["plant_ids"])
            lines.append(f"• {_day(visit['date'])}: {names}")
        lines += [
            "",
            "Water slowly until it runs out at the bottom, then empty the saucer after 15 minutes. "
            "If the soil is still moist 2 cm deep, skip it.",
        ]
    else:
        lines.append("Nothing to water, all plants last until we are back.")
    if notes := (vacation.get("notes") or "").strip():
        lines += ["", notes]
    return "\n".join(lines)
