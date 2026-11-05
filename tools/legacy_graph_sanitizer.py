#!/usr/bin/env python3
"""JANUS historical graph -> inert label-stripped structural projection.

Derived from NAS first-generation Shrine/Memory Fusion graph *formats*.
This module is not a production memory importer or a de-identification guarantee.
No network, database access, model load, process spawn, or runtime mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_NODES = 25000
MAX_EDGES = 100000
NODE_KINDS = frozenset({
    "accepted", "json", "route", "old_shrine_html", "semantic_event",
    "concept", "essence", "doctrine", "bias", "core", "mirror",
    "memory", "default", "root", "hypothesis", "artifact", "event",
})
EDGE_KINDS = frozenset({
    "related", "references", "hypothesized", "observed",
    "derived", "semantic", "member", "link", "source", "target",
})

def _id(value: Any) -> str | None:
    if type(value) not in (str, int):
        return None
    result = str(value)
    if not result or len(result) > 512:
        return None
    return result

def _kind(raw: dict, *, edge: bool) -> str:
    value = raw.get("kind") or raw.get("type") or raw.get("relation")
    allowed = EDGE_KINDS if edge else NODE_KINDS
    if type(value) is not str:
        return "other"
    clean = value.strip().casefold()
    return clean if clean in allowed else "other"

def project(graph: dict, source_sha256: str) -> dict:
    """Produce a *non-authoritative* graph with numeric IDs and no private fields.

    A node key in a nodes map counts as an explicit identity. Does not invent
    nodes, add artificial CORE links, retain descriptions or chatHistory,
    infer edges, execute callbacks, or include private input fields.
    """
    if not isinstance(graph, dict):
        raise ValueError("LEGACY_GRAPH_MUST_BE_OBJECT")
    if not isinstance(source_sha256, str) or len(source_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in source_sha256):
        raise ValueError("LEGACY_SOURCE_SHA_INVALID")
    node_input = graph.get("nodes", [])
    if isinstance(node_input, dict):
        iterable = ((name, v) for name, v in node_input.items())
    elif isinstance(node_input, list):
        iterable = ((None, v) for v in node_input)
    else:
        raise ValueError("LEGACY_NODES_INVALID")
    if len(node_input) > MAX_NODES:
        raise ValueError("LEGACY_NODES_LIMIT")
    nodes = []
    ids: dict[str, int] = {}
    ignored_nodes = 0
    for alias, raw in iterable:
        if not isinstance(raw, dict):
            ignored_nodes += 1
            continue
        data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
        name = _id(raw.get("id")) or _id(data.get("id")) or _id(alias)
        if name is None:
            ignored_nodes += 1
            continue
        if name in ids:
            raise ValueError("LEGACY_DUPLICATE_NODE_ID")
        idx = len(nodes)
        ids[name] = idx
        nodes.append({"n": idx, "kind": _kind(raw, edge=False)})
    # Legacy formats: list links/edges, named "a->b" link map, or Prism adj.
    raw_edges = graph.get("links", graph.get("edges"))
    pairs: list[tuple[Any, Any, dict]] = []
    if raw_edges is None:
        adj = graph.get("adj", {})
        if not isinstance(adj, dict):
            raise ValueError("LEGACY_ADJ_INVALID")
        for src, neighbors in adj.items():
            if not isinstance(neighbors, dict):
                raise ValueError("LEGACY_ADJ_ROW_INVALID")
            if len(pairs) + len(neighbors) > MAX_EDGES:
                raise ValueError("LEGACY_EDGES_LIMIT")
            pairs.extend((src, dst, {}) for dst in neighbors)
    elif isinstance(raw_edges, list):
        if len(raw_edges) > MAX_EDGES:
            raise ValueError("LEGACY_EDGES_LIMIT")
        for e in raw_edges:
            if not isinstance(e, dict):
                continue
            pairs.append((
                e.get("source", e.get("src")),
                e.get("target", e.get("dst")),
                e,
            ))
    elif isinstance(raw_edges, dict):
        if len(raw_edges) > MAX_EDGES:
            raise ValueError("LEGACY_EDGES_LIMIT")
        for key, val in raw_edges.items():
            if type(key) is not str or "->" not in key:
                continue
            src, dst = key.split("->", 1)
            pairs.append((src, dst, val if isinstance(val, dict) else {}))
    else:
        raise ValueError("LEGACY_LINKS_INVALID")
    kept: set[tuple[int, int, str]] = set()
    missing = 0
    for src, dst, raw in pairs:
        s = _id(src)
        t = _id(dst)
        if s is None or t is None or s not in ids or t not in ids:
            missing += 1
            continue
        kept.add((ids[s], ids[t], _kind(raw, edge=True)))
    # No access to raw names/labels/description/history beyond this point.
    return {
        "schema": "janus.hrain.legacy_graph_sanitized_structure.v1",
        "source_sha256": source_sha256,
        "authority": "NON_AUTHORITATIVE_HISTORICAL_REFERENCE",
        "privacy_note": "LABELS_STRIPPED_NOT_FORMAL_ANONYMIZATION",
        "nodes": nodes,
        "edges": [list(e) for e in sorted(kept)],
        "stats": {
            "nodes_kept": len(nodes),
            "nodes_skipped_missing_id": ignored_nodes,
            "edges_kept": len(kept),
            "edges_skipped_dangling": missing,
            "edges_collapsed_exact_duplicate": len(pairs) - missing - len(kept),
        },
    }

def inspect_file(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("LEGACY_SOURCE_MUST_BE_REGULAR_FILE")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("LEGACY_SOURCE_TOO_LARGE")
    with path.open("rb") as handle:
        contents = handle.read(MAX_INPUT_BYTES + 1)
    if len(contents) > MAX_INPUT_BYTES:
        raise ValueError("LEGACY_SOURCE_TOO_LARGE")
    # UTF-8 BOM appears in historical sources; no fallback or OCR.
    obj = json.loads(contents.decode("utf-8-sig"))
    return project(obj, hashlib.sha256(contents).hexdigest())

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--acknowledge-topology-correlation-risk",
                        action="store_true")
    args = parser.parse_args()
    projection = inspect_file(args.source)
    if args.output is not None:
        if not args.acknowledge_topology_correlation_risk:
            raise ValueError("DERIVED_EXPORT_REQUIRES_PRIVACY_REVIEW_ACK")
        if args.output.is_symlink():
            raise ValueError("DERIVED_OUTPUT_SYMLINK_REFUSED")
        # Never overwrite existing graph or production state.
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(projection, output, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False)
            output.write("\n")
    print(json.dumps({"status": "READ_ONLY_LEGACY_GRAPH_PROJECTION",
                      "written": args.output is not None,
                      "source_sha256": projection["source_sha256"],
                      "stats": projection["stats"]}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
