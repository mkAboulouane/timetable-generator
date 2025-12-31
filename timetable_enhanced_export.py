"""
Enhanced export capabilities for timetables.
Supports multiple formats, customizable layouts, and integration with external systems.
"""

import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET
from dataclasses import dataclass

@dataclass
class ExportFormat:
    """Configuration for export format."""
    name: str
    extension: str
    description: str
    supports_filtering: bool = True
    supports_styling: bool = False

class EnhancedTimetableExporter:
    """Enhanced exporter with multiple format support."""

    FORMATS = {
        'csv': ExportFormat('CSV', 'csv', 'Comma-separated values for spreadsheets', True, False),
        'excel': ExportFormat('Excel', 'xlsx', 'Microsoft Excel format', True, True),
        'ical': ExportFormat('iCal', 'ics', 'Calendar format for Outlook/Google Calendar', True, False),
        'xml': ExportFormat('XML', 'xml', 'Structured XML format', True, False),
        'json': ExportFormat('JSON', 'json', 'Enhanced JSON with metadata', True, False),
        'pdf': ExportFormat('PDF', 'pdf', 'Formatted PDF document', True, True),
        'moodle': ExportFormat('Moodle', 'xml', 'Moodle course import format', False, False),
        'teams': ExportFormat('Teams', 'json', 'Microsoft Teams integration', False, False)
    }

    def __init__(self, timetable_data: Dict):
        self.data = timetable_data
        self.assignments = timetable_data.get('assignments', [])
        self.meta = timetable_data.get('meta', {})

    def export_csv(self, output_file: str, include_details: bool = True):
        """Export to CSV format."""
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'Event', 'Module', 'Teacher', 'Groups', 'Day', 'Start Time', 'End Time',
                'Room', 'Duration (hours)', 'Weeks', 'Students', 'Room Capacity'
            ]

            if include_details:
                fieldnames.extend(['Session', 'Module Hours/Week', 'Required Capacity'])

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for assignment in self.assignments:
                # Parse timeslot
                timeslot_parts = assignment['timeslot_id'].split('_')
                day = timeslot_parts[0] if len(timeslot_parts) > 0 else 'Unknown'
                time_range = timeslot_parts[1] if len(timeslot_parts) > 1 else 'Unknown'

                start_time, end_time = 'Unknown', 'Unknown'
                if '-' in time_range:
                    times = time_range.split('-')
                    start_time = times[0].replace('-', ':')
                    end_time = times[1].replace('-', ':') if len(times) > 1 else 'Unknown'

                row = {
                    'Event': assignment['event_id'],
                    'Module': assignment['module_id'],
                    'Teacher': assignment['teacher_id'],
                    'Groups': ', '.join(assignment['group_ids']),
                    'Day': day,
                    'Start Time': start_time,
                    'End Time': end_time,
                    'Room': assignment['room_id'],
                    'Duration (hours)': assignment.get('duration_hours', 0),
                    'Weeks': ', '.join(map(str, assignment['weeks'])),
                    'Students': assignment['demand'],
                    'Room Capacity': assignment['room_capacity']
                }

                if include_details:
                    row.update({
                        'Session': assignment['session_id'],
                        'Module Hours/Week': assignment.get('module_hours_per_week', 0),
                        'Required Capacity': assignment['required_capacity']
                    })

                writer.writerow(row)

        print(f"✅ CSV exported to: {output_file}")

    def export_ical(self, output_file: str):
        """Export to iCal format for calendar applications."""
        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Timetable Agent//Timetable Generator//EN',
            'CALSCALE:GREGORIAN'
        ]

        # Calculate dates (assuming current academic year)
        base_date = datetime.now().replace(month=9, day=1)  # September 1st
        if datetime.now().month < 9:
            base_date = base_date.replace(year=base_date.year - 1)

        for assignment in self.assignments:
            # Parse timeslot
            timeslot_parts = assignment['timeslot_id'].split('_')
            day = timeslot_parts[0] if len(timeslot_parts) > 0 else 'Mon'
            time_range = timeslot_parts[1] if len(timeslot_parts) > 1 else '08-10'

            # Convert to datetime
            day_offset = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}.get(day, 0)
            start_date = base_date + timedelta(days=day_offset)

            # Parse time
            if '-' in time_range:
                start_time_str, end_time_str = time_range.split('-')
                start_hour = int(start_time_str[:2])
                start_minute = int(start_time_str[2:]) if len(start_time_str) > 2 else 0
                end_hour = int(end_time_str[:2])
                end_minute = int(end_time_str[2:]) if len(end_time_str) > 2 else 0

                start_datetime = start_date.replace(hour=start_hour, minute=start_minute)
                end_datetime = start_date.replace(hour=end_hour, minute=end_minute)

                # Create event for each week
                for week in assignment['weeks'][:5]:  # Limit to first 5 weeks for demo
                    event_start = start_datetime + timedelta(weeks=week-1)
                    event_end = end_datetime + timedelta(weeks=week-1)

                    lines.extend([
                        'BEGIN:VEVENT',
                        f'UID:{assignment["event_id"]}-week{week}@timetable-agent',
                        f'DTSTART:{event_start.strftime("%Y%m%dT%H%M%S")}',
                        f'DTEND:{event_end.strftime("%Y%m%dT%H%M%S")}',
                        f'SUMMARY:{assignment["event_id"]} - {assignment["module_id"]}',
                        f'DESCRIPTION:Teacher: {assignment["teacher_id"]}\\nGroups: {", ".join(assignment["group_ids"])}\\nStudents: {assignment["demand"]}',
                        f'LOCATION:{assignment["room_id"]}',
                        'END:VEVENT'
                    ])

        lines.append('END:VCALENDAR')

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\\n'.join(lines))

        print(f"📅 iCal exported to: {output_file}")

    def export_xml(self, output_file: str):
        """Export to XML format."""
        root = ET.Element('timetable')

        # Metadata
        meta_elem = ET.SubElement(root, 'metadata')
        for key, value in self.meta.items():
            elem = ET.SubElement(meta_elem, key)
            elem.text = str(value)

        # Assignments
        assignments_elem = ET.SubElement(root, 'assignments')

        for assignment in self.assignments:
            assign_elem = ET.SubElement(assignments_elem, 'assignment')

            for key, value in assignment.items():
                if isinstance(value, list):
                    list_elem = ET.SubElement(assign_elem, key)
                    for item in value:
                        item_elem = ET.SubElement(list_elem, 'item')
                        item_elem.text = str(item)
                else:
                    elem = ET.SubElement(assign_elem, key)
                    elem.text = str(value)

        # Write to file
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)

        print(f"📄 XML exported to: {output_file}")

    def export_enhanced_json(self, output_file: str):
        """Export enhanced JSON with additional metadata and statistics."""
        enhanced_data = self.data.copy()

        # Add statistics
        stats = self._calculate_statistics()
        enhanced_data['statistics'] = stats

        # Add export metadata
        enhanced_data['export_info'] = {
            'export_timestamp': datetime.now().isoformat(),
            'export_version': '2.0',
            'total_assignments': len(self.assignments),
            'unique_teachers': len(set(a['teacher_id'] for a in self.assignments)),
            'unique_rooms': len(set(a['room_id'] for a in self.assignments)),
            'unique_modules': len(set(a['module_id'] for a in self.assignments))
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)

        print(f"✨ Enhanced JSON exported to: {output_file}")

    def export_moodle_xml(self, output_file: str):
        """Export in Moodle course format."""
        root = ET.Element('moodle_backup')

        # Course information
        course = ET.SubElement(root, 'course')
        ET.SubElement(course, 'fullname').text = f"Timetable - {self.meta.get('week_name', 'Schedule')}"
        ET.SubElement(course, 'shortname').text = f"TT_{self.meta.get('week_name', 'SCH')}"
        ET.SubElement(course, 'category').text = "Timetables"

        # Activities (events as activities)
        activities = ET.SubElement(root, 'activities')

        for i, assignment in enumerate(self.assignments):
            activity = ET.SubElement(activities, 'activity')
            activity.set('id', str(i + 1))

            ET.SubElement(activity, 'modulename').text = 'label'
            ET.SubElement(activity, 'name').text = assignment['event_id']
            ET.SubElement(activity, 'intro').text = f"""
            <p><strong>Module:</strong> {assignment['module_id']}</p>
            <p><strong>Teacher:</strong> {assignment['teacher_id']}</p>
            <p><strong>Room:</strong> {assignment['room_id']}</p>
            <p><strong>Groups:</strong> {', '.join(assignment['group_ids'])}</p>
            <p><strong>Schedule:</strong> {assignment['timeslot_id']}</p>
            <p><strong>Weeks:</strong> {', '.join(map(str, assignment['weeks']))}</p>
            """

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)

        print(f"🎓 Moodle XML exported to: {output_file}")

    def export_teams_integration(self, output_file: str):
        """Export for Microsoft Teams integration."""
        teams_data = {
            'version': '1.0',
            'name': f"Timetable - {self.meta.get('week_name', 'Schedule')}",
            'description': f"Generated timetable with {len(self.assignments)} events",
            'created': datetime.now().isoformat(),
            'meetings': []
        }

        for assignment in self.assignments:
            # Parse timeslot for Teams meeting
            timeslot_parts = assignment['timeslot_id'].split('_')
            day = timeslot_parts[0] if len(timeslot_parts) > 0 else 'Mon'

            meeting = {
                'id': assignment['event_id'],
                'subject': f"{assignment['module_id']} - {assignment['event_id']}",
                'organizer': assignment['teacher_id'],
                'attendees': assignment['group_ids'],
                'location': assignment['room_id'],
                'recurrence': {
                    'pattern': 'weekly',
                    'dayOfWeek': day.lower(),
                    'weeks': assignment['weeks']
                },
                'duration_minutes': assignment['duration_min'],
                'description': f"Module: {assignment['module_id']}\\nTeacher: {assignment['teacher_id']}\\nStudents: {assignment['demand']}"
            }

            teams_data['meetings'].append(meeting)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(teams_data, f, indent=2, ensure_ascii=False)

        print(f"👥 Teams integration file exported to: {output_file}")

    def export_statistics_report(self, output_file: str):
        """Export detailed statistics report."""
        stats = self._calculate_statistics()

        report_lines = [
            "📊 TIMETABLE STATISTICS REPORT",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Schedule: {self.meta.get('week_name', 'Unknown')}",
            f"Total Events: {len(self.assignments)}",
            "",
            "📈 RESOURCE UTILIZATION",
            "-" * 30
        ]

        # Teacher statistics
        report_lines.extend([
            f"Teachers: {stats['unique_teachers']} teachers",
            f"Average events per teacher: {stats['avg_events_per_teacher']:.1f}",
            f"Teacher workload range: {stats['teacher_workload_range']}",
            ""
        ])

        # Room statistics
        report_lines.extend([
            f"Rooms: {stats['unique_rooms']} rooms used",
            f"Average room utilization: {stats['avg_room_utilization']:.1%}",
            f"Most used room: {stats['most_used_room']} ({stats['most_used_room_count']} events)",
            ""
        ])

        # Time distribution
        report_lines.extend([
            "⏰ TIME DISTRIBUTION",
            "-" * 25
        ])

        for day, count in stats['events_per_day'].items():
            report_lines.append(f"{day}: {count} events")

        report_lines.extend([
            "",
            f"Peak day: {stats['peak_day']} ({stats['peak_day_events']} events)",
            f"Average events per day: {stats['avg_events_per_day']:.1f}",
            ""
        ])

        # Module statistics
        report_lines.extend([
            "📚 MODULE STATISTICS",
            "-" * 25,
            f"Total modules: {stats['unique_modules']}",
            f"Average hours per module: {stats['avg_hours_per_module']:.1f}h/week"
        ])

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\\n'.join(report_lines))

        print(f"📊 Statistics report exported to: {output_file}")

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive statistics."""
        if not self.assignments:
            return {}

        # Basic counts
        unique_teachers = set(a['teacher_id'] for a in self.assignments)
        unique_rooms = set(a['room_id'] for a in self.assignments)
        unique_modules = set(a['module_id'] for a in self.assignments)

        # Teacher workload
        teacher_workload = {}
        for assignment in self.assignments:
            teacher = assignment['teacher_id']
            hours = assignment.get('duration_hours', 0)
            teacher_workload[teacher] = teacher_workload.get(teacher, 0) + hours

        # Room utilization
        room_usage = {}
        for assignment in self.assignments:
            room = assignment['room_id']
            room_usage[room] = room_usage.get(room, 0) + 1

        # Time distribution
        events_per_day = {}
        for assignment in self.assignments:
            day = assignment['timeslot_id'].split('_')[0]
            events_per_day[day] = events_per_day.get(day, 0) + 1

        # Module hours
        module_hours = {}
        for assignment in self.assignments:
            module = assignment['module_id']
            hours = assignment.get('module_hours_per_week', 0)
            if hours > 0:
                module_hours[module] = hours

        return {
            'unique_teachers': len(unique_teachers),
            'unique_rooms': len(unique_rooms),
            'unique_modules': len(unique_modules),
            'avg_events_per_teacher': len(self.assignments) / len(unique_teachers) if unique_teachers else 0,
            'teacher_workload_range': f"{min(teacher_workload.values()):.1f}h - {max(teacher_workload.values()):.1f}h" if teacher_workload else "0h",
            'avg_room_utilization': len(self.assignments) / len(unique_rooms) if unique_rooms else 0,
            'most_used_room': max(room_usage, key=room_usage.get) if room_usage else "None",
            'most_used_room_count': max(room_usage.values()) if room_usage else 0,
            'events_per_day': events_per_day,
            'peak_day': max(events_per_day, key=events_per_day.get) if events_per_day else "None",
            'peak_day_events': max(events_per_day.values()) if events_per_day else 0,
            'avg_events_per_day': sum(events_per_day.values()) / len(events_per_day) if events_per_day else 0,
            'avg_hours_per_module': sum(module_hours.values()) / len(module_hours) if module_hours else 0
        }

    def export_all_formats(self, base_filename: str):
        """Export to all available formats."""
        base_name = base_filename.rsplit('.', 1)[0]

        print("🚀 Exporting to all formats...")

        try:
            self.export_csv(f"{base_name}.csv")
            self.export_enhanced_json(f"{base_name}_enhanced.json")
            self.export_xml(f"{base_name}.xml")
            self.export_ical(f"{base_name}.ics")
            self.export_moodle_xml(f"{base_name}_moodle.xml")
            self.export_teams_integration(f"{base_name}_teams.json")
            self.export_statistics_report(f"{base_name}_stats.txt")

            print("✅ All formats exported successfully!")

        except Exception as e:
            print(f"❌ Error during export: {e}")

def load_and_export(json_file: str, formats: List[str] = None, output_prefix: str = "timetable"):
    """Load timetable data and export to specified formats."""
    if formats is None:
        formats = ['csv', 'ical', 'xml']

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        exporter = EnhancedTimetableExporter(data)

        for format_name in formats:
            if format_name == 'csv':
                exporter.export_csv(f"{output_prefix}.csv")
            elif format_name == 'ical':
                exporter.export_ical(f"{output_prefix}.ics")
            elif format_name == 'xml':
                exporter.export_xml(f"{output_prefix}.xml")
            elif format_name == 'json':
                exporter.export_enhanced_json(f"{output_prefix}_enhanced.json")
            elif format_name == 'moodle':
                exporter.export_moodle_xml(f"{output_prefix}_moodle.xml")
            elif format_name == 'teams':
                exporter.export_teams_integration(f"{output_prefix}_teams.json")
            elif format_name == 'stats':
                exporter.export_statistics_report(f"{output_prefix}_stats.txt")
            elif format_name == 'all':
                exporter.export_all_formats(output_prefix)
                break
            else:
                print(f"⚠️ Unknown format: {format_name}")

    except Exception as e:
        print(f"❌ Error loading or exporting: {e}")

if __name__ == "__main__":
    # Example usage
    print("📤 Enhanced Timetable Exporter")
    print("Usage: load_and_export('timetable_output.json', ['csv', 'ical', 'xml'])")
