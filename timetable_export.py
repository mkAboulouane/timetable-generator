"""
Timetable Export Module
Generates visual timetable formats (HTML, PDF, PNG) from the JSON output.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from collections import defaultdict


def load_output_json(path: str) -> Dict[str, Any]:
    """Load the timetable output JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_html_timetable(
    data: Dict[str, Any],
    output_path: str,
    week_filter: Optional[int] = None,
    group_filter: Optional[str] = None,
    teacher_filter: Optional[str] = None,
    session_filter: Optional[str] = None,
    title_override: Optional[str] = None,
) -> str:
    """
    Generate an HTML timetable view from the output data.

    Args:
        data: The output JSON data
        output_path: Path to save the HTML file
        week_filter: If provided, show only this week's schedule
        group_filter: If provided, show only this group's schedule
        teacher_filter: If provided, show only this teacher's schedule
        session_filter: If provided, show only this session's schedule
        title_override: If provided, use this as the title instead of week_name

    Returns:
        Path to the generated HTML file
    """
    meta = data.get("meta", {})
    assignments = data.get("assignments", [])

    # Filter by session early if specified
    if session_filter:
        assignments = [a for a in assignments if a.get("session_id") == session_filter]

    week_name = title_override or meta.get("week_name", "Timetable")
    weeks_total = meta.get("weeks_total", 16)
    status = meta.get("status", "unknown")
    strategy = meta.get("strategy", "unknown")

    # Extract unique days and time slots from assignments
    timeslot_info = {}
    days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for a in assignments:
        ts_id = a["timeslot_id"]
        if ts_id not in timeslot_info:
            # Parse timeslot id like "Mon_08-10" or "Tue_10-1230"
            parts = ts_id.split("_", 1)
            day = parts[0] if len(parts) > 1 else "Mon"
            time_part = parts[1] if len(parts) > 1 else ts_id
            timeslot_info[ts_id] = {"day": day, "time": time_part, "id": ts_id}

    # Get unique days and sort them
    days = sorted(set(t["day"] for t in timeslot_info.values()),
                  key=lambda d: days_order.index(d) if d in days_order else 99)

    # Get unique time slots (just the time part) and sort them
    time_slots = sorted(set(t["time"] for t in timeslot_info.values()))

    # If no assignments, use default structure
    if not days:
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    if not time_slots:
        time_slots = ["08-10", "10-12", "14-16", "16-18"]

    # Build grid: timeslot -> day -> list of events
    # Consider week filter
    grid = defaultdict(lambda: defaultdict(list))

    for a in assignments:
        weeks = a.get("weeks", [])

        # Apply filters
        if week_filter is not None and week_filter not in weeks:
            continue
        if group_filter is not None and group_filter not in a.get("group_ids", []):
            continue
        if teacher_filter is not None and a.get("teacher_id") != teacher_filter:
            continue

        ts_id = a["timeslot_id"]
        if ts_id in timeslot_info:
            day = timeslot_info[ts_id]["day"]
            time = timeslot_info[ts_id]["time"]
            grid[time][day].append(a)

    # Define colors for different modules
    module_colors = {}
    color_palette = [
        "#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#E91E63",
        "#00BCD4", "#8BC34A", "#FFC107", "#673AB7", "#3F51B5",
        "#009688", "#CDDC39", "#FF5722", "#795548", "#607D8B"
    ]
    color_idx = 0
    for a in assignments:
        mid = a.get("module_id", "")
        if mid and mid not in module_colors:
            module_colors[mid] = color_palette[color_idx % len(color_palette)]
            color_idx += 1

    # Build filter description
    filter_desc = []
    if session_filter:
        filter_desc.append(f"Session: {session_filter}")
    if week_filter:
        filter_desc.append(f"Week {week_filter}")
    if group_filter:
        filter_desc.append(f"Group: {group_filter}")
    if teacher_filter:
        filter_desc.append(f"Teacher: {teacher_filter}")
    filter_text = " | ".join(filter_desc) if filter_desc else "All Sessions & Weeks"

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timetable - {week_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .header .meta {{
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
            margin-top: 15px;
        }}
        .header .meta-item {{
            background: rgba(255,255,255,0.1);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
        }}
        .header .status {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 10px;
        }}
        .header .status.success {{
            background: #4CAF50;
        }}
        .header .status.failure {{
            background: #f44336;
        }}
        .filter-info {{
            background: #f8f9fa;
            padding: 15px 30px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 1.1em;
            color: #555;
        }}
        .timetable-wrapper {{
            padding: 30px;
            overflow-x: auto;
        }}
        .timetable {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}
        .timetable th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 10px;
            text-align: center;
            font-weight: 600;
            font-size: 1.1em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .timetable th.time-header {{
            width: 100px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        }}
        .timetable td {{
            border: 1px solid #e0e0e0;
            padding: 8px;
            vertical-align: top;
            min-height: 120px;
            height: 120px;
        }}
        .timetable td.time-cell {{
            background: #f8f9fa;
            text-align: center;
            font-weight: 600;
            color: #333;
            vertical-align: middle;
        }}
        .event {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 6px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.2);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .event:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        .event-title {{
            font-weight: bold;
            font-size: 0.95em;
            margin-bottom: 6px;
            border-bottom: 1px solid rgba(255,255,255,0.3);
            padding-bottom: 4px;
        }}
        .event-details {{
            font-size: 0.8em;
            opacity: 0.9;
        }}
        .event-details div {{
            margin: 2px 0;
        }}
        .event-weeks {{
            font-size: 0.75em;
            opacity: 0.8;
            margin-top: 5px;
            padding-top: 5px;
            border-top: 1px solid rgba(255,255,255,0.2);
        }}
        .legend {{
            padding: 20px 30px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
        }}
        .legend h3 {{
            margin-bottom: 15px;
            color: #333;
        }}
        .legend-items {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        .footer {{
            background: #1a1a2e;
            color: white;
            padding: 15px 30px;
            text-align: center;
            font-size: 0.9em;
            opacity: 0.8;
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
            }}
            .event:hover {{
                transform: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📅 {week_name}</h1>
            <div class="meta">
                <span class="meta-item">📊 Strategy: {strategy}</span>
                <span class="meta-item">📆 Total Weeks: {weeks_total}</span>
                <span class="meta-item">📝 Events: {meta.get('events_scheduled', 0)}/{meta.get('events_total', 0)}</span>
            </div>
            <div class="status {'success' if status == 'success' else 'failure'}">{status.upper()}</div>
        </div>
        
        <div class="filter-info">
            🔍 Showing: <strong>{filter_text}</strong>
        </div>
        
        <div class="timetable-wrapper">
            <table class="timetable">
                <thead>
                    <tr>
                        <th class="time-header">Time</th>
"""

    # Add day headers
    for day in days:
        html += f'                        <th>{day}</th>\n'

    html += """                    </tr>
                </thead>
                <tbody>
"""

    # Add rows for each time slot
    for time in time_slots:
        html += f'                    <tr>\n'
        html += f'                        <td class="time-cell">{time.replace("-", "<br>to<br>")}</td>\n'

        for day in days:
            html += '                        <td>\n'
            events = grid[time][day]
            for event in events:
                module_id = event.get("module_id", "")
                color = module_colors.get(module_id, "#667eea")
                weeks_list = event.get("weeks", [])
                weeks_str = format_weeks_compact(weeks_list)

                html += f'''                            <div class="event" style="background: {color};">
                                <div class="event-title">{event.get("event_id", "")}</div>
                                <div class="event-details">
                                    <div>🏫 {event.get("room_id", "")} ({event.get("room_capacity", "")} seats)</div>
                                    <div>👨‍🏫 {event.get("teacher_id", "")}</div>
                                    <div>👥 {", ".join(event.get("group_ids", []))}</div>
                                </div>
                                <div class="event-weeks">📆 Weeks: {weeks_str}</div>
                            </div>
'''
            html += '                        </td>\n'

        html += '                    </tr>\n'

    html += """                </tbody>
            </table>
        </div>
        
        <div class="legend">
            <h3>📚 Module Legend</h3>
            <div class="legend-items">
"""

    for module_id, color in module_colors.items():
        html += f'                <div class="legend-item"><div class="legend-color" style="background: {color};"></div><span>{module_id}</span></div>\n'

    html += """            </div>
        </div>
        
        <div class="footer">
            Generated by Auto-Drive Timetable Agent
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def format_weeks_compact(weeks: List[int]) -> str:
    """Format a list of weeks into a compact string like '1-4, 6, 8-10'."""
    if not weeks:
        return ""

    weeks = sorted(weeks)
    ranges = []
    start = weeks[0]
    end = weeks[0]

    for w in weeks[1:]:
        if w == end + 1:
            end = w
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = end = w

    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ", ".join(ranges)


def generate_weekly_html_reports(
    data: Dict[str, Any],
    output_dir: str,
) -> List[str]:
    """Generate individual HTML timetables for each week."""
    os.makedirs(output_dir, exist_ok=True)

    weeks_total = data.get("meta", {}).get("weeks_total", 16)
    generated_files = []

    for week in range(1, weeks_total + 1):
        output_path = os.path.join(output_dir, f"week_{week:02d}.html")
        generate_html_timetable(data, output_path, week_filter=week)
        generated_files.append(output_path)

    return generated_files


def generate_session_html_reports(
    data: Dict[str, Any],
    output_dir: str,
    generate_combined: bool = True,
) -> List[str]:
    """
    Generate individual HTML timetables for each session.

    Args:
        data: The output JSON data
        output_dir: Directory to save the HTML files
        generate_combined: If True, also generate a combined view with all sessions

    Returns:
        List of generated file paths
    """
    os.makedirs(output_dir, exist_ok=True)

    assignments = data.get("assignments", [])
    meta = data.get("meta", {})
    week_name = meta.get("week_name", "Timetable")

    # Get unique sessions
    sessions = sorted(set(a.get("session_id", "unknown") for a in assignments))

    generated_files = []

    # Generate per-session files
    for session in sessions:
        safe_session_name = session.replace("/", "_").replace("\\", "_").replace(" ", "_")
        output_path = os.path.join(output_dir, f"session_{safe_session_name}.html")
        generate_html_timetable(
            data, output_path,
            session_filter=session,
            title_override=f"{week_name} - {session}"
        )
        generated_files.append(output_path)
        print(f"  ✓ Session {session}: {output_path}")

    # Generate combined view if requested
    if generate_combined:
        combined_path = os.path.join(output_dir, "all_sessions.html")
        generate_html_timetable(data, combined_path, title_override=f"{week_name} - All Sessions")
        generated_files.append(combined_path)
        print(f"  ✓ Combined: {combined_path}")

    # Generate index page
    index_path = os.path.join(output_dir, "index.html")
    _generate_session_index(sessions, week_name, meta, index_path, generate_combined)
    generated_files.append(index_path)
    print(f"  ✓ Index: {index_path}")

    return generated_files


def _generate_session_index(
    sessions: List[str],
    week_name: str,
    meta: Dict[str, Any],
    output_path: str,
    has_combined: bool = True,
) -> None:
    """Generate an index HTML page linking to all session timetables."""
    status = meta.get("status", "unknown")
    strategy = meta.get("strategy", "unknown")
    weeks_total = meta.get("weeks_total", 16)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timetable Index - {week_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.2em;
            margin-bottom: 15px;
        }}
        .header .meta {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .header .meta-item {{
            background: rgba(255,255,255,0.1);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
        }}
        .status {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 15px;
        }}
        .status.success {{ background: #4CAF50; }}
        .status.failure {{ background: #f44336; }}
        .content {{
            padding: 40px;
        }}
        .content h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}
        .session-list {{
            list-style: none;
        }}
        .session-item {{
            margin-bottom: 15px;
        }}
        .session-link {{
            display: block;
            padding: 20px 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}
        .session-link:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5);
        }}
        .session-link.combined {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            box-shadow: 0 4px 15px rgba(26, 26, 46, 0.4);
        }}
        .session-link.combined:hover {{
            box-shadow: 0 8px 25px rgba(26, 26, 46, 0.5);
        }}
        .session-icon {{ margin-right: 10px; }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📅 {week_name}</h1>
            <div class="meta">
                <span class="meta-item">📊 Strategy: {strategy}</span>
                <span class="meta-item">📆 Weeks: {weeks_total}</span>
                <span class="meta-item">📚 Sessions: {len(sessions)}</span>
            </div>
            <div class="status {'success' if status == 'success' else 'failure'}">{status.upper()}</div>
        </div>
        
        <div class="content">
            <h2>📚 Select a Session</h2>
            <ul class="session-list">
"""

    for session in sessions:
        safe_name = session.replace("/", "_").replace("\\", "_").replace(" ", "_")
        html += f'''                <li class="session-item">
                    <a class="session-link" href="session_{safe_name}.html">
                        <span class="session-icon">🎓</span>{session}
                    </a>
                </li>
'''

    if has_combined:
        html += '''                <li class="session-item">
                    <a class="session-link combined" href="all_sessions.html">
                        <span class="session-icon">📋</span>View All Sessions Combined
                    </a>
                </li>
'''

    html += f"""            </ul>
        </div>
        
        <div class="footer">
            Generated by Auto-Drive Timetable Agent
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def export_to_pdf(html_path: str, pdf_path: str) -> Optional[str]:
    """
    Convert HTML timetable to PDF using available tools.
    Requires either weasyprint or pdfkit to be installed.
    """
    try:
        # Try weasyprint first
        from weasyprint import HTML
        HTML(html_path).write_pdf(pdf_path)
        return pdf_path
    except ImportError:
        pass

    try:
        # Try pdfkit (requires wkhtmltopdf)
        import pdfkit
        pdfkit.from_file(html_path, pdf_path)
        return pdf_path
    except ImportError:
        pass

    print("Warning: Neither 'weasyprint' nor 'pdfkit' is installed.")
    print("Install one of them to enable PDF export:")
    print("  pip install weasyprint")
    print("  or")
    print("  pip install pdfkit  (also requires wkhtmltopdf)")
    return None


def export_to_png(html_path: str, png_path: str) -> Optional[str]:
    """
    Convert HTML timetable to PNG using available tools.
    Requires either playwright or selenium to be installed.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(f"file:///{html_path.replace(os.sep, '/')}")
            page.screenshot(path=png_path, full_page=True)
            browser.close()
        return png_path
    except ImportError:
        pass

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=1400,900")

        driver = webdriver.Chrome(options=options)
        driver.get(f"file:///{html_path.replace(os.sep, '/')}")
        driver.save_screenshot(png_path)
        driver.quit()
        return png_path
    except ImportError:
        pass

    print("Warning: Neither 'playwright' nor 'selenium' is installed.")
    print("Install one of them to enable PNG export:")
    print("  pip install playwright && playwright install chromium")
    print("  or")
    print("  pip install selenium  (also requires chromedriver)")
    return None


def main():
    """Main function to demonstrate timetable export."""
    import argparse

    parser = argparse.ArgumentParser(description="Export timetable to various formats")
    parser.add_argument("input", nargs="?", default="timetable_output.json",
                        help="Input JSON file (default: timetable_output.json)")
    parser.add_argument("-o", "--output", default="timetable_visual",
                        help="Output file name without extension (default: timetable_visual)")
    parser.add_argument("-f", "--format", choices=["html", "pdf", "png", "all"],
                        default="html", help="Output format (default: html)")
    parser.add_argument("-w", "--week", type=int, default=None,
                        help="Filter by specific week number")
    parser.add_argument("-g", "--group", type=str, default=None,
                        help="Filter by group ID")
    parser.add_argument("-t", "--teacher", type=str, default=None,
                        help="Filter by teacher ID")
    parser.add_argument("-s", "--session", type=str, default=None,
                        help="Filter by session ID")
    parser.add_argument("--weekly", action="store_true",
                        help="Generate separate HTML files for each week")
    parser.add_argument("--by-session", action="store_true",
                        help="Generate separate HTML files for each session (with index page)")

    args = parser.parse_args()

    # Load data
    print(f"Loading {args.input}...")
    data = load_output_json(args.input)

    # Generate session-based reports if requested
    if args.by_session:
        output_dir = f"{args.output}_sessions"
        print(f"Generating session-based reports in {output_dir}/...")
        files = generate_session_html_reports(data, output_dir)
        print(f"\n✓ Generated {len(files)} files.")
        print(f"Open {output_dir}/index.html to browse all sessions.")
        return

    # Generate weekly reports if requested
    if args.weekly:
        output_dir = f"{args.output}_weekly"
        print(f"Generating weekly reports in {output_dir}/...")
        files = generate_weekly_html_reports(data, output_dir)
        print(f"Generated {len(files)} weekly HTML files.")
        return

    # Generate HTML
    html_path = f"{args.output}.html"
    print(f"Generating HTML: {html_path}")
    generate_html_timetable(
        data, html_path,
        week_filter=args.week,
        group_filter=args.group,
        teacher_filter=args.teacher,
        session_filter=args.session
    )
    print(f"✓ HTML generated: {html_path}")

    # Generate PDF if requested
    if args.format in ("pdf", "all"):
        pdf_path = f"{args.output}.pdf"
        print(f"Generating PDF: {pdf_path}")
        result = export_to_pdf(html_path, pdf_path)
        if result:
            print(f"✓ PDF generated: {pdf_path}")

    # Generate PNG if requested
    if args.format in ("png", "all"):
        png_path = f"{args.output}.png"
        print(f"Generating PNG: {png_path}")
        result = export_to_png(html_path, png_path)
        if result:
            print(f"✓ PNG generated: {png_path}")

    print("\nDone! Open the HTML file in a browser to view the timetable.")
    print("You can also print it to PDF from the browser (Ctrl+P).")


if __name__ == "__main__":
    main()

