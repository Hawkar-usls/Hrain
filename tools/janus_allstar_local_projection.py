#!/usr/bin/env python3
"""Owner-local, NON-authoritative All Star v89/Genesis/BFain read-only projection.

Adapted from audited All Star ecosystem_bridges.py by retaining ONLY typed
snapshot interpretation. Never imports legacy modules, fetches URLs, accesses
private devices or mutates v89 autonomous graph. Only writes an explicit local
derived receipt when --output is supplied.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

SCHEMA = "janus.allstar.private_local_crosssystem_projection.v1"
MAX_BYTES = {"hrain_graph_state.json": 8_000_000,
             "janus_world_state.json": 2_000_000,
             "janus_world_agents.json": 2_000_000,
             "bfain_snapshot.json": 2_000_000}
SOURCE_TYPES = {"hrain_graph_state.json": "HRAIN_PRIVATE_GRAPH",
                "janus_world_state.json": "GENESIS_SIMULATION_WORLD",
                "janus_world_agents.json": "GENESIS_SIMULATION_AGENTS",
                "bfain_snapshot.json": "BFAIN_SIMULATION_LOCAL_SNAPSHOT"}
FIELDS = ("level", "health", "mana", "gold", "record_count",
          "lethal_count", "base_level", "swarm_count")

def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()

def _checked_read(root: Path, filename: str):
    if filename not in MAX_BYTES:
        raise ValueError("UNLISTED_LOCAL_SOURCE_HOLD")
    base = (root / "raw_logs").resolve(strict=True)
    item = base / filename
    if item.is_symlink():
        raise ValueError("SOURCE_SYMLINK_HOLD")
    if not item.exists():
        return None
    if not item.is_file() or item.resolve(strict=True).parent != base:
        raise ValueError("SOURCE_OUTSIDE_APPROVED_RAW_LOGS")
    stat = item.stat()
    if stat.st_size < 1 or stat.st_size > MAX_BYTES[filename]:
        raise ValueError("SOURCE_BYTES_CAP_HOLD:" + filename)
    body = item.read_bytes()
    if len(body) != stat.st_size or len(body) > MAX_BYTES[filename]:
        raise ValueError("SOURCE_CHANGED_DURING_READ_HOLD")
    doc = json.loads(body)
    if not isinstance(doc, dict):
        raise ValueError("EXPECTED_OBJECT_HOLD:" + filename)
    return doc, _sha(body), len(body)

def _valid_count(container, expected: type) -> int:
    if not isinstance(container, expected):
        raise ValueError("LOCAL_SOURCE_SCHEMA_HOLD")
    if len(container) > 200_000:
        raise ValueError("LOCAL_COLLECTION_BOUND_HOLD")
    return len(container)

def _number(value):
    if type(value) not in (int, float):
        return None
    if not -1e12 <= value <= 1e12:
        return None
    return value

def build(root: Path):
    root = root.resolve(strict=True)
    if not (root / "raw_logs").is_dir():
        raise ValueError("RAW_LOGS_NOT_FOUND")
    nodes = [{"id": "local:allstar", "label": "All Star (private snapshot)",
              "kind": "SOURCE_ROOT", "readOnly": True}]
    edges = []
    sources = []
    def node(node_id, label, kind, parent="local:allstar", data=None):
        entry = {"id": node_id, "label": label, "kind": kind, "readOnly": True,
                 "scientificVerdict": "NOT_TOPA_ADJUDICATED",
                 "synthAuthority": False, "sourceClass": "LOCAL_OWNER_SNAPSHOT"}
        if data is not None:
            entry["snapshotMetadata"] = data
        nodes.append(entry)
        edges.append({"sourceId": parent, "targetId": node_id,
                      "relationClass": "LOCAL_DERIVED_STRUCTURE",
                      "scientificVerdict": "NOT_TOPA_ADJUDICATED"})
    for filename in MAX_BYTES:
        result = _checked_read(root, filename)
        typ = SOURCE_TYPES[filename]
        if result is None:
            sources.append({"sourceType": typ, "status": "MISSING_LOCAL_SOURCE"})
            continue
        doc, digest, size = result
        summary = {}
        if filename == "hrain_graph_state.json":
            summary = {"nodes": _valid_count(doc.get("nodes"), dict),
                       "edges": _valid_count(doc.get("edges"), dict)}
            if type(doc.get("tick")) is int:
                summary["tick"] = doc["tick"]
        elif filename == "janus_world_state.json":
            summary = {"fieldCount": len(doc)}
            for name in FIELDS:
                value = _number(doc.get(name))
                if value is not None:
                    summary[name] = value
            for k, cls in (("limbs", list), ("inventory", list),
                           ("base_upgrades", dict), ("faction_reputation", dict)):
                if k in doc:
                    summary[k + "Count"] = _valid_count(doc[k], cls)
        elif filename == "janus_world_agents.json":
            summary = {"populationCount": _valid_count(doc.get("population"), list),
                       "memoryEvents": _valid_count(doc.get("memory"), list)}
            if type(doc.get("tick")) is int:
                summary["tick"] = doc["tick"]
        elif filename == "bfain_snapshot.json":
            # ONLY manually recorded local snapshot, never 127.0.0.1:1139 API.
            if not isinstance(doc.get("state"), dict) or not isinstance(doc.get("progress"), dict):
                raise ValueError("BFAIN_OFFLINE_SNAPSHOT_SCHEMA_HOLD")
            summary = {"agentCount": _valid_count(doc["state"].get("agents"), list),
                       "snapshotRecorded": True}
            value = _number(doc["progress"].get("np_progress"))
            if value is not None:
                summary["gameProgressNotNPProof"] = value
        sources.append({"sourceType": typ, "status": "VERIFIED_LOCAL_BYTES",
                        "sha256": digest, "bytes": size, "metadata": summary})
        key = filename.removesuffix(".json")
        node("local:" + key, typ + " · LOCAL ONLY",
             "SIMULATION_SOURCE" if filename != "hrain_graph_state.json" else "GRAPH_SOURCE",
             data=summary)
    if len(nodes) > 12 or len(edges) > 11:
        raise ValueError("DERIVED_OUTPUT_BOUND_HOLD")
    return {"schema": SCHEMA, "status": "PRIVATE_READONLY_DERIVED_SNAPSHOT",
            "authority": {"readOnly": True, "writeAuthority": False,
                          "sourceMutationAllowed": False,
                          "semanticCandidatesAreEvidence": False,
                          "topaAutoAdjudication": False, "pEqualsNpClaim": False},
            "provenance": {"sourceRoot": "OWNER_LOCAL_ALLSTAR",
                           "noWebFetch": True, "noLegacyAutonomyImport": True,
                           "privateGraphNotCopied": True},
            "sources": sources, "nodes": nodes, "edges": edges}

def save_private(root: Path, destination: Path, value):
    # Output only under local All Star artifacts/audits. Never GitHub, source
    # raw_logs or source-tree files. No symlink escapes or overwrite by default.
    base = (root.resolve(strict=True) / "artifacts" / "audits").resolve(strict=True)
    path = destination.resolve(strict=False)
    if not path.is_relative_to(base) or path == base or path.suffix != ".json":
        raise ValueError("PRIVATE_LOCAL_OUTPUT_PATH_REQUIRED")
    if path.exists() or destination.is_symlink():
        raise FileExistsError("NO_OVERWRITE_EXISTING_LOCAL_RECEIPT")
    body = (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as file:
        file.write(body)
        file.flush()
        os.fsync(file.fileno())
    return _sha(body)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True,
                        help="Owner-authorized LOCAL All Star directory")
    parser.add_argument("--output", type=Path,
                        help="Optional local path under All Star/artifacts/audits")
    args = parser.parse_args()
    result = build(args.root)
    if args.output:
        sha = save_private(args.root, args.output, result)
        print(json.dumps({"status": result["status"], "receiptSha256": sha,
                          "sourcesPresent": sum(s["status"] == "VERIFIED_LOCAL_BYTES"
                                                for s in result["sources"]),
                          "sourcesMissing": sum(s["status"] == "MISSING_LOCAL_SOURCE"
                                                for s in result["sources"]),
                          "nodeCount": len(result["nodes"]), "edgeCount": len(result["edges"])}))
    else:
        print(json.dumps({"status": result["status"], "sourceStatus": [
            {"sourceType": s["sourceType"], "status": s["status"]}
            for s in result["sources"]], "nodeCount": len(result["nodes"])}))

if __name__ == "__main__":
    main()
