"""
Advanced preference and soft constraint system for timetabling.
Allows optimization based on preferences rather than just finding any feasible solution.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, FrozenSet, Tuple
from enum import Enum

class PreferenceType(Enum):
    """Types of scheduling preferences."""
    TEACHER_PREFERRED_TIMES = "teacher_preferred_times"
    ROOM_PREFERRED_USAGE = "room_preferred_usage"
    GROUP_PREFERRED_TIMES = "group_preferred_times"
    EVENT_SPACING = "event_spacing"
    DAY_COMPACTNESS = "day_compactness"
    LUNCH_BREAK = "lunch_break"
    AVOID_LATE_CLASSES = "avoid_late_classes"
    MINIMIZE_ROOM_CHANGES = "minimize_room_changes"

@dataclass
class Preference:
    """A scheduling preference with weight and parameters."""
    type: PreferenceType
    weight: float  # 0.0 to 1.0, higher = more important
    target: str  # teacher_id, room_id, group_id, or event_id
    parameters: Dict[str, any]
    description: str

class PreferenceManager:
    """Manages and evaluates scheduling preferences."""

    def __init__(self):
        self.preferences: List[Preference] = []

    def add_teacher_preference(self, teacher_id: str, preferred_slots: List[str],
                             weight: float = 0.7, description: str = ""):
        """Add teacher's preferred time slots."""
        self.preferences.append(Preference(
            type=PreferenceType.TEACHER_PREFERRED_TIMES,
            weight=weight,
            target=teacher_id,
            parameters={"preferred_slots": preferred_slots},
            description=description or f"Teacher {teacher_id} prefers certain time slots"
        ))

    def add_lunch_break_preference(self, start_time: str = "12:00", end_time: str = "14:00",
                                 weight: float = 0.8):
        """Prefer to keep lunch break free."""
        self.preferences.append(Preference(
            type=PreferenceType.LUNCH_BREAK,
            weight=weight,
            target="all",
            parameters={"start_time": start_time, "end_time": end_time},
            description=f"Prefer lunch break {start_time}-{end_time} free"
        ))

    def add_compact_day_preference(self, group_id: str, weight: float = 0.6):
        """Prefer compact schedules (minimize gaps between classes)."""
        self.preferences.append(Preference(
            type=PreferenceType.DAY_COMPACTNESS,
            weight=weight,
            target=group_id,
            parameters={},
            description=f"Prefer compact schedule for {group_id}"
        ))

    def add_avoid_late_classes_preference(self, cutoff_time: str = "18:00", weight: float = 0.5):
        """Avoid scheduling classes after certain time."""
        self.preferences.append(Preference(
            type=PreferenceType.AVOID_LATE_CLASSES,
            weight=weight,
            target="all",
            parameters={"cutoff_time": cutoff_time},
            description=f"Avoid classes after {cutoff_time}"
        ))

    def evaluate_schedule_quality(self, assignment, problem) -> float:
        """Evaluate how well a schedule satisfies preferences (0.0 to 1.0)."""
        total_score = 0.0
        total_weight = 0.0

        for preference in self.preferences:
            score = self._evaluate_preference(preference, assignment, problem)
            total_score += score * preference.weight
            total_weight += preference.weight

        return total_score / total_weight if total_weight > 0 else 1.0

    def _evaluate_preference(self, preference: Preference, assignment, problem) -> float:
        """Evaluate a single preference (0.0 = worst, 1.0 = best)."""
        if preference.type == PreferenceType.TEACHER_PREFERRED_TIMES:
            return self._evaluate_teacher_preferred_times(preference, assignment, problem)
        elif preference.type == PreferenceType.LUNCH_BREAK:
            return self._evaluate_lunch_break(preference, assignment, problem)
        elif preference.type == PreferenceType.DAY_COMPACTNESS:
            return self._evaluate_day_compactness(preference, assignment, problem)
        elif preference.type == PreferenceType.AVOID_LATE_CLASSES:
            return self._evaluate_avoid_late_classes(preference, assignment, problem)
        else:
            return 1.0  # Unknown preference type

    def _evaluate_teacher_preferred_times(self, preference: Preference, assignment, problem) -> float:
        """Evaluate how well teacher's preferred times are used."""
        teacher_id = preference.target
        preferred_slots = set(preference.parameters["preferred_slots"])

        teacher_assignments = [
            (eid, tid, rid) for eid, tid, rid in assignment
            if problem.events[eid].teacher_id == teacher_id
        ]

        if not teacher_assignments:
            return 1.0  # No assignments for this teacher

        preferred_count = sum(1 for _, tid, _ in teacher_assignments if tid in preferred_slots)
        return preferred_count / len(teacher_assignments)

    def _evaluate_lunch_break(self, preference: Preference, assignment, problem) -> float:
        """Evaluate lunch break preservation."""
        start_time = preference.parameters["start_time"]
        end_time = preference.parameters["end_time"]

        lunch_violations = 0
        total_slots = 0

        for _, tid, _ in assignment:
            timeslot = problem.timeslots[tid]
            total_slots += 1

            # Check if this slot conflicts with lunch time
            if self._time_overlaps_lunch(timeslot.start, timeslot.end, start_time, end_time):
                lunch_violations += 1

        return 1.0 - (lunch_violations / total_slots) if total_slots > 0 else 1.0

    def _evaluate_day_compactness(self, preference: Preference, assignment, problem) -> float:
        """Evaluate schedule compactness for a group."""
        group_id = preference.target

        # Group assignments by day for this group
        day_assignments = {}
        for eid, tid, _ in assignment:
            event = problem.events[eid]
            if group_id in event.group_ids:
                timeslot = problem.timeslots[tid]
                day = timeslot.day
                if day not in day_assignments:
                    day_assignments[day] = []
                day_assignments[day].append(timeslot.start)

        # Calculate compactness score for each day
        total_gap_penalty = 0.0
        total_days = len(day_assignments)

        for day, start_times in day_assignments.items():
            if len(start_times) > 1:
                start_times.sort()
                # Penalize gaps between classes
                gaps = 0
                for i in range(1, len(start_times)):
                    # Simple gap detection (could be more sophisticated)
                    gaps += 1 if self._has_large_gap(start_times[i-1], start_times[i]) else 0
                total_gap_penalty += gaps / (len(start_times) - 1)

        return 1.0 - (total_gap_penalty / total_days) if total_days > 0 else 1.0

    def _evaluate_avoid_late_classes(self, preference: Preference, assignment, problem) -> float:
        """Evaluate avoidance of late classes."""
        cutoff_time = preference.parameters["cutoff_time"]

        late_classes = 0
        total_classes = len(assignment)

        for _, tid, _ in assignment:
            timeslot = problem.timeslots[tid]
            if timeslot.start >= cutoff_time:
                late_classes += 1

        return 1.0 - (late_classes / total_classes) if total_classes > 0 else 1.0

    def _time_overlaps_lunch(self, start: str, end: str, lunch_start: str, lunch_end: str) -> bool:
        """Check if time slot overlaps with lunch break."""
        # Simple string comparison (assumes HH:MM format)
        return not (end <= lunch_start or start >= lunch_end)

    def _has_large_gap(self, time1: str, time2: str) -> bool:
        """Check if there's a large gap between two time slots."""
        # Simple heuristic: gap > 2 hours
        # In real implementation, would parse times properly
        return abs(int(time1.split(':')[0]) - int(time2.split(':')[0])) > 2

def load_preferences_from_json(preferences_data: Dict) -> PreferenceManager:
    """Load preferences from JSON configuration."""
    manager = PreferenceManager()

    # Teacher preferences
    for teacher_pref in preferences_data.get("teacher_preferences", []):
        manager.add_teacher_preference(
            teacher_id=teacher_pref["teacher_id"],
            preferred_slots=teacher_pref["preferred_slots"],
            weight=teacher_pref.get("weight", 0.7),
            description=teacher_pref.get("description", "")
        )

    # Global preferences
    if "lunch_break" in preferences_data:
        lunch = preferences_data["lunch_break"]
        manager.add_lunch_break_preference(
            start_time=lunch.get("start_time", "12:00"),
            end_time=lunch.get("end_time", "14:00"),
            weight=lunch.get("weight", 0.8)
        )

    # Group preferences
    for group_pref in preferences_data.get("group_preferences", []):
        if group_pref.get("type") == "compact":
            manager.add_compact_day_preference(
                group_id=group_pref["group_id"],
                weight=group_pref.get("weight", 0.6)
            )

    # Global time preferences
    if "avoid_late_classes" in preferences_data:
        late_pref = preferences_data["avoid_late_classes"]
        manager.add_avoid_late_classes_preference(
            cutoff_time=late_pref.get("cutoff_time", "18:00"),
            weight=late_pref.get("weight", 0.5)
        )

    return manager
