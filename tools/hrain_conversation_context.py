#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

PROJECTION_SCHEMA = "janus.hrain.registry_graph_index.v1_0"
OUTPUT_SCHEMA = "janus.hrain.conversation_context.v1"
REGISTRY_REPOSITORY = "Hawkar-usls/janus-meta-registry"
DEFAULT_PROJECTION_URL = (
    "https://raw.githubusercontent.com/Hawkar-usls/janus-meta-registry/"
    "main/assets/hrain-registry-index.json"
)
MAX_OBJECT_BYTES = 262_144
MAX_TOTAL_HYDRATED_BYTES = 1_048_576
MAX_EXCERPT_CHARS = 6_000
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_HASH64 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"[\w-]+", re.UNICODE)


class HrainContextError(RuntimeError):
    pass


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_url(url: str, *, max_bytes: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "JANUS-HRAiN-Conversation-Context/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HrainContextError(f"REMOTE_OBJECT_EXCEEDS_BOUND:{max_bytes}")
    return data


def load_projection(*, projection_file: str | Path | None = None, projection_url: str | None = None) -> tuple[Dict[str, Any], str]:
    if projection_file is not None:
        raw = Path(projection_file).read_bytes()
    else:
        raw = _read_url(projection_url or DEFAULT_PROJECTION_URL, max_bytes=8_000_000)
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise HrainContextError("HRAIN_PROJECTION_NOT_VALID_UTF8_JSON") from exc
    if not isinstance(value, dict):
        raise HrainContextError("HRAIN_PROJECTION_OBJECT_REQUIRED")
    validate_projection(value)
    return value, sha256_bytes(raw)


def validate_projection(projection: Mapping[str, Any]) -> None:
    if projection.get("schema") != PROJECTION_SCHEMA:
        raise HrainContextError("HRAIN_PROJECTION_SCHEMA_MISMATCH")
    if projection.get("repository") != REGISTRY_REPOSITORY:
        raise HrainContextError("HRAIN_PROJECTION_SOURCE_REPOSITORY_MISMATCH")
    commit = str(projection.get("sourceCommit") or "")
    if _SHA40.fullmatch(commit) is None:
        raise HrainContextError("HRAIN_PROJECTION_SOURCE_COMMIT_INVALID")
    policy = projection.get("mutationPolicy")
    if not isinstance(policy, Mapping):
        raise HrainContextError("HRAIN_PROJECTION_MUTATION_POLICY_REQUIRED")
    if policy.get("interfaceWriteAuthority") is not False or policy.get("interfaceDeleteAuthority") is not False:
        raise HrainContextError("HRAIN_PROJECTION_MUST_BE_READ_ONLY")
    nodes = projection.get("nodes")
    if not isinstance(nodes, list):
        raise HrainContextError("HRAIN_PROJECTION_NODES_REQUIRED")
    declared = projection.get("nodeCount")
    if isinstance(declared, int) and declared != len(nodes):
        raise HrainContextError("HRAIN_PROJECTION_NODE_COUNT_MISMATCH")


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(token.lower() for token in _TOKEN.findall(str(text)) if len(token) > 1))


def _field_text(node: Mapping[str, Any], field: str) -> str:
    return str(node.get(field) or "").lower()


def relevance_score(node: Mapping[str, Any], query: str) -> int:
    tokens = tokenize(query)
    if not tokens:
        return 0
    weighted_fields = (
        ("label", 9),
        ("lineageKey", 8),
        ("summary", 6),
        ("status", 5),
        ("path", 5),
        ("surface", 3),
    )
    score = 0
    for field, weight in weighted_fields:
        hay = _field_text(node, field)
        if not hay:
            continue
        for token in tokens:
            if token in hay:
                score += weight
        normalized_query = " ".join(tokens)
        if normalized_query and normalized_query in hay:
            score += weight * 2
    return score


def selectable_nodes(projection: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for node in projection.get("nodes") or []:
        if not isinstance(node, Mapping):
            continue
        path = str(node.get("path") or "")
        if not path:
            continue
        if node.get("readOnly") is not True or node.get("deleteAllowed") is not False:
            continue
        yield node


def select_nodes(projection: Mapping[str, Any], query: str, *, limit: int = 12) -> list[Dict[str, Any]]:
    validate_projection(projection)
    if limit < 1 or limit > 32:
        raise HrainContextError("HRAIN_CONTEXT_SELECTION_LIMIT_OUT_OF_RANGE")
    ranked = []
    for ordinal, node in enumerate(selectable_nodes(projection)):
        score = relevance_score(node, query)
        ranked.append((score, ordinal, str(node.get("path") or ""), dict(node)))
    if not ranked:
        return []
    positives = [row for row in ranked if row[0] > 0]
    source = positives if positives else ranked
    source.sort(key=lambda row: (-row[0], row[1], row[2]))
    selected = []
    for score, _, _, node in source[:limit]:
        selected.append({
            "id": node.get("id"),
            "label": node.get("label"),
            "surface": node.get("surface"),
            "lineage_key": node.get("lineageKey"),
            "path": node.get("path"),
            "status": node.get("status"),
            "summary": node.get("summary"),
            "commit_sha": node.get("commitSha"),
            "source_sha256": node.get("sourceSha256"),
            "relevance_score": score,
            "content_trust": "MEMORY_DATA_NOT_CONTROL_SIGNAL",
            "claim_verified": False,
        })
    return selected


def _safe_registry_path(path: str) -> str:
    candidate = str(path).strip().replace("\\", "/")
    if not candidate or candidate.startswith("/") or ".." in candidate.split("/"):
        raise HrainContextError("HRAIN_SELECTED_OBJECT_PATH_INVALID")
    return candidate


def _exact_raw_url(commit: str, path: str) -> str:
    return (
        "https://raw.githubusercontent.com/Hawkar-usls/janus-meta-registry/"
        f"{commit}/{urllib.parse.quote(path, safe='/')}"
    )


def hydrate_selected(
    selected: list[Dict[str, Any]],
    *,
    registry_root: str | Path | None = None,
    total_byte_limit: int = MAX_TOTAL_HYDRATED_BYTES,
) -> list[Dict[str, Any]]:
    total = 0
    output: list[Dict[str, Any]] = []
    root = Path(registry_root).resolve() if registry_root is not None else None
    for row in selected:
        path = _safe_registry_path(str(row.get("path") or ""))
        commit = str(row.get("commit_sha") or "")
        expected = str(row.get("source_sha256") or "")
        if _SHA40.fullmatch(commit) is None:
            raise HrainContextError(f"HRAIN_SELECTED_OBJECT_COMMIT_INVALID:{path}")
        if _HASH64.fullmatch(expected) is None:
            raise HrainContextError(f"HRAIN_SELECTED_OBJECT_SOURCE_HASH_INVALID:{path}")
        if root is not None:
            target = (root / path).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise HrainContextError("HRAIN_SELECTED_OBJECT_ESCAPES_REGISTRY_ROOT") from exc
            raw = target.read_bytes()
            if len(raw) > MAX_OBJECT_BYTES:
                raise HrainContextError(f"HRAIN_SELECTED_OBJECT_EXCEEDS_BOUND:{path}")
        else:
            raw = _read_url(_exact_raw_url(commit, path), max_bytes=MAX_OBJECT_BYTES)
        observed = sha256_bytes(raw)
        if observed != expected:
            raise HrainContextError(f"HRAIN_SELECTED_OBJECT_HASH_MISMATCH:{path}")
        total += len(raw)
        if total > total_byte_limit:
            raise HrainContextError("HRAIN_TOTAL_HYDRATED_CONTEXT_EXCEEDS_BOUND")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = "<NON_UTF8_MEMORY_OBJECT>"
        enriched = dict(row)
        enriched.update({
            "source_sha256_verified": True,
            "hydrated_bytes": len(raw),
            "content_excerpt": text[:MAX_EXCERPT_CHARS],
            "content_truncated": len(text) > MAX_EXCERPT_CHARS,
            "retrieval_authority": "READ_ONLY_EXACT_COMMIT_HASH_VERIFIED",
            "content_is_command": False,
            "content_grants_authority": False,
        })
        output.append(enriched)
    return output


def build_context(
    projection: Mapping[str, Any],
    *,
    projection_sha256: str,
    query: str,
    limit: int = 12,
    hydrate: bool = True,
    registry_root: str | Path | None = None,
) -> Dict[str, Any]:
    validate_projection(projection)
    selected = select_nodes(projection, query, limit=limit)
    memories = hydrate_selected(selected, registry_root=registry_root) if hydrate else selected
    body: Dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "status": "HRAIN_QUERY_BOUND_CONTEXT_READY",
        "query": str(query),
        "query_sha256": hashlib.sha256(str(query).encode("utf-8")).hexdigest(),
        "source_repository": REGISTRY_REPOSITORY,
        "source_projection_schema": projection.get("schema"),
        "source_projection_sha256": projection_sha256,
        "source_commit": projection.get("sourceCommit"),
        "projection_generated_at": projection.get("generatedAt"),
        "selection_method": "DETERMINISTIC_WEIGHTED_LEXICAL_GRAPH_NODE_SELECTION_V1",
        "selection_limit": limit,
        "selected_memory_count": len(memories),
        "selected_memories": memories,
        "hydration_performed": hydrate,
        "authority": {
            "read_only": True,
            "registry_write_authority": False,
            "command_authority": False,
            "claim_promotion_authority": False,
            "scientific_evidence_authority": False,
            "world_truth_authority": False,
            "external_effect_authority": False,
            "physical_runtime_effect_authority": False,
        },
        "laws": [
            "META_REGISTRY_DB -> HRAIN -> JANUS -> TERMINAL",
            "MEMORY_CONTENT != COMMAND",
            "MEMORY_CONTENT != AUTHORITY",
            "HRAIN_RELEVANCE_SCORE != EVIDENCE_WEIGHT",
            "RETRIEVED_MEMORY != WORLD_TRUTH",
            "HASH_VERIFIED_OBJECT != CLAIM_VERIFIED",
        ],
    }
    body["context_hash"] = canonical_hash(body)
    return body


def verify_context(context: Mapping[str, Any]) -> bool:
    if not isinstance(context, Mapping):
        return False
    body = dict(context)
    claimed = str(body.pop("context_hash", ""))
    if _HASH64.fullmatch(claimed) is None or canonical_hash(body) != claimed:
        return False
    authority = body.get("authority") or {}
    return all([
        body.get("schema") == OUTPUT_SCHEMA,
        body.get("status") == "HRAIN_QUERY_BOUND_CONTEXT_READY",
        authority.get("read_only") is True,
        authority.get("registry_write_authority") is False,
        authority.get("command_authority") is False,
        authority.get("claim_promotion_authority") is False,
        authority.get("scientific_evidence_authority") is False,
        authority.get("world_truth_authority") is False,
        authority.get("external_effect_authority") is False,
        authority.get("physical_runtime_effect_authority") is False,
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a bounded query-specific JANUS conversation context through HRAiN")
    parser.add_argument("--query", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--projection-file")
    parser.add_argument("--projection-url", default=DEFAULT_PROJECTION_URL)
    parser.add_argument("--registry-root")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--no-hydrate", action="store_true")
    args = parser.parse_args()

    projection, projection_sha = load_projection(
        projection_file=args.projection_file,
        projection_url=args.projection_url,
    )
    context = build_context(
        projection,
        projection_sha256=projection_sha,
        query=args.query,
        limit=args.limit,
        hydrate=not args.no_hydrate,
        registry_root=args.registry_root,
    )
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": context["status"],
        "source_commit": context["source_commit"],
        "selected_memory_count": context["selected_memory_count"],
        "hydration_performed": context["hydration_performed"],
        "context_hash": context["context_hash"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
