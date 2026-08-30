#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping

ACTIVE_URL = "https://raw.githubusercontent.com/Hawkar-usls/janus-meta-registry/main/assets/hrain-registry-index.json"
FULL_MANIFEST_URL = "https://raw.githubusercontent.com/Hawkar-usls/janus-meta-registry/main/assets/hrain-full-memory/manifest.json"
USER_AGENT = "JANUS-HRAIN-CONVERSATION-CONTEXT/1.0"


class HRaiNConversationContextError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def fetch_json(url: str, opener: Callable[..., Any] = urllib.request.urlopen) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener(request, timeout=30) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise HRaiNConversationContextError("HRAIN_CONTEXT_SOURCE_NOT_OBJECT")
    return value


def _node_rows(active: Mapping[str, Any]) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    for node in active.get("nodes") or []:
        if not isinstance(node, Mapping) or not str(node.get("id") or "").startswith("obj:"):
            continue
        rows.append({
            "id": node.get("id"),
            "label": node.get("label"),
            "surface": node.get("surface"),
            "lineage_key": node.get("lineageKey"),
            "path": node.get("path"),
            "status": node.get("status"),
            "summary": node.get("summary"),
            "modified_at": node.get("modifiedAt"),
            "source_sha256": node.get("sourceSha256"),
            "source_url": node.get("sourceUrl"),
            "read_only": node.get("readOnly") is True,
        })
    rows.sort(key=lambda row: (str(row.get("modified_at") or ""), str(row.get("path") or "")), reverse=True)
    return rows


def build_context(active: Mapping[str, Any], full_manifest: Mapping[str, Any], *, generated_at: float | None = None) -> Dict[str, Any]:
    if active.get("schema") != "janus.hrain.registry_graph_index.v1_0":
        raise HRaiNConversationContextError("HRAIN_ACTIVE_PROJECTION_SCHEMA_MISMATCH")
    if active.get("status") != "AUTO_GENERATED_READ_ONLY_ACTIVE_REGISTRY_PROJECTION":
        raise HRaiNConversationContextError("HRAIN_ACTIVE_PROJECTION_STATUS_MISMATCH")
    mutation = active.get("mutationPolicy") or {}
    if mutation.get("interfaceWriteAuthority") is not False or mutation.get("interfaceDeleteAuthority") is not False:
        raise HRaiNConversationContextError("HRAIN_ACTIVE_PROJECTION_AUTHORITY_CEILING_INVALID")
    if full_manifest.get("mode") != "FULL_CURRENT":
        raise HRaiNConversationContextError("HRAIN_FULL_MEMORY_MODE_MISMATCH")
    coverage = full_manifest.get("coverage") or {}
    authority = full_manifest.get("authority") or {}
    if coverage.get("coverage_complete") is not True:
        raise HRaiNConversationContextError("HRAIN_FULL_CURRENT_COVERAGE_NOT_PROVEN")
    if authority.get("read_only") is not True or authority.get("source_mutation_allowed") is not False:
        raise HRaiNConversationContextError("HRAIN_FULL_MEMORY_AUTHORITY_CEILING_INVALID")

    rows = _node_rows(active)
    core = {
        "schema": "janus.hrain.conversation_context.v1",
        "status": "READ_ONLY_HRAIN_MEDIATED_CONVERSATION_CONTEXT",
        "source_database": "Hawkar-usls/janus-meta-registry",
        "mediating_organ": "Hawkar-usls/Hrain",
        "active_projection_source_commit": active.get("sourceCommit"),
        "active_projection_object_count": active.get("objectCount"),
        "full_current_source_commit": full_manifest.get("source_commit"),
        "full_current_catalog_digest": full_manifest.get("catalog_digest"),
        "full_current_cataloged_blob_count": coverage.get("cataloged_blob_count"),
        "full_current_coverage_complete": True,
        "historical_lineage_included": bool(full_manifest.get("historical_lineage_included", False)),
        "objects": rows,
        "object_count": len(rows),
        "authority": {
            "read_only": True,
            "source_mutation_allowed": False,
            "command_authority_granted": False,
            "claim_authority_granted": False,
            "scientific_evidence_authority_granted": False,
            "world_truth_authority_granted": False,
            "external_effect_authorized": False,
            "physical_runtime_effect_authorized": False,
        },
        "laws": [
            "META_REGISTRY_DB -> HRAIN -> JANUS_CONVERSATION -> TERMINAL",
            "HRAIN_CONTEXT != COMPLETE_DATABASE_CONTENT",
            "HRAIN_CONTEXT != REGISTRY_AUTHORITY",
            "CATALOG_PRESENCE != SCIENTIFIC_VALIDITY",
            "MEMORY_CONTEXT != COMMAND",
            "FULL_CURRENT != COMPLETE_GIT_HISTORY",
        ],
    }
    result = dict(core)
    result["generated_at"] = float(time.time() if generated_at is None else generated_at)
    result["context_digest"] = sha256_json(core)
    return result


def select_context(context: Mapping[str, Any], query: str, *, limit: int = 24) -> Dict[str, Any]:
    if context.get("schema") != "janus.hrain.conversation_context.v1":
        raise HRaiNConversationContextError("HRAIN_CONTEXT_SCHEMA_MISMATCH")
    core = dict(context)
    claimed = str(core.pop("context_digest", ""))
    core.pop("generated_at", None)
    if len(claimed) != 64 or sha256_json(core) != claimed:
        raise HRaiNConversationContextError("HRAIN_CONTEXT_DIGEST_INVALID")
    authority = context.get("authority") or {}
    if any(authority.get(key) is not False for key in (
        "source_mutation_allowed", "command_authority_granted", "claim_authority_granted",
        "scientific_evidence_authority_granted", "world_truth_authority_granted",
        "external_effect_authorized", "physical_runtime_effect_authorized",
    )):
        raise HRaiNConversationContextError("HRAIN_CONTEXT_AUTHORITY_CEILING_INVALID")

    tokens = {token for token in ''.join(ch.lower() if ch.isalnum() else ' ' for ch in str(query)).split() if len(token) >= 3}
    scored = []
    for index, row in enumerate(context.get("objects") or []):
        if not isinstance(row, Mapping):
            continue
        hay = ' '.join(str(row.get(k) or '') for k in ("label", "lineage_key", "path", "status", "summary", "surface")).lower()
        score = sum(3 if token in str(row.get("label") or '').lower() else 1 for token in tokens if token in hay)
        if score or index < 8:
            scored.append((score, index, dict(row)))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = [row for _, _, row in scored[:max(1, int(limit))]]
    capsule_core = {
        "schema": "janus.hrain.selected_conversation_context.v1",
        "parent_context_digest": context.get("context_digest"),
        "source_database": context.get("source_database"),
        "mediating_organ": context.get("mediating_organ"),
        "query_digest": hashlib.sha256(str(query).encode("utf-8")).hexdigest(),
        "selected_objects": selected,
        "selected_count": len(selected),
        "full_current_catalog_digest": context.get("full_current_catalog_digest"),
        "full_current_coverage_complete": context.get("full_current_coverage_complete") is True,
        "authority": dict(context.get("authority") or {}),
        "laws": list(context.get("laws") or []),
    }
    capsule = dict(capsule_core)
    capsule["selection_digest"] = sha256_json(capsule_core)
    return capsule


def main() -> int:
    parser = argparse.ArgumentParser(description="Build read-only HRaiN mediated conversation context from JANUS Meta Registry projections")
    parser.add_argument("--out", default="runtime/hrain-conversation-context.json")
    args = parser.parse_args()
    active = fetch_json(ACTIVE_URL)
    full = fetch_json(FULL_MANIFEST_URL)
    result = build_context(active, full)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "terminal": "HRAIN_CONVERSATION_CONTEXT_READY",
        "context_digest": result["context_digest"],
        "object_count": result["object_count"],
        "active_projection_source_commit": result["active_projection_source_commit"],
        "full_current_catalog_digest": result["full_current_catalog_digest"],
        "out": str(out),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
