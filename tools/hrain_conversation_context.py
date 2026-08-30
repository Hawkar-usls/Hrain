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
SELECTION_METHOD = "DETERMINISTIC_RARITY_WEIGHTED_DIVERSE_GRAPH_ATTENTION_V2"
MAX_OBJECT_BYTES = 262_144
MAX_TOTAL_HYDRATED_BYTES = 1_048_576
MAX_EXCERPT_CHARS = 6_000
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
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "JANUS-HRAiN-Conversation-Context/1.2"},
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
        path = str(node.get("path") or "")
        if not path:
            continue
        if node.get("readOnly") is not True or node.get("deleteAllowed") is not False:
            continue
        yield node


def _rarity_weight(document_count: int, document_frequency: int) -> int:
    """Integer inverse-frequency attention weight; deterministic and bounded."""
    if document_count < 1 or document_frequency < 1:
        return 0
    return max(1, min(12, (document_count + (2 * document_frequency) - 1) // (2 * document_frequency)))


def attention_profile(projection: Mapping[str, Any], query: str) -> Dict[str, Any]:
    validate_projection(projection)
    nodes = [dict(node) for node in selectable_nodes(projection)]
    query_tokens = tokenize(query)
    node_tokens = [_node_tokens(node) for node in nodes]
    structural_tokens = [_structural_tokens(node) for node in nodes]
    stats: list[Dict[str, Any]] = []
    for ordinal, token in enumerate(query_tokens):
        df = sum(1 for tokens in node_tokens if token in tokens)
        structural_df = sum(1 for tokens in structural_tokens if token in tokens)
        rarity = _rarity_weight(len(nodes), df)
        coverage_eligible = bool(df > 0 and structural_df > 0 and rarity > 1)
        stats.append({
            "token": token,
            "query_ordinal": ordinal,
            "document_frequency": df,
            "structural_document_frequency": structural_df,
            "rarity_weight": rarity,
            "informative": coverage_eligible,
            "coverage_eligible": coverage_eligible,
        })
    return {
        "selectable_document_count": len(nodes),
        "query_tokens": list(query_tokens),
        "token_stats": stats,
        "coverage_rule": "RARE_TOKEN_MUST_APPEAR_IN_LABEL_LINEAGE_OR_PATH",
        "law": "TOKEN_RARITY_IS_ATTENTION_NOT_EVIDENCE",
    }


def _rarity_map(profile: Mapping[str, Any]) -> Dict[str, int]:
    return {
        str(row.get("token")): int(row.get("rarity_weight") or 0)
        for row in profile.get("token_stats") or []
        if isinstance(row, Mapping)
    }


def _matched_tokens(node: Mapping[str, Any], query_tokens: Iterable[str]) -> list[str]:
    available = _node_tokens(node)
    return [token for token in query_tokens if token in available]


def relevance_score(
    node: Mapping[str, Any],
    query: str,
    *,
    token_rarity: Mapping[str, int] | None = None,
) -> int:
    tokens = tokenize(query)
    if not tokens:
        return 0
    rarity = dict(token_rarity or {})
    score = 0
    matched: set[str] = set()
    for field, field_weight in _SCORE_FIELDS:
        hay_tokens = _field_tokens(node, field)
        if not hay_tokens:
            continue
        for token in tokens:
            if token in hay_tokens:
                token_weight = max(1, int(rarity.get(token, 1)))
                score += field_weight * token_weight
                matched.add(token)
    coverage = len(matched)
    score += 6 * coverage * coverage
    return score


def _ranked_nodes(projection: Mapping[str, Any], query: str) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
    profile = attention_profile(projection, query)
    rarity = _rarity_map(profile)
    query_tokens = tuple(profile["query_tokens"])
    ranked: list[Dict[str, Any]] = []
    for ordinal, raw in enumerate(selectable_nodes(projection)):
        node = dict(raw)
        matched = _matched_tokens(node, query_tokens)
        score = relevance_score(node, query, token_rarity=rarity)
        ranked.append({
            "score": score,
            "ordinal": ordinal,
            "path_sort": str(node.get("path") or ""),
            "node": node,
            "matched_tokens": matched,
            "coverage_count": len(matched),
        })
    ranked.sort(key=lambda row: (-int(row["score"]), -int(row["coverage_count"]), int(row["ordinal"]), str(row["path_sort"])))
    return ranked, profile


def select_nodes(projection: Mapping[str, Any], query: str, *, limit: int = 12) -> list[Dict[str, Any]]:
    validate_projection(projection)
    if limit < 1 or limit > 32:
        raise HrainContextError("HRAIN_CONTEXT_SELECTION_LIMIT_OUT_OF_RANGE")
    ranked, profile = _ranked_nodes(projection, query)
    if not ranked:
        return []

    coverage_tokens = [
        row for row in profile["token_stats"]
        if isinstance(row, Mapping) and row.get("coverage_eligible") is True
    ]
    coverage_tokens.sort(
        key=lambda row: (-int(row["rarity_weight"]), int(row["structural_document_frequency"]), int(row["query_ordinal"])),
    )
    chosen: list[tuple[Dict[str, Any], str]] = []
    chosen_paths: set[str] = set()
    for token_row in coverage_tokens:
        if len(chosen) >= limit:
            break
        token = str(token_row["token"])
        candidate = next(
            (
                row for row in ranked
                if int(row["score"]) > 0
                and token in row["matched_tokens"]
                and str(row["path_sort"]) not in chosen_paths
            ),
            None,
        )
        if candidate is None:
            continue
        chosen.append((candidate, f"RARE_STRUCTURAL_QUERY_TOKEN_COVERAGE:{token}"))
        chosen_paths.add(str(candidate["path_sort"]))

    for row in ranked:
        if len(chosen) >= limit:
            break
        path = str(row["path_sort"])
        if path in chosen_paths:
            continue
        if int(row["score"]) <= 0 and chosen:
            continue
        chosen.append((row, "GLOBAL_RARITY_WEIGHTED_SCORE" if int(row["score"]) > 0 else "DETERMINISTIC_FALLBACK_NO_QUERY_MATCH"))
        chosen_paths.add(path)

    rarity = _rarity_map(profile)
    selected: list[Dict[str, Any]] = []
    for rank, (ranked_row, reason) in enumerate(chosen, start=1):
        node = ranked_row["node"]
        matched = list(ranked_row["matched_tokens"])
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
            "relevance_score": int(ranked_row["score"]),
            "attention_rank": rank,
            "selection_reason": reason,
            "matched_query_tokens": matched,
            "matched_query_token_rarity": {token: int(rarity.get(token, 0)) for token in matched},
            "query_coverage_count": int(ranked_row["coverage_count"]),
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
    profile = attention_profile(projection, query)
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
        "selection_method": SELECTION_METHOD,
        "attention_profile": profile,
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
            "TOKEN_RARITY_IS_ATTENTION_NOT_EVIDENCE",
            "RARE_SUMMARY_WORD != MEMORY_ENTITY",
            "QUERY_COVERAGE_IS_ATTENTION_NOT_CLAIM_CONFIDENCE",
            "RETRIEVAL_DIVERSITY != EVIDENCE_INDEPENDENCE",
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
    memories = body.get("selected_memories")
    if not isinstance(memories, list) or int(body.get("selected_memory_count") or 0) != len(memories):
        return False
    if body.get("selection_method") not in {
        "DETERMINISTIC_WEIGHTED_LEXICAL_GRAPH_NODE_SELECTION_V1",
        SELECTION_METHOD,
    }:
        return False
    if body.get("selection_method") == SELECTION_METHOD:
        profile = body.get("attention_profile")
        if not isinstance(profile, Mapping):
            return False
        if profile.get("law") != "TOKEN_RARITY_IS_ATTENTION_NOT_EVIDENCE":
            return False
        if profile.get("coverage_rule") != "RARE_TOKEN_MUST_APPEAR_IN_LABEL_LINEAGE_OR_PATH":
            return False
        for rank, row in enumerate(memories, start=1):
            if not isinstance(row, Mapping):
                return False
            if int(row.get("attention_rank") or 0) != rank:
                return False
            if not isinstance(row.get("matched_query_tokens"), list):
                return False
            if not str(row.get("selection_reason") or ""):
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
        "selection_method": context["selection_method"],
        "selected_memory_count": context["selected_memory_count"],
        "selected_paths": [row.get("path") for row in context["selected_memories"]],
        "hydration_performed": context["hydration_performed"],
        "context_hash": context["context_hash"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
