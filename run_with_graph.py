"""Run a timetabling search and export a graph of *all* steps.

Usage (from repo root):
  python run_with_graph.py test/01_baseline_success.json out.dot out.png

Notes:
- Always writes the DOT file.
- Writes PNG/SVG only if Graphviz is installed (`dot` on PATH).
"""

from __future__ import annotations

import sys
from pathlib import Path

from timetable_io import load_input_json
from timetable_agent import dfs_search
from search_graph import write_text, try_render_graphviz


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python run_with_graph.py <input_json> [out_dot] [out_image]")
        return 2

    input_path = argv[1]
    out_dot = argv[2] if len(argv) >= 3 else "search_graph.dot"
    out_img = argv[3] if len(argv) >= 4 else "search_graph.png"

    _, problem = load_input_json(input_path)

    # Record full graph; keep console quieter if you want
    result = dfs_search(problem, verbose=True, record_graph=True, algorithm_label="DFS")

    graph = getattr(result, "graph", None)
    if graph is None:
        print("No graph recorded. Did you call dfs_search(..., record_graph=True)?")
        return 1

    dot_text = graph.to_dot()
    write_text(out_dot, dot_text)
    print(f"Wrote DOT: {out_dot}")

    ok = False
    try:
        ok = try_render_graphviz(out_dot, out_img)
    except Exception as e:
        print(f"Graphviz render failed: {e}")
        ok = False

    if ok:
        print(f"Wrote image: {out_img}")
    else:
        print("Graphviz 'dot' not found (or render failed). Install Graphviz to get PNG/SVG.")
        print("You can still open the .dot with a DOT viewer.")

    # Helpful: print output location absolute
    print(f"DOT absolute: {Path(out_dot).resolve()}")
    print(f"IMG absolute: {Path(out_img).resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

