"""Alerts derived from the plants' care status. Pure functions."""

from __future__ import annotations

from typing import Any

from .care import PROBLEM_TEXT

KIND_WATER = "water"
KIND_FERTILIZE = "fertilize"
KIND_PROBLEM = "problem"


def compute_alerts(
    plants: list[dict[str, Any]], statuses: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return the active alerts. Each has a stable ``key`` so it is announced once."""
    alerts: list[dict[str, Any]] = []
    for plant in plants:
        status = statuses.get(plant["id"])
        if status is None:
            continue
        name = plant["name"]
        if status["needs_water"]:
            overdue = status["status"] == "overdue"
            alerts.append(
                {
                    "key": f"water_{plant['id']}",
                    "kind": KIND_WATER,
                    "plant_id": plant["id"],
                    "severity": "high" if overdue else "medium",
                    "message": f"{name} is overdue for water" if overdue else f"{name} needs water",
                }
            )
        if status["fertilize_due"]:
            alerts.append(
                {
                    "key": f"fertilize_{plant['id']}",
                    "kind": KIND_FERTILIZE,
                    "plant_id": plant["id"],
                    "severity": "low",
                    "message": f"{name} could use fertilizer",
                }
            )
        problems = [code for code in status["problems"] if code != "watering_overdue"]
        if problems:
            alerts.append(
                {
                    # The key includes the problems, so a new problem is announced again.
                    "key": f"problem_{plant['id']}_{'_'.join(sorted(problems))}",
                    "kind": KIND_PROBLEM,
                    "plant_id": plant["id"],
                    "severity": "medium",
                    "problems": problems,
                    "message": f"{name}: " + ", ".join(PROBLEM_TEXT[code] for code in problems),
                }
            )
    return alerts


def summary_message(plants: list[dict[str, Any]], statuses: dict[str, dict[str, Any]]) -> str:
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
        lines.append("💧 Water: " + ", ".join(water))
    if fertilize:
        lines.append("🌱 Fertilize: " + ", ".join(fertilize))
    return "\n".join(lines)
