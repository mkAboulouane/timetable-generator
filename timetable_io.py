from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from timetable_agent import (
    TimeSlot, Group, Room, Teacher, Event,
    TimetablingProblem, AssignmentTuple,
    event_demand,
)


def load_input_json(path: str) -> Tuple[Dict[str, Any], TimetablingProblem]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = data.get("config", {})
    use_mrv = bool(config.get("use_mrv", True))

    timeslots = [
        TimeSlot(
            id=t["id"],
            day=t["day"],
            start=t["start"],
            end=t["end"],
            duration_min=int(t["duration_min"]),
        )
        for t in data["timeslots"]
    ]

    groups = [
        Group(
            id=g["id"],
            size=int(g["size"]),
            available=frozenset(g.get("available", [])),
        )
        for g in data["groups"]
    ]

    rooms = [
        Room(
            id=r["id"],
            capacity=int(r["capacity"]),
            available=frozenset(r.get("available", [])),
        )
        for r in data["rooms"]
    ]

    teachers = [
        Teacher(
            id=t["id"],
            available=frozenset(t.get("available", [])),
        )
        for t in data["teachers"]
    ]

    events = [
        Event(
            id=e["id"],
            teacher_id=e["teacher_id"],
            group_ids=tuple(e.get("group_ids", [])),
            duration_min=int(e["duration_min"]),
            allowed_slots=frozenset(e["allowed_slots"]) if "allowed_slots" in e else None,
        )
        for e in data["events"]
    ]

    problem = TimetablingProblem(
        initial_state=tuple(),
        events=events,
        timeslots=timeslots,
        rooms=rooms,
        teachers=teachers,
        groups=groups,
        use_mrv=use_mrv,
    )

    return config, problem


def export_output_json(
    path: str,
    *,
    config: Dict[str, Any],
    problem: TimetablingProblem,
    final_state: AssignmentTuple | None,
    status: str,
    strategy: str,
):
    output: Dict[str, Any] = {
        "meta": {
            "week_name": config.get("week_name", ""),
            "strategy": strategy,
            "use_mrv": bool(config.get("use_mrv", True)),
            "status": status,
            "events_total": len(problem.events_list),
            "events_scheduled": 0 if final_state is None else len(final_state),
        },
        "assignments": []
    }

    if final_state is not None:
        for (eid, tid, rid) in final_state:
            e = problem.events[eid]
            dem = event_demand(e, problem.groups)
            output["assignments"].append({
                "event_id": eid,
                "teacher_id": e.teacher_id,
                "group_ids": list(e.group_ids),
                "timeslot_id": tid,
                "room_id": rid,
                "demand": dem,
                "room_capacity": problem.rooms[rid].capacity,
            })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)