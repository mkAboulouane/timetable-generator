"""
Advanced conflict detection and resolution system for timetabling.
Provides detailed conflict analysis and suggestions for resolution.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum

class ConflictType(Enum):
    """Types of scheduling conflicts."""
    TEACHER_DOUBLE_BOOKING = "teacher_double_booking"
    ROOM_DOUBLE_BOOKING = "room_double_booking"
    GROUP_DOUBLE_BOOKING = "group_double_booking"
    CAPACITY_EXCEEDED = "capacity_exceeded"
    TEACHER_UNAVAILABLE = "teacher_unavailable"
    ROOM_UNAVAILABLE = "room_unavailable"
    GROUP_UNAVAILABLE = "group_unavailable"
    DURATION_MISMATCH = "duration_mismatch"
    INSUFFICIENT_WEEKLY_HOURS = "insufficient_weekly_hours"
    EXCESSIVE_DAILY_LOAD = "excessive_daily_load"

@dataclass
class Conflict:
    """Represents a scheduling conflict with detailed information."""
    type: ConflictType
    severity: str  # "critical", "warning", "minor"
    description: str
    affected_entities: List[str]  # IDs of affected teachers, rooms, groups, events
    timeslot: Optional[str] = None
    suggestions: List[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []

class ConflictDetector:
    """Detects and analyzes scheduling conflicts."""

    def __init__(self, problem):
        self.problem = problem
        self.conflicts: List[Conflict] = []

    def analyze_schedule(self, assignment) -> List[Conflict]:
        """Comprehensive conflict analysis of a schedule."""
        self.conflicts = []

        # Check hard constraint violations
        self._check_double_bookings(assignment)
        self._check_capacity_violations(assignment)
        self._check_availability_violations(assignment)
        self._check_duration_mismatches(assignment)

        # Check soft constraint violations
        self._check_weekly_hour_requirements(assignment)
        self._check_daily_load_distribution(assignment)

        return self.conflicts

    def _check_double_bookings(self, assignment):
        """Check for teacher, room, and group double bookings."""
        # Group by timeslot for conflict detection
        timeslot_assignments = {}
        for eid, tid, rid in assignment:
            if tid not in timeslot_assignments:
                timeslot_assignments[tid] = []
            timeslot_assignments[tid].append((eid, rid))

        for tid, assignments in timeslot_assignments.items():
            if len(assignments) <= 1:
                continue

            # Check teacher conflicts
            teachers_in_slot = {}
            rooms_in_slot = {}
            groups_in_slot = {}

            for eid, rid in assignments:
                event = self.problem.events[eid]
                teacher_id = event.teacher_id

                # Teacher conflicts
                if teacher_id in teachers_in_slot:
                    # Check if weeks overlap
                    existing_event = self.problem.events[teachers_in_slot[teacher_id]]
                    if self._weeks_overlap(event.weeks, existing_event.weeks):
                        self._add_conflict(Conflict(
                            type=ConflictType.TEACHER_DOUBLE_BOOKING,
                            severity="critical",
                            description=f"Teacher {teacher_id} has overlapping assignments",
                            affected_entities=[teacher_id, eid, teachers_in_slot[teacher_id]],
                            timeslot=tid,
                            suggestions=[
                                f"Move one event to a different timeslot",
                                f"Assign different teacher to one event",
                                f"Check if events can run in different weeks"
                            ]
                        ))
                else:
                    teachers_in_slot[teacher_id] = eid

                # Room conflicts
                if rid in rooms_in_slot:
                    existing_event = self.problem.events[rooms_in_slot[rid]]
                    if self._weeks_overlap(event.weeks, existing_event.weeks):
                        self._add_conflict(Conflict(
                            type=ConflictType.ROOM_DOUBLE_BOOKING,
                            severity="critical",
                            description=f"Room {rid} has overlapping bookings",
                            affected_entities=[rid, eid, rooms_in_slot[rid]],
                            timeslot=tid,
                            suggestions=[
                                f"Move one event to different room",
                                f"Move one event to different timeslot",
                                f"Check if events can run in different weeks"
                            ]
                        ))
                else:
                    rooms_in_slot[rid] = eid

                # Group conflicts
                for group_id in event.group_ids:
                    if group_id in groups_in_slot:
                        existing_event = self.problem.events[groups_in_slot[group_id]]
                        if self._weeks_overlap(event.weeks, existing_event.weeks):
                            self._add_conflict(Conflict(
                                type=ConflictType.GROUP_DOUBLE_BOOKING,
                                severity="critical",
                                description=f"Group {group_id} has overlapping classes",
                                affected_entities=[group_id, eid, groups_in_slot[group_id]],
                                timeslot=tid,
                                suggestions=[
                                    f"Move one event to different timeslot",
                                    f"Split group into smaller groups",
                                    f"Check if events can run in different weeks"
                                ]
                            ))
                    else:
                        groups_in_slot[group_id] = eid

    def _check_capacity_violations(self, assignment):
        """Check for room capacity violations."""
        for eid, tid, rid in assignment:
            event = self.problem.events[eid]
            room = self.problem.rooms[rid]

            # Calculate required capacity
            total_students = sum(
                self.problem.groups[gid].size
                for gid in event.group_ids
            )
            required_capacity = max(total_students, event.min_room_capacity)

            if required_capacity > room.capacity:
                self._add_conflict(Conflict(
                    type=ConflictType.CAPACITY_EXCEEDED,
                    severity="critical",
                    description=f"Room {rid} capacity ({room.capacity}) insufficient for event {eid} (needs {required_capacity})",
                    affected_entities=[rid, eid],
                    timeslot=tid,
                    suggestions=[
                        f"Use larger room (capacity >= {required_capacity})",
                        f"Split groups into smaller sessions",
                        f"Reduce group sizes"
                    ]
                ))

    def _check_availability_violations(self, assignment):
        """Check for availability constraint violations."""
        for eid, tid, rid in assignment:
            event = self.problem.events[eid]
            timeslot = self.problem.timeslots[tid]
            room = self.problem.rooms[rid]
            teacher = self.problem.teachers[event.teacher_id]

            # Check teacher availability
            if tid not in teacher.available:
                self._add_conflict(Conflict(
                    type=ConflictType.TEACHER_UNAVAILABLE,
                    severity="critical",
                    description=f"Teacher {event.teacher_id} not available at {tid}",
                    affected_entities=[event.teacher_id, eid],
                    timeslot=tid,
                    suggestions=[
                        f"Move event to teacher's available time",
                        f"Update teacher availability",
                        f"Assign different teacher"
                    ]
                ))

            # Check room availability
            if tid not in room.available:
                self._add_conflict(Conflict(
                    type=ConflictType.ROOM_UNAVAILABLE,
                    severity="critical",
                    description=f"Room {rid} not available at {tid}",
                    affected_entities=[rid, eid],
                    timeslot=tid,
                    suggestions=[
                        f"Move event to different room",
                        f"Move event to different timeslot",
                        f"Update room availability"
                    ]
                ))

            # Check group availability
            for group_id in event.group_ids:
                group = self.problem.groups[group_id]
                if tid not in group.available:
                    self._add_conflict(Conflict(
                        type=ConflictType.GROUP_UNAVAILABLE,
                        severity="critical",
                        description=f"Group {group_id} not available at {tid}",
                        affected_entities=[group_id, eid],
                        timeslot=tid,
                        suggestions=[
                            f"Move event to group's available time",
                            f"Update group availability",
                            f"Exclude group from this event"
                        ]
                    ))

            # Check duration match
            if event.duration_min != timeslot.duration_min:
                self._add_conflict(Conflict(
                    type=ConflictType.DURATION_MISMATCH,
                    severity="critical",
                    description=f"Event {eid} duration ({event.duration_min}min) doesn't match timeslot {tid} ({timeslot.duration_min}min)",
                    affected_entities=[eid, tid],
                    timeslot=tid,
                    suggestions=[
                        f"Use timeslot with {event.duration_min}min duration",
                        f"Adjust event duration to {timeslot.duration_min}min",
                        f"Create new timeslot with correct duration"
                    ]
                ))

    def _check_weekly_hour_requirements(self, assignment):
        """Check if modules meet their weekly hour requirements."""
        module_hours = {}

        # Calculate actual hours per module
        for eid, tid, rid in assignment:
            event = self.problem.events[eid]
            module_id = event.module_id

            if module_id not in module_hours:
                module_hours[module_id] = 0

            # Add event duration in hours
            module_hours[module_id] += event.duration_min / 60.0

        # Check against expected hours
        for event in self.problem.events_list:
            module_id = event.module_id
            expected_hours = event.module_hours_per_week

            if expected_hours > 0:
                actual_hours = module_hours.get(module_id, 0)
                if actual_hours < expected_hours:
                    self._add_conflict(Conflict(
                        type=ConflictType.INSUFFICIENT_WEEKLY_HOURS,
                        severity="warning",
                        description=f"Module {module_id} has {actual_hours}h/week, expected {expected_hours}h/week",
                        affected_entities=[module_id],
                        suggestions=[
                            f"Add more events for {module_id}",
                            f"Increase duration of existing events",
                            f"Verify expected hours are correct"
                        ]
                    ))

    def _check_daily_load_distribution(self, assignment):
        """Check for excessive daily loads on groups/teachers."""
        # Group assignments by day and entity
        daily_loads = {}

        for eid, tid, rid in assignment:
            event = self.problem.events[eid]
            timeslot = self.problem.timeslots[tid]
            day = timeslot.day

            # Track teacher daily load
            teacher_key = f"teacher_{event.teacher_id}_{day}"
            if teacher_key not in daily_loads:
                daily_loads[teacher_key] = 0
            daily_loads[teacher_key] += event.duration_min / 60.0

            # Track group daily loads
            for group_id in event.group_ids:
                group_key = f"group_{group_id}_{day}"
                if group_key not in daily_loads:
                    daily_loads[group_key] = 0
                daily_loads[group_key] += event.duration_min / 60.0

        # Check for excessive loads (> 8 hours per day)
        for key, hours in daily_loads.items():
            if hours > 8:
                entity_type, entity_id, day = key.split('_', 2)
                self._add_conflict(Conflict(
                    type=ConflictType.EXCESSIVE_DAILY_LOAD,
                    severity="warning",
                    description=f"{entity_type.title()} {entity_id} has {hours:.1f} hours on {day}",
                    affected_entities=[entity_id],
                    suggestions=[
                        f"Redistribute events across multiple days",
                        f"Reduce event durations",
                        f"Split large events into smaller sessions"
                    ]
                ))

    def _weeks_overlap(self, weeks1, weeks2) -> bool:
        """Check if two sets of weeks overlap."""
        return not weeks1.isdisjoint(weeks2)

    def _add_conflict(self, conflict: Conflict):
        """Add a conflict to the list."""
        self.conflicts.append(conflict)

    def get_conflict_summary(self) -> Dict[str, int]:
        """Get summary of conflicts by type and severity."""
        summary = {
            "critical": 0,
            "warning": 0,
            "minor": 0,
            "total": len(self.conflicts)
        }

        for conflict in self.conflicts:
            summary[conflict.severity] += 1

        return summary

    def get_conflicts_by_entity(self, entity_id: str) -> List[Conflict]:
        """Get all conflicts affecting a specific entity."""
        return [
            conflict for conflict in self.conflicts
            if entity_id in conflict.affected_entities
        ]

def generate_conflict_report(conflicts: List[Conflict]) -> str:
    """Generate a human-readable conflict report."""
    if not conflicts:
        return "✅ No conflicts detected in the schedule."

    report = []
    report.append(f"🚨 CONFLICT ANALYSIS REPORT")
    report.append(f"=" * 50)

    # Group by severity
    by_severity = {}
    for conflict in conflicts:
        if conflict.severity not in by_severity:
            by_severity[conflict.severity] = []
        by_severity[conflict.severity].append(conflict)

    for severity in ["critical", "warning", "minor"]:
        if severity not in by_severity:
            continue

        severity_conflicts = by_severity[severity]
        icon = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "🟢"

        report.append(f"\n{icon} {severity.upper()} CONFLICTS ({len(severity_conflicts)})")
        report.append("-" * 30)

        for i, conflict in enumerate(severity_conflicts, 1):
            report.append(f"\n{i}. {conflict.description}")
            report.append(f"   Type: {conflict.type.value}")
            report.append(f"   Affected: {', '.join(conflict.affected_entities)}")
            if conflict.timeslot:
                report.append(f"   Timeslot: {conflict.timeslot}")

            if conflict.suggestions:
                report.append(f"   💡 Suggestions:")
                for suggestion in conflict.suggestions:
                    report.append(f"      • {suggestion}")

    report.append(f"\n📊 SUMMARY")
    report.append(f"Total conflicts: {len(conflicts)}")
    report.append(f"Critical: {len(by_severity.get('critical', []))}")
    report.append(f"Warning: {len(by_severity.get('warning', []))}")
    report.append(f"Minor: {len(by_severity.get('minor', []))}")

    return "\n".join(report)
