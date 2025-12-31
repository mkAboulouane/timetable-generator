# Basic HTML export
python timetable_export.py timetable_output.json -o timetable_visual

# Filter by week
python timetable_export.py timetable_output.json -o week5 -w 5

# Filter by group
python timetable_export.py timetable_output.json -o group1 -g "CP-1-S1_G1"

# Generate weekly reports (one HTML per week)
python timetable_export.py timetable_output.json -o reports --weekly

# Export to PDF (if weasyprint is installed)
python timetable_export.py timetable_output.json -o timetable -f pdf

# Filter by specific session
python timetable_export.py output.json -s "CP-1-S1"

# Filter by week
python timetable_export.py output.json -w 5

# Filter by group
python timetable_export.py output.json -g "CP_G1"

# Filter by teacher
python timetable_export.py output.json -t "T_MATH"


pip install weasyprint   # For PDF
# or
pip install playwright   # For PNG
playwright install chromium
