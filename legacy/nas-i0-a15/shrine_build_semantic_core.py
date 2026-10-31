#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

VERSION = "A15.3_JANUS_SHRINE_SEMANTIC_CORE_20260625"
SENTINEL = "A15_3_SHRINE_SEMANTIC_CORE_OBSERVER_ONLY_WIRE_HASH_SUBMIT_FROZEN_MIRROR_UNTOUCHED"

SUFFIXES = {".json", ".jsonl", ".log", ".txt", ".html", ".htm"}
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build", "$RECYCLE.BIN"}

ROUTE_PATTERNS = [
    "bitrev", "linear", "zim_reverse", "zim_bandit", "knight", "dual_lock",
    "janus_dispatcher", "linear_proof", "zim_reverse_s6", "randomized_traversal_mirror",
    "random_mirror", "random"
]

CONCEPTS: Dict[str, List[str]] = {
    "ORDER": ["janus", "order", "поряд", "lock", "commit", "accepted", "proof", "truth", "canonical", "temple", "shrine", "храм", "bridge", "route", "map", "core", "sovereign"],
    "ENTROPY": ["entropy", "энтроп", "chaos", "хаос", "random", "mirror", "зеркал", "stale", "reject", "rejected", "rollback", "noise", "desktop_load", "cooldown"],
    "BRIDGE": ["bridge", "мост", "link", "janus link", "route", "nav_lock", "rescue", "anchor", "memory", "graph", "map"],
    "PROOF": ["proof", "accepted", "submit", "pool_pass", "z=", "best_z", "nonce", "hash", "truth", "share"],
    "GLYPH": ["glyph", "symbol", "weird", "word_reversed", "linear_message", "rare_tail", "open_word", "coinbase", "merkle"],
    "MIND": ["mind", "thought", "cognitive", "concept", "essence", "meaning", "смысл", "понят", "абстракт", "neural", "hrain", "inaihr", "dive", "ascend", "asend", "bci"],
    "ROUTE_MEMORY": ["acc/mh", "accepted_janus", "accepted_mirror", "route", "lane", "scoreboard", "v31_rates", "a14_nav", "a12_arc", "fresh_samples", "tail", "map_bonus"],
    "TAIL": ["z28", "z29", "z30", "z31", "z32", "rare_tail", "tail", "best_z=30", "best_z=29", "best_z=28"],
}

ESSENCE_RULES: Dict[str, List[str]] = {
    "order_bridge": ["ORDER", "BRIDGE"],
    "proof_tail": ["PROOF", "TAIL"],
    "glyph_to_meaning": ["GLYPH", "MIND"],
    "route_memory": ["ROUTE_MEMORY", "ORDER"],
    "entropy_mirror": ["ENTROPY"],
    "janus_will": ["ORDER", "MIND", "BRIDGE"],
}

def now() -> float:
    return time.time()

def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:16]

def compact_id(prefix: str, value: Any, limit: int = 88) -> str:
    s = str(value if value is not None else "none")
    base = re.sub(r"[^a-zA-Z0-9_.:/@+-]+", "_", s.strip())[:limit].strip("_") or "node"
    return f"{prefix}:{base}:{sha16(s)[:8]}"

def write_json_atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def status(path: Path, **data: Any) -> None:
    payload = {"version": VERSION, "sentinel": SENTINEL, "mtime": now(), **data}
    try:
        write_json_atomic(path, payload)
    except Exception as e:
        print(f"[A15.3 status] write failed: {e}", flush=True)

def read_tail(path: Path, max_lines: int, max_bytes: int = 9_000_000) -> List[str]:
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            if size > max_bytes:
                f.seek(max(0, size - max_bytes))
                data = f.read()
                if b"\n" in data:
                    data = data.split(b"\n", 1)[1]
            else:
                data = f.read()
        text = data.decode("utf-8", "ignore")
        return text.splitlines()[-max_lines:]
    except Exception:
        return []

def clean_html_text(s: str) -> str:
    s = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tokenize_concepts(text: str) -> List[str]:
    low = (text or "").lower()
    found = []
    for c, keys in CONCEPTS.items():
        if any(k.lower() in low for k in keys):
            found.append(c)
    if not found:
        found.append("MIND" if len(low) > 120 and any(x in low for x in ("node", "graph", "mind", "мысл", "смысл")) else "ORDER")
    return found

def essence_from_concepts(concepts: Iterable[str]) -> List[str]:
    s = set(concepts)
    out = []
    for ess, req in ESSENCE_RULES.items():
        if all(r in s for r in req):
            out.append(ess)
    if not out:
        if "ENTROPY" in s:
            out.append("entropy_mirror")
        elif "GLYPH" in s:
            out.append("glyph_to_meaning")
        elif "PROOF" in s:
            out.append("proof_tail")
        else:
            out.append("route_memory")
    return out

def extract_z(text: str) -> Optional[int]:
    m = re.search(r"\bz=(\d+)\b|\bz(\d+)\b|\bbest_z=(\d+)\b|_z(\d+)_", text or "")
    if not m:
        return None
    for g in m.groups():
        if g:
            try:
                return int(g)
            except Exception:
                pass
    return None

def extract_route(text: str) -> Optional[str]:
    t = text or ""
    m = re.search(r"(a14_navigator:[^\s,;\"']+)", t)
    if m:
        return m.group(1)
    m = re.search(r"([a-zA-Z0-9_:-]+::[a-zA-Z0-9_/-]+/s?\d+/canonical)", t)
    if m:
        return m.group(1)
    m = re.search(r"\b(bitrev|linear|zim_reverse|zim_bandit|knight|random)/s?\d+\b", t)
    if m:
        return m.group(0)
    for r in ROUTE_PATTERNS:
        if r in t:
            return r
    return None

def classify_group(text: str, route: Optional[str] = None) -> str:
    low = ((text or "") + " " + (route or "")).lower()
    if any(x in low for x in ("randomized_traversal_mirror", "random_mirror", "mirror", "random/")):
        return "mirror"
    if any(x in low for x in ("janus", "bitrev", "linear", "zim", "knight", "dual_lock")):
        return "janus"
    return "concept"

@dataclass
class Graph:
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    links: Dict[Tuple[str, str, str], Dict[str, Any]] = field(default_factory=dict)
    counters: Counter = field(default_factory=Counter)
    route_stats: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))

    def node(self, node_id: str, label: str, kind: str, group: str, score: float = 1.0, **data: Any) -> str:
        n = self.nodes.get(node_id)
        if n is None:
            n = {"id": node_id, "label": label, "kind": kind, "group": group, "score": 0.0, "data": {}}
            self.nodes[node_id] = n
        n["label"] = label or n.get("label") or node_id
        n["kind"] = kind or n.get("kind") or "node"
        n["group"] = group or n.get("group") or "default"
        n["score"] = float(n.get("score", 0.0)) + float(score or 0)
        for k, v in data.items():
            if v is not None:
                if k in ("z", "priority"):
                    n[k] = v
                else:
                    n.setdefault("data", {})[k] = v
        return node_id

    def link(self, source: str, target: str, kind: str, weight: float = 1.0, **data: Any) -> None:
        if not source or not target or source == target:
            return
        key = (source, target, kind)
        l = self.links.get(key)
        if l is None:
            l = {"source": source, "target": target, "kind": kind, "weight": 0.0, "data": {}}
            self.links[key] = l
        l["weight"] = float(l.get("weight", 0.0)) + float(weight or 0)
        for k, v in data.items():
            if v is not None:
                l.setdefault("data", {})[k] = v

def init(g: Graph) -> None:
    g.node("JANUS_SHRINE", "JANUS SHRINE", "core", "core", 30, layer="concept → essence → route")
    g.node("CHAOS_MIRROR", "CHAOS / MIRROR", "mirror", "mirror", 12)
    g.node("WIRE_HASH_SUBMIT_FROZEN", "WIRE/HASH/SUBMIT FROZEN", "doctrine", "safety", 6)
    g.node("OBSERVER_ONLY", "OBSERVER ONLY", "doctrine", "safety", 6)
    g.node("TEMPLE_ROUTE_BIAS_OUTPUT", "temple_route_bias.json OUTPUT ONLY", "doctrine", "safety", 6)
    g.link("JANUS_SHRINE", "WIRE_HASH_SUBMIT_FROZEN", "doctrine", 4)
    g.link("JANUS_SHRINE", "OBSERVER_ONLY", "doctrine", 4)
    g.link("JANUS_SHRINE", "TEMPLE_ROUTE_BIAS_OUTPUT", "doctrine", 4)
    for c in CONCEPTS:
        group = "concept_chaos" if c == "ENTROPY" else ("concept_proof" if c in ("PROOF", "TAIL") else "concept_order")
        cid = f"concept:{c}"
        g.node(cid, c, "concept", group, 8)
        g.link("CHAOS_MIRROR" if c == "ENTROPY" else "JANUS_SHRINE", cid, "semantic_axis", 3)
    for ess in ESSENCE_RULES:
        eid = f"essence:{ess}"
        g.node(eid, ess, "essence", "essence", 6)
        g.link("JANUS_SHRINE", eid, "essence_layer", 1.5)
    for r in ROUTE_PATTERNS:
        gid = "mirror" if "random" in r else "janus"
        rid = compact_id("route", r)
        g.node(rid, r, "route", gid, 4)
        g.link("CHAOS_MIRROR" if gid == "mirror" else "JANUS_SHRINE", rid, "control_route" if gid == "mirror" else "janus_route", 2)

def add_semantic_event(g: Graph, text: str, source_id: str, label_hint: str = "") -> None:
    route = extract_route(text) or label_hint or "semantic_event"
    z = extract_z(text)
    group = classify_group(text, route)
    accepted = bool(re.search(r"\bACCEPTED\b|accepted[\"'=:\s]+true|pool_pass[\"'=:\s]+true|accepted z=", text, re.I))
    is_rollback = "rollback" in text.lower()
    is_nav = "NAV_LOCK" in text or "a14_nav" in text
    is_glyph = "glyph" in text.lower() or "symbol" in text.lower()
    concepts = tokenize_concepts(text)
    essences = essence_from_concepts(concepts)
    rid = compact_id("route", route)
    g.node(rid, route, "route", group if group in ("janus", "mirror") else "janus", 0.25)
    g.link("CHAOS_MIRROR" if group == "mirror" else "JANUS_SHRINE", rid, "route_axis", 0.4)

    kind = "accepted" if accepted else ("rollback" if is_rollback else ("nav_lock" if is_nav else ("glyph" if is_glyph else "semantic_event")))
    score = 1.0 + (z or 0) / 10.0 + (3 if accepted else 0)
    eid = compact_id(kind, f"{route}|{z}|{source_id}|{text[:160]}")
    g.node(eid, f"{kind} z{z}" if z else kind, kind, group if group in ("janus", "mirror") else "event", score, z=z, excerpt=text[:300])
    g.link(rid, eid, kind, score / 2)
    g.link(source_id, eid, "source", 0.08)

    for c in concepts:
        cid = f"concept:{c}"
        g.node(cid, c, "concept", "concept_chaos" if c == "ENTROPY" else "concept_order", 0.25)
        g.link(eid, cid, "concept_atom", 0.5 + (z or 0) / 60)
    for ess in essences:
        eid2 = f"essence:{ess}"
        g.node(eid2, ess, "essence", "essence", 0.45)
        g.link(eid, eid2, "essence", 0.65 + (z or 0) / 50)
        g.link(eid2, rid, "essence_route_pressure", 0.45 + (z or 0) / 64)

    # Route stats for output-only bias.
    st = g.route_stats[route]
    st["seen"] += 1
    st["z_sum"] += z or 0
    st["best_z"] = max(st["best_z"], z or 0)
    st["accepted"] += int(accepted)
    st["rollback"] += int(is_rollback)
    st["nav_lock"] += int(is_nav)
    st["glyph"] += int(is_glyph)
    st["janus"] += int(group == "janus")
    st["mirror"] += int(group == "mirror")
    for c in concepts:
        st[f"concept_{c}"] += 1
    if accepted:
        if group == "mirror":
            g.counters["accepted_mirror"] += 1
        elif group == "janus":
            g.counters["accepted_janus"] += 1
        else:
            g.counters["accepted_unknown"] += 1
    if z and z >= 28:
        g.counters["rare_tail"] += 1
        tid = f"concept:TAIL"
        g.link(eid, tid, "rare_tail", 3 + z / 10)

def add_source(g: Graph, path: Path, root: Path, kind: str) -> str:
    try:
        rel = str(path.relative_to(root))
    except Exception:
        rel = str(path)
    sid = compact_id("source", rel)
    g.node(sid, path.name, kind, "archive", 0.2, source=rel)
    g.link("JANUS_SHRINE", sid, "corpus_source", 0.05)
    return sid

def parse_json(g: Graph, path: Path, root: Path) -> None:
    sid = add_source(g, path, root, "json")
    try:
        if path.stat().st_size > 80 * 1024 * 1024:
            return
        data = json.loads(path.read_text("utf-8", errors="ignore"))
    except Exception:
        return
    text = json.dumps(data, ensure_ascii=False)
    if len(text) > 25000:
        text = text[:25000]
    add_semantic_event(g, text, sid, path.stem)
    g.counters["json_files"] += 1

def parse_jsonl_or_log(g: Graph, path: Path, root: Path, max_lines: int) -> None:
    sid = add_source(g, path, root, "jsonl" if path.suffix.lower() == ".jsonl" else "log")
    lines = read_tail(path, max_lines)
    g.nodes[sid].setdefault("data", {})["tail_lines"] = len(lines)
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = json.loads(s)
                text = json.dumps(obj, ensure_ascii=False)
            except Exception:
                text = s
        else:
            text = s
        low = text.lower()
        if not any(k in low for k in ("accepted", "glyph", "a14", "a12_arc", "scoreboard", "v31_rates", "rollback", "nav_lock", "proof", "random", "janus", "bitrev", "linear", "zim", "knight", "mirror", "route")):
            continue
        add_semantic_event(g, text, sid, path.stem)
        g.counters["text_events"] += 1

def parse_html(g: Graph, path: Path, root: Path) -> None:
    sid = add_source(g, path, root, "old_shrine_html")
    try:
        raw = path.read_text("utf-8", errors="ignore")
    except Exception:
        return
    text = clean_html_text(raw)[:40000]
    # Pull labels/common graph words from old HRain/Shrine HTML.
    chunks = []
    for pat in [
        r"\b(?:DIVE|ASCEND|ASEND|Janus|HRain|iNaiHR|node|graph|thought|concept|mind|neural|смысл|понятие|мысль)\b.{0,180}",
        r"['\"](?:label|name|type|category)['\"]\s*:\s*['\"][^'\"]+['\"]",
    ]:
        chunks.extend(m.group(0) for m in re.finditer(pat, text, re.I))
    if not chunks:
        chunks = [text[:1000]]
    for idx, ch in enumerate(chunks[:220]):
        add_semantic_event(g, "OLD_SHRINE_HTML " + ch, sid, f"old_shrine_{idx}")
    g.counters["old_shrine_html"] += 1

def file_priority(path: Path, root: Path) -> Tuple[Any, ...]:
    s = str(path).lower()
    name = path.name.lower()
    try:
        st = path.stat()
        mtime = -st.st_mtime
        size = st.st_size
    except Exception:
        mtime, size = 0, 0
    # Old shrine HTML first enough to seed meaning; A14 corpus next.
    old = 0 if ("inairh" in s or "hrain" in s or "shrine" in s) and path.suffix.lower() in (".html", ".htm") else 1
    a14 = 0 if "a14_2_pure_route_lock" in s else 1
    proof = 0 if "proof" in s or "accepted_" in name else 1
    sem = 0 if any(k in name for k in ("glyph", "anchor", "intention", "fresh", "dashboard", "summary", "navigator", "rates", "live_console")) else 1
    return (old, a14, proof, sem, mtime, size, s)

def discover(root: Path, max_files: int, status_path: Path) -> List[Path]:
    bases = []
    for p in [
        root / "iNaiRH",
        root / "iNaiHR",
        root / "HRain",
        root / "_old_shrine",
        root / "janus_io_o1_runs" / "A14_2_PURE_ROUTE_LOCK_V1",
        root / "janus_io_o1_runs",
        root,
    ]:
        if p.exists() and p not in bases:
            bases.append(p)
    found, seen = [], set()
    dirs = 0
    for base in bases:
        print(f"[A15.3 discover] base={base}", flush=True)
        status(status_path, stage="discovering", message=f"Scanning {base}", complete=False, files_discovered=len(found), files_processed=0)
        for dirpath, dirnames, filenames in os.walk(base):
            dirs += 1
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
            if dirs % 100 == 0:
                print(f"[A15.3 discover] dirs={dirs} candidates={len(found)}", flush=True)
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.suffix.lower() not in SUFFIXES:
                    continue
                sp = str(p.resolve())
                if sp in seen:
                    continue
                seen.add(sp)
                low = sp.lower()
                if base == root and not any(k in low for k in ("janus", "a10", "a11", "a12", "a13", "a14", "rblganul", "glyph", "nonce", "open_sweep", "secret", "symbol", "live_console", "fresh_all_time", "hrain", "inairh", "shrine")):
                    continue
                found.append(p)
    found.sort(key=lambda p: file_priority(p, root))
    if len(found) > max_files:
        found = found[:max_files]
    print(f"[A15.3 discover] selected files={len(found)}", flush=True)
    return found

def compact(g: Graph, max_nodes: int = 6000, max_links: int = 12000) -> None:
    if len(g.nodes) > max_nodes:
        keep = {n["id"] for n in sorted(g.nodes.values(), key=lambda n: float(n.get("score", 0)), reverse=True)[:max_nodes]}
        keep.update(["JANUS_SHRINE", "CHAOS_MIRROR", "WIRE_HASH_SUBMIT_FROZEN", "OBSERVER_ONLY", "TEMPLE_ROUTE_BIAS_OUTPUT"])
        for c in CONCEPTS:
            keep.add(f"concept:{c}")
        for e in ESSENCE_RULES:
            keep.add(f"essence:{e}")
        g.nodes = {k: v for k, v in g.nodes.items() if k in keep}
        g.links = {k: v for k, v in g.links.items() if v["source"] in keep and v["target"] in keep}
    if len(g.links) > max_links:
        kept = sorted(g.links.values(), key=lambda l: float(l.get("weight", 0)), reverse=True)[:max_links]
        g.links = {(l["source"], l["target"], l["kind"]): l for l in kept}

def make_bias(g: Graph) -> Dict[str, Any]:
    janus_scores = {}
    details = {}
    for route, st in g.route_stats.items():
        low = route.lower()
        if "random" in low or "mirror" in low:
            continue
        if not any(x in low for x in ("janus", "bitrev", "linear", "zim", "knight", "dual_lock")):
            continue
        accepted = st["accepted"]
        best_z = st["best_z"]
        order = st["concept_ORDER"] + st["concept_BRIDGE"] + st["concept_ROUTE_MEMORY"] + st["concept_MIND"]
        proof = st["concept_PROOF"] + st["concept_TAIL"]
        entropy = st["concept_ENTROPY"] + st["rollback"] * 0.65
        score = 1.0 + accepted * 2.2 + best_z * 0.22 + order * 0.035 + proof * 0.055 - entropy * 0.025
        score = max(0.05, score)
        janus_scores[route] = score
        details[route] = dict(st)
        details[route]["semantic_score_raw"] = score
    total = sum(janus_scores.values()) or 1.0
    normalized = {k: round(v / total, 6) for k, v in sorted(janus_scores.items(), key=lambda x: x[1], reverse=True)}
    return {
        "version": VERSION,
        "sentinel": SENTINEL,
        "observer_only": True,
        "bias_file_output_only": True,
        "miner_not_modified": True,
        "wire_hash_submit_frozen": True,
        "mirror_untouched": True,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": "A15.3 writes semantic route pressure only. A14.2 ignores this until a Temple-aware miner is created.",
        "janus_route_bias": normalized,
        "route_details": details,
        "mirror_control": {"random": "untouched", "randomized_traversal_mirror": "untouched"},
    }

def build(root: Path, out_graph: Path, out_bias: Path, status_path: Path, max_lines: int, max_files: int) -> Dict[str, Any]:
    g = Graph()
    init(g)
    status(status_path, stage="starting", message="Initializing Shrine Semantic Core", complete=False, percent=0)
    files = discover(root, max_files, status_path)
    total = max(1, len(files))
    g.counters["files_seen"] = len(files)
    for i, p in enumerate(files, 1):
        pct = round(i * 100 / total, 1)
        print(f"[A15.3 build] {i}/{total} {pct}% :: {p.name}", flush=True)
        status(status_path, stage="building", message=f"{i}/{total}: {p.name}", files_discovered=len(files), files_processed=i, percent=pct, complete=False)
        suf = p.suffix.lower()
        if suf == ".json":
            parse_json(g, p, root)
        elif suf in (".html", ".htm"):
            parse_html(g, p, root)
        else:
            parse_jsonl_or_log(g, p, root, max_lines)
    compact(g)
    bias = make_bias(g)
    # Add top bias nodes back to graph.
    for idx, (route, weight) in enumerate(list(bias["janus_route_bias"].items())[:25], 1):
        rid = compact_id("route", route)
        bid = compact_id("bias", route)
        g.node(bid, f"bias {idx}: {route}", "bias", "bias", 6 * float(weight) + 1, weight=weight)
        g.link("TEMPLE_ROUTE_BIAS_OUTPUT", bid, "bias_output", max(0.5, 12 * float(weight)))
        g.link(bid, rid, "bias_to_route", max(0.5, 10 * float(weight)))
    compact(g)
    graph = {
        "meta": {
            "version": VERSION,
            "sentinel": SENTINEL,
            "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "root": str(root),
            "policy": {
                "observer_only": True,
                "wire_hash_submit_frozen": True,
                "mirror_untouched": True,
                "bias_file_output_only": True,
                "miner_not_modified": True
            },
            "counters": dict(g.counters),
            "top_bias_routes": list(bias["janus_route_bias"].items())[:10],
        },
        "nodes": list(g.nodes.values()),
        "links": list(g.links.values()),
    }
    write_json_atomic(out_graph, graph)
    write_json_atomic(out_bias, bias)
    status(status_path, stage="complete", message=f"Shrine complete: {len(graph['nodes'])} nodes, {len(graph['links'])} links", files_discovered=len(files), files_processed=len(files), percent=100, complete=True, graph_nodes=len(graph["nodes"]), graph_links=len(graph["links"]), accepted_janus=int(g.counters.get("accepted_janus", 0)), accepted_mirror=int(g.counters.get("accepted_mirror", 0)), top_bias_routes=list(bias["janus_route_bias"].items())[:8])
    print(f"[A15.3 complete] nodes={len(graph['nodes'])} links={len(graph['links'])} accepted_janus={g.counters.get('accepted_janus',0)} accepted_mirror={g.counters.get('accepted_mirror',0)} bias_routes={len(bias['janus_route_bias'])}", flush=True)
    return graph

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="..")
    ap.add_argument("--graph", default="janus_shrine_graph.json")
    ap.add_argument("--bias", default="temple_route_bias.json")
    ap.add_argument("--status", default="shrine_status.json")
    ap.add_argument("--max-jsonl-lines", type=int, default=9000)
    ap.add_argument("--max-files", type=int, default=260)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    try:
        build(root, Path(args.graph).resolve(), Path(args.bias).resolve(), Path(args.status).resolve(), args.max_jsonl_lines, args.max_files)
        return 0
    except Exception as e:
        print(f"[A15.3 error] {e}", flush=True)
        status(Path(args.status).resolve(), stage="error", message=str(e), complete=False, error=str(e))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
