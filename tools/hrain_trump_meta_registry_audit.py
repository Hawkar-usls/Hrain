#!/usr/bin/env python3
"""Read-only HRAiN x TRUMP audit over the Meta Registry full-current catalog.

This is a repository-audit adapter, not the SAT solve entrypoint of candidate TRUMP.
It verifies the entire HRAiN full-current catalog against a frozen source commit,
then ranks textual artifacts by mechanics relevant to POLY_FIND/POLY_HOLD/
POLY_ADVANCE and related exact/resource gates.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

TEXT_EXTS = {
    ".json", ".md", ".py", ".yml", ".yaml", ".txt", ".js", ".html",
    ".xml", ".ps1", ".pas", ".hpp", ".h", ".c", ".cpp", ".css", ""
}

AXES = {
    "POLY_FIND": (
        "candidate grammar", "canonical first", "first admitted", "admit", "discover",
        "discovery", "prefilter", "recognizer", "dispatch", "pivot", "selector",
        "successor", "next move", "backdoor", "route law",
    ),
    "POLY_HOLD": (
        "gpei", "global polynomial envelope", "polynomial envelope", "state cap",
        "bounded state", "representation bound", "resource ledger", "resource cap",
        "budget", "no blow-up", "compression", "quotient", "bounded width",
    ),
    "POLY_ADVANCE": (
        "well-founded", "well founded", "rank", "strict progress", "progress measure",
        "decreases", "decrease", "termination", "step bound", "macrostep", "micro-rank",
        "defect dependency", "monotone progress",
    ),
    "EXACTNESS_CERTIFICATION": (
        "exact", "certificate", "certified", "proof-carrying", "proof carrying",
        "verify", "verification", "replay", "fail-closed", "fail closed", "unknown is not pass",
        "open is a valid result", "semantic equivalence",
    ),
    "DEBT_RESOURCE_ACCOUNTING": (
        "debt", "deferred", "liability", "outstanding", "resource accounting",
        "amortized", "potential", "verification work", "discovery work", "proof bytes",
    ),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_json(value: Any, prefix: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            p = f"{prefix}.{key}"
            yield p, child
            yield from flatten_json(child, p)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from flatten_json(child, f"{prefix}[{i}]")


def semantic_flags(path: str, parsed: Any) -> list[dict]:
    """Attention flags only; never claim a file is false merely from a field value."""
    out: list[dict] = []
    if not isinstance(parsed, (dict, list)):
        return out
    for field, value in flatten_json(parsed):
        leaf = field.rsplit(".", 1)[-1].lower()
        if leaf in {"p_equals_np_proved", "polynomial_time_sat_proved"} and value is True:
            out.append({"path": path, "field": field, "value": value, "kind": "SCIENTIFIC_PROMOTION_ATTENTION"})
        if leaf in {"proof_authority", "scientific_claim_promotion_authority"} and value is True:
            out.append({"path": path, "field": field, "value": value, "kind": "AUTHORITY_ATTENTION"})
    return out


def mechanic_scores(text: str) -> tuple[dict[str, int], dict[str, list[str]]]:
    lowered = text.lower()
    scores: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    for axis, terms in AXES.items():
        matched = [term for term in terms if term in lowered]
        scores[axis] = len(matched)
        hits[axis] = matched
    return scores, hits


def audit(catalog_dir: Path, source_dir: Path, top_n: int) -> dict:
    manifest_path = catalog_dir / "assets/hrain-full-memory/manifest.json"
    manifest = load_json(manifest_path)
    errors: list[dict] = []
    attention: list[dict] = []

    coverage = manifest.get("coverage", {})
    if manifest.get("schema") != "janus.hrain.full_memory_manifest.v1":
        errors.append({"kind": "MANIFEST_SCHEMA_MISMATCH"})
    if coverage.get("coverage_complete") is not True:
        errors.append({"kind": "COVERAGE_NOT_COMPLETE"})

    expected_source = manifest.get("source_commit")
    actual_source = None
    git_head = source_dir / ".git"
    # Worktrees may use a .git file; the workflow writes SOURCE_COMMIT separately.
    source_commit_file = source_dir / ".janus-source-commit"
    if source_commit_file.exists():
        actual_source = source_commit_file.read_text(encoding="utf-8").strip()
    if actual_source and expected_source != actual_source:
        errors.append({"kind": "SOURCE_COMMIT_MISMATCH", "expected": expected_source, "actual": actual_source})

    objects: list[dict] = []
    shard_verified = 0
    for shard_meta in manifest.get("sharding", {}).get("shards", []):
        shard_path = catalog_dir / shard_meta["path"]
        data = shard_path.read_bytes()
        actual = sha256_bytes(data)
        if actual != shard_meta.get("sha256"):
            errors.append({"kind": "SHARD_SHA256_MISMATCH", "path": shard_meta["path"], "expected": shard_meta.get("sha256"), "actual": actual})
            continue
        shard_verified += 1
        shard = json.loads(data)
        rows = shard.get("objects", [])
        if len(rows) != shard_meta.get("object_count") or len(rows) != shard.get("object_count"):
            errors.append({"kind": "SHARD_OBJECT_COUNT_MISMATCH", "path": shard_meta["path"]})
        objects.extend(rows)

    expected_objects = coverage.get("cataloged_blob_count")
    if len(objects) != expected_objects:
        errors.append({"kind": "CATALOG_OBJECT_COUNT_MISMATCH", "expected": expected_objects, "actual": len(objects)})

    paths = [row.get("path") for row in objects]
    if len(paths) != len(set(paths)):
        errors.append({"kind": "DUPLICATE_CATALOG_PATH"})

    verified = 0
    json_ok = 0
    json_failed = 0
    bytes_verified = 0
    duplicate_hashes: dict[str, list[str]] = defaultdict(list)
    candidates: list[dict] = []
    class_counts = Counter()
    namespace_counts = Counter()

    for row in objects:
        rel = row["path"]
        path = source_dir / rel
        class_counts[row.get("memory_class", "UNKNOWN")] += 1
        namespace_counts[row.get("namespace", "UNKNOWN")] += 1
        if not path.is_file():
            errors.append({"kind": "CATALOG_PATH_MISSING_AT_SOURCE", "path": rel})
            continue
        data = path.read_bytes()
        bytes_verified += len(data)
        actual_sha = sha256_bytes(data)
        actual_blob = git_blob_sha(data)
        if actual_sha != row.get("sha256"):
            errors.append({"kind": "OBJECT_SHA256_MISMATCH", "path": rel, "expected": row.get("sha256"), "actual": actual_sha})
            continue
        if actual_blob != row.get("git_blob_sha"):
            errors.append({"kind": "OBJECT_GIT_BLOB_MISMATCH", "path": rel})
            continue
        if len(data) != row.get("size_bytes"):
            errors.append({"kind": "OBJECT_SIZE_MISMATCH", "path": rel, "expected": row.get("size_bytes"), "actual": len(data)})
            continue
        verified += 1
        duplicate_hashes[actual_sha].append(rel)

        ext = row.get("extension", "")
        if ext == ".json":
            try:
                parsed = json.loads(data)
                json_ok += 1
                attention.extend(semantic_flags(rel, parsed))
            except Exception as exc:  # catalog may legitimately contain malformed historical data; report, do not rewrite.
                json_failed += 1
                attention.append({"kind": "JSON_PARSE_ATTENTION", "path": rel, "error": type(exc).__name__})

        if ext in TEXT_EXTS:
            text = data.decode("utf-8", errors="replace")
            scores, hits = mechanic_scores(text)
            total = sum(scores.values())
            if total:
                candidates.append({
                    "path": rel,
                    "memory_class": row.get("memory_class"),
                    "namespace": row.get("namespace"),
                    "score": total,
                    "axes": scores,
                    "hits": {k: v for k, v in hits.items() if v},
                    "sha256": actual_sha,
                })

    candidates.sort(key=lambda r: (-r["score"], r["path"]))
    dup_groups = [paths for paths in duplicate_hashes.values() if len(paths) > 1]
    dup_groups.sort(key=lambda g: (-len(g), g[0]))

    axis_file_counts = Counter()
    for row in candidates:
        for axis, score in row["axes"].items():
            if score:
                axis_file_counts[axis] += 1

    verdict = (
        "FULL_CURRENT_STRUCTURAL_INTEGRITY_AUDITED__SEMANTIC_MECHANICS_RANKED__AUTHORITY_UNCHANGED"
        if not errors
        else "FAIL_CLOSED_STRUCTURAL_INTEGRITY_ERROR"
    )

    return {
        "schema": "janus.hrain.trump_meta_registry_audit_receipt.v1",
        "terminal": verdict,
        "mode": "TRUMP_REGISTRY_AUDIT_ADAPTER_NOT_SAT_SOLVE",
        "source": {
            "repository": manifest.get("source_repository"),
            "catalog_source_commit": expected_source,
            "catalog_digest": manifest.get("catalog_digest"),
            "coverage_complete": coverage.get("coverage_complete"),
        },
        "integrity": {
            "shards_expected": manifest.get("sharding", {}).get("shard_count"),
            "shards_verified": shard_verified,
            "objects_expected": expected_objects,
            "objects_verified": verified,
            "bytes_verified": bytes_verified,
            "errors": errors,
        },
        "content_surface": {
            "json_parse_ok": json_ok,
            "json_parse_attention": json_failed,
            "memory_class_counts": dict(sorted(class_counts.items())),
            "namespace_counts": dict(sorted(namespace_counts.items())),
            "exact_duplicate_content_groups": len(dup_groups),
            "largest_duplicate_groups": dup_groups[:20],
        },
        "trump_mechanic_projection": {
            "axis_file_counts": dict(axis_file_counts),
            "candidate_file_count": len(candidates),
            "top_candidates": candidates[:top_n],
            "attention_flags": attention[:500],
            "attention_flag_count": len(attention),
            "interpretation_boundary": "Mechanic phrase matches are advisory retrieval candidates. They are not proofs, semantic equivalence claims, or scientific promotion."
        },
        "authority": {
            "proof_authority": False,
            "scientific_claim_promotion_authority": False,
            "command_authority": False,
            "registry_write_authority": False,
        },
        "scientific_boundary": {
            "TRUMP_finished": False,
            "polynomial_time_SAT_proved": False,
            "P_equals_NP_proved": False,
            "P_VS_NP": "OPEN",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog-dir", required=True, type=Path)
    ap.add_argument("--source-dir", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--top", type=int, default=100)
    args = ap.parse_args()
    result = audit(args.catalog_dir, args.source_dir, args.top)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "terminal": result["terminal"],
        "source_commit": result["source"]["catalog_source_commit"],
        "objects_expected": result["integrity"]["objects_expected"],
        "objects_verified": result["integrity"]["objects_verified"],
        "shards_verified": result["integrity"]["shards_verified"],
        "bytes_verified": result["integrity"]["bytes_verified"],
        "candidate_file_count": result["trump_mechanic_projection"]["candidate_file_count"],
        "axis_file_counts": result["trump_mechanic_projection"]["axis_file_counts"],
        "attention_flag_count": result["trump_mechanic_projection"]["attention_flag_count"],
        "P_VS_NP": result["scientific_boundary"]["P_VS_NP"],
    }, ensure_ascii=False, sort_keys=True))
    return 0 if not result["integrity"]["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
