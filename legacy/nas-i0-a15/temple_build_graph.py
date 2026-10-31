#!/usr/bin/env python3
"""
A15 JANUS TEMPLE GRAPH builder
Observer-only JSON/JSONL corpus scanner for Janus/I0 run folders.

It builds janus_temple_graph.json for index.html.
It does not touch miner WIRE/HASH/SUBMIT or pool submit paths.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

VERSION = "A15_JANUS_TEMPLE_GRAPH_20260624"
SENTINEL = "A15_JANUS_TEMPLE_GRAPH_OBSERVER_ONLY_WIRE_HASH_SUBMIT_FROZEN"

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
ROUTE_WORDS = ("random", "bitrev", "linear", "zim_reverse", "zim_bandit", "knight", "dual_lock", "janus_dispatcher", "linear_proof", "randomized_traversal_mirror")
JANUS_WORDS = ("janus", "bitrev", "linear", "zim", "knight", "dual", "temple")
MIRROR_WORDS = ("randomized_traversal_mirror", "random_mirror", "mirror", "random/")


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:16]


def safe_id(prefix: str, value: Any) -> str:
    raw = str(value) if value is not None else "none"
    compact = re.sub(r"[^a-zA-Z0-9_.:/@+-]+", "_", raw.strip())[:80]
    return f"{prefix}:{compact}:{sha16(raw)[:8]}"


def first_not_none(*vals: Any) -> Any:
    for v in vals:
        if v is not None:
            return v
    return None


def dig(obj: Any, key_names: Iterable[str], depth: int = 0, max_depth: int = 7) -> Optional[Any]:
    if depth > max_depth:
        return None
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in key_names:
                return v
        for v in obj.values():
            r = dig(v, key_names, depth + 1, max_depth)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj[:200]:
            r = dig(v, key_names, depth + 1, max_depth)
            if r is not None:
                return r
    return None


def as_int(v: Any) -> Optional[int]:
    try:
        if v is None or v == "":
            return None
        return int(float(str(v)))
    except Exception:
        return None


def path_is_excluded(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & EXCLUDE_DIRS)


@dataclass
class Graph:
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    links: Dict[Tuple[str, str, str], Dict[str, Any]] = field(default_factory=dict)
    counters: Counter = field(default_factory=Counter)

    def add_node(self, node_id: str, label: str, kind: str, group: str = "default", **kwargs: Any) -> str:
        node = self.nodes.get(node_id)
        if node is None:
            node = {
                "id": node_id,
                "label": label,
                "kind": kind,
                "group": group,
                "score": 1.0,
                "data": {},
            }
            self.nodes[node_id] = node
        node["label"] = node.get("label") or label
        node["kind"] = node.get("kind") or kind
        node["group"] = node.get("group") or group
        node["score"] = float(node.get("score") or 0) + float(kwargs.pop("score_add", 0) or 0)
        for k, v in kwargs.items():
            if v is None:
                continue
            if k in ("z", "source", "priority"):
                node[k] = v
            else:
                node.setdefault("data", {})[k] = v
        return node_id

    def add_link(self, src: str, dst: str, kind: str = "link", weight: float = 1.0, **data: Any) -> None:
        if not src or not dst or src == dst:
            return
        key = (src, dst, kind)
        link = self.links.get(key)
        if link is None:
            link = {"source": src, "target": dst, "kind": kind, "weight": 0.0, "data": {}}
            self.links[key] = link
        link["weight"] = float(link.get("weight", 0.0)) + float(weight)
        link["data"].update({k: v for k, v in data.items() if v is not None})


def init_base_graph(g: Graph) -> None:
    g.add_node("JANUS_TEMPLE", "JANUS TEMPLE", "core", "core", score_add=10)
    g.add_node("CHAOS_MIRROR", "CHAOS / MIRROR CONTROL", "mirror", "mirror", score_add=5)
    g.add_node("WIRE_HASH_SUBMIT_FROZEN", "WIRE/HASH/SUBMIT FROZEN", "doctrine", "safety", score_add=5)
    g.add_node("OBSERVER_ONLY", "OBSERVER ONLY", "doctrine", "safety", score_add=5)
    g.add_link("JANUS_TEMPLE", "WIRE_HASH_SUBMIT_FROZEN", "doctrine", 3)
    g.add_link("JANUS_TEMPLE", "OBSERVER_ONLY", "doctrine", 3)

    for route in ["bitrev", "linear", "zim_reverse", "zim_bandit", "knight", "dual_lock", "janus_dispatcher", "linear_proof"]:
        rid = safe_id("route", route)
        g.add_node(rid, route, "route", "janus", score_add=2)
        g.add_link("JANUS_TEMPLE", rid, "temple_route", 2)
    for route in ["randomized_traversal_mirror", "random_mirror", "random"]:
        rid = safe_id("route", route)
        g.add_node(rid, route, "route", "mirror", score_add=2)
        g.add_link("CHAOS_MIRROR", rid, "control_route", 2)


def classify_group(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in MIRROR_WORDS):
        return "mirror"
    if any(w in t for w in JANUS_WORDS):
        return "janus"
    return "default"


def extract_route(text: str) -> Optional[str]:
    if not text:
        return None
    # Preserve full route if it looks like a route key.
    m = re.search(r"([a-zA-Z0-9_:-]+::[a-zA-Z0-9_/-]+/s?\d+/canonical)", text)
    if m:
        return m.group(1)
    m = re.search(r"(a14_navigator:[^\s,;]+)", text)
    if m:
        return m.group(1)
    m = re.search(r"\b(bitrev|linear|zim_reverse|zim_bandit|knight|random)/s?\d+\b", text)
    if m:
        return m.group(0)
    for w in ROUTE_WORDS:
        if w in text:
            return w
    return None


def accepted_from_filename(path: Path) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    name = path.name
    z = None
    nonce = None
    job = None
    mz = re.search(r"_z(\d+)_", name)
    if mz:
        z = int(mz.group(1))
    mn = re.search(r"nonce(0x[0-9a-fA-F]+)", name)
    if mn:
        nonce = mn.group(1)
    mj = re.search(r"job([a-zA-Z0-9]+)", name)
    if mj:
        job = mj.group(1)
    return z, nonce, job


def add_file_node(g: Graph, path: Path, root: Path, kind: str = "file") -> str:
    rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    fid = safe_id("file", rel)
    g.add_node(fid, path.name, kind, "archive", source=rel, score_add=0.2)
    g.add_link("JANUS_TEMPLE", fid, "corpus_file", 0.15)
    return fid


def add_route_event(g: Graph, route: str, event_kind: str, z: Optional[int], source_id: str, label_extra: str = "", group_hint: Optional[str] = None, weight: float = 1.0) -> str:
    group = group_hint or classify_group(route)
    route_id = safe_id("route", route)
    g.add_node(route_id, route, "route", group, score_add=0.3)
    if group == "mirror":
        g.add_link("CHAOS_MIRROR", route_id, "control_route", 0.6)
    else:
        g.add_link("JANUS_TEMPLE", route_id, "janus_route", 0.6)

    zlabel = f" z{z}" if z is not None else ""
    event_id = safe_id(event_kind, f"{route}|{z}|{source_id}|{label_extra}")
    g.add_node(event_id, f"{event_kind}{zlabel} {label_extra}".strip(), event_kind, group, z=z, score_add=(z or 1) / 8.0)
    g.add_link(route_id, event_id, event_kind, weight + ((z or 0) / 32.0))
    g.add_link(source_id, event_id, "source", 0.2)
    if z is not None and z >= 28:
        tail_id = safe_id("tail", f"z{z}")
        g.add_node(tail_id, f"RARE TAIL z{z}+", "tail", "tail", z=z, score_add=z / 4.0)
        g.add_link(event_id, tail_id, "rare_tail", max(1.0, z / 8.0))
    return event_id


def parse_json_file(g: Graph, path: Path, root: Path) -> None:
    try:
        if path.stat().st_size > 64 * 1024 * 1024:
            return
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
    except Exception:
        return

    fid = add_file_node(g, path, root, kind="json_file")
    text_hint = json.dumps(data, ensure_ascii=False)[:4000]

    # Proof/accepted file or proof-like object.
    filename_z, filename_nonce, filename_job = accepted_from_filename(path)
    z = first_not_none(as_int(dig(data, {"z", "best_z", "local_z", "zbits"})), filename_z)
    accepted = dig(data, {"accepted", "pool_pass"})
    group = first_not_none(dig(data, {"group", "lane_group", "strategy_group"}), None)
    route = first_not_none(
        dig(data, {"route", "lane", "strategy", "path", "choice", "best"}),
        extract_route(text_hint),
        path.parent.name if "proof" in path.parent.name.lower() else None,
    )
    job = first_not_none(dig(data, {"job", "job_id", "jobid"}), filename_job)
    nonce = first_not_none(dig(data, {"nonce", "nonce_submit", "nonce_int"}), filename_nonce)

    if "accepted" in path.name.lower() or accepted is True or (z is not None and "proof" in str(path).lower()):
        route_text = str(route or group or "accepted_unknown")
        group_hint = classify_group(str(group or route_text))
        ev = add_route_event(g, route_text, "accepted", z, fid, group_hint=group_hint, weight=2.5)
        if job:
            jid = safe_id("job", job)
            g.add_node(jid, f"job {job}", "job", "job", score_add=0.4)
            g.add_link(jid, ev, "accepted_job", 0.6)
        if nonce:
            nid = safe_id("nonce", nonce)
            g.add_node(nid, f"nonce {nonce}", "nonce", "proof", score_add=0.25)
            g.add_link(nid, ev, "accepted_nonce", 0.4)
        g.counters["accepted_json"] += 1
        if group_hint == "mirror":
            g.counters["accepted_mirror"] += 1
        elif group_hint == "janus":
            g.counters["accepted_janus"] += 1

    # Dashboard/session metrics.
    for key in ["accepted", "acc", "rejected", "rej", "best_z", "hps", "hps_ewma", "janus_z32/MH", "mirror_z32/MH", "janus_z32_per_mh", "mirror_z32_per_mh"]:
        val = dig(data, {key.lower()})
        if val is not None:
            mid = safe_id("metric", key)
            g.add_node(mid, key, "metric", "metric", value=str(val), score_add=0.1)
            g.add_link(fid, mid, "metric", 0.2)

    # If file names are familiar, create semantic nodes.
    lname = path.name.lower()
    if "glyph" in lname:
        g.add_node(fid, path.name, "glyph_file", "glyph", score_add=1)
    if "registry" in lname or "memory" in lname or "corpus" in lname:
        g.add_node(fid, path.name, "memory_file", "archive", score_add=1)
    if "dashboard" in lname or "summary" in lname:
        g.add_node(fid, path.name, "dashboard_file", "metric", score_add=1)


def parse_jsonl_file(g: Graph, path: Path, root: Path, max_lines: int) -> None:
    fid = add_file_node(g, path, root, kind="jsonl_file")
    n = 0
    accepted_seen = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if n >= max_lines:
                    break
                n += 1
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                z = as_int(first_not_none(data.get("z"), data.get("best_z"), data.get("local_z"), data.get("zbits")))
                accepted = bool(data.get("accepted") is True or data.get("pool_pass") is True or str(data.get("event", "")).lower() == "accepted")
                group = str(first_not_none(data.get("group"), data.get("lane_group"), data.get("strategy_group"), data.get("family"), ""))
                priority = str(first_not_none(data.get("priority"), data.get("kind"), data.get("event"), "event"))
                text = str(first_not_none(data.get("text"), data.get("message"), data.get("route"), data.get("lane"), data.get("strategy"), ""))
                route = str(first_not_none(data.get("route"), data.get("lane"), data.get("strategy"), extract_route(text), group or priority))
                group_hint = classify_group(" ".join([group, route, text, priority]))

                if accepted or z or "glyph" in path.name.lower() or "radar" in path.name.lower() or "gate" in path.name.lower():
                    kind = "accepted" if accepted else ("glyph" if "glyph" in path.name.lower() or priority else "event")
                    ev = add_route_event(g, route or priority, kind, z, fid, label_extra=priority[:32], group_hint=group_hint, weight=1.0)
                    if text:
                        tid = safe_id("text", text[:120])
                        g.add_node(tid, text[:80], "glyph_text", "glyph", priority=priority, score_add=0.15)
                        g.add_link(ev, tid, "glyph_text", 0.35)
                    if accepted:
                        accepted_seen += 1
                        if group_hint == "mirror":
                            g.counters["accepted_mirror"] += 1
                        elif group_hint == "janus":
                            g.counters["accepted_janus"] += 1
    except Exception:
        return
    g.counters["jsonl_lines"] += n
    g.counters["accepted_jsonl"] += accepted_seen
    g.nodes[fid]["data"].update({"lines_scanned": n, "accepted_seen": accepted_seen})


def parse_log_file(g: Graph, path: Path, root: Path, max_lines: int) -> None:
    fid = add_file_node(g, path, root, kind="log_file")
    n = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if n >= max_lines:
                    break
                n += 1
                if "[Rblganul" not in line and "a14" not in line and "ACCEPTED" not in line:
                    continue
                z = None
                mz = re.search(r"\bz=(\d+)\b|\bz(\d+)\b", line)
                if mz:
                    z = int(mz.group(1) or mz.group(2))
                route = extract_route(line) or ("randomized_traversal_mirror" if "randomized_traversal_mirror" in line else None)
                group_hint = classify_group(line)
                if "ACCEPTED" in line or "accepted z=" in line:
                    add_route_event(g, route or group_hint or "accepted_log", "accepted", z, fid, group_hint=group_hint, weight=1.4)
                elif "NAV_LOCK" in line:
                    add_route_event(g, route or "nav_lock", "nav_lock", z, fid, group_hint=group_hint, weight=0.8)
                elif "rollback" in line:
                    add_route_event(g, route or "rollback", "rollback", z, fid, group_hint=group_hint, weight=0.25)
                elif "rescue" in line:
                    add_route_event(g, route or "rescue", "rescue", z, fid, group_hint=group_hint, weight=0.35)
    except Exception:
        return
    g.nodes[fid]["data"].update({"lines_scanned": n})


def scan_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for base in [root, root / "janus_io_o1_runs", root.parent / "janus_io_o1_runs"]:
        if not base.exists() or not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or path_is_excluded(p):
                continue
            if p.suffix.lower() in {".json", ".jsonl", ".log"}:
                files.append(p)
    # Stable unique order, prefer recent small summaries later too.
    seen = set()
    uniq = []
    for p in files:
        rp = str(p.resolve())
        if rp in seen:
            continue
        seen.add(rp)
        uniq.append(p)
    uniq.sort(key=lambda x: (0 if "A14_2" in str(x) else 1, str(x)))
    return uniq


def build(root: Path, out_path: Path, max_jsonl_lines: int = 200000) -> Dict[str, Any]:
    g = Graph()
    init_base_graph(g)
    files = scan_files(root)
    g.counters["files_seen"] = len(files)

    for p in files:
        suffix = p.suffix.lower()
        if suffix == ".json":
            parse_json_file(g, p, root)
        elif suffix == ".jsonl":
            parse_jsonl_file(g, p, root, max_jsonl_lines)
        elif suffix == ".log":
            parse_log_file(g, p, root, min(max_jsonl_lines, 100000))

    # Add summary/meta nodes.
    for k, v in sorted(g.counters.items()):
        mid = safe_id("counter", k)
        g.add_node(mid, f"{k}: {v}", "counter", "metric", value=v, score_add=0.5)
        g.add_link("JANUS_TEMPLE", mid, "counter", 0.25)

    # Strengthen Janus/mirror poles based on counts.
    janus_count = g.counters.get("accepted_janus", 0)
    mirror_count = g.counters.get("accepted_mirror", 0)
    g.nodes["JANUS_TEMPLE"]["data"]["accepted_janus_detected"] = janus_count
    g.nodes["CHAOS_MIRROR"]["data"]["accepted_mirror_detected"] = mirror_count

    # If empty, include sample-like seed nodes.
    if len(g.nodes) < 12:
        sample_route = safe_id("route", "a14_navigator:janus_dispatcher::bitrev/s1/canonical")
        g.add_node(sample_route, "bitrev/s1", "route", "janus", score_add=3)
        g.add_link("JANUS_TEMPLE", sample_route, "janus_route", 2)
        mirror_route = safe_id("route", "randomized_traversal_mirror::random/s6/canonical")
        g.add_node(mirror_route, "random/s6 mirror", "route", "mirror", score_add=3)
        g.add_link("CHAOS_MIRROR", mirror_route, "control_route", 2)

    graph = {
        "meta": {
            "version": VERSION,
            "sentinel": SENTINEL,
            "source_root": str(root.resolve()),
            "output": str(out_path.resolve()),
            "policy": {
                "observer_only": True,
                "wire_hash_submit_frozen": True,
                "mirror_untouched": True,
                "scheduler_bias_export": False,
            },
            "counters": dict(g.counters),
        },
        "nodes": list(g.nodes.values()),
        "links": list(g.links.values()),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    return graph


def main() -> int:
    ap = argparse.ArgumentParser(description="Build A15 Janus Temple D3 graph from JSON/JSONL corpus")
    ap.add_argument("--root", default=".", help="I0 root or folder containing janus_io_o1_runs")
    ap.add_argument("--out", default="janus_temple_graph.json", help="Output graph JSON")
    ap.add_argument("--max-jsonl-lines", type=int, default=200000)
    args = ap.parse_args()
    root = Path(args.root).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    graph = build(root, out, args.max_jsonl_lines)
    print(f"[A15 TEMPLE] PASS graph={out}")
    print(f"[A15 TEMPLE] nodes={len(graph['nodes'])} links={len(graph['links'])}")
    print(f"[A15 TEMPLE] counters={graph['meta']['counters']}")
    print("[A15 TEMPLE] observer_only=True wire_hash_submit_frozen=True mirror_untouched=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
