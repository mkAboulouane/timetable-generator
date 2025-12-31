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
            print(item)
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


def parse_availability(available_obj: Any, all_timeslots: List[str]) -> FrozenSet[str]:
    """
    Parse availability field with support for "ALL" macro.

    available_obj can be:
      - None or [] => empty availability (no slots available)
      - ["ALL"] => all available timeslots
      - ["Mon_08-10", "Tue_10-12", ...] => specific timeslots
      - ["ALL", "-Mon_08-10", "-Tue_10-12"] => all except specified (exclusion)
    """
    if not available_obj:
        return frozenset()

    if not isinstance(available_obj, list):
        available_obj = [available_obj]

    # Check if "ALL" is in the list
    if "ALL" in available_obj:
        # Start with all timeslots
        result_set = set(all_timeslots)

        # Remove any exclusions (items starting with "-")
        for item in available_obj:
            if isinstance(item, str) and item.startswith("-"):
                exclude_slot = item[1:]  # Remove the "-" prefix
                result_set.discard(exclude_slot)

        return frozenset(result_set)
    else:
        # Regular list of specific timeslots
        return frozenset(str(slot) for slot in available_obj)


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

    # Get all timeslot IDs for "ALL" macro
    all_timeslot_ids = [t.id for t in timeslots]

    rooms = [
        Room(
            id=r["id"],
            capacity=int(r["capacity"]),
            available=parse_availability(r.get("available"), all_timeslot_ids),
        )
        for r in data["rooms"]
    ]

    teachers = [
        Teacher(
            id=t["id"],
            available=parse_availability(t.get("available"), all_timeslot_ids),
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
                available=parse_availability(g.get("available"), all_timeslot_ids),
            )
            for g in s.get("groups", [])
        ]
        groups.extend(session_groups)
        session_group_ids = [g.id for g in session_groups]

        for m in s.get("modules", []):
            module_id = m["id"]
            min_room_capacity = int(m.get("min_room_capacity", 0))
            hours_per_week = float(m.get("hours_per_week", 0))

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
                        module_hours_per_week=hours_per_week,
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
                "duration_min": e.duration_min,
                "duration_hours": e.duration_min / 60.0,
                "module_hours_per_week": e.module_hours_per_week,
                "demand": dem,
                "min_room_capacity": int(getattr(e, "min_room_capacity", 0)),
                "required_capacity": required,
                "room_capacity": problem.rooms[rid].capacity,
            })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output
