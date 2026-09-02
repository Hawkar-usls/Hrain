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

from hrain_topa_semantic_overlay import (
    expand_selected_with_semantic_neighbors,
    load_default_overlay,
)

PROJECTION_SCHEMA = "janus.hrain.registry_graph_index.v1_0"
OUTPUT_SCHEMA = "janus.hrain.conversation_context.v1"
REGISTRY_REPOSITORY = "Hawkar-usls/janus-meta-registry"
DEFAULT_PROJECTION_URL = (
    "https://raw.githubusercontent.com/Hawkar-usls/janus-meta-registry/"
    "main/assets/hrain-registry-index.json"
)
SELECTION_METHOD = "DETERMINISTIC_FOCUS_CLUSTER_THRESHOLD_ATTENTION_V3"
LEGACY_SELECTION_METHODS = {
    "DETERMINISTIC_WEIGHTED_LEXICAL_GRAPH_NODE_SELECTION_V1",
    "DETERMINISTIC_RARITY_WEIGHTED_DIVERSE_GRAPH_ATTENTION_V2",
}
MAX_OBJECT_BYTES = 262_144
MAX_TOTAL_HYDRATED_BYTES = 1_048_576
MAX_EXCERPT_CHARS = 6_000
PRIMARY_NAMED_SHARED_SCORE_PERCENT = 15
PRIMARY_SHARED_SCORE_PERCENT = 35
SECONDARY_CLUSTER_SCORE_PERCENT = 65
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_HASH64 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"[\w]+", re.UNICODE)
_SCORE_FIELDS = (
    ("label", 10),
    ("lineageKey", 9),
    ("path", 8),
    ("summary", 5),
    ("status", 3),
    ("surface", 2),
)
_STRUCTURAL_FIELDS = ("label", "lineageKey", "path")


class HrainContextError(RuntimeError):
    pass


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_url(url: str, *, max_bytes: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "JANUS-HRAiN-Conversation-Context/1.3"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HrainContextError(f"REMOTE_OBJECT_EXCEEDS_BOUND:{max_bytes}")
    return data


def load_projection(*, projection_file: str | Path | None = None, projection_url: str | None = None) -> tuple[Dict[str, Any], str]:
    raw = Path(projection_file).read_bytes() if projection_file is not None else _read_url(
        projection_url or DEFAULT_PROJECTION_URL, max_bytes=8_000_000
    )
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
    if _SHA40.fullmatch(str(projection.get("sourceCommit") or "")) is None:
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


def named_query_tokens(text: str) -> tuple[str, ...]:
    out: list[str] = []
    for token in _TOKEN.findall(str(text)):
        if len(token) < 2:
            continue
        has_alpha = any(ch.isalpha() for ch in token)
        all_caps = has_alpha and token.upper() == token and token.lower() != token
        mixed_case = has_alpha and any(ch.isupper() for ch in token[1:]) and any(ch.islower() for ch in token)
        if all_caps or mixed_case:
            lowered = token.lower()
            if lowered not in out:
                out.append(lowered)
    return tuple(out)


def _field_tokens(node: Mapping[str, Any], field: str) -> set[str]:
    return set(tokenize(str(node.get(field) or "")))


def _tokens_for_fields(node: Mapping[str, Any], fields: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for field in fields:
        out.update(_field_tokens(node, field))
    return out


def _node_tokens(node: Mapping[str, Any]) -> set[str]:
    return _tokens_for_fields(node, (field for field, _ in _SCORE_FIELDS))


def _structural_tokens(node: Mapping[str, Any]) -> set[str]:
    return _tokens_for_fields(node, _STRUCTURAL_FIELDS)


def selectable_nodes(projection: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for node in projection.get("nodes") or []:
        if not isinstance(node, Mapping):
            continue
        if not str(node.get("path") or ""):
            continue
        if node.get("readOnly") is not True or node.get("deleteAllowed") is not False:
            continue
        yield node


def _rarity_weight(document_count: int, document_frequency: int) -> int:
    if document_count < 1 or document_frequency < 1:
        return 0
    return max(1, min(12, (document_count + (2 * document_frequency) - 1) // (2 * document_frequency)))


def attention_profile(projection: Mapping[str, Any], query: str) -> Dict[str, Any]:
    validate_projection(projection)
    nodes = [dict(node) for node in selectable_nodes(projection)]
    query_tokens = tokenize(query)
    node_tokens = [_node_tokens(node) for node in nodes]
    structural_tokens = [_structural_tokens(node) for node in nodes]
    named_tokens = set(named_query_tokens(query))
    stats: list[Dict[str, Any]] = []
    for ordinal, token in enumerate(query_tokens):
        df = sum(1 for tokens in node_tokens if token in tokens)
        structural_df = sum(1 for tokens in structural_tokens if token in tokens)
        rarity = _rarity_weight(len(nodes), df)
        focus_eligible = bool(df > 0 and structural_df > 0 and rarity > 1)
        stats.append({
            "token": token,
            "query_ordinal": ordinal,
            "document_frequency": df,
            "structural_document_frequency": structural_df,
            "rarity_weight": rarity,
            "informative": focus_eligible,
            "focus_eligible": focus_eligible,
            "named_anchor": bool(focus_eligible and token in named_tokens),
        })
    return {
        "selectable_document_count": len(nodes),
        "query_tokens": list(query_tokens),
        "named_query_tokens": list(named_query_tokens(query)),
        "token_stats": stats,
        "coverage_rule": "PRIMARY_FOCUS_CLUSTER_THEN_RELATIVE_SCORE_THRESHOLD",
        "limit_semantics": "UPPER_BOUND_NOT_TARGET_COUNT",
        "no_match_policy": "RETURN_FEWER_OR_ZERO_NOT_NOISE_FILL",
        "primary_named_shared_score_percent": PRIMARY_NAMED_SHARED_SCORE_PERCENT,
        "primary_shared_score_percent": PRIMARY_SHARED_SCORE_PERCENT,
        "secondary_cluster_score_percent": SECONDARY_CLUSTER_SCORE_PERCENT,
        "law": "TOKEN_RARITY_IS_ATTENTION_NOT_EVIDENCE",
    }


def _rarity_map(profile: Mapping[str, Any]) -> Dict[str, int]:
    return {
        str(row.get("token")): int(row.get("rarity_weight") or 0)
        for row in profile.get("token_stats") or [] if isinstance(row, Mapping)
    }


def _focus_eligible_tokens(profile: Mapping[str, Any]) -> set[str]:
    return {
        str(row.get("token")) for row in profile.get("token_stats") or []
        if isinstance(row, Mapping) and row.get("focus_eligible") is True
    }


def _named_anchor_tokens(profile: Mapping[str, Any]) -> set[str]:
    return {
        str(row.get("token")) for row in profile.get("token_stats") or []
        if isinstance(row, Mapping) and row.get("named_anchor") is True
    }


def _matched_tokens(node: Mapping[str, Any], query_tokens: Iterable[str]) -> list[str]:
    available = _node_tokens(node)
    return [token for token in query_tokens if token in available]


def _matched_structural_tokens(node: Mapping[str, Any], query_tokens: Iterable[str]) -> list[str]:
    available = _structural_tokens(node)
    return [token for token in query_tokens if token in available]


def relevance_score(node: Mapping[str, Any], query: str, *, token_rarity: Mapping[str, int] | None = None) -> int:
    tokens = tokenize(query)
    if not tokens:
        return 0
    rarity = dict(token_rarity or {})
    score = 0
    matched: set[str] = set()
    for field, field_weight in _SCORE_FIELDS:
        hay_tokens = _field_tokens(node, field)
        for token in tokens:
            if token in hay_tokens:
                score += field_weight * max(1, int(rarity.get(token, 1)))
                matched.add(token)
    score += 6 * len(matched) * len(matched)
    return score


def _ranked_nodes(projection: Mapping[str, Any], query: str) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
    profile = attention_profile(projection, query)
    rarity = _rarity_map(profile)
    query_tokens = tuple(profile["query_tokens"])
    focus_eligible = _focus_eligible_tokens(profile)
    ranked: list[Dict[str, Any]] = []
    for ordinal, raw in enumerate(selectable_nodes(projection)):
        node = dict(raw)
        matched = _matched_tokens(node, query_tokens)
        structural_matched = _matched_structural_tokens(node, query_tokens)
        structural_focus = [token for token in structural_matched if token in focus_eligible]
        ranked.append({
            "score": relevance_score(node, query, token_rarity=rarity),
            "ordinal": ordinal,
            "path_sort": str(node.get("path") or ""),
            "node": node,
            "matched_tokens": matched,
            "structural_matched_tokens": structural_matched,
            "structural_focus_tokens": structural_focus,
            "coverage_count": len(matched),
            "structural_focus_count": len(structural_focus),
        })
    ranked.sort(key=lambda row: (
        -int(row["score"]), -int(row["structural_focus_count"]), -int(row["coverage_count"]),
        int(row["ordinal"]), str(row["path_sort"]),
    ))
    return ranked, profile


def _percent_of_top(score: int, top_score: int) -> int:
    return 0 if top_score <= 0 else (100 * max(0, score)) // top_score


def select_nodes(projection: Mapping[str, Any], query: str, *, limit: int = 12) -> list[Dict[str, Any]]:
    validate_projection(projection)
    if limit < 1 or limit > 32:
        raise HrainContextError("HRAIN_CONTEXT_SELECTION_LIMIT_OUT_OF_RANGE")
    ranked, profile = _ranked_nodes(projection, query)
    positive = [row for row in ranked if int(row["score"]) > 0]
    if not positive:
        return []
    top = positive[0]
    top_score = int(top["score"])
    primary_focus = set(top["structural_focus_tokens"])
    named_anchors = _named_anchor_tokens(profile)
    chosen: list[tuple[Dict[str, Any], str]] = [(top, "PRIMARY_FOCUS_CLUSTER")]
    chosen_paths = {str(top["path_sort"])}
    for row in positive[1:]:
        if len(chosen) >= limit:
            break
        path = str(row["path_sort"])
        if path in chosen_paths:
            continue
        relative = _percent_of_top(int(row["score"]), top_score)
        row_focus = set(row["structural_focus_tokens"])
        shared_focus = sorted(primary_focus.intersection(row_focus))
        shared_named = sorted(set(shared_focus).intersection(named_anchors))
        if shared_named and relative >= PRIMARY_NAMED_SHARED_SCORE_PERCENT:
            reason = "PRIMARY_NAMED_FOCUS_SHARED_MATCH:" + ",".join(shared_named)
        elif shared_focus and relative >= PRIMARY_SHARED_SCORE_PERCENT:
            reason = "PRIMARY_FOCUS_SHARED_STRONG_MATCH:" + ",".join(shared_focus)
        elif relative >= SECONDARY_CLUSTER_SCORE_PERCENT and row_focus.intersection(named_anchors):
            reason = "SECONDARY_NAMED_FOCUS_CLUSTER:" + ",".join(sorted(row_focus.intersection(named_anchors)))
        else:
            continue
        chosen.append((row, reason))
        chosen_paths.add(path)
    rarity = _rarity_map(profile)
    selected: list[Dict[str, Any]] = []
    for rank, (row, reason) in enumerate(chosen, start=1):
        node = row["node"]
        matched = list(row["matched_tokens"])
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
            "relevance_score": int(row["score"]),
            "relative_score_percent_of_top": _percent_of_top(int(row["score"]), top_score),
            "attention_rank": rank,
            "selection_reason": reason,
            "matched_query_tokens": matched,
            "matched_structural_query_tokens": list(row["structural_matched_tokens"]),
            "matched_focus_tokens": list(row["structural_focus_tokens"]),
            "matched_named_anchor_tokens": sorted(set(row["structural_focus_tokens"]).intersection(named_anchors)),
            "matched_query_token_rarity": {token: int(rarity.get(token, 0)) for token in matched},
            "query_coverage_count": int(row["coverage_count"]),
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
    return "https://raw.githubusercontent.com/Hawkar-usls/janus-meta-registry/" + f"{commit}/{urllib.parse.quote(path, safe='/')}"


def hydrate_selected(selected: list[Dict[str, Any]], *, registry_root: str | Path | None = None, total_byte_limit: int = MAX_TOTAL_HYDRATED_BYTES) -> list[Dict[str, Any]]:
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
        if sha256_bytes(raw) != expected:
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


def build_context(projection: Mapping[str, Any], *, projection_sha256: str, query: str, limit: int = 12, hydrate: bool = True, registry_root: str | Path | None = None) -> Dict[str, Any]:
    validate_projection(projection)
    profile = attention_profile(projection, query)
    selected = select_nodes(projection, query, limit=limit)
    overlay, overlay_sha256, overlay_status = load_default_overlay(projection)
    if overlay is not None:
        selected = expand_selected_with_semantic_neighbors(selected, projection, overlay, limit=limit)
    semantic_neighbor_count = sum(1 for row in selected if row.get("semantic_relation") == "TOPA_SEMANTIC_SIMILARITY")
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
        "selection_method": SELECTION_METHOD,
        "attention_profile": profile,
        "selection_limit": limit,
        "selection_limit_is_target_count": False,
        "semantic_overlay_status": overlay_status,
        "semantic_overlay_sha256": overlay_sha256,
        "semantic_neighbor_count": semantic_neighbor_count,
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
            "TOKEN_RARITY_IS_ATTENTION_NOT_EVIDENCE",
            "QUERY_INSTRUCTION_TOKENS != MEMORY_TOPIC",
            "LIMIT != TARGET_COUNT",
            "NO_STRONG_MATCH != FILL_WITH_NOISE",
            "QUERY_COVERAGE_IS_ATTENTION_NOT_CLAIM_CONFIDENCE",
            "RETRIEVAL_DIVERSITY != EVIDENCE_INDEPENDENCE",
            "RETRIEVED_MEMORY != WORLD_TRUTH",
            "HASH_VERIFIED_OBJECT != CLAIM_VERIFIED",
            "TOPA_SEMANTIC_NEIGHBOR != EVIDENCE",
            "SEMANTIC_SIMILARITY_IS_NOT_MECHANISM",
            "EMPTY_LEXICAL_ANCHOR_SET != SEMANTIC_FILL",
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
    memories = body.get("selected_memories")
    if not isinstance(memories, list) or int(body.get("selected_memory_count") or 0) != len(memories):
        return False
    method = body.get("selection_method")
    if method not in LEGACY_SELECTION_METHODS | {SELECTION_METHOD}:
        return False
    if method == SELECTION_METHOD:
        profile = body.get("attention_profile")
        if not isinstance(profile, Mapping):
            return False
        if profile.get("law") != "TOKEN_RARITY_IS_ATTENTION_NOT_EVIDENCE":
            return False
        if profile.get("coverage_rule") != "PRIMARY_FOCUS_CLUSTER_THEN_RELATIVE_SCORE_THRESHOLD":
            return False
        if profile.get("limit_semantics") != "UPPER_BOUND_NOT_TARGET_COUNT":
            return False
        if body.get("selection_limit_is_target_count") is not False:
            return False
        if len(memories) > int(body.get("selection_limit") or 0):
            return False
        for rank, row in enumerate(memories, start=1):
            if not isinstance(row, Mapping) or int(row.get("attention_rank") or 0) != rank:
                return False
            if not isinstance(row.get("matched_query_tokens"), list):
                return False
            if not isinstance(row.get("matched_focus_tokens"), list):
                return False
            if not isinstance(row.get("matched_named_anchor_tokens"), list):
                return False
            if not str(row.get("selection_reason") or ""):
                return False
            if int(row.get("relative_score_percent_of_top") or 0) < 0:
                return False
            if row.get("claim_verified") is not False:
                return False
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
    projection, projection_sha = load_projection(projection_file=args.projection_file, projection_url=args.projection_url)
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
        "selection_method": context["selection_method"],
        "selection_limit": context["selection_limit"],
        "selection_limit_is_target_count": context["selection_limit_is_target_count"],
        "selected_memory_count": context["selected_memory_count"],
        "selected_paths": [row.get("path") for row in context["selected_memories"]],
        "hydration_performed": context["hydration_performed"],
        "context_hash": context["context_hash"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
