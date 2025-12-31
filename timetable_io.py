from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple, FrozenSet

from timetable_agent import (
    TimeSlot, Group, Room, Teacher, Event,
    TimetablingProblem, AssignmentTuple,
    event_demand,
)


def _parse_week_ranges(values: List[str]) -> List[int]:
    weeks: List[int] = []
    for item in values:
        item = str(item).strip()
        if "-" in item:
            a_str, b_str = item.split("-", 1)
            a = int(a_str.strip())
            b = int(b_str.strip())
            if b < a:
                raise ValueError(f"Invalid range '{item}' (end < start).")
            weeks.extend(list(range(a, b + 1)))
        else:
            weeks.append(int(item))
    return weeks


def parse_weeks(weeks_obj: Any, weeks_total: int) -> FrozenSet[int]:
    """
    weeks_obj can be:
      - None => all weeks 1..weeks_total
      - {"mode":"all"}
      - {"mode":"list","values":[1,3,5]}
      - {"mode":"ranges","values":["1-6","10-14"]}
    """
    if weeks_total <= 0:
        raise ValueError(f"weeks_total must be > 0, got {weeks_total}")

    if weeks_obj is None:
        return frozenset(range(1, weeks_total + 1))

    mode = str(weeks_obj.get("mode", "all")).lower()

    if mode == "all":
        return frozenset(range(1, weeks_total + 1))

    if mode == "list":
        vals = weeks_obj.get("values", [])
        weeks = [int(x) for x in vals]
        for w in weeks:
            if w < 1 or w > weeks_total:
                raise ValueError(f"Week {w} out of bounds 1..{weeks_total}")
        return frozenset(weeks)

    if mode == "ranges":
        vals = weeks_obj.get("values", [])
        weeks = _parse_week_ranges(vals)
        for w in weeks:
            if w < 1 or w > weeks_total:
                raise ValueError(f"Week {w} out of bounds 1..{weeks_total}")
        return frozenset(weeks)

    raise ValueError(f"Unknown weeks.mode '{mode}'. Use: all, list, ranges.")


def load_input_json(path: str) -> Tuple[Dict[str, Any], TimetablingProblem]:
    """
    JSON format (v3):
      config: { weeks_total, strategy, use_mrv, week_name }
      timeslots: [...]
      rooms: [...]
      teachers: [...]
      sessions: [
        {
          id, weeks_total(optional),
          groups: [...],
          modules: [
            { id, min_room_capacity, weeks(optional), events:[{..., weeks(optional)}] }
          ]
        }
      ]
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = data.get("config", {})
    use_mrv = bool(config.get("use_mrv", True))

    global_weeks_total = int(config.get("weeks_total", 16))

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
        raise ValueError("Input JSON must contain a non-empty 'sessions' list.")

    groups: List[Group] = []
    events: List[Event] = []

    for s in sessions:
        session_id = s["id"]
        session_weeks_total = int(s.get("weeks_total", global_weeks_total))

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

            module_weeks = parse_weeks(m.get("weeks"), session_weeks_total)

            for e in m.get("events", []):
                # event weeks override module weeks if provided, else inherit module weeks
                event_weeks = parse_weeks(e.get("weeks"), session_weeks_total) if "weeks" in e else module_weeks

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
                        weeks=event_weeks,
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
    weeks_total = int(config.get("weeks_total", 16))

    output: Dict[str, Any] = {
        "meta": {
            "week_name": config.get("week_name", ""),
            "weeks_total": weeks_total,
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
                "session_id": e.session_id,
                "module_id": e.module_id,
                "teacher_id": e.teacher_id,
                "group_ids": list(e.group_ids),
                "timeslot_id": tid,
                "room_id": rid,
                "weeks": sorted(list(e.weeks)),
                "demand": dem,
                "min_room_capacity": int(getattr(e, "min_room_capacity", 0)),
                "required_capacity": required,
                "room_capacity": problem.rooms[rid].capacity,
            })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output
