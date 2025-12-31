# 📚 Auto-Drive Timetable Agent - Documentation

> **Version:** 1.0  
> **Date:** December 31, 2025  
> **Author:** Auto-Drive Agent Team

---

## Table of Contents

1. [Overview](#1-overview)
2. [Input JSON Format](#2-input-json-format)
3. [Constraints & Behavior](#3-constraints--behavior)
4. [Search Algorithms](#4-search-algorithms)
5. [Output JSON Format](#5-output-json-format)
6. [Visual Export](#6-visual-export)
7. [Usage Examples](#7-usage-examples)

---

## 1. Overview

The **Auto-Drive Timetable Agent** is an AI-powered scheduling system that automatically generates feasible timetables for educational institutions. It uses state-space search algorithms to find valid assignments of events to timeslots and rooms while respecting all hard constraints.

### Key Features

- ✅ **Multi-session support** - Handle multiple programs/classes (e.g., CP-1-S1, GI-S1)
- ✅ **Week-aware scheduling** - Events can run on specific weeks (not just all semester)
- ✅ **Multiple search algorithms** - DFS, BFS, UCS, A* with automatic comparison
- ✅ **MRV heuristic** - Minimum Remaining Values for efficient search
- ✅ **Visual exports** - HTML timetables with per-session views

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT (JSON)                                │
│  config, timeslots, rooms, teachers, sessions/groups/modules/events │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      timetable_io.py                                │
│              (Parse JSON → TimetablingProblem)                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     timetable_agent.py                              │
│         (Search Algorithms: DFS, BFS, UCS, A*)                      │
│         (Constraint Checking: teacher, group, room, weeks)          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        OUTPUT (JSON)                                │
│              (meta + assignments with all details)                  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    timetable_export.py                              │
│            (Visual: HTML, PDF, PNG per session/week)                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Input JSON Format

### 2.1 Complete Structure

```json
{
  "config": {
    "week_name": "Semester-1-2025",
    "weeks_total": 16,
    "strategy": "dfs",
    "use_mrv": true
  },
  "timeslots": [...],
  "rooms": [...],
  "teachers": [...],
  "sessions": [...]
}
```

### 2.2 Config Object

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `week_name` | string | `""` | Identifier/name for the schedule (appears in output) |
| `weeks_total` | integer | `16` | Total number of weeks in the semester |
| `strategy` | string | `"dfs"` | Search algorithm: `"dfs"`, `"bfs"`, `"ucs"`, `"astar"` |
| `use_mrv` | boolean | `true` | Enable Minimum Remaining Values heuristic |

**Example:**
```json
{
  "config": {
    "week_name": "Fall-2025-Schedule",
    "weeks_total": 14,
    "strategy": "dfs",
    "use_mrv": true
  }
}
```

### 2.3 Timeslots Array

Defines all available time periods in a week.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique identifier (e.g., `"Mon_08-10"`) |
| `day` | string | ✅ | Day of week: `"Mon"`, `"Tue"`, `"Wed"`, `"Thu"`, `"Fri"`, `"Sat"`, `"Sun"` |
| `start` | string | ✅ | Start time (e.g., `"08:00"`) |
| `end` | string | ✅ | End time (e.g., `"10:00"`) |
| `duration_min` | integer | ✅ | Duration in minutes (e.g., `120`) |

**Example:**
```json
{
  "timeslots": [
    { "id": "Mon_08-10", "day": "Mon", "start": "08:00", "end": "10:00", "duration_min": 120 },
    { "id": "Mon_10-12", "day": "Mon", "start": "10:00", "end": "12:00", "duration_min": 120 },
    { "id": "Mon_14-16", "day": "Mon", "start": "14:00", "end": "16:00", "duration_min": 120 },
    { "id": "Tue_08-10", "day": "Tue", "start": "08:00", "end": "10:00", "duration_min": 120 }
  ]
}
```

### 2.4 Rooms Array

Defines all available rooms/venues.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique identifier (e.g., `"Room_A1"`) |
| `capacity` | integer | ✅ | Maximum number of students |
| `available` | array[string] | ❌ | List of timeslot IDs when room is available. If empty/missing, room is always available. |

**Example:**
```json
{
  "rooms": [
    { "id": "Amphi_A", "capacity": 200, "available": ["Mon_08-10", "Mon_10-12", "Tue_08-10"] },
    { "id": "Room_101", "capacity": 40, "available": ["Mon_08-10", "Mon_10-12", "Mon_14-16", "Tue_08-10"] },
    { "id": "Lab_Info", "capacity": 30, "available": ["Mon_14-16", "Tue_08-10"] }
  ]
}
```

### 2.5 Teachers Array

Defines all teachers and their availability.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique identifier (e.g., `"T_DUPONT"`) |
| `available` | array[string] | ❌ | List of timeslot IDs when teacher is available. If empty/missing, teacher is never available. |

**Example:**
```json
{
  "teachers": [
    { "id": "T_MATH", "available": ["Mon_08-10", "Mon_10-12", "Tue_08-10", "Tue_10-12"] },
    { "id": "T_INFO", "available": ["Mon_14-16", "Tue_08-10", "Tue_14-16"] },
    { "id": "T_PHYS", "available": ["Mon_08-10", "Wed_08-10", "Wed_10-12"] }
  ]
}
```

### 2.6 Sessions Array

Sessions represent distinct programs or class cohorts (e.g., "Computer Science Year 1", "Engineering Year 2").

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique session identifier (e.g., `"CP-1-S1"`) |
| `weeks_total` | integer | ❌ | Override global weeks_total for this session |
| `groups` | array | ✅ | Student groups in this session |
| `modules` | array | ✅ | Modules/courses in this session |

**Example:**
```json
{
  "sessions": [
    {
      "id": "CP-Year1-Sem1",
      "groups": [...],
      "modules": [...]
    },
    {
      "id": "GI-Year2-Sem1",
      "weeks_total": 14,
      "groups": [...],
      "modules": [...]
    }
  ]
}
```

### 2.7 Groups (within Session)

Student groups belong to a session.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique group identifier (e.g., `"CP_G1"`) |
| `size` | integer | ✅ | Number of students in the group |
| `available` | array[string] | ❌ | List of timeslot IDs when group is available |

**Example:**
```json
{
  "groups": [
    { "id": "CP_G1", "size": 28, "available": ["Mon_08-10", "Mon_10-12", "Tue_08-10"] },
    { "id": "CP_G2", "size": 30, "available": ["Mon_08-10", "Mon_10-12", "Tue_08-10"] }
  ]
}
```

### 2.8 Modules (within Session)

Modules are courses/subjects containing one or more events.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique module identifier (e.g., `"MATH101"`) |
| `hours_per_week` | number | ❌ | Total hours per week for this module (e.g., `2`, `4`, `6`). Used for documentation and validation. |
| `min_room_capacity` | integer | ❌ | Minimum required room capacity (default: 0) |
| `weeks` | object | ❌ | Weeks when this module runs (inherited by events) |
| `events` | array | ✅ | List of events for this module |

**Example:**
```json
{
  "modules": [
    {
      "id": "MATH101",
      "hours_per_week": 4,
      "min_room_capacity": 60,
      "weeks": { "mode": "all" },
      "events": [
        { "id": "CM_MATH", "duration_min": 120, ... },
        { "id": "TD_MATH", "duration_min": 120, ... }
      ]
    },
    {
      "id": "INFO101",
      "hours_per_week": 6,
      "min_room_capacity": 30,
      "events": [
        { "id": "CM_INFO", "duration_min": 120, ... },
        { "id": "TD_INFO_G1", "duration_min": 120, ... },
        { "id": "TP_INFO_G1", "duration_min": 120, ... }
      ]
    }
  ]
}
```

> **Note:** The `hours_per_week` field is informational. The actual scheduling is based on individual event `duration_min` values. Use this to document the expected weekly load for each module.

### 2.9 Weeks Object

The `weeks` object specifies which weeks an event/module runs.

#### Mode: `"all"` (default)
Runs on all weeks (1 to weeks_total).
```json
{ "weeks": { "mode": "all" } }
```
Or simply omit the `weeks` field.

#### Mode: `"list"`
Runs on specific weeks listed explicitly.
```json
{ "weeks": { "mode": "list", "values": [1, 3, 5, 7, 9, 11, 13, 15] } }
```

#### Mode: `"ranges"`
Runs on week ranges (inclusive).
```json
{ "weeks": { "mode": "ranges", "values": ["1-8", "12-16"] } }
```
This means weeks 1,2,3,4,5,6,7,8,12,13,14,15,16.

### 2.10 Events (within Module)

Events are the actual scheduled items (lectures, tutorials, labs).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique event identifier (e.g., `"CM_MATH101"`) |
| `teacher_id` | string | ✅ | ID of the teacher for this event |
| `duration_min` | integer | ✅ | Duration in minutes (must match a timeslot duration) |
| `audience` | object | ✅ | Specifies which groups attend |
| `allowed_slots` | array[string] | ❌ | Restrict to specific timeslot IDs |
| `weeks` | object | ❌ | Override module weeks for this event |

#### Audience Object

**Type: `"all_groups"`** - All groups in the session attend (e.g., for lectures)
```json
{ "audience": { "type": "all_groups" } }
```

**Type: `"groups"`** - Specific groups attend (e.g., for tutorials)
```json
{ "audience": { "type": "groups", "group_ids": ["CP_G1"] } }
```

### 2.11 Complete Input Example

```json
{
  "config": {
    "week_name": "Fall-2025",
    "weeks_total": 16,
    "strategy": "dfs",
    "use_mrv": true
  },
  "timeslots": [
    { "id": "Mon_08-10", "day": "Mon", "start": "08:00", "end": "10:00", "duration_min": 120 },
    { "id": "Mon_10-12", "day": "Mon", "start": "10:00", "end": "12:00", "duration_min": 120 },
    { "id": "Tue_08-10", "day": "Tue", "start": "08:00", "end": "10:00", "duration_min": 120 },
    { "id": "Tue_10-12", "day": "Tue", "start": "10:00", "end": "12:00", "duration_min": 120 }
  ],
  "rooms": [
    { "id": "Amphi_A", "capacity": 100, "available": ["Mon_08-10", "Mon_10-12", "Tue_08-10", "Tue_10-12"] },
    { "id": "Room_101", "capacity": 35, "available": ["Mon_08-10", "Mon_10-12", "Tue_08-10", "Tue_10-12"] }
  ],
  "teachers": [
    { "id": "T_MATH", "available": ["Mon_08-10", "Mon_10-12", "Tue_08-10", "Tue_10-12"] },
    { "id": "T_INFO", "available": ["Mon_10-12", "Tue_10-12"] }
  ],
  "sessions": [
    {
      "id": "CP-Year1",
      "groups": [
        { "id": "CP_G1", "size": 28, "available": ["Mon_08-10", "Mon_10-12", "Tue_08-10", "Tue_10-12"] },
        { "id": "CP_G2", "size": 30, "available": ["Mon_08-10", "Mon_10-12", "Tue_08-10", "Tue_10-12"] }
      ],
      "modules": [
        {
          "id": "MATH101",
          "hours_per_week": 2,
          "min_room_capacity": 60,
          "weeks": { "mode": "list", "values": [1, 3, 5, 7, 9, 11, 13, 15] },
          "events": [
            {
              "id": "CM_MATH101",
              "teacher_id": "T_MATH",
              "audience": { "type": "all_groups" },
              "duration_min": 120
            }
          ]
        },
        {
          "id": "INFO101",
          "hours_per_week": 4,
          "min_room_capacity": 30,
          "weeks": { "mode": "ranges", "values": ["1-8", "10-16"] },
          "events": [
            {
              "id": "TD_INFO_G1",
              "teacher_id": "T_INFO",
              "audience": { "type": "groups", "group_ids": ["CP_G1"] },
              "duration_min": 120
            },
            {
              "id": "TD_INFO_G2",
              "teacher_id": "T_INFO",
              "audience": { "type": "groups", "group_ids": ["CP_G2"] },
              "duration_min": 120
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 3. Constraints & Behavior

### 3.1 Hard Constraints

The agent enforces the following **hard constraints** that cannot be violated:

| # | Constraint | Description |
|---|------------|-------------|
| 1 | **Duration Match** | Event duration must exactly match timeslot duration |
| 2 | **Teacher Availability** | Teacher must be available during the timeslot (weekly pattern) |
| 3 | **Group Availability** | All groups must be available during the timeslot (weekly pattern) |
| 4 | **Room Availability** | Room must be available during the timeslot (weekly pattern) |
| 5 | **Room Capacity** | Room capacity ≥ max(sum of group sizes, min_room_capacity) |
| 6 | **Teacher Conflict** | Same teacher cannot have 2 events at same timeslot if weeks overlap |
| 7 | **Group Conflict** | Same group cannot have 2 events at same timeslot if weeks overlap |
| 8 | **Room Conflict** | Same room cannot host 2 events at same timeslot if weeks overlap |

### 3.2 Week-Aware Conflict Detection

Conflicts are checked using **week intersection**:

```
Event A: weeks = {1, 2, 3, 4}
Event B: weeks = {5, 6, 7, 8}
→ NO CONFLICT (disjoint weeks, can share same slot/room)

Event A: weeks = {1, 2, 3, 4, 5}
Event B: weeks = {4, 5, 6, 7, 8}
→ CONFLICT (weeks 4,5 overlap, cannot share same slot/room)
```

### 3.3 Constraint Checking Flow

```
For each candidate action (event, timeslot, room):
│
├─ 1. Is timeslot duration == event duration?
│     └─ NO → Skip (incompatible)
│
├─ 2. Is teacher available at this timeslot?
│     └─ NO → Skip (teacher unavailable)
│
├─ 3. Are ALL groups available at this timeslot?
│     └─ NO → Skip (group unavailable)
│
├─ 4. Is room available at this timeslot?
│     └─ NO → Skip (room unavailable)
│
├─ 5. Is room capacity sufficient?
│     └─ NO → Skip (room too small)
│
├─ 6. Is teacher free? (no conflict with already assigned events)
│     └─ Check: same teacher + same timeslot + weeks intersect?
│     └─ CONFLICT → Skip
│
├─ 7. Are all groups free? (no conflict)
│     └─ Check: same group + same timeslot + weeks intersect?
│     └─ CONFLICT → Skip
│
├─ 8. Is room free? (no conflict)
│     └─ Check: same room + same timeslot + weeks intersect?
│     └─ CONFLICT → Skip
│
└─ ✅ All checks passed → Valid action
```

### 3.4 MRV Heuristic (Minimum Remaining Values)

When `use_mrv: true`, the agent selects the next event to schedule based on:

```
Domain Size = |compatible_slots| × |compatible_rooms|
```

The event with the **smallest domain size** is scheduled first. This:
- Fails faster on impossible branches
- Reduces search space significantly
- Typically finds solutions much faster

### 3.5 Precomputation

For efficiency, the agent precomputes:

1. **Compatible Rooms per Event:**
   - Rooms where capacity ≥ max(demand, min_room_capacity)

2. **Compatible Slots per Event:**
   - Slots with matching duration
   - Where teacher is available
   - Where all groups are available
   - Filtered by `allowed_slots` if specified

---

## 4. Search Algorithms

### 4.1 Available Algorithms

| Algorithm | Description | Best For |
|-----------|-------------|----------|
| **DFS** | Depth-First Search | Fast first solution, memory efficient |
| **BFS** | Breadth-First Search | Shortest path (fewest assignments) |
| **UCS** | Uniform Cost Search | Optimal cost (currently all costs = 1) |
| **A*** | A* Search | Optimal with heuristic (currently h=0) |

### 4.2 Algorithm Comparison Mode

By default, the agent runs **all 4 algorithms** and compares:

```
====================================================================================================
  COMPARAISON DES ALGORITHMES DE RECHERCHE
====================================================================================================
Algorithme   Statut       Itérations   Explorés     Max Frontière   Coût Final   Temps (s)   
----------------------------------------------------------------------------------------------------
DFS          ✅ Succès     9            8            12              5.0          0.0015      
BFS          ✅ Succès     82           209          128             5.0          0.0024      
UCS          ✅ Succès     82           82           128             5.0          0.0028      
A*           ✅ Succès     82           82           128             5.0          0.0026      
====================================================================================================
```

### 4.3 State Representation

The state is a tuple of assignments:
```python
state = (
    ("event_id_1", "timeslot_id", "room_id"),
    ("event_id_2", "timeslot_id", "room_id"),
    ...
)
```

### 4.4 Goal Test

The goal is reached when all events are assigned:
```python
len(state) == len(all_events)
```

---

## 5. Output JSON Format

### 5.1 Structure

```json
{
  "meta": {
    "week_name": "Fall-2025",
    "weeks_total": 16,
    "strategy": "dfs",
    "use_mrv": true,
    "status": "success",
    "events_total": 5,
    "events_scheduled": 5
  },
  "assignments": [...]
}
```

### 5.2 Meta Object

| Field | Type | Description |
|-------|------|-------------|
| `week_name` | string | From input config |
| `weeks_total` | integer | Total weeks in semester |
| `strategy` | string | Algorithm used |
| `use_mrv` | boolean | Whether MRV was enabled |
| `status` | string | `"success"` or `"failure"` |
| `events_total` | integer | Total events to schedule |
| `events_scheduled` | integer | Events successfully scheduled |

### 5.3 Assignment Object

Each assignment contains:

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string | Event identifier |
| `session_id` | string | Session this event belongs to |
| `module_id` | string | Module this event belongs to |
| `teacher_id` | string | Assigned teacher |
| `group_ids` | array[string] | Groups attending |
| `timeslot_id` | string | Assigned timeslot |
| `room_id` | string | Assigned room |
| `weeks` | array[int] | Weeks when event runs |
| `duration_min` | integer | Event duration in minutes |
| `duration_hours` | number | Event duration in hours (e.g., 2.0) |
| `module_hours_per_week` | number | Module's weekly hour allocation (from input) |
| `demand` | integer | Total students (sum of group sizes) |
| `min_room_capacity` | integer | From module definition |
| `required_capacity` | integer | max(demand, min_room_capacity) |
| `room_capacity` | integer | Actual room capacity |

### 5.4 Output Example

```json
{
  "meta": {
    "week_name": "T06",
    "weeks_total": 16,
    "strategy": "dfs",
    "use_mrv": true,
    "status": "success",
    "events_total": 5,
    "events_scheduled": 5
  },
  "assignments": [
    {
      "event_id": "CP_CM_MATH1",
      "session_id": "CP-1-S1",
      "module_id": "MATH1",
      "teacher_id": "T_MATH",
      "group_ids": ["CP_G1", "CP_G2"],
      "timeslot_id": "Tue_08-10",
      "room_id": "R2",
      "weeks": [1, 3, 5, 7, 10, 16],
      "duration_min": 120,
      "duration_hours": 2.0,
      "module_hours_per_week": 4.0,
      "demand": 55,
      "min_room_capacity": 60,
      "required_capacity": 60,
      "room_capacity": 80
    },
    {
      "event_id": "GI_CM_NET1",
      "session_id": "GI-S1",
      "module_id": "NET1",
      "teacher_id": "T_NET",
      "group_ids": ["GI_G1"],
      "timeslot_id": "Tue_08-10",
      "room_id": "R1",
      "weeks": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
      "duration_min": 120,
      "duration_hours": 2.0,
      "module_hours_per_week": 2.0,
      "demand": 34,
      "min_room_capacity": 30,
      "required_capacity": 34,
      "room_capacity": 35
    }
  ]
}
```

---

## 6. Visual Export

### 6.1 Export Modes

| Mode | Command | Description |
|------|---------|-------------|
| Single HTML | `python timetable_export.py output.json` | One file, all events |
| By Session | `python timetable_export.py output.json --by-session` | Separate file per session + index |
| Weekly | `python timetable_export.py output.json --weekly` | Separate file per week |

### 6.2 Filtering Options

```bash
# Filter by session
python timetable_export.py output.json -s "CP-1-S1"

# Filter by week
python timetable_export.py output.json -w 5

# Filter by group
python timetable_export.py output.json -g "CP_G1"

# Filter by teacher
python timetable_export.py output.json -t "T_MATH"

# Combine filters
python timetable_export.py output.json -s "CP-1-S1" -w 5
```

### 6.3 Output Formats

| Format | Flag | Requirement |
|--------|------|-------------|
| HTML | `-f html` (default) | None |
| PDF | `-f pdf` | `pip install weasyprint` or `pdfkit` |
| PNG | `-f png` | `pip install playwright` or `selenium` |
| All | `-f all` | All above |

### 6.4 Session-Based Export Structure

```
timetable_visual_sessions/
├── index.html              ← Navigation page with links to all sessions
├── session_CP-1-S1.html    ← Timetable for CP-1-S1 only
├── session_GI-S1.html      ← Timetable for GI-S1 only
└── all_sessions.html       ← Combined view with all sessions
```

---

## 7. Usage Examples

### 7.1 Running the Agent

```bash
# Edit timetable_agent.py to specify input file, then run:
python timetable_agent.py

# Output: timetable_output.json
```

### 7.2 Generating Visual Timetables

```bash
# Basic HTML export
python timetable_export.py timetable_output.json -o my_timetable

# Session-based export (recommended for multi-session)
python timetable_export.py timetable_output.json -o schedule --by-session

# Weekly breakdown
python timetable_export.py timetable_output.json -o schedule --weekly

# Export specific session
python timetable_export.py timetable_output.json -o cp_schedule -s "CP-1-S1"

# Export to PDF (requires weasyprint)
python timetable_export.py timetable_output.json -o schedule -f pdf
```

### 7.3 Common Scenarios

#### Scenario 1: Two events, same slot, disjoint weeks ✅
```json
{
  "events": [
    { "id": "E1", "weeks": { "mode": "ranges", "values": ["1-8"] }, ... },
    { "id": "E2", "weeks": { "mode": "ranges", "values": ["9-16"] }, ... }
  ]
}
```
→ Both can use same timeslot and room (no conflict)

#### Scenario 2: Lecture for all groups
```json
{
  "events": [
    {
      "id": "CM_MATH",
      "audience": { "type": "all_groups" },
      "teacher_id": "T_MATH",
      "duration_min": 120
    }
  ]
}
```
→ Agent ensures room capacity ≥ sum of all group sizes

#### Scenario 3: Tutorials for specific groups
```json
{
  "events": [
    {
      "id": "TD_MATH_G1",
      "audience": { "type": "groups", "group_ids": ["G1"] },
      ...
    },
    {
      "id": "TD_MATH_G2",
      "audience": { "type": "groups", "group_ids": ["G2"] },
      ...
    }
  ]
}
```
→ Can run in parallel if same teacher is not assigned to both

---

## Appendix A: Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `weeks_total must be > 0` | Invalid config | Set `weeks_total` to positive integer |
| `Week X out of bounds` | Week number exceeds weeks_total | Fix weeks values |
| `Unknown weeks.mode` | Invalid mode in weeks object | Use `"all"`, `"list"`, or `"ranges"` |
| `Unknown audience.type` | Invalid audience type | Use `"all_groups"` or `"groups"` |
| `No feasible schedule found` | Hard constraints cannot be satisfied | Review constraints, add more timeslots/rooms |

---

## Appendix B: File Reference

| File | Purpose |
|------|---------|
| `timetable_agent.py` | Main agent with search algorithms and constraints |
| `timetable_io.py` | JSON input parsing and output generation |
| `timetable_export.py` | Visual export (HTML, PDF, PNG) |
| `problem_solving_agent.py` | Base Problem class for search |
| `search_graph.py` | Optional: search tree visualization |

---

*End of Documentation*

