"""
Schedule validation and quality assessment system.
Provides comprehensive analysis of schedule quality and adherence to best practices.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional
import statistics
from datetime import datetime, time

@dataclass
class QualityMetric:
    """Represents a quality metric with score and details."""
    name: str
    score: float  # 0.0 to 1.0 (1.0 = perfect)
    max_score: float
    description: str
    details: Dict[str, any] = None

@dataclass
class ScheduleQualityReport:
    """Comprehensive quality assessment of a schedule."""
    overall_score: float
    metrics: List[QualityMetric]
    recommendations: List[str]
    strengths: List[str]
    weaknesses: List[str]

class ScheduleValidator:
    """Validates and assesses schedule quality."""

    def __init__(self, problem):
        self.problem = problem

    def validate_and_assess(self, assignment) -> ScheduleQualityReport:
        """Comprehensive schedule validation and quality assessment."""
        metrics = []

        # Core validation metrics
        metrics.append(self._assess_constraint_adherence(assignment))
        metrics.append(self._assess_resource_utilization(assignment))
        metrics.append(self._assess_time_distribution(assignment))
        metrics.append(self._assess_workload_balance(assignment))
        metrics.append(self._assess_schedule_compactness(assignment))
        metrics.append(self._assess_room_efficiency(assignment))
        metrics.append(self._assess_teacher_satisfaction(assignment))
        metrics.append(self._assess_student_convenience(assignment))

        # Calculate overall score
        overall_score = sum(m.score * m.max_score for m in metrics) / sum(m.max_score for m in metrics)

        # Generate recommendations, strengths, and weaknesses
        recommendations = self._generate_recommendations(metrics, assignment)
        strengths = self._identify_strengths(metrics)
        weaknesses = self._identify_weaknesses(metrics)

        return ScheduleQualityReport(
            overall_score=overall_score,
            metrics=metrics,
            recommendations=recommendations,
            strengths=strengths,
            weaknesses=weaknesses
        )

    def _assess_constraint_adherence(self, assignment) -> QualityMetric:
        """Assess adherence to hard constraints."""
        violations = 0
        total_checks = 0

        # Check all hard constraints
        for eid, tid, rid in assignment:
            event = self.problem.events[eid]
            timeslot = self.problem.timeslots[tid]
            room = self.problem.rooms[rid]
            teacher = self.problem.teachers[event.teacher_id]

            total_checks += 4  # duration, teacher avail, room avail, capacity

            # Duration match
            if event.duration_min != timeslot.duration_min:
                violations += 1

            # Teacher availability
            if tid not in teacher.available:
                violations += 1

            # Room availability
            if tid not in room.available:
                violations += 1

            # Capacity check
            required_capacity = max(
                sum(self.problem.groups[gid].size for gid in event.group_ids),
                event.min_room_capacity
            )
            if required_capacity > room.capacity:
                violations += 1

        score = 1.0 - (violations / total_checks) if total_checks > 0 else 1.0

        return QualityMetric(
            name="Constraint Adherence",
            score=score,
            max_score=1.0,
            description=f"Hard constraint violations: {violations}/{total_checks}",
            details={"violations": violations, "total_checks": total_checks}
        )

    def _assess_resource_utilization(self, assignment) -> QualityMetric:
        """Assess efficiency of resource utilization."""
        # Room utilization
        room_usage = {}
        timeslot_count = len(self.problem.timeslots_list)

        for eid, tid, rid in assignment:
            if rid not in room_usage:
                room_usage[rid] = 0
            room_usage[rid] += 1

        # Calculate utilization rates
        utilization_rates = []
        for room in self.problem.rooms_list:
            available_slots = len(room.available)
            used_slots = room_usage.get(room.id, 0)
            if available_slots > 0:
                utilization_rates.append(used_slots / available_slots)

        avg_utilization = statistics.mean(utilization_rates) if utilization_rates else 0.0

        return QualityMetric(
            name="Resource Utilization",
            score=min(avg_utilization * 1.5, 1.0),  # Reward good utilization
            max_score=1.0,
            description=f"Average room utilization: {avg_utilization:.1%}",
            details={"room_utilization": room_usage, "average": avg_utilization}
        )

    def _assess_time_distribution(self, assignment) -> QualityMetric:
        """Assess distribution of events across time slots."""
        timeslot_usage = {}

        for eid, tid, rid in assignment:
            if tid not in timeslot_usage:
                timeslot_usage[tid] = 0
            timeslot_usage[tid] += 1

        # Calculate distribution evenness (lower std dev = more even)
        usage_values = list(timeslot_usage.values())
        if len(usage_values) > 1:
            mean_usage = statistics.mean(usage_values)
            std_dev = statistics.stdev(usage_values)
            evenness = 1.0 - min(std_dev / mean_usage, 1.0) if mean_usage > 0 else 1.0
        else:
            evenness = 1.0

        return QualityMetric(
            name="Time Distribution",
            score=evenness,
            max_score=0.8,
            description=f"Event distribution evenness: {evenness:.1%}",
            details={"timeslot_usage": timeslot_usage, "evenness": evenness}
        )

    def _assess_workload_balance(self, assignment) -> QualityMetric:
        """Assess balance of workload across teachers and groups."""
        teacher_loads = {}
        group_loads = {}

        for eid, tid, rid in assignment:
            event = self.problem.events[eid]

            # Teacher workload
            if event.teacher_id not in teacher_loads:
                teacher_loads[event.teacher_id] = 0
            teacher_loads[event.teacher_id] += event.duration_min / 60.0

            # Group workload
            for gid in event.group_ids:
                if gid not in group_loads:
                    group_loads[gid] = 0
                group_loads[gid] += event.duration_min / 60.0

        # Calculate balance (lower coefficient of variation = better balance)
        def calculate_balance(loads):
            values = list(loads.values())
            if len(values) <= 1:
                return 1.0
            mean_load = statistics.mean(values)
            if mean_load == 0:
                return 1.0
            std_dev = statistics.stdev(values)
            cv = std_dev / mean_load
            return max(0.0, 1.0 - cv)

        teacher_balance = calculate_balance(teacher_loads)
        group_balance = calculate_balance(group_loads)
        overall_balance = (teacher_balance + group_balance) / 2.0

        return QualityMetric(
            name="Workload Balance",
            score=overall_balance,
            max_score=0.9,
            description=f"Teacher balance: {teacher_balance:.1%}, Group balance: {group_balance:.1%}",
            details={
                "teacher_loads": teacher_loads,
                "group_loads": group_loads,
                "teacher_balance": teacher_balance,
                "group_balance": group_balance
            }
        )

    def _assess_schedule_compactness(self, assignment) -> QualityMetric:
        """Assess compactness of schedules (fewer gaps)."""
        # Group events by entity and day
        daily_schedules = {}

        for eid, tid, rid in assignment:
            event = self.problem.events[eid]
            timeslot = self.problem.timeslots[tid]
            day = timeslot.day

            # Track for each group
            for gid in event.group_ids:
                key = f"{gid}_{day}"
                if key not in daily_schedules:
                    daily_schedules[key] = []
                daily_schedules[key].append(timeslot.start)

        # Calculate compactness score
        total_gaps = 0
        total_possible_gaps = 0

        for key, times in daily_schedules.items():
            if len(times) <= 1:
                continue

            times.sort()
            possible_gaps = len(times) - 1
            total_possible_gaps += possible_gaps

            # Count actual gaps (simplified - assumes 2+ hour gaps are bad)
            gaps = 0
            for i in range(1, len(times)):
                hour1 = int(times[i-1].split(':')[0])
                hour2 = int(times[i].split(':')[0])
                if hour2 - hour1 > 2:  # More than 2-hour gap
                    gaps += 1
            total_gaps += gaps

        compactness = 1.0 - (total_gaps / total_possible_gaps) if total_possible_gaps > 0 else 1.0

        return QualityMetric(
            name="Schedule Compactness",
            score=compactness,
            max_score=0.7,
            description=f"Schedule compactness: {compactness:.1%} (fewer gaps is better)",
            details={"total_gaps": total_gaps, "possible_gaps": total_possible_gaps}
        )

    def _assess_room_efficiency(self, assignment) -> QualityMetric:
        """Assess efficiency of room assignments."""
        room_utilization_efficiency = []

        for eid, tid, rid in assignment:
            event = self.problem.events[eid]
            room = self.problem.rooms[rid]

            # Calculate required vs actual capacity
            required = max(
                sum(self.problem.groups[gid].size for gid in event.group_ids),
                event.min_room_capacity
            )

            if room.capacity > 0:
                efficiency = required / room.capacity
                room_utilization_efficiency.append(min(efficiency, 1.0))

        avg_efficiency = statistics.mean(room_utilization_efficiency) if room_utilization_efficiency else 0.0

        return QualityMetric(
            name="Room Efficiency",
            score=avg_efficiency,
            max_score=0.6,
            description=f"Average room space efficiency: {avg_efficiency:.1%}",
            details={"efficiency_scores": room_utilization_efficiency}
        )

    def _assess_teacher_satisfaction(self, assignment) -> QualityMetric:
        """Assess teacher satisfaction factors."""
        teacher_metrics = {}

        for eid, tid, rid in assignment:
            event = self.problem.events[eid]
            timeslot = self.problem.timeslots[tid]
            teacher_id = event.teacher_id

            if teacher_id not in teacher_metrics:
                teacher_metrics[teacher_id] = {
                    "total_hours": 0,
                    "days_worked": set(),
                    "late_classes": 0,
                    "early_classes": 0
                }

            metrics = teacher_metrics[teacher_id]
            metrics["total_hours"] += event.duration_min / 60.0
            metrics["days_worked"].add(timeslot.day)

            # Check for early/late classes
            hour = int(timeslot.start.split(':')[0])
            if hour < 8:
                metrics["early_classes"] += 1
            elif hour >= 18:
                metrics["late_classes"] += 1

        # Calculate satisfaction score
        satisfaction_scores = []
        for teacher_id, metrics in teacher_metrics.items():
            score = 1.0

            # Penalize too many days
            if len(metrics["days_worked"]) > 4:
                score -= 0.2

            # Penalize early/late classes
            total_classes = len([a for a in assignment if self.problem.events[a[0]].teacher_id == teacher_id])
            if total_classes > 0:
                score -= (metrics["early_classes"] + metrics["late_classes"]) * 0.1 / total_classes

            satisfaction_scores.append(max(score, 0.0))

        avg_satisfaction = statistics.mean(satisfaction_scores) if satisfaction_scores else 1.0

        return QualityMetric(
            name="Teacher Satisfaction",
            score=avg_satisfaction,
            max_score=0.6,
            description=f"Average teacher satisfaction: {avg_satisfaction:.1%}",
            details={"teacher_metrics": teacher_metrics}
        )

    def _assess_student_convenience(self, assignment) -> QualityMetric:
        """Assess convenience factors for students."""
        group_convenience = {}

        for eid, tid, rid in assignment:
            event = self.problem.events[eid]
            timeslot = self.problem.timeslots[tid]

            for gid in event.group_ids:
                if gid not in group_convenience:
                    group_convenience[gid] = {
                        "days_with_classes": set(),
                        "room_changes": [],
                        "early_classes": 0,
                        "late_classes": 0
                    }

                conv = group_convenience[gid]
                conv["days_with_classes"].add(timeslot.day)
                conv["room_changes"].append(rid)

                # Check timing
                hour = int(timeslot.start.split(':')[0])
                if hour < 8:
                    conv["early_classes"] += 1
                elif hour >= 18:
                    conv["late_classes"] += 1

        # Calculate convenience scores
        convenience_scores = []
        for gid, conv in group_convenience.items():
            score = 1.0

            # Reward fewer days with classes
            days_count = len(conv["days_with_classes"])
            if days_count <= 3:
                score += 0.1
            elif days_count > 5:
                score -= 0.2

            # Penalize too many room changes
            unique_rooms = len(set(conv["room_changes"]))
            if unique_rooms > 3:
                score -= 0.1

            # Penalize early/late classes
            total_classes = len(conv["room_changes"])
            if total_classes > 0:
                inconvenient = conv["early_classes"] + conv["late_classes"]
                score -= inconvenient * 0.15 / total_classes

            convenience_scores.append(max(score, 0.0))

        avg_convenience = statistics.mean(convenience_scores) if convenience_scores else 1.0

        return QualityMetric(
            name="Student Convenience",
            score=min(avg_convenience, 1.0),
            max_score=0.5,
            description=f"Average student convenience: {min(avg_convenience, 1.0):.1%}",
            details={"group_convenience": group_convenience}
        )

    def _generate_recommendations(self, metrics: List[QualityMetric], assignment) -> List[str]:
        """Generate specific recommendations based on metrics."""
        recommendations = []

        # Low constraint adherence
        constraint_metric = next((m for m in metrics if m.name == "Constraint Adherence"), None)
        if constraint_metric and constraint_metric.score < 0.8:
            recommendations.append("🚨 Address hard constraint violations first - these make the schedule invalid")

        # Poor resource utilization
        resource_metric = next((m for m in metrics if m.name == "Resource Utilization"), None)
        if resource_metric and resource_metric.score < 0.4:
            recommendations.append("📊 Consider adding more events to better utilize available rooms and time slots")

        # Poor workload balance
        balance_metric = next((m for m in metrics if m.name == "Workload Balance"), None)
        if balance_metric and balance_metric.score < 0.6:
            recommendations.append("⚖️ Redistribute workload more evenly across teachers and student groups")

        # Poor compactness
        compact_metric = next((m for m in metrics if m.name == "Schedule Compactness"), None)
        if compact_metric and compact_metric.score < 0.5:
            recommendations.append("🗂️ Reduce gaps between classes by scheduling consecutive time slots")

        # Low room efficiency
        room_metric = next((m for m in metrics if m.name == "Room Efficiency"), None)
        if room_metric and room_metric.score < 0.6:
            recommendations.append("🏢 Use appropriately sized rooms - avoid large rooms for small classes")

        # Teacher satisfaction issues
        teacher_metric = next((m for m in metrics if m.name == "Teacher Satisfaction"), None)
        if teacher_metric and teacher_metric.score < 0.7:
            recommendations.append("👨‍🏫 Improve teacher schedules - reduce early/late classes and spread across fewer days")

        return recommendations

    def _identify_strengths(self, metrics: List[QualityMetric]) -> List[str]:
        """Identify strengths in the schedule."""
        strengths = []

        for metric in metrics:
            if metric.score >= 0.8:
                strengths.append(f"✅ {metric.name}: {metric.description}")

        return strengths

    def _identify_weaknesses(self, metrics: List[QualityMetric]) -> List[str]:
        """Identify weaknesses in the schedule."""
        weaknesses = []

        for metric in metrics:
            if metric.score < 0.6:
                weaknesses.append(f"⚠️ {metric.name}: {metric.description}")

        return weaknesses

def generate_quality_report(report: ScheduleQualityReport) -> str:
    """Generate a human-readable quality report."""
    lines = []

    lines.append("📊 SCHEDULE QUALITY REPORT")
    lines.append("=" * 50)
    lines.append(f"\n🎯 OVERALL SCORE: {report.overall_score:.1%}")

    # Quality level
    if report.overall_score >= 0.8:
        lines.append("🌟 Quality Level: EXCELLENT")
    elif report.overall_score >= 0.6:
        lines.append("✅ Quality Level: GOOD")
    elif report.overall_score >= 0.4:
        lines.append("⚠️ Quality Level: FAIR")
    else:
        lines.append("🚨 Quality Level: POOR")

    # Detailed metrics
    lines.append(f"\n📋 DETAILED METRICS")
    lines.append("-" * 30)
    for metric in sorted(report.metrics, key=lambda x: x.score, reverse=True):
        score_bar = "█" * int(metric.score * 10) + "░" * (10 - int(metric.score * 10))
        lines.append(f"{metric.name:20} [{score_bar}] {metric.score:.1%}")
        lines.append(f"{'':20} {metric.description}")
        lines.append("")

    # Strengths
    if report.strengths:
        lines.append("🌟 STRENGTHS")
        lines.append("-" * 20)
        for strength in report.strengths:
            lines.append(f"  {strength}")
        lines.append("")

    # Weaknesses
    if report.weaknesses:
        lines.append("⚠️ AREAS FOR IMPROVEMENT")
        lines.append("-" * 30)
        for weakness in report.weaknesses:
            lines.append(f"  {weakness}")
        lines.append("")

    # Recommendations
    if report.recommendations:
        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 25)
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    return "\n".join(lines)
