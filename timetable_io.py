from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from timetable_agent import (
    TimeSlot, Group, Room, Teacher, Event,
    TimetablingProblem, AssignmentTuple,
    event_demand,
)


def load_input_json(path: str) -> Tuple[Dict[str, Any], TimetablingProblem]:
    """
    Loads input JSON v2 with:
      - config
      - timeslots
      - rooms
      - teachers
      - sessions[] each having groups[] and modules[] (modules have min_room_capacity and events[])
    Returns (config, problem)
    """
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

    sessions = data.get("sessions", [])
    if not sessions:
        raise ValueError("Input JSON must contain a non-empty 'sessions' list (v2 format).")

    # Flatten sessions/modules into global lists of groups/events
    groups: List[Group] = []
    events: List[Event] = []

    for s in sessions:
        session_id = s["id"]

        session_groups = [
            Group(
                id=g["id"],
                size=int(g["size"]),
                available=frozenset(g.get("available", [])),
            )
            for g in s.get("groups", [])
        ]
        groups.extend(session_groups)

        session_group_ids = [g.id for g in session_groups]

        for m in s.get("modules", []):
            module_id = m["id"]
            min_room_capacity = int(m.get("min_room_capacity", 0))

            for e in m.get("events", []):
                audience = e.get("audience", {"type": "groups", "group_ids": []})
                aud_type = audience.get("type", "groups")

                if aud_type == "all_groups":
                    group_ids = session_group_ids
                elif aud_type == "groups":
                    group_ids = audience.get("group_ids", [])
                else:
                    raise ValueError(
                        f"Unknown audience.type='{aud_type}' in event '{e.get('id')}'. "
                        f"Use 'all_groups' or 'groups'."
                    )

                events.append(
                    Event(
                        id=e["id"],
                        teacher_id=e["teacher_id"],
                        group_ids=tuple(group_ids),
                        duration_min=int(e["duration_min"]),
                        allowed_slots=frozenset(e["allowed_slots"]) if "allowed_slots" in e else None,
                        min_room_capacity=min_room_capacity,
                        session_id=session_id,
                        module_id=module_id,
                    )
                )

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
    """
    Exports result in a JSON file:
      meta + assignments list
    """
    output: Dict[str, Any] = {
        "meta": {
            "week_name": config.get("week_name", ""),
            "strategy": strategy,
            "use_mrv": bool(config.get("use_mrv", True)),
            "status": status,
            "events_total": len(problem.events_list),
            "events_scheduled": 0 if final_state is None else len(final_state),
        },
        "assignments": [],
    }

    if final_state is not None:
        for (eid, tid, rid) in final_state:
            e = problem.events[eid]
            dem = event_demand(e, problem.groups)
            required = max(dem, int(getattr(e, "min_room_capacity", 0)))
            output["assignments"].append({
                "event_id": eid,
                "session_id": getattr(e, "session_id", ""),
                "module_id": getattr(e, "module_id", ""),
                "teacher_id": e.teacher_id,
                "group_ids": list(e.group_ids),
                "timeslot_id": tid,
                "room_id": rid,
                "demand": dem,
                "min_room_capacity": int(getattr(e, "min_room_capacity", 0)),
                "required_capacity": required,
                "room_capacity": problem.rooms[rid].capacity,
            })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)