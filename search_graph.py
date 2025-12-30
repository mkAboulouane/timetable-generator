"""Graph export for timetabling search.

This module records the DFS exploration steps into a graph and exports using Graphviz.
It’s kept independent of the solver so you can re-use it for BFS/UCS later.

Outputs:
- .dot   (always)
- .png/.svg (optional, if `graphviz` is installed)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SearchGraphRecorder:
    """Collects search steps as a directed graph.

    Nodes are states; edges represent expansions (state -> child).
    Also stores per-iteration metadata for labeling.
    """

    algorithm: str
    max_label_len: int = 140

    node_ids: Dict[Any, str] = field(default_factory=dict)
    node_labels: Dict[str, str] = field(default_factory=dict)
    node_attrs: Dict[str, Dict[str, str]] = field(default_factory=dict)
    edges: List[Tuple[str, str, Dict[str, str]]] = field(default_factory=list)

    iterations: List[Dict[str, Any]] = field(default_factory=list)

    _next_id: int = 0

    def _new_node_id(self) -> str:
        nid = f"n{self._next_id}"
        self._next_id += 1
        return nid

    def _safe_label(self, label: str) -> str:
        s = label.replace("\n", " ")
        if len(s) > self.max_label_len:
            s = s[: self.max_label_len - 3] + "..."
        return s

    def ensure_node(self, state: Any, *, label: str, attrs: Optional[Dict[str, str]] = None) -> str:
        if state in self.node_ids:
            nid = self.node_ids[state]
            # Merge/refresh attrs if provided
            if attrs:
                self.node_attrs.setdefault(nid, {}).update(attrs)
            return nid

        nid = self._new_node_id()
        self.node_ids[state] = nid
        self.node_labels[nid] = self._safe_label(label)
        if attrs:
            self.node_attrs[nid] = dict(attrs)
        else:
            self.node_attrs[nid] = {}
        return nid

    def add_edge(self, parent_state: Any, child_state: Any, *, parent_label: str, child_label: str,
                 attrs: Optional[Dict[str, str]] = None) -> None:
        pid = self.ensure_node(parent_state, label=parent_label)
        cid = self.ensure_node(child_state, label=child_label)
        self.edges.append((pid, cid, dict(attrs or {})))

    def add_iteration(self, *, iteration: int, current_state: Any, frontier_size: int, explored_size: int,
                      cost: float, actions_count: int, current_label: str) -> None:
        cid = self.ensure_node(current_state, label=current_label)
        self.iterations.append(
            {
                "iteration": iteration,
                "current_node": cid,
                "frontier_size": frontier_size,
                "explored_size": explored_size,
                "cost": cost,
                "actions": actions_count,
            }
        )

    def mark_goal(self, state: Any, *, label: str) -> None:
        nid = self.ensure_node(state, label=label)
        self.node_attrs.setdefault(nid, {}).update({"shape": "doubleoctagon", "color": "green", "penwidth": "2"})

    def mark_start(self, state: Any, *, label: str) -> None:
        nid = self.ensure_node(state, label=label)
        self.node_attrs.setdefault(nid, {}).update({"shape": "octagon", "color": "blue", "penwidth": "2"})

    def to_dot(self) -> str:
        # Graphviz DOT
        lines: List[str] = []
        lines.append("digraph Search {")
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, fontsize=10, fontname=Helvetica];")
        lines.append("  edge [fontsize=9, fontname=Helvetica];")

        # nodes
        for nid, label in self.node_labels.items():
            attrs = {"label": label, **(self.node_attrs.get(nid) or {})}
            attr_str = ", ".join(f"{k}=\"{str(v).replace('\\"', '\\\\"')}\"" for k, v in attrs.items())
            lines.append(f"  {nid} [{attr_str}];")

        # edges
        for (src, dst, attrs) in self.edges:
            if attrs:
                attr_str = ", ".join(f"{k}=\"{str(v).replace('\\"', '\\\\"')}\"" for k, v in attrs.items())
                lines.append(f"  {src} -> {dst} [{attr_str}];")
            else:
                lines.append(f"  {src} -> {dst};")

        # Optional iteration chain to visualize order (dotted)
        if self.iterations:
            prev = None
            for it in self.iterations:
                cur = it["current_node"]
                if prev is not None:
                    lines.append(f"  {prev} -> {cur} [style=dotted, color=gray, constraint=false];")
                prev = cur

        lines.append("}")
        return "\n".join(lines)


def write_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def try_render_graphviz(dot_path: str, out_path: str) -> bool:
    """Render a DOT file to an image using the `dot` executable if available."""
    import shutil
    import subprocess

    dot_exe = shutil.which("dot")
    if not dot_exe:
        return False

    # Determine format from extension
    ext = out_path.lower().rsplit(".", 1)[-1]
    fmt = ext
    cmd = [dot_exe, f"-T{fmt}", dot_path, "-o", out_path]
    subprocess.run(cmd, check=True)
    return True

