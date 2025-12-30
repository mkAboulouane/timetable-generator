"""Compare DFS/BFS/UCS/A* on the same JSON input.

This is meant for *demonstration*.

- Runs all algorithms
- Writes one output JSON per algorithm (schedule)
- Optionally writes a search graph (DOT, and PNG/SVG if Graphviz installed)

Usage:
  python compare_algos.py test\07_algo_comparison_branching_success.json

Options:
  python compare_algos.py <input_json> --graphs

Output folder:
  compare_out/<case_name>/<algo>.*
"""

from __future__ import annotations

import argparse
from pathlib import Path

from timetable_io import load_input_json, export_output_json
from timetable_agent import (
    dfs_search,
    bfs_search,
    ucs_search,
    a_star_search,
    h_zero,
)

from search_graph import write_text, try_render_graphviz


def run_one(algo: str, problem):
    if algo == "dfs":
        return dfs_search(problem, verbose=False, record_graph=True, algorithm_label="DFS")
    if algo == "bfs":
        # (graphs not implemented for bfs/ucs/a* in this repo yet)
        return bfs_search(problem, verbose=False)
    if algo == "ucs":
        return ucs_search(problem, verbose=False)
    if algo in ("astar", "a*", "a_star"):
        return a_star_search(problem, h_zero, verbose=False)
    raise ValueError(algo)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("input_json")
    p.add_argument("--graphs", action="store_true", help="Export DFS search graph (DOT + image if possible)")
    args = p.parse_args()

    input_path = args.input_json
    config, problem = load_input_json(input_path)

    case_name = Path(input_path).stem
    out_dir = Path("compare_out") / case_name
    out_dir.mkdir(parents=True, exist_ok=True)

    algos = ["dfs", "bfs", "ucs", "a_star"]
    results = []

    for a in algos:
        # Reload a fresh problem each time (clean state)
        _, problem_i = load_input_json(input_path)

        res = run_one(a, problem_i)
        results.append(res)

        final_state = None if res.path is None else res.path[-1]
        status = "success" if final_state is not None else "failure"

        out_json = out_dir / f"{a}.output.json"
        export_output_json(
            str(out_json),
            config=config,
            problem=problem_i,
            final_state=final_state,
            status=status,
            strategy=a,
        )

        if args.graphs and a == "dfs":
            graph = getattr(res, "graph", None)
            if graph is not None:
                dot_path = out_dir / "dfs.search.dot"
                img_path = out_dir / "dfs.search.png"
                write_text(str(dot_path), graph.to_dot())
                try_render_graphviz(str(dot_path), str(img_path))

    # Print summary
    print("\n=== Comparison summary ===")
    for r in results:
        ok = "OK" if r.path is not None else "FAIL"
        print(
            f"{r.algorithm:>4} | {ok:>4} | iterations={r.iterations:>6} | explored={r.nodes_explored:>6} | "
            f"max_frontier={r.max_frontier_size:>6} | time={r.elapsed_time:.4f}s | cost={r.final_cost}"
        )

    print(f"\nWrote outputs under: {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

