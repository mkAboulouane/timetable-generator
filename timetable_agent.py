"""
Timetabling agent (feasible schedule) WITHOUT modifying problem_solving_agent.py.
Includes CLI-like run: read input JSON, solve, print, export output JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Tuple
from collections import deque
import heapq

from problem_solving_agent import Problem


@dataclass(frozen=True)
class TimeSlot:
    id: str
    day: str
    start: str
    end: str
    duration_min: int


@dataclass(frozen=True)
class Group:
    id: str
    size: int
    available: FrozenSet[str]


@dataclass(frozen=True)
class Room:
    id: str
    capacity: int
    available: FrozenSet[str]


@dataclass(frozen=True)
class Teacher:
    id: str
    available: FrozenSet[str]


@dataclass(frozen=True)
class Event:
    id: str
    teacher_id: str
    group_ids: Tuple[str, ...]
    duration_min: int
    allowed_slots: Optional[FrozenSet[str]] = None


AssignmentTuple = Tuple[Tuple[str, str, str], ...]


def event_demand(e: Event, groups: Dict[str, Group]) -> int:
    return sum(groups[gid].size for gid in e.group_ids)


def is_room_free(assignment: AssignmentTuple, t_id: str, r_id: str) -> bool:
    return all(not (t == t_id and r == r_id) for (_, t, r) in assignment)


def is_teacher_free(assignment: AssignmentTuple, events: Dict[str, Event], t_id: str, teacher_id: str) -> bool:
    for (eid, t, _) in assignment:
        if t == t_id and events[eid].teacher_id == teacher_id:
            return False
    return True


def is_group_free(assignment: AssignmentTuple, events: Dict[str, Event], t_id: str, group_id: str) -> bool:
    for (eid, t, _) in assignment:
        if t == t_id and group_id in events[eid].group_ids:
            return False
    return True


class TimetablingProblem(Problem):
    def __init__(
        self,
        initial_state: AssignmentTuple,
        goal: Any = None,
        *,
        events: List[Event],
        timeslots: List[TimeSlot],
        rooms: List[Room],
        teachers: List[Teacher],
        groups: List[Group],
        use_mrv: bool = True,
    ):
        super().__init__(initial_state, goal)

        self.use_mrv = use_mrv

        self.events_list = events
        self.timeslots_list = timeslots
        self.rooms_list = rooms
        self.teachers_list = teachers
        self.groups_list = groups

        self.events: Dict[str, Event] = {e.id: e for e in events}
        self.timeslots: Dict[str, TimeSlot] = {t.id: t for t in timeslots}
        self.rooms: Dict[str, Room] = {r.id: r for r in rooms}
        self.teachers: Dict[str, Teacher] = {t.id: t for t in teachers}
        self.groups: Dict[str, Group] = {g.id: g for g in groups}

        self.all_event_ids: Tuple[str, ...] = tuple(e.id for e in events)

        self.compatible_rooms: Dict[str, Tuple[str, ...]] = {}
        for e in events:
            dem = event_demand(e, self.groups)
            self.compatible_rooms[e.id] = tuple(r.id for r in rooms if r.capacity >= dem)

        self.compatible_slots: Dict[str, Tuple[str, ...]] = {}
        all_slot_ids = set(self.timeslots.keys())

        for e in events:
            duration_slots = {t.id for t in timeslots if t.duration_min == e.duration_min}
            teacher_av = set(self.teachers[e.teacher_id].available)

            group_av = set(all_slot_ids)
            for gid in e.group_ids:
                group_av &= set(self.groups[gid].available)

            slots = duration_slots & teacher_av & group_av
            if e.allowed_slots is not None:
                slots &= set(e.allowed_slots)

            self.compatible_slots[e.id] = tuple(sorted(slots))

    def _unassigned(self, state: AssignmentTuple) -> List[str]:
        assigned = {eid for (eid, _, _) in state}
        return [eid for eid in self.all_event_ids if eid not in assigned]

    def _select_next_event(self, state: AssignmentTuple) -> Optional[str]:
        unassigned = self._unassigned(state)
        if not unassigned:
            return None
        if not self.use_mrv:
            return unassigned[0]

        best_eid = None
        best_size = None
        for eid in unassigned:
            size = len(self.compatible_slots[eid]) * len(self.compatible_rooms[eid])
            if best_eid is None or size < best_size:
                best_eid, best_size = eid, size
        return best_eid

    def actions(self, state: AssignmentTuple) -> List[Tuple[str, str, str]]:
        eid = self._select_next_event(state)
        if eid is None:
            return []

        e = self.events[eid]
        acts: List[Tuple[str, str, str]] = []

        for t_id in self.compatible_slots[eid]:
            if not is_teacher_free(state, self.events, t_id, e.teacher_id):
                continue
            if any(not is_group_free(state, self.events, t_id, gid) for gid in e.group_ids):
                continue

            for r_id in self.compatible_rooms[eid]:
                room = self.rooms[r_id]
                if t_id not in room.available:
                    continue
                if not is_room_free(state, t_id, r_id):
                    continue
                acts.append((eid, t_id, r_id))

        return acts

    def result(self, state: AssignmentTuple, action: Tuple[str, str, str]) -> AssignmentTuple:
        eid, t_id, r_id = action
        new_state = list(state) + [(eid, t_id, r_id)]
        new_state.sort(key=lambda x: x[0])
        return tuple(new_state)

    def goal_test(self, state: AssignmentTuple) -> bool:
        return len(state) == len(self.all_event_ids)

    def path_cost(self, cost_so_far: float, state1: Any, action: Any, state2: Any) -> float:
        return cost_so_far + 1.0


def reconstruct_path(parents: Dict[Any, Any], start: Any, goal: Any) -> List[Any]:
    path = [goal]
    cur = goal
    while cur != start:
        cur = parents[cur]
        path.append(cur)
    path.reverse()
    return path


def dfs_search(problem: TimetablingProblem) -> Optional[List[Any]]:
    start = problem.initial_state
    frontier = [start]
    parents: Dict[Any, Any] = {}
    visited = set()

    while frontier:
        state = frontier.pop()
        if problem.goal_test(state):
            return reconstruct_path(parents, start, state)

        if state in visited:
            continue
        visited.add(state)

        for action in problem.actions(state):
            child = problem.result(state, action)
            if child not in visited:
                parents[child] = state
                frontier.append(child)

    return None


def bfs_search(problem: TimetablingProblem) -> Optional[List[Any]]:
    start = problem.initial_state
    frontier = deque([start])
    parents: Dict[Any, Any] = {}
    visited = set([start])

    while frontier:
        state = frontier.popleft()
        if problem.goal_test(state):
            return reconstruct_path(parents, start, state)

        for action in problem.actions(state):
            child = problem.result(state, action)
            if child not in visited:
                visited.add(child)
                parents[child] = state
                frontier.append(child)

    return None


def ucs_search(problem: TimetablingProblem) -> Optional[List[Any]]:
    start = problem.initial_state
    frontier: List[Tuple[float, Any]] = [(0.0, start)]
    parents: Dict[Any, Any] = {}
    best_g: Dict[Any, float] = {start: 0.0}

    while frontier:
        g, state = heapq.heappop(frontier)
        if g != best_g.get(state, float("inf")):
            continue

        if problem.goal_test(state):
            return reconstruct_path(parents, start, state)

        for action in problem.actions(state):
            child = problem.result(state, action)
            new_g = problem.path_cost(g, state, action, child)
            if new_g < best_g.get(child, float("inf")):
                best_g[child] = new_g
                parents[child] = state
                heapq.heappush(frontier, (new_g, child))

    return None


def h_zero(state: AssignmentTuple) -> float:
    return 0.0


def a_star_search(problem: TimetablingProblem, h=h_zero) -> Optional[List[Any]]:
    start = problem.initial_state
    frontier: List[Tuple[float, Any]] = [(h(start), start)]
    parents: Dict[Any, Any] = {}
    best_g: Dict[Any, float] = {start: 0.0}

    while frontier:
        f, state = heapq.heappop(frontier)
        g = best_g[state]
        if f != g + h(state):
            continue

        if problem.goal_test(state):
            return reconstruct_path(parents, start, state)

        for action in problem.actions(state):
            child = problem.result(state, action)
            new_g = problem.path_cost(g, state, action, child)
            if new_g < best_g.get(child, float("inf")):
                best_g[child] = new_g
                parents[child] = state
                heapq.heappush(frontier, (new_g + h(child), child))

    return None


def pretty_print_schedule(problem: TimetablingProblem, assignment: AssignmentTuple):
    print("\n================= SCHEDULE =================")

    def key_fn(x):
        eid, tid, _ = x
        ts = problem.timeslots[tid]
        return (ts.day, ts.start, eid)

    for eid, tid, rid in sorted(assignment, key=key_fn):
        e = problem.events[eid]
        ts = problem.timeslots[tid]
        dem = event_demand(e, problem.groups)
        cap = problem.rooms[rid].capacity
        print(
            f"- {ts.day} {ts.start}-{ts.end} | event={eid} | teacher={e.teacher_id} "
            f"| groups={list(e.group_ids)} | room={rid} | demand={dem}/{cap}"
        )

    print("===========================================\n")


def solve_from_json(input_path: str = "timetable_input.json", output_path: str = "timetable_output.json"):
    from timetable_io import load_input_json, export_output_json

    config, problem = load_input_json(input_path)
    strategy = str(config.get("strategy", "dfs")).lower()

    if strategy == "dfs":
        path = dfs_search(problem)
    elif strategy == "bfs":
        path = bfs_search(problem)
    elif strategy == "ucs":
        path = ucs_search(problem)
    elif strategy in ("astar", "a*", "a_star"):
        path = a_star_search(problem, h_zero)
        strategy = "a_star"
    else:
        raise ValueError(f"Unknown strategy '{strategy}'. Use one of: dfs, bfs, ucs, astar")

    if path is None:
        print("❌ No feasible schedule found.")
        export_output_json(
            output_path,
            config=config,
            problem=problem,
            final_state=None,
            status="failure",
            strategy=strategy,
        )
        return

    final_state: AssignmentTuple = path[-1]
    print(f"✅ Feasible schedule found. events_scheduled={len(final_state)}/{len(problem.events_list)}")
    pretty_print_schedule(problem, final_state)

    export_output_json(
        output_path,
        config=config,
        problem=problem,
        final_state=final_state,
        status="success",
        strategy=strategy,
    )
    print(f"💾 Exported JSON: {output_path}")


if __name__ == "__main__":
    solve_from_json("timetable_input.json", "timetable_output.json")