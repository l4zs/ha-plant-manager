"""Alerts derived from the plants' care status. Pure functions."""

from __future__ import annotations

from typing import Any

from .care import PROBLEM_TEXT
from .i18n import tr

KIND_WATER = "water"
KIND_FERTILIZE = "fertilize"
KIND_PROBLEM = "problem"


def alert_message(alert: dict[str, Any], lang: str | None) -> str:
    """The alert as a sentence in a language."""
    name = alert["name"]
    if alert["kind"] == KIND_WATER:
        if alert["severity"] == "high":
            return tr(lang, "{name} is overdue for water", name=name)
        return tr(lang, "{name} needs water", name=name)
    if alert["kind"] == KIND_FERTILIZE:
        return tr(lang, "{name} could use fertilizer", name=name)
    return f"{name}: " + ", ".join(tr(lang, PROBLEM_TEXT[code]) for code in alert["problems"])


def compute_alerts(
    plants: list[dict[str, Any]], statuses: dict[str, dict[str, Any]], lang: str | None = None
) -> list[dict[str, Any]]:
    """Return the active alerts. Each has a stable ``key`` so it is announced once."""
    alerts: list[dict[str, Any]] = []
    for plant in plants:
        status = statuses.get(plant["id"])
        if status is None:
            continue
        base = {"plant_id": plant["id"], "name": plant["name"]}
        if status["needs_water"]:
            overdue = status["status"] == "overdue"
            alerts.append(
                {
                    "key": f"water_{plant['id']}",
                    "kind": KIND_WATER,
                    **base,
                    "severity": "high" if overdue else "medium",
                }
            )
        if status["fertilize_due"]:
            alerts.append(
                {
                    "key": f"fertilize_{plant['id']}",
                    "kind": KIND_FERTILIZE,
                    **base,
                    "severity": "low",
                }
            )
        problems = [code for code in status["problems"] if code != "watering_overdue"]
        if problems:
            alerts.append(
                {
                    # The key includes the problems, so a new problem is announced again.
                    "key": f"problem_{plant['id']}_{'_'.join(sorted(problems))}",
                    "kind": KIND_PROBLEM,
                    **base,
                    "severity": "medium",
                    "problems": problems,
                }
            )
    for alert in alerts:
        alert["message"] = alert_message(alert, lang)
    return alerts


def summary_message(
    plants: list[dict[str, Any]], statuses: dict[str, dict[str, Any]], lang: str | None = None
) -> str:
    """The daily reminder: what needs water (today) and fertilizer."""
    water = sorted(
        plant["name"]
        for plant in plants
        if (status := statuses.get(plant["id"]))
        and (status["needs_water"] or status["days_until_watering"] < 1)
    )
    fertilize = sorted(
        plant["name"]
        for plant in plants
        if (status := statuses.get(plant["id"])) and status["fertilize_due"]
    )
    lines = []
    if water:
        lines.append(tr(lang, "💧 Water: {names}", names=", ".join(water)))
    if fertilize:
        lines.append(tr(lang, "🌱 Fertilize: {names}", names=", ".join(fertilize)))
    return "\n".join(lines)
