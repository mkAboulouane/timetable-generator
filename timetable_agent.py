"""
Timetabling agent (feasible schedule) WITHOUT modifying problem_solving_agent.py.

Weeks constraint (flexible):
- Each Event has a set of active weeks: event.weeks (FrozenSet[int]).
- A resource conflict (teacher/group/room) occurs only if:
  same timeslot AND weeks sets intersect.

Hard constraints:
- teacher availability (weekly pattern) + no teacher conflict (weeks-aware)
- group availability (weekly pattern) + no group conflict (weeks-aware)
- room availability (weekly pattern) + no room conflict (weeks-aware)
- room capacity >= max(sum(group sizes), module min_room_capacity)
- timeslot duration == event duration

Input/Output handled by timetable_io.py (JSON v3 with weeks as list/ranges/all).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Tuple
from collections import deque
import heapq
import json
from datetime import datetime

from problem_solving_agent import Problem

# ==========================================================
# Search trace / graph export (optional)
# ==========================================================

try:
    from search_graph import SearchGraphRecorder
except Exception:  # pragma: no cover
    SearchGraphRecorder = None  # type: ignore


# ==========================================================
# Data model
# ==========================================================

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
    available: FrozenSet[str]  # timeslot ids (weekly pattern)


@dataclass(frozen=True)
class Room:
    id: str
    capacity: int
    available: FrozenSet[str]  # timeslot ids (weekly pattern)


@dataclass(frozen=True)
class Teacher:
    id: str
    available: FrozenSet[str]  # timeslot ids (weekly pattern)


@dataclass(frozen=True)
class Event:
    id: str
    teacher_id: str
    group_ids: Tuple[str, ...]
    duration_min: int
    allowed_slots: Optional[FrozenSet[str]] = None

    # From module/session structure (input JSON)
    min_room_capacity: int = 0
    session_id: str = ""
    module_id: str = ""

    # Module hours per week (informational, from module config)
    module_hours_per_week: float = 0.0

    # Active weeks for this event (e.g., {1,3,5} or weeks from ranges)
    weeks: FrozenSet[int] = frozenset()


# State: tuple of assignments (event_id, timeslot_id, room_id) sorted by event_id
AssignmentTuple = Tuple[Tuple[str, str, str], ...]


# ==========================================================
# Weeks logic
# ==========================================================

def weeks_intersect(a: FrozenSet[int], b: FrozenSet[int]) -> bool:
    """True if week sets intersect."""
    return not a.isdisjoint(b)


# ==========================================================
# Helpers
# ==========================================================

def event_demand(e: Event, groups: Dict[str, Group]) -> int:
    return sum(groups[gid].size for gid in e.group_ids)


def is_room_free(
    assignment: AssignmentTuple,
    events: Dict[str, Event],
    t_id: str,
    r_id: str,
    candidate: Event,
) -> bool:
    for (eid, t, r) in assignment:
        if t != t_id or r != r_id:
            continue
        existing = events[eid]
        if weeks_intersect(existing.weeks, candidate.weeks):
            return False
    return True


def is_teacher_free(
    assignment: AssignmentTuple,
    events: Dict[str, Event],
    t_id: str,
    teacher_id: str,
    candidate: Event,
) -> bool:
    for (eid, t, _) in assignment:
        if t != t_id:
            continue
        existing = events[eid]
        if existing.teacher_id != teacher_id:
            continue
        if weeks_intersect(existing.weeks, candidate.weeks):
            return False
    return True


def is_group_free(
    assignment: AssignmentTuple,
    events: Dict[str, Event],
    t_id: str,
    group_id: str,
    candidate: Event,
) -> bool:
    for (eid, t, _) in assignment:
        if t != t_id:
            continue
        existing = events[eid]
        if group_id not in existing.group_ids:
            continue
        if weeks_intersect(existing.weeks, candidate.weeks):
            return False
    return True


# ==========================================================
# Problem definition
# ==========================================================

class TimetablingProblem(Problem):
    """
    Feasible scheduling problem with hard constraints only, using week-sets.
    """

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

        # Precompute compatible rooms per event:
        # room.capacity >= max(demand, min_room_capacity)
        self.compatible_rooms: Dict[str, Tuple[str, ...]] = {}
        for e in events:
            dem = event_demand(e, self.groups)
            required = max(dem, int(getattr(e, "min_room_capacity", 0)))
            self.compatible_rooms[e.id] = tuple(r.id for r in rooms if r.capacity >= required)

        # Precompute compatible slots per event:
        # duration + teacher availability + all groups availability (+ allowed_slots)
        self.compatible_slots: Dict[str, Tuple[str, ...]] = {}
        all_slot_ids = set(self.timeslots.keys())

        for e in events:
            duration_slots = {t.id for t in timeslots if t.duration_min == e.duration_min}
            teacher_av = set(self.teachers[e.teacher_id].available)

            group_av = set(all_slot_ids)
            for gid in e.group_ids:
                group_av &= set(self.groups[gid].available)

            slots = duration_slots & teacher_av & group_av

            # Handle allowed_slots with support for ALL/all macro
            if e.allowed_slots is not None:
                allowed_set = set()
                for slot in e.allowed_slots:
                    if slot.upper() == "ALL":
                        # "ALL" or "all" means all available timeslots
                        allowed_set = all_slot_ids
                        break
                    else:
                        allowed_set.add(slot)
                slots &= allowed_set

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

        # MRV: smallest estimated domain size slots*rooms
        best_eid = None
        best_size = None
        for eid in unassigned:
            size = len(self.compatible_slots[eid]) * len(self.compatible_rooms[eid])
            if best_eid is None or size < best_size:
                best_eid, best_size = eid, size
        return best_eid

    def actions(self, state: AssignmentTuple) -> List[Tuple[str, str, str]]:
        """
        Actions are (event_id, timeslot_id, room_id).
        We generate actions only for the next event (MRV) to keep branching manageable.
        """
        eid = self._select_next_event(state)
        if eid is None:
            return []

        e = self.events[eid]
        acts: List[Tuple[str, str, str]] = []

        for t_id in self.compatible_slots[eid]:
            # teacher conflict (weeks-aware)
            if not is_teacher_free(state, self.events, t_id, e.teacher_id, e):
                continue

            # group conflicts (weeks-aware)
            if any(not is_group_free(state, self.events, t_id, gid, e) for gid in e.group_ids):
                continue

            for r_id in self.compatible_rooms[eid]:
                room = self.rooms[r_id]

                # room availability (weekly pattern)
                if t_id not in room.available:
                    continue

                # room conflict (weeks-aware)
                if not is_room_free(state, self.events, t_id, r_id, e):
                    continue

                acts.append((eid, t_id, r_id))

        return acts

    def result(self, state: AssignmentTuple, action: Tuple[str, str, str]) -> AssignmentTuple:
        eid, t_id, r_id = action
        new_state = list(state) + [(eid, t_id, r_id)]
        new_state.sort(key=lambda x: x[0])  # canonical
        return tuple(new_state)

    def goal_test(self, state: AssignmentTuple) -> bool:
        return len(state) == len(self.all_event_ids)

    def path_cost(self, cost_so_far: float, state1: Any, action: Any, state2: Any) -> float:
        return cost_so_far + 1.0


# ==========================================================
# Search algorithms (no Trace dependency)
# ==========================================================

import time

@dataclass
class SearchResult:
    """Result of a search algorithm with statistics."""
    path: Optional[List[Any]]
    iterations: int
    nodes_explored: int
    max_frontier_size: int
    final_cost: float
    elapsed_time: float
    algorithm: str


def reconstruct_path(parents: Dict[Any, Any], start: Any, goal: Any) -> List[Any]:
    path = [goal]
    cur = goal
    while cur != start:
        cur = parents[cur]
        path.append(cur)
    path.reverse()
    return path


def state_repr(state: AssignmentTuple, max_items: int = 3) -> str:
    """Compact representation of state for console output."""
    if len(state) == 0:
        return "(empty)"
    if len(state) <= max_items:
        return str(list(state))
    return f"[{len(state)} assignments: {list(state[:max_items])}...]"


def dfs_search(
    problem: TimetablingProblem,
    verbose: bool = True,
    *,
    record_graph: bool = False,
    algorithm_label: str = "DFS",
    max_iterations: int = 100000,
    timeout: float = 300.0,
):
    algo_name = algorithm_label
    start_time = time.time()
    start = problem.initial_state
    frontier = [start]
    parents: Dict[Any, Any] = {}
    visited = set()
    iteration = 0
    max_frontier = 1

    recorder = None
    if record_graph:
        if SearchGraphRecorder is None:
            raise RuntimeError(
                "Graph recording requested but 'search_graph.py' could not be imported."
            )
        recorder = SearchGraphRecorder(algorithm=algo_name)
        recorder.mark_start(start, label=f"{state_repr(start)}\nstart")

    if verbose:
        print(f"\n{'='*60}")
        print(f"  ALGORITHME: {algo_name}")
        print(f"{'='*60}")
        print(f"État initial: {state_repr(start)}")
        print(f"Frontière initiale: taille={len(frontier)}")
        print(f"Explorés: 0 | Coût initial: 0.0")
        print("-" * 60)

    while frontier:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > timeout:
            if verbose:
                print(f"\n⏱️ TIMEOUT après {iteration} itérations ({elapsed:.2f}s)")
            result = SearchResult(
                path=None,
                iterations=iteration,
                nodes_explored=len(visited),
                max_frontier_size=max_frontier,
                final_cost=float('inf'),
                elapsed_time=elapsed,
                algorithm=algo_name,
            )
            if recorder is not None:
                setattr(result, "graph", recorder)
            return result

        # Check max iterations
        if iteration >= max_iterations:
            elapsed = time.time() - start_time
            if verbose:
                print(f"\n⚠️ MAX ITERATIONS atteint ({max_iterations})")
            result = SearchResult(
                path=None,
                iterations=iteration,
                nodes_explored=len(visited),
                max_frontier_size=max_frontier,
                final_cost=float('inf'),
                elapsed_time=elapsed,
                algorithm=algo_name,
            )
            if recorder is not None:
                setattr(result, "graph", recorder)
            return result

        iteration += 1
        max_frontier = max(max_frontier, len(frontier))
        state = frontier.pop()

        actions_list = problem.actions(state)

        if recorder is not None:
            recorder.add_iteration(
                iteration=iteration,
                current_state=state,
                frontier_size=len(frontier),
                explored_size=len(visited),
                cost=float(len(state)),
                actions_count=len(actions_list),
                current_label=f"{state_repr(state)}\niter={iteration} f={len(frontier)} e={len(visited)}",
            )

        if verbose and iteration <= 10:
            print(f"Itération {iteration}:")
            print(f"  État courant: {state_repr(state)}")
            print(f"  Frontière: {len(frontier)} états")
            print(f"  Explorés: {len(visited)}")
            print(f"  Coût: {len(state)}")

        if problem.goal_test(state):
            elapsed = time.time() - start_time
            path = reconstruct_path(parents, start, state)
            if recorder is not None:
                recorder.mark_goal(state, label=f"{state_repr(state)}\nGOAL")
            if verbose:
                print(f"\n✅ SOLUTION TROUVÉE à l'itération {iteration}")
                print(f"  Coût final: {len(state)}")
            result = SearchResult(
                path=path,
                iterations=iteration,
                nodes_explored=len(visited),
                max_frontier_size=max_frontier,
                final_cost=float(len(state)),
                elapsed_time=elapsed,
                algorithm=algo_name,
            )
            # Attach recorder if present (non-breaking: just set attribute)
            if recorder is not None:
                setattr(result, "graph", recorder)
            return result

        if state in visited:
            continue
        visited.add(state)

        for action in actions_list:
            child = problem.result(state, action)
            if child not in visited:
                parents[child] = state
                frontier.append(child)
                if recorder is not None:
                    recorder.add_edge(
                        state,
                        child,
                        parent_label=state_repr(state),
                        child_label=state_repr(child),
                        attrs={"label": str(action)},
                    )

        if verbose and iteration <= 10:
            print(f"  Actions possibles: {len(actions_list)}")
            print("-" * 60)
        elif verbose and iteration == 11:
            print("... (affichage des itérations suivantes omis)")

    elapsed = time.time() - start_time
    if verbose:
        print(f"\n❌ Aucune solution trouvée après {iteration} itérations")
    result = SearchResult(
        path=None,
        iterations=iteration,
        nodes_explored=len(visited),
        max_frontier_size=max_frontier,
        final_cost=float('inf'),
        elapsed_time=elapsed,
        algorithm=algo_name,
    )
    if recorder is not None:
        setattr(result, "graph", recorder)
    return result


def bfs_search(problem: TimetablingProblem, verbose: bool = True, max_iterations: int = 100000, timeout: float = 300.0) -> SearchResult:
    algo_name = "BFS"
    start_time = time.time()
    start = problem.initial_state
    frontier = deque([start])
    parents: Dict[Any, Any] = {}
    visited = set([start])
    iteration = 0
    max_frontier = 1

    if verbose:
        print(f"\n{'='*60}")
        print(f"  ALGORITHME: {algo_name}")
        print(f"{'='*60}")
        print(f"État initial: {state_repr(start)}")
        print(f"Frontière initiale: taille={len(frontier)}")
        print(f"Explorés: 1 | Coût initial: 0.0")
        print("-" * 60)

    while frontier:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > timeout:
            if verbose:
                print(f"\n⏱️ TIMEOUT après {iteration} itérations ({elapsed:.2f}s)")
            return SearchResult(
                path=None,
                iterations=iteration,
                nodes_explored=len(visited),
                max_frontier_size=max_frontier,
                final_cost=float('inf'),
                elapsed_time=elapsed,
                algorithm=algo_name
            )

        # Check max iterations
        if iteration >= max_iterations:
            elapsed = time.time() - start_time
            if verbose:
                print(f"\n⚠️ MAX ITERATIONS atteint ({max_iterations})")
            return SearchResult(
                path=None,
                iterations=iteration,
                nodes_explored=len(visited),
                max_frontier_size=max_frontier,
                final_cost=float('inf'),
                elapsed_time=elapsed,
                algorithm=algo_name
            )
        iteration += 1
        max_frontier = max(max_frontier, len(frontier))
        state = frontier.popleft()

        if verbose and iteration <= 10:
            print(f"Itération {iteration}:")
            print(f"  État courant: {state_repr(state)}")
            print(f"  Frontière: {len(frontier)} états")
            print(f"  Explorés: {len(visited)}")
            print(f"  Coût: {len(state)}")

        if problem.goal_test(state):
            elapsed = time.time() - start_time
            path = reconstruct_path(parents, start, state)
            if verbose:
                print(f"\n✅ SOLUTION TROUVÉE à l'itération {iteration}")
                print(f"  Coût final: {len(state)}")
            return SearchResult(
                path=path,
                iterations=iteration,
                nodes_explored=len(visited),
                max_frontier_size=max_frontier,
                final_cost=float(len(state)),
                elapsed_time=elapsed,
                algorithm=algo_name
            )

        for action in problem.actions(state):
            child = problem.result(state, action)
            if child not in visited:
                visited.add(child)
                parents[child] = state
                frontier.append(child)

        if verbose and iteration <= 10:
            print(f"  Actions possibles: {len(problem.actions(state))}")
            print("-" * 60)
        elif verbose and iteration == 11:
            print("... (affichage des itérations suivantes omis)")

    elapsed = time.time() - start_time
    if verbose:
        print(f"\n❌ Aucune solution trouvée après {iteration} itérations")
    return SearchResult(
        path=None,
        iterations=iteration,
        nodes_explored=len(visited),
        max_frontier_size=max_frontier,
        final_cost=float('inf'),
        elapsed_time=elapsed,
        algorithm=algo_name
    )


def ucs_search(problem: TimetablingProblem, verbose: bool = True, max_iterations: int = 100000, timeout: float = 300.0) -> SearchResult:
    algo_name = "UCS"
    start_time = time.time()
    start = problem.initial_state
    frontier: List[Tuple[float, Any]] = [(0.0, start)]
    parents: Dict[Any, Any] = {}
    best_g: Dict[Any, float] = {start: 0.0}
    iteration = 0
    max_frontier = 1
    explored_count = 0

    if verbose:
        print(f"\n{'='*60}")
        print(f"  ALGORITHME: {algo_name}")
        print(f"{'='*60}")
        print(f"État initial: {state_repr(start)}")
        print(f"Frontière initiale: taille={len(frontier)}")
        print(f"Explorés: 0 | Coût initial: 0.0")
        print("-" * 60)

    while frontier:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > timeout:
            if verbose:
                print(f"\n⏱️ TIMEOUT après {iteration} itérations ({elapsed:.2f}s)")
            return SearchResult(
                path=None,
                iterations=iteration,
                nodes_explored=explored_count,
                max_frontier_size=max_frontier,
                final_cost=float('inf'),
                elapsed_time=elapsed,
                algorithm=algo_name
            )

        # Check max iterations
        if iteration >= max_iterations:
            elapsed = time.time() - start_time
            if verbose:
                print(f"\n⚠️ MAX ITERATIONS atteint ({max_iterations})")
            return SearchResult(
                path=None,
                iterations=iteration,
                nodes_explored=explored_count,
                max_frontier_size=max_frontier,
                final_cost=float('inf'),
                elapsed_time=elapsed,
                algorithm=algo_name
            )
        iteration += 1
        max_frontier = max(max_frontier, len(frontier))
        g, state = heapq.heappop(frontier)

        if g != best_g.get(state, float("inf")):
            continue

        explored_count += 1

        if verbose and iteration <= 10:
            print(f"Itération {iteration}:")
            print(f"  État courant: {state_repr(state)}")
            print(f"  Frontière: {len(frontier)} états")
            print(f"  Explorés: {explored_count}")
            print(f"  Coût g(n): {g}")

        if problem.goal_test(state):
            elapsed = time.time() - start_time
            path = reconstruct_path(parents, start, state)
            if verbose:
                print(f"\n✅ SOLUTION TROUVÉE à l'itération {iteration}")
                print(f"  Coût final: {g}")
            return SearchResult(
                path=path,
                iterations=iteration,
                nodes_explored=explored_count,
                max_frontier_size=max_frontier,
                final_cost=g,
                elapsed_time=elapsed,
                algorithm=algo_name
            )

        for action in problem.actions(state):
            child = problem.result(state, action)
            new_g = problem.path_cost(g, state, action, child)
            if new_g < best_g.get(child, float("inf")):
                best_g[child] = new_g
                parents[child] = state
                heapq.heappush(frontier, (new_g, child))

        if verbose and iteration <= 10:
            print(f"  Actions possibles: {len(problem.actions(state))}")
            print("-" * 60)
        elif verbose and iteration == 11:
            print("... (affichage des itérations suivantes omis)")

    elapsed = time.time() - start_time
    if verbose:
        print(f"\n❌ Aucune solution trouvée après {iteration} itérations")
    return SearchResult(
        path=None,
        iterations=iteration,
        nodes_explored=explored_count,
        max_frontier_size=max_frontier,
        final_cost=float('inf'),
        elapsed_time=elapsed,
        algorithm=algo_name
    )


def h_zero(state: AssignmentTuple) -> float:
    return 0.0


def a_star_search(problem: TimetablingProblem, h=h_zero, verbose: bool = True, max_iterations: int = 100000, timeout: float = 300.0) -> SearchResult:
    algo_name = "A*"
    start_time = time.time()
    start = problem.initial_state
    frontier: List[Tuple[float, Any]] = [(h(start), start)]
    parents: Dict[Any, Any] = {}
    best_g: Dict[Any, float] = {start: 0.0}
    iteration = 0
    max_frontier = 1
    explored_count = 0

    if verbose:
        print(f"\n{'='*60}")
        print(f"  ALGORITHME: {algo_name}")
        print(f"{'='*60}")
        print(f"État initial: {state_repr(start)}")
        print(f"Frontière initiale: taille={len(frontier)}")
        print(f"Explorés: 0 | Coût initial g=0.0, h={h(start)}, f={h(start)}")
        print("-" * 60)

    while frontier:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > timeout:
            if verbose:
                print(f"\n⏱️ TIMEOUT après {iteration} itérations ({elapsed:.2f}s)")
            return SearchResult(
                path=None,
                iterations=iteration,
                nodes_explored=explored_count,
                max_frontier_size=max_frontier,
                final_cost=float('inf'),
                elapsed_time=elapsed,
                algorithm=algo_name
            )

        # Check max iterations
        if iteration >= max_iterations:
            elapsed = time.time() - start_time
            if verbose:
                print(f"\n⚠️ MAX ITERATIONS atteint ({max_iterations})")
            return SearchResult(
                path=None,
                iterations=iteration,
                nodes_explored=explored_count,
                max_frontier_size=max_frontier,
                final_cost=float('inf'),
                elapsed_time=elapsed,
                algorithm=algo_name
            )
        iteration += 1
        max_frontier = max(max_frontier, len(frontier))
        f, state = heapq.heappop(frontier)
        g = best_g[state]

        if f != g + h(state):
            continue

        explored_count += 1

        if verbose and iteration <= 10:
            print(f"Itération {iteration}:")
            print(f"  État courant: {state_repr(state)}")
            print(f"  Frontière: {len(frontier)} états")
            print(f"  Explorés: {explored_count}")
            print(f"  Coût g(n): {g}, h(n): {h(state)}, f(n): {f}")

        if problem.goal_test(state):
            elapsed = time.time() - start_time
            path = reconstruct_path(parents, start, state)
            if verbose:
                print(f"\n✅ SOLUTION TROUVÉE à l'itération {iteration}")
                print(f"  Coût final: {g}")
            return SearchResult(
                path=path,
                iterations=iteration,
                nodes_explored=explored_count,
                max_frontier_size=max_frontier,
                final_cost=g,
                elapsed_time=elapsed,
                algorithm=algo_name
            )

        for action in problem.actions(state):
            child = problem.result(state, action)
            new_g = problem.path_cost(g, state, action, child)
            if new_g < best_g.get(child, float("inf")):
                best_g[child] = new_g
                parents[child] = state
                heapq.heappush(frontier, (new_g + h(child), child))

        if verbose and iteration <= 10:
            print(f"  Actions possibles: {len(problem.actions(state))}")
            print("-" * 60)
        elif verbose and iteration == 11:
            print("... (affichage des itérations suivantes omis)")

    elapsed = time.time() - start_time
    if verbose:
        print(f"\n❌ Aucune solution trouvée après {iteration} itérations")
    return SearchResult(
        path=None,
        iterations=iteration,
        nodes_explored=explored_count,
        max_frontier_size=max_frontier,
        final_cost=float('inf'),
        elapsed_time=elapsed,
        algorithm=algo_name
    )


# ==========================================================
# Output formatting
# ==========================================================

def _weeks_to_ranges(weeks: FrozenSet[int]) -> str:
    """Compact printing: 1,3,5,7,10,16 or 1-6,10-14 style."""
    if not weeks:
        return ""
    w = sorted(weeks)
    ranges = []
    start = prev = w[0]
    for x in w[1:]:
        if x == prev + 1:
            prev = x
            continue
        ranges.append((start, prev))
        start = prev = x
    ranges.append((start, prev))
    return ",".join([f"{a}-{b}" if a != b else f"{a}" for a, b in ranges])


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
        required = max(dem, int(getattr(e, "min_room_capacity", 0)))

        print(
            f"- {ts.day} {ts.start}-{ts.end} | event={eid} | teacher={e.teacher_id} "
            f"| groups={list(e.group_ids)} | room={rid} | required={required}/{cap} "
            f"| weeks={_weeks_to_ranges(e.weeks)} | session={e.session_id} module={e.module_id}"
        )

    print("===========================================\n")



def diagnose_domains(problem: TimetablingProblem, limit: int = 50):
    """
    Prints events that have 0 possible actions from the INITIAL state,
    i.e. no (timeslot, room) satisfies availability + capacity constraints
    (without considering conflicts with other events).
    """
    print("\n========== DIAGNOSE: INITIAL DOMAINS ==========")
    bad = 0
    for e in problem.events_list:
        slots = problem.compatible_slots.get(e.id, ())
        rooms = problem.compatible_rooms.get(e.id, ())
        domain_size = len(slots) * len(rooms)
        if domain_size == 0:
            bad += 1
            dem = event_demand(e, problem.groups)
            required = max(dem, int(getattr(e, "min_room_capacity", 0)))
            print(f"- EVENT {e.id} | teacher={e.teacher_id} | session={e.session_id} module={e.module_id}")
            print(f"  groups={list(e.group_ids)} demand={dem} min_room_capacity={e.min_room_capacity} required={required}")
            print(f"  compatible_slots={list(slots)}")
            print(f"  compatible_rooms={list(rooms)}")
            if bad >= limit:
                print(f"... (stopping after {limit} zero-domain events)")
                break
    if bad == 0:
        print("✅ All events have a non-empty initial domain (before conflicts).")
    else:
        print(f"❌ Found {bad} events with empty initial domain.")
    print("=============================================\n")

# ==========================================================
# Main solve entry (JSON in/out)
# ==========================================================

def _generate_html_timetable(json_path: str, config: Dict[str, Any]):
    """Generate HTML timetable automatically after JSON export."""
    try:
        from timetable_export import load_output_json, generate_html_timetable
        import os

        # Generate HTML filename from JSON filename
        base_name = os.path.splitext(json_path)[0]
        html_path = f"{base_name}.html"

        # Load the JSON data
        data = load_output_json(json_path)

        # Generate HTML timetable
        generate_html_timetable(data, html_path)

        print(f"📊 Auto-generated HTML: {html_path}")
        print("   💡 Open the HTML file in a browser to view the visual timetable.")

        # Check if we have multiple sessions, offer session-based export
        assignments = data.get("assignments", [])
        sessions = set(a.get("session_id", "unknown") for a in assignments)

        if len(sessions) > 1:
            print(f"   📚 Multiple sessions detected ({len(sessions)} sessions)")
            print(f"   💡 Run: python timetable_export.py {json_path} --by-session")
            print("      to generate separate timetables per session.")

    except Exception as e:
        print(f"⚠️  Failed to generate HTML: {e}")
        print("   You can manually generate it with:")
        print(f"   python timetable_export.py {json_path}")


def print_comparison_table(results: List[SearchResult]):
    """Print a comparison table of all search algorithms."""
    print("\n" + "=" * 100)
    print("  COMPARAISON DES ALGORITHMES DE RECHERCHE")
    print("=" * 100)
    print(f"{'Algorithme':<12} {'Statut':<12} {'Itérations':<12} {'Explorés':<12} {'Max Frontière':<15} {'Coût Final':<12} {'Temps (s)':<12}")
    print("-" * 100)

    for r in results:
        status = "✅ Succès" if r.path is not None else "❌ Échec"
        cost_str = f"{r.final_cost:.1f}" if r.final_cost != float('inf') else "∞"
        print(f"{r.algorithm:<12} {status:<12} {r.iterations:<12} {r.nodes_explored:<12} {r.max_frontier_size:<15} {cost_str:<12} {r.elapsed_time:<12.4f}")

    print("=" * 100)
    print()


def _export_search_graph(graph, algorithm_name: str, input_path: str):
    """
    Export search graph to DOT and PNG files.

    Args:
        graph: SearchGraphRecorder instance
        algorithm_name: Name of the algorithm (e.g., 'dfs', 'bfs')
        input_path: Path to input file (used to derive output filename)
    """
    try:
        from search_graph import write_text, try_render_graphviz
        from pathlib import Path

        # Derive base name from input file
        base_name = Path(input_path).stem
        dot_file = f"search_graph_{algorithm_name}_{base_name}.dot"
        png_file = f"search_graph_{algorithm_name}_{base_name}.png"

        # Write DOT file
        dot_text = graph.to_dot()
        write_text(dot_file, dot_text)
        print(f"📊 Exported search graph DOT: {dot_file}")

        # Try to render PNG
        try:
            if try_render_graphviz(dot_file, png_file):
                print(f"📊 Exported search graph PNG: {png_file}")
            else:
                print(f"⚠️ Graphviz not available, DOT file saved but PNG not generated")
        except Exception as e:
            print(f"⚠️ Could not render PNG: {e}")

    except Exception as e:
        print(f"⚠️ Could not export search graph: {e}")


def solve_from_json(input_path: str, output_path: str, compare_all: bool = True, auto_html: bool = True, record_graph: bool = True):
    from timetable_io import load_input_json, export_output_json
    import os

    config, problem = load_input_json(input_path)
    diagnose_domains(problem)

    if compare_all:
        # Run all 4 algorithms and compare results
        print("\n" + "#" * 100)
        print("  EXÉCUTION DE TOUS LES ALGORITHMES POUR COMPARAISON")
        print("#" * 100)

        results: List[SearchResult] = []

        # DFS
        result_dfs = dfs_search(problem, verbose=True, record_graph=record_graph, algorithm_label="DFS")
        results.append(result_dfs)
        if record_graph and hasattr(result_dfs, 'graph'):
            _export_search_graph(result_dfs.graph, "dfs", input_path)

        # BFS
        result_bfs = bfs_search(problem, verbose=True)
        results.append(result_bfs)

        # UCS
        result_ucs = ucs_search(problem, verbose=True)
        results.append(result_ucs)

        # A*
        result_astar = a_star_search(problem, h_zero, verbose=True)
        results.append(result_astar)

        # Print comparison table
        print_comparison_table(results)

        # Use first successful result for output
        best_result = None
        for r in results:
            if r.path is not None:
                best_result = r
                break

        if best_result is None:
            print("❌ Aucun algorithme n'a trouvé de solution.")
            export_output_json(
                output_path,
                config=config,
                problem=problem,
                final_state=None,
                status="failure",
                strategy="compare_all",
            )
            return

        final_state: AssignmentTuple = best_result.path[-1]
        print(f"✅ Meilleur résultat avec {best_result.algorithm}: {len(final_state)} événements planifiés")
        pretty_print_schedule(problem, final_state)

        export_output_json(
            output_path,
            config=config,
            problem=problem,
            final_state=final_state,
            status="success",
            strategy=best_result.algorithm.lower(),
        )
        print(f"💾 Exported JSON: {output_path}")

        # Auto-generate HTML timetable
        if auto_html:
            _generate_html_timetable(output_path, config)

    else:
        # Original behavior: run only the specified strategy
        strategy = str(config.get("strategy", "dfs")).lower()

        if strategy == "dfs":
            result = dfs_search(problem, verbose=True, record_graph=record_graph, algorithm_label="DFS")
        elif strategy == "bfs":
            result = bfs_search(problem, verbose=True)
        elif strategy == "ucs":
            result = ucs_search(problem, verbose=True)
        elif strategy in ("astar", "a*", "a_star"):
            result = a_star_search(problem, h_zero, verbose=True)
            strategy = "a_star"
        else:
            raise ValueError(f"Unknown strategy '{strategy}'. Use one of: dfs, bfs, ucs, astar")

        # Export graph if recording was enabled
        if record_graph and hasattr(result, 'graph'):
            _export_search_graph(result.graph, strategy, input_path)

        if result.path is None:
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

        final_state: AssignmentTuple = result.path[-1]
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

        # Auto-generate HTML timetable
        if auto_html:
            _generate_html_timetable(output_path, config)


def solve_from_json_advanced(input_path: str, output_path: str,
                           compare_all: bool = True, auto_html: bool = True,
                           enable_validation: bool = True, enable_backup: bool = True,
                           export_formats: List[str] = None, record_graph: bool = True):
    """
    Enhanced solve function with advanced features:
    - Conflict detection and analysis
    - Quality validation and scoring
    - Automatic backup creation
    - Multiple export formats
    - Preference-based optimization
    """
    from timetable_io import load_input_json, export_output_json
    import os

    if not ADVANCED_FEATURES:
        print("⚠️ Advanced features not available, falling back to basic solve")
        return solve_from_json(input_path, output_path, compare_all, auto_html)

    # Create backup if enabled
    backup_manager = None
    if enable_backup:
        backup_manager = TimetableBackupManager()
        backup_version = backup_manager.create_backup(
            input_path, output_path,
            f"Pre-solve backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"🔄 Created backup: {backup_version}")

    # Load configuration and create problem
    config, problem = load_input_json(input_path)

    # Enhanced domain diagnosis with conflict detection
    print("\n🔍 ENHANCED PROBLEM ANALYSIS")
    print("=" * 50)
    diagnose_domains(problem)

    # Load preferences if available
    preferences = None
    if "preferences" in config:
        preferences = load_preferences_from_json(config["preferences"])
        print(f"✅ Loaded {len(preferences.preferences)} scheduling preferences")

    # Solve the problem
    if compare_all:
        print("\n" + "#" * 100)
        print("  EXÉCUTION DE TOUS LES ALGORITHMES POUR COMPARAISON")
        print("#" * 100)

        results: List[SearchResult] = []

        # Run all algorithms
        result_dfs = dfs_search(problem, verbose=True, record_graph=record_graph, algorithm_label="DFS")
        results.append(result_dfs)
        if record_graph and hasattr(result_dfs, 'graph'):
            _export_search_graph(result_dfs.graph, "dfs", input_path)

        result_bfs = bfs_search(problem, verbose=True)
        results.append(result_bfs)

        result_ucs = ucs_search(problem, verbose=True)
        results.append(result_ucs)

        result_astar = a_star_search(problem, h_zero, verbose=True)
        results.append(result_astar)

        print_comparison_table(results)

        # Select best result (prefer DFS if multiple succeed)
        best_result = None
        for r in results:
            if r.path is not None:
                best_result = r
                break

        if best_result is None:
            print("❌ Aucun algorithme n'a trouvé de solution.")

            # Analyze why no solution was found
            conflict_detector = ConflictDetector(problem)
            conflicts = conflict_detector.analyze_schedule([])  # Empty schedule analysis
            if conflicts:
                print("\n🚨 CONFLICT ANALYSIS")
                print(generate_conflict_report(conflicts))

            export_output_json(
                output_path, config=config, problem=problem,
                final_state=None, status="failure", strategy="compare_all"
            )
            return None

        final_state: AssignmentTuple = best_result.path[-1]
        print(f"✅ Meilleur résultat avec {best_result.algorithm}: {len(final_state)} événements planifiés")
        pretty_print_schedule(problem, final_state)

        export_output_json(
            output_path,
            config=config,
            problem=problem,
            final_state=final_state,
            status="success",
            strategy=best_result.algorithm.lower(),
        )
        print(f"💾 Exported JSON: {output_path}")

        # Auto-generate HTML timetable
        if auto_html:
            _generate_html_timetable(output_path, config)

    else:
        # Single algorithm mode
        strategy = str(config.get("strategy", "dfs")).lower()

        if strategy == "dfs":
            result = dfs_search(problem, verbose=True, record_graph=record_graph, algorithm_label="DFS")
        elif strategy == "bfs":
            result = bfs_search(problem, verbose=True)
        elif strategy == "ucs":
            result = ucs_search(problem, verbose=True)
        elif strategy in ("astar", "a*", "a_star"):
            result = a_star_search(problem, h_zero, verbose=True)
            strategy = "a_star"
        else:
            raise ValueError(f"Unknown strategy '{strategy}'. Use one of: dfs, bfs, ucs, astar")

        # Export graph if recording was enabled
        if record_graph and hasattr(result, 'graph'):
            _export_search_graph(result.graph, strategy, input_path)

        if result.path is None:
            print("❌ No feasible schedule found.")

            # Analyze conflicts
            conflict_detector = ConflictDetector(problem)
            conflicts = conflict_detector.analyze_schedule([])
            if conflicts:
                print("\n🚨 CONFLICT ANALYSIS")
                print(generate_conflict_report(conflicts))

            export_output_json(
                output_path, config=config, problem=problem,
                final_state=None, status="failure", strategy=strategy
            )
            return None

        final_state: AssignmentTuple = result.path[-1]
        best_result = result
        print(f"✅ Feasible schedule found. events_scheduled={len(final_state)}/{len(problem.events_list)}")

    # Display basic schedule
    pretty_print_schedule(problem, final_state)

    # Advanced validation and quality analysis
    conflicts = []
    quality_report = None

    if enable_validation:
        print("\n📊 ADVANCED SCHEDULE ANALYSIS")
        print("=" * 50)

        # Conflict detection
        conflict_detector = ConflictDetector(problem)
        conflicts = conflict_detector.analyze_schedule(final_state)

        if conflicts:
            print("🚨 CONFLICTS DETECTED:")
            print(generate_conflict_report(conflicts))
        else:
            print("✅ No conflicts detected in final schedule")

        # Quality validation
        validator = ScheduleValidator(problem)
        quality_report = validator.validate_and_assess(final_state)

        print(f"\n{generate_quality_report(quality_report)}")

        # Preference evaluation if available
        if preferences:
            preference_score = preferences.evaluate_schedule_quality(final_state, problem)
            print(f"\n🎯 PREFERENCE SATISFACTION: {preference_score:.1%}")

    # Export main JSON
    export_output_json(
        output_path, config=config, problem=problem,
        final_state=final_state, status="success",
        strategy=best_result.algorithm.lower()
    )
    print(f"💾 Exported JSON: {output_path}")

    # Auto-generate HTML
    if auto_html:
        _generate_html_timetable(output_path, config)

    # Enhanced export formats
    if export_formats:
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            exporter = EnhancedTimetableExporter(data)
            base_name = os.path.splitext(output_path)[0]

            print(f"\n📤 EXPORTING ADDITIONAL FORMATS")
            print("-" * 40)

            for fmt in export_formats:
                if fmt == 'csv':
                    exporter.export_csv(f"{base_name}.csv")
                elif fmt == 'ical':
                    exporter.export_ical(f"{base_name}.ics")
                elif fmt == 'xml':
                    exporter.export_xml(f"{base_name}.xml")
                elif fmt == 'enhanced_json':
                    exporter.export_enhanced_json(f"{base_name}_enhanced.json")
                elif fmt == 'moodle':
                    exporter.export_moodle_xml(f"{base_name}_moodle.xml")
                elif fmt == 'teams':
                    exporter.export_teams_integration(f"{base_name}_teams.json")
                elif fmt == 'stats':
                    exporter.export_statistics_report(f"{base_name}_stats.txt")
                elif fmt == 'all':
                    exporter.export_all_formats(base_name)
                    break

        except Exception as e:
            print(f"⚠️ Error exporting formats: {e}")

    # Create post-solve backup
    if enable_backup and backup_manager:
        backup_manager.create_backup(
            input_path, output_path,
            f"Post-solve results - {best_result.algorithm} - {len(final_state)} events"
        )

    return {
        'result': best_result,
        'final_state': final_state,
        'conflicts': conflicts,
        'quality_report': quality_report,
        'preference_score': preferences.evaluate_schedule_quality(final_state, problem) if preferences else None
    }


def print_advanced_help():
    """Print help for advanced features."""
    help_text = """
🚀 ADVANCED TIMETABLING FEATURES

Enhanced Solve Function:
  solve_from_json_advanced(
      input_path="input.json", 
      output_path="output.json",
      compare_all=True,          # Run all algorithms
      auto_html=True,            # Generate HTML automatically  
      enable_validation=True,    # Quality analysis & conflict detection
      enable_backup=True,        # Automatic backups
      export_formats=['csv', 'ical', 'stats']  # Additional export formats
  )

Available Export Formats:
  • csv         - Spreadsheet format
  • ical        - Calendar format (Outlook/Google)
  • xml         - Structured XML
  • enhanced_json - JSON with statistics
  • moodle      - Moodle course import
  • teams       - Microsoft Teams integration
  • stats       - Statistics report
  • all         - Export all formats

Preference Configuration (in input JSON):
  {
    "config": { ... },
    "preferences": {
      "teacher_preferences": [
        {
          "teacher_id": "T_MATH", 
          "preferred_slots": ["Mon_08-10", "Tue_08-10"],
          "weight": 0.7
        }
      ],
      "lunch_break": {
        "start_time": "12:00",
        "end_time": "14:00", 
        "weight": 0.8
      },
      "group_preferences": [
        {
          "group_id": "G1",
          "type": "compact",
          "weight": 0.6
        }
      ],
      "avoid_late_classes": {
        "cutoff_time": "18:00",
        "weight": 0.5
      }
    },
    "timeslots": [...],
    ...
  }

Backup & Version Control:
  from timetable_backup import TimetableBackupManager, VersionControl
  
  # Backup management
  backup = TimetableBackupManager()
  backup.create_backup("input.json", "output.json", "Description")
  backup.list_backups()
  backup.restore_backup("20251231_143022")
  
  # Version control
  vc = VersionControl()
  vc.commit_version(["input.json", "output.json"], "Version message")
  vc.checkout_version("20251231_143022")

Manual Analysis:
  from timetable_conflicts import ConflictDetector
  from timetable_validation import ScheduleValidator
  
  # Conflict analysis
  detector = ConflictDetector(problem)
  conflicts = detector.analyze_schedule(assignment)
  
  # Quality assessment  
  validator = ScheduleValidator(problem)
  report = validator.validate_and_assess(assignment)
"""
    print(help_text)


# Import new advanced features
try:
    from timetable_preferences import PreferenceManager, load_preferences_from_json
    from timetable_conflicts import ConflictDetector, generate_conflict_report
    from timetable_validation import ScheduleValidator, generate_quality_report
    from timetable_backup import TimetableBackupManager, auto_backup_wrapper
    from timetable_enhanced_export import EnhancedTimetableExporter
    ADVANCED_FEATURES = True
except ImportError as e:
    # Create dummy classes/functions for graceful fallback
    class PreferenceManager:
        def __init__(self): pass
    class ConflictDetector:
        def __init__(self, problem): pass
    class ScheduleValidator:
        def __init__(self, problem): pass
    class TimetableBackupManager:
        def __init__(self): pass
    class EnhancedTimetableExporter:
        def __init__(self, data): pass

    def load_preferences_from_json(data): return PreferenceManager()
    def generate_conflict_report(conflicts): return ""
    def generate_quality_report(report): return ""
    def auto_backup_wrapper(func): return func

    print(f"⚠️ Advanced features not available: {e}")
    ADVANCED_FEATURES = False


if __name__ == "__main__":
    input_path = "test/test_university_scenario.json"
    output_path = "timetable_output.json"
    # Enable advanced features for testing
    if ADVANCED_FEATURES:
        print("🚀 Running with ADVANCED FEATURES enabled")
        solve_from_json_advanced(
            input_path,
            output_path,
            compare_all=True,
            enable_validation=True,
            enable_backup=True,
            export_formats=['csv', 'ical', 'stats']
        )
    else:
        print("📝 Running with BASIC FEATURES only")
        solve_from_json(input_path, output_path, compare_all=True)
