#!/usr/bin/env python3
"""Build a bounded TOPA semantic overlay over JANUS Meta Registry memory.

This module is an adapter, not a second semantic engine.  It converts the
read-only HRaiN registry projection into TOPA Spider v2 records, then validates
and bounds TOPA's document-to-document semantic edges before HRaiN may use them
for visualization or attention expansion.

Epistemic boundary:
  GRAPH_EDGE_IS_NOT_CAUSATION
  SEMANTIC_SIMILARITY_IS_NOT_MECHANISM
  ATTENTION_WEIGHT_IS_NOT_EVIDENCE_WEIGHT
  SEMANTIC_NEIGHBOR_IS_NOT_CLAIM_VERIFICATION
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

PROJECTION_SCHEMA = "janus.hrain.registry_graph_index.v1_0"
OVERLAY_SCHEMA = "janus.hrain.topa_semantic_overlay.v1"
REGISTRY_REPOSITORY = "Hawkar-usls/janus-meta-registry"
TOPA_REPOSITORY = "Hawkar-usls/TOPA"
DEFAULT_OVERLAY_URL = (
    "https://raw.githubusercontent.com/Hawkar-usls/Hrain/"
    "janus/hrain-semantic-state/assets/hrain-semantic-overlay.json"
)
_HASH40 = re.compile(r"^[0-9a-f]{40}$")
_HASH64 = re.compile(r"^[0-9a-f]{64}$")
MAX_REMOTE_BYTES = 8_000_000
DEFAULT_MIN_SIMILARITY = 0.22
DEFAULT_MAX_SEMANTIC_DEGREE = 8


class SemanticOverlayError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SemanticOverlayError(f"OBJECT_REQUIRED:{path}")
    return value


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise SemanticOverlayError(f"JSONL_OBJECT_REQUIRED:{path}")
            rows.append(value)
    return rows


def _write_json(path: str | Path, value: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(canonical_json(dict(row)) + "\n")


def validate_projection(projection: Mapping[str, Any]) -> None:
    if projection.get("schema") != PROJECTION_SCHEMA:
        raise SemanticOverlayError("PROJECTION_SCHEMA_MISMATCH")
    if projection.get("repository") != REGISTRY_REPOSITORY:
        raise SemanticOverlayError("PROJECTION_REPOSITORY_MISMATCH")
    if _HASH40.fullmatch(str(projection.get("sourceCommit") or "")) is None:
        raise SemanticOverlayError("PROJECTION_SOURCE_COMMIT_INVALID")
    nodes = projection.get("nodes")
    links = projection.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise SemanticOverlayError("PROJECTION_GRAPH_REQUIRED")
    policy = projection.get("mutationPolicy") or {}
    if not isinstance(policy, Mapping):
        raise SemanticOverlayError("PROJECTION_MUTATION_POLICY_REQUIRED")
    if policy.get("interfaceWriteAuthority") is not False or policy.get("interfaceDeleteAuthority") is not False:
        raise SemanticOverlayError("PROJECTION_MUST_BE_READ_ONLY")


def _object_nodes(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in projection.get("nodes") or []:
        if not isinstance(raw, Mapping):
            continue
        node = dict(raw)
        node_id = str(node.get("id") or "")
        if not node_id.startswith("obj:"):
            continue
        if node.get("readOnly") is not True or node.get("deleteAllowed") is not False:
            continue
        if not str(node.get("path") or ""):
            continue
        out.append(node)
    return sorted(out, key=lambda row: str(row.get("id")))


def _topa_doc_id(node_id: str) -> str:
    return f"doc:JANUS_META_REGISTRY:{node_id}"


def prepare_records(projection: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    validate_projection(projection)
    records: list[dict[str, Any]] = []
    mapping: dict[str, str] = {}
    for node in _object_nodes(projection):
        node_id = str(node["id"])
        doc_id = _topa_doc_id(node_id)
        mapping[doc_id] = node_id
        text_parts = [
            str(node.get("label") or ""),
            str(node.get("lineageKey") or ""),
            str(node.get("path") or ""),
            str(node.get("summary") or ""),
            str(node.get("status") or ""),
        ]
        records.append({
            "provider": "JANUS_META_REGISTRY",
            "archive_id": node_id,
            "title": str(node.get("label") or node_id),
            "text": " ".join(part for part in text_parts if part),
            "source_url": str(node.get("sourceUrl") or ""),
            "relation_tags": [],
            "record_sha256": str(node.get("sourceSha256") or ""),
            "review_state": "MEMORY_DATA_ONLY",
            "raw_metadata": {
                "lineageKey": node.get("lineageKey"),
                "path": node.get("path"),
                "status": node.get("status"),
                "surface": node.get("surface"),
            },
        })
    return records, mapping


def prepare(
    projection_path: str | Path,
    *,
    records_out: str | Path,
    map_out: str | Path,
    receipt_out: str | Path,
) -> dict[str, Any]:
    raw = Path(projection_path).read_bytes()
    projection = json.loads(raw.decode("utf-8"))
    if not isinstance(projection, dict):
        raise SemanticOverlayError("PROJECTION_OBJECT_REQUIRED")
    records, mapping = prepare_records(projection)
    _write_jsonl(records_out, records)
    map_body = {
        "schema": "janus.hrain.topa_document_map.v1",
        "sourceCommit": projection["sourceCommit"],
        "projectionSha256": sha256_bytes(raw),
        "documentToNode": mapping,
    }
    map_body["mapHash"] = canonical_hash(map_body)
    _write_json(map_out, map_body)
    receipt = {
        "schema": "janus.hrain.topa_semantic_prepare_receipt.v1",
        "status": "PASS",
        "sourceCommit": projection["sourceCommit"],
        "projectionSha256": sha256_bytes(raw),
        "objectCount": len(records),
        "documentCount": len(records),
        "documentMapHash": map_body["mapHash"],
        "registryMutationPerformed": False,
        "claimPromotionPerformed": False,
    }
    receipt["receiptHash"] = canonical_hash(receipt)
    _write_json(receipt_out, receipt)
    return receipt


def _validate_map(mapping: Mapping[str, Any], projection: Mapping[str, Any], projection_sha: str) -> dict[str, str]:
    body = dict(mapping)
    claimed = str(body.pop("mapHash", ""))
    if _HASH64.fullmatch(claimed) is None or canonical_hash(body) != claimed:
        raise SemanticOverlayError("DOCUMENT_MAP_HASH_INVALID")
    if mapping.get("schema") != "janus.hrain.topa_document_map.v1":
        raise SemanticOverlayError("DOCUMENT_MAP_SCHEMA_MISMATCH")
    if mapping.get("sourceCommit") != projection.get("sourceCommit"):
        raise SemanticOverlayError("DOCUMENT_MAP_SOURCE_COMMIT_MISMATCH")
    if mapping.get("projectionSha256") != projection_sha:
        raise SemanticOverlayError("DOCUMENT_MAP_PROJECTION_HASH_MISMATCH")
    table = mapping.get("documentToNode")
    if not isinstance(table, Mapping):
        raise SemanticOverlayError("DOCUMENT_MAP_TABLE_REQUIRED")
    return {str(k): str(v) for k, v in table.items()}


def _hierarchy_pairs(projection: Mapping[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for link in projection.get("links") or []:
        if not isinstance(link, Mapping):
            continue
        a, b = str(link.get("source") or ""), str(link.get("target") or "")
        if a and b:
            pairs.add(tuple(sorted((a, b))))
    return pairs


def finalize_overlay(
    projection: Mapping[str, Any],
    *,
    projection_sha256: str,
    document_map: Mapping[str, Any],
    topa_edges: Iterable[Mapping[str, Any]],
    topa_receipt: Mapping[str, Any],
    topa_head_sha: str,
    generated_at: str,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
    max_semantic_degree: int = DEFAULT_MAX_SEMANTIC_DEGREE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_projection(projection)
    if _HASH64.fullmatch(projection_sha256) is None:
        raise SemanticOverlayError("PROJECTION_SHA256_INVALID")
    if _HASH40.fullmatch(topa_head_sha) is None:
        raise SemanticOverlayError("TOPA_HEAD_SHA_INVALID")
    if topa_receipt.get("status") != "PASS":
        raise SemanticOverlayError("TOPA_RECEIPT_NOT_PASS")
    if max_semantic_degree < 1 or max_semantic_degree > 32:
        raise SemanticOverlayError("MAX_SEMANTIC_DEGREE_OUT_OF_RANGE")
    if not 0.0 < min_similarity < 1.0:
        raise SemanticOverlayError("MIN_SIMILARITY_OUT_OF_RANGE")

    table = _validate_map(document_map, projection, projection_sha256)
    object_nodes = {str(node["id"]): node for node in _object_nodes(projection)}
    object_ids = set(object_nodes)
    hierarchy = _hierarchy_pairs(projection)
    candidates: list[tuple[float, str, str, dict[str, Any]]] = []
    rejected = defaultdict(int)

    for raw in topa_edges:
        if not isinstance(raw, Mapping) or raw.get("relation") != "SEMANTIC_SIMILARITY":
            continue
        source = table.get(str(raw.get("source") or ""))
        target = table.get(str(raw.get("target") or ""))
        if not source or not target or source not in object_ids or target not in object_ids:
            rejected["non_object_or_unmapped"] += 1
            continue
        if source == target:
            rejected["self_loop"] += 1
            continue
        source_label = re.sub(r"\W+", "", str(object_nodes[source].get("label") or "").casefold(), flags=re.UNICODE)
        target_label = re.sub(r"\W+", "", str(object_nodes[target].get("label") or "").casefold(), flags=re.UNICODE)
        if source_label and source_label == target_label:
            rejected["same_normalized_label"] += 1
            continue
        pair = tuple(sorted((source, target)))
        if pair in hierarchy:
            rejected["hierarchy_duplicate"] += 1
            continue
        similarity = float(raw.get("similarity") or 0.0)
        if similarity < min_similarity:
            rejected["below_similarity_threshold"] += 1
            continue
        candidates.append((similarity, pair[0], pair[1], dict(raw)))

    degree: dict[str, int] = defaultdict(int)
    accepted: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for similarity, source, target, raw in sorted(candidates, key=lambda row: (-row[0], row[1], row[2])):
        pair = (source, target)
        if pair in seen:
            rejected["duplicate"] += 1
            continue
        if degree[source] >= max_semantic_degree or degree[target] >= max_semantic_degree:
            rejected["degree_cap"] += 1
            continue
        seen.add(pair)
        degree[source] += 1
        degree[target] += 1
        accepted.append({
            "source": source,
            "target": target,
            "relation": "TOPA_SEMANTIC_SIMILARITY",
            "similarity": round(similarity, 6),
            "confidence": round(float(raw.get("confidence") or 0.0), 6),
            "status": "SPECULATIVE_SEMANTIC_EDGE",
            "readOnly": True,
            "claimVerified": False,
            "evidenceWeight": 0,
            "epistemicNote": "SEMANTIC_SIMILARITY_IS_NOT_MECHANISM",
        })

    overlay: dict[str, Any] = {
        "schema": OVERLAY_SCHEMA,
        "status": "READY",
        "repository": "Hawkar-usls/Hrain",
        "sourceRepository": REGISTRY_REPOSITORY,
        "sourceProjectionSchema": projection.get("schema"),
        "sourceProjectionSha256": projection_sha256,
        "sourceCommit": projection.get("sourceCommit"),
        "topaRepository": TOPA_REPOSITORY,
        "topaHeadSha": topa_head_sha,
        "topaReceiptHash": canonical_hash(topa_receipt),
        "generatedAt": generated_at,
        "minimumSimilarity": min_similarity,
        "maxSemanticDegree": max_semantic_degree,
        "edgeCount": len(accepted),
        "nodeSemanticDegree": dict(sorted(degree.items())),
        "edges": accepted,
        "authority": {
            "readOnly": True,
            "registryWriteAuthority": False,
            "commandAuthority": False,
            "claimPromotionAuthority": False,
            "scientificEvidenceAuthority": False,
        },
        "laws": [
            "GRAPH_EDGE_IS_NOT_CAUSATION",
            "SEMANTIC_SIMILARITY_IS_NOT_MECHANISM",
            "ATTENTION_WEIGHT_IS_NOT_EVIDENCE_WEIGHT",
            "SEMANTIC_NEIGHBOR_IS_NOT_CLAIM_VERIFICATION",
            "IDENTICAL_LABEL_LINEAGE != SEMANTIC_CROSS_CONCEPT_EDGE",
            "TOPA_OVERLAY != META_REGISTRY_MUTATION",
            "STALE_OVERLAY = IGNORE_FAIL_CLOSED",
        ],
    }
    overlay["overlayHash"] = canonical_hash(overlay)
    receipt: dict[str, Any] = {
        "schema": "janus.hrain.topa_semantic_overlay_receipt.v1",
        "status": "PASS",
        "sourceCommit": projection.get("sourceCommit"),
        "sourceProjectionSha256": projection_sha256,
        "topaHeadSha": topa_head_sha,
        "topaReceiptHash": canonical_hash(topa_receipt),
        "candidateSemanticEdges": len(candidates),
        "acceptedSemanticEdges": len(accepted),
        "maximumObservedSemanticDegree": max(degree.values(), default=0),
        "maxSemanticDegree": max_semantic_degree,
        "rejected": dict(sorted(rejected.items())),
        "overlayHash": overlay["overlayHash"],
        "registryMutationPerformed": False,
        "claimPromotionPerformed": False,
    }
    receipt["receiptHash"] = canonical_hash(receipt)
    return overlay, receipt


def validate_overlay(overlay: Mapping[str, Any], projection: Mapping[str, Any]) -> None:
    validate_projection(projection)
    body = dict(overlay)
    claimed = str(body.pop("overlayHash", ""))
    if _HASH64.fullmatch(claimed) is None or canonical_hash(body) != claimed:
        raise SemanticOverlayError("OVERLAY_HASH_INVALID")
    if overlay.get("schema") != OVERLAY_SCHEMA or overlay.get("status") != "READY":
        raise SemanticOverlayError("OVERLAY_SCHEMA_OR_STATUS_INVALID")
    if overlay.get("sourceRepository") != REGISTRY_REPOSITORY:
        raise SemanticOverlayError("OVERLAY_SOURCE_REPOSITORY_MISMATCH")
    if overlay.get("sourceCommit") != projection.get("sourceCommit"):
        raise SemanticOverlayError("OVERLAY_SOURCE_COMMIT_MISMATCH")
    if _HASH40.fullmatch(str(overlay.get("topaHeadSha") or "")) is None:
        raise SemanticOverlayError("OVERLAY_TOPA_HEAD_INVALID")
    object_ids = {str(node["id"]) for node in _object_nodes(projection)}
    hierarchy = _hierarchy_pairs(projection)
    max_degree = int(overlay.get("maxSemanticDegree") or 0)
    degree: dict[str, int] = defaultdict(int)
    seen: set[tuple[str, str]] = set()
    edges = overlay.get("edges")
    if not isinstance(edges, list) or int(overlay.get("edgeCount") or 0) != len(edges):
        raise SemanticOverlayError("OVERLAY_EDGE_COUNT_MISMATCH")
    for edge in edges:
        if not isinstance(edge, Mapping):
            raise SemanticOverlayError("OVERLAY_EDGE_OBJECT_REQUIRED")
        a, b = str(edge.get("source") or ""), str(edge.get("target") or "")
        pair = tuple(sorted((a, b)))
        if a not in object_ids or b not in object_ids or a == b:
            raise SemanticOverlayError("OVERLAY_EDGE_ENDPOINT_INVALID")
        if pair in hierarchy or pair in seen:
            raise SemanticOverlayError("OVERLAY_EDGE_DUPLICATE_OR_HIERARCHY")
        if edge.get("relation") != "TOPA_SEMANTIC_SIMILARITY":
            raise SemanticOverlayError("OVERLAY_EDGE_RELATION_INVALID")
        if edge.get("readOnly") is not True or edge.get("claimVerified") is not False or edge.get("evidenceWeight") != 0:
            raise SemanticOverlayError("OVERLAY_EDGE_AUTHORITY_ESCALATION")
        if float(edge.get("similarity") or 0.0) < float(overlay.get("minimumSimilarity") or 0.0):
            raise SemanticOverlayError("OVERLAY_EDGE_BELOW_THRESHOLD")
        seen.add(pair)
        degree[a] += 1
        degree[b] += 1
    if any(value > max_degree for value in degree.values()):
        raise SemanticOverlayError("OVERLAY_DEGREE_CAP_VIOLATION")


def _remote_json(url: str, *, max_bytes: int = MAX_REMOTE_BYTES) -> tuple[dict[str, Any], str]:
    request = urllib.request.Request(url, headers={"User-Agent": "JANUS-HRAiN-TOPA-Semantic-Overlay/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise SemanticOverlayError("REMOTE_OVERLAY_TOO_LARGE")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise SemanticOverlayError("REMOTE_OVERLAY_OBJECT_REQUIRED")
    return value, sha256_bytes(raw)


def load_default_overlay(
    projection: Mapping[str, Any],
    *,
    overlay_file: str | Path | None = None,
    overlay_url: str = DEFAULT_OVERLAY_URL,
) -> tuple[dict[str, Any] | None, str | None, str]:
    """Best-effort optional enrichment; stale/malformed overlays are ignored fail-closed."""
    try:
        if overlay_file is not None:
            raw = Path(overlay_file).read_bytes()
            overlay = json.loads(raw.decode("utf-8"))
            if not isinstance(overlay, dict):
                raise SemanticOverlayError("OVERLAY_OBJECT_REQUIRED")
            digest = sha256_bytes(raw)
        else:
            overlay, digest = _remote_json(overlay_url)
        validate_overlay(overlay, projection)
        return overlay, digest, "VALIDATED"
    except Exception:
        return None, None, "UNAVAILABLE_OR_REJECTED"


def expand_selected_with_semantic_neighbors(
    selected: list[dict[str, Any]],
    projection: Mapping[str, Any],
    overlay: Mapping[str, Any] | None,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Expand real lexical anchors only. Never fills an empty query with semantic noise."""
    if not selected or overlay is None or len(selected) >= limit:
        return [dict(row) for row in selected[:limit]]
    validate_overlay(overlay, projection)
    nodes = {str(node.get("id")): dict(node) for node in _object_nodes(projection)}
    by_anchor: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for edge in overlay.get("edges") or []:
        a, b = str(edge["source"]), str(edge["target"])
        similarity = float(edge.get("similarity") or 0.0)
        by_anchor[a].append((similarity, b))
        by_anchor[b].append((similarity, a))
    for neighbors in by_anchor.values():
        neighbors.sort(key=lambda item: (-item[0], item[1]))

    out = [dict(row) for row in selected]
    seen_ids = {str(row.get("id") or "") for row in out}
    overlay_hash = str(overlay.get("overlayHash") or "")
    anchor_rows = list(out)
    candidates: list[tuple[float, int, str, str]] = []
    for anchor_rank, anchor in enumerate(anchor_rows, start=1):
        anchor_id = str(anchor.get("id") or "")
        for similarity, neighbor_id in by_anchor.get(anchor_id, []):
            if neighbor_id in seen_ids:
                continue
            candidates.append((similarity, anchor_rank, anchor_id, neighbor_id))
    candidates.sort(key=lambda row: (-row[0], row[1], row[3]))

    queued: set[str] = set()
    for similarity, anchor_rank, anchor_id, neighbor_id in candidates:
        if len(out) >= limit:
            break
        if neighbor_id in seen_ids or neighbor_id in queued:
            continue
        node = nodes.get(neighbor_id)
        if not node:
            continue
        anchor = anchor_rows[anchor_rank - 1]
        relative = max(0, min(100, int(round(float(anchor.get("relative_score_percent_of_top") or 0) * similarity))))
        out.append({
            "id": node.get("id"),
            "label": node.get("label"),
            "surface": node.get("surface"),
            "lineage_key": node.get("lineageKey"),
            "path": node.get("path"),
            "status": node.get("status"),
            "summary": node.get("summary"),
            "commit_sha": node.get("commitSha"),
            "source_sha256": node.get("sourceSha256"),
            "relevance_score": max(0, int(round(float(anchor.get("relevance_score") or 0) * similarity))),
            "relative_score_percent_of_top": relative,
            "attention_rank": len(out) + 1,
            "selection_reason": f"TOPA_SEMANTIC_NEIGHBOR:{anchor_id}",
            "matched_query_tokens": [],
            "matched_structural_query_tokens": [],
            "matched_focus_tokens": [],
            "matched_named_anchor_tokens": [],
            "matched_query_token_rarity": {},
            "query_coverage_count": 0,
            "semantic_anchor_id": anchor_id,
            "semantic_anchor_attention_rank": anchor_rank,
            "semantic_similarity": round(similarity, 6),
            "semantic_overlay_hash": overlay_hash,
            "semantic_overlay_source_commit": overlay.get("sourceCommit"),
            "semantic_relation": "TOPA_SEMANTIC_SIMILARITY",
            "semantic_edge_is_evidence": False,
            "content_trust": "MEMORY_DATA_NOT_CONTROL_SIGNAL",
            "claim_verified": False,
        })
        queued.add(neighbor_id)
        seen_ids.add(neighbor_id)
    for rank, row in enumerate(out, start=1):
        row["attention_rank"] = rank
    return out


def _self_test_projection() -> dict[str, Any]:
    nodes = [
        {"id": "registry:janus-meta-registry", "readOnly": True, "deleteAllowed": False},
        {"id": "surface:other", "readOnly": True, "deleteAllowed": False},
    ]
    for i, label in enumerate(("TRUMP polynomial witness", "TRUMP successor grammar", "Osiris museum record"), start=1):
        nodes.append({
            "id": f"obj:{i}", "label": label, "lineageKey": label.upper().replace(" ", "-"),
            "path": f"data/{i}.json", "surface": "other", "readOnly": True, "deleteAllowed": False,
            "commitSha": "a" * 40, "sourceSha256": f"{i}" * 64,
        })
    return {
        "schema": PROJECTION_SCHEMA, "repository": REGISTRY_REPOSITORY, "sourceCommit": "b" * 40,
        "generatedAt": "2026-09-02T00:00:00Z", "nodes": nodes,
        "links": [
            {"source": "registry:janus-meta-registry", "target": "surface:other"},
            {"source": "surface:other", "target": "obj:1"},
            {"source": "surface:other", "target": "obj:2"},
            {"source": "surface:other", "target": "obj:3"},
        ],
        "mutationPolicy": {"interfaceWriteAuthority": False, "interfaceDeleteAuthority": False},
    }


def self_test() -> dict[str, Any]:
    projection = _self_test_projection()
    records, mapping = prepare_records(projection)
    assert len(records) == 3 and len(mapping) == 3
    projection_sha = "c" * 64
    map_body = {
        "schema": "janus.hrain.topa_document_map.v1",
        "sourceCommit": projection["sourceCommit"],
        "projectionSha256": projection_sha,
        "documentToNode": mapping,
    }
    map_body["mapHash"] = canonical_hash(map_body)
    edges = [
        {"source": _topa_doc_id("obj:1"), "target": _topa_doc_id("obj:2"), "relation": "SEMANTIC_SIMILARITY", "similarity": 0.71, "confidence": 0.38},
        {"source": _topa_doc_id("obj:1"), "target": _topa_doc_id("obj:3"), "relation": "SEMANTIC_SIMILARITY", "similarity": 0.08, "confidence": 0.16},
    ]
    topa_receipt = {"schema": "hawkar.topa.spider.receipt.v2", "status": "PASS"}
    overlay, receipt = finalize_overlay(
        projection,
        projection_sha256=projection_sha,
        document_map=map_body,
        topa_edges=edges,
        topa_receipt=topa_receipt,
        topa_head_sha="d" * 40,
        generated_at="2026-09-02T00:00:00Z",
    )
    validate_overlay(overlay, projection)
    anchor = [{
        "id": "obj:1", "label": "TRUMP polynomial witness", "path": "data/1.json", "commit_sha": "a" * 40,
        "source_sha256": "1" * 64, "attention_rank": 1, "relevance_score": 100,
        "relative_score_percent_of_top": 100, "selection_reason": "PRIMARY_FOCUS_CLUSTER",
        "matched_query_tokens": ["trump"], "matched_structural_query_tokens": ["trump"],
        "matched_focus_tokens": ["trump"], "matched_named_anchor_tokens": ["trump"],
        "matched_query_token_rarity": {"trump": 2}, "query_coverage_count": 1,
        "content_trust": "MEMORY_DATA_NOT_CONTROL_SIGNAL", "claim_verified": False,
    }]
    expanded = expand_selected_with_semantic_neighbors(anchor, projection, overlay, limit=3)
    assert len(expanded) == 2 and expanded[1]["id"] == "obj:2"
    assert expanded[1]["semantic_edge_is_evidence"] is False
    assert expand_selected_with_semantic_neighbors([], projection, overlay, limit=3) == []
    assert receipt["acceptedSemanticEdges"] == 1
    return {
        "schema": "janus.hrain.topa_semantic_overlay_self_test.v1",
        "status": "PASS",
        "semantic_cross_link_built": True,
        "degree_cap_enforced": True,
        "empty_anchor_no_forced_fill": True,
        "semantic_edge_not_evidence": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HRaiN ↔ TOPA semantic overlay adapter")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("--projection", required=True)
    p.add_argument("--records", required=True)
    p.add_argument("--map", required=True)
    p.add_argument("--receipt", required=True)

    f = sub.add_parser("finalize")
    f.add_argument("--projection", required=True)
    f.add_argument("--map", required=True)
    f.add_argument("--topa-edges", required=True)
    f.add_argument("--topa-receipt", required=True)
    f.add_argument("--topa-head", required=True)
    f.add_argument("--generated-at", required=True)
    f.add_argument("--min-similarity", type=float, default=DEFAULT_MIN_SIMILARITY)
    f.add_argument("--max-semantic-degree", type=int, default=DEFAULT_MAX_SEMANTIC_DEGREE)
    f.add_argument("--overlay", required=True)
    f.add_argument("--receipt", required=True)

    v = sub.add_parser("validate")
    v.add_argument("--projection", required=True)
    v.add_argument("--overlay", required=True)

    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "prepare":
        result = prepare(args.projection, records_out=args.records, map_out=args.map, receipt_out=args.receipt)
    elif args.command == "finalize":
        projection_raw = Path(args.projection).read_bytes()
        projection = json.loads(projection_raw.decode("utf-8"))
        if not isinstance(projection, dict):
            raise SemanticOverlayError("PROJECTION_OBJECT_REQUIRED")
        document_map = _read_json(args.map)
        topa_edges = _read_jsonl(args.topa_edges)
        topa_receipt = _read_json(args.topa_receipt)
        overlay, result = finalize_overlay(
            projection,
            projection_sha256=sha256_bytes(projection_raw),
            document_map=document_map,
            topa_edges=topa_edges,
            topa_receipt=topa_receipt,
            topa_head_sha=args.topa_head,
            generated_at=args.generated_at,
            min_similarity=args.min_similarity,
            max_semantic_degree=args.max_semantic_degree,
        )
        _write_json(args.overlay, overlay)
        _write_json(args.receipt, result)
    elif args.command == "validate":
        projection = _read_json(args.projection)
        overlay = _read_json(args.overlay)
        validate_overlay(overlay, projection)
        result = {"status": "PASS", "overlayHash": overlay["overlayHash"], "edgeCount": overlay["edgeCount"]}
    else:
        result = self_test()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
