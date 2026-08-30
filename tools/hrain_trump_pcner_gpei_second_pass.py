#!/usr/bin/env python3
"""HRAiN + TRUMP PCNER_GPEI second-pass red-team.

Pipeline:
  ranked mechanic candidate
  -> canonical formula translation
  -> required-assumption audit
  -> conditional SAT-transfer gate
  -> generic counterexample attacks

This is deliberately fail-closed.  It does not execute TRUMP's CNF solver on
registry JSON and it cannot promote a theorem.  A candidate that survives is
only a conditional route candidate whose universal premise still needs proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

SCHEMA = "janus.hrain.trump_pcner_gpei_second_pass_receipt.v1"
TERMINAL = "PCNER_GPEI_SECOND_PASS_COMPLETE__CONDITIONAL_SURVIVORS_ONLY__P_VS_NP_OPEN"

FORMULAS = {
    "POLY_FIND": "forall reachable nonterminal S: exists canonical exact action a, Discover(S,a) <= N^d for one fixed d",
    "POLY_HOLD": "forall reachable t: Size(S_t)+Rep_t+Cert_t+Aux_t+Debt_t <= N^c for one fixed c measured against original N",
    "POLY_ADVANCE": "for every committed step: Sem(S_t)=SemStep(S_t,S_t+1) and mu(S_t+1)<mu(S_t), mu(S_0)<=N^k, normalization microsteps <= N^q",
    "EXACTNESS_CERTIFICATION": "every committed transition has independent exact replay/certificate verification with verifier work and bytes <= N^v",
    "DEBT_RESOURCE_ACCOUNTING": "all discovery failures, representation growth, deferred work, proof bytes, verification, recovery, switching and normalization are charged",
    "PCNER_GPEI": "POLY_FIND and POLY_HOLD and POLY_ADVANCE and EXACTNESS_CERTIFICATION and DEBT_RESOURCE_ACCOUNTING under one frozen deterministic arbitrary-CNF algorithm",
}

ASSUMPTION_RULES = {
    "FIXED_DETERMINISTIC_ALGORITHM": (
        "frozen algorithm", "fixed algorithm", "one fixed deterministic", "before the input", "before input",
    ),
    "ARBITRARY_CNF_SCOPE": (
        "arbitrary cnf", "arbitrary-cnf", "every cnf", "for every cnf", "sat_in_p", "sat is in p",
    ),
    "POLYNOMIAL_DISCOVERY": (
        "discovery", "discover", "recognition", "recognizer", "recognize", "selector",
    ),
    "ORIGINAL_N_POLYNOMIAL_ENVELOPE": (
        "gpei", "global polynomial envelope", "polynomial envelope", "original input length n", "original-n", "b(n)=n^",
    ),
    "STRICT_WELL_FOUNDED_PROGRESS": (
        "strict progress", "well-founded", "strictly decreases", "strict decrease", "step count", "macrosteps",
    ),
    "EXACT_DECISION_PRESERVATION": (
        "exact", "decision-preserving", "contextual semantics", "semantic equivalence", "exact existential",
    ),
    "INDEPENDENT_CERTIFICATE_REPLAY": (
        "independent replay", "independent deterministic verification", "certificate", "proof-carrying", "replay",
    ),
    "HIDDEN_DEBT_CHARGED": (
        "hidden debt", "charge all hidden debt", "debt", "resource ledger", "proof bytes", "verification work", "recovery debt",
    ),
    "POLYNOMIAL_MICRO_NORMALIZATION": (
        "microstep", "micro-normalization", "normalization microsteps", "polynomial normalization",
    ),
    "POLYNOMIAL_VERIFIER_WORK": (
        "verifier work", "verification work", "verification are bounded", "certificate and verifier work", "verification under one fixed exponent",
    ),
    "TRACTABLE_TERMINAL_QUERY": (
        "terminal truth", "terminal representation", "terminal truth query", "polynomial-time truth", "tractable terminal", "terminal decision",
    ),
    "SCOPE_DISCIPLINE": (
        "finite test not theorem", "finite probes", "scope discipline", "remains scoped", "universal bridge",
    ),
}

CRITICAL_ASSUMPTIONS = [
    "FIXED_DETERMINISTIC_ALGORITHM",
    "ARBITRARY_CNF_SCOPE",
    "POLYNOMIAL_DISCOVERY",
    "ORIGINAL_N_POLYNOMIAL_ENVELOPE",
    "STRICT_WELL_FOUNDED_PROGRESS",
    "EXACT_DECISION_PRESERVATION",
    "INDEPENDENT_CERTIFICATE_REPLAY",
    "HIDDEN_DEBT_CHARGED",
    "POLYNOMIAL_MICRO_NORMALIZATION",
    "POLYNOMIAL_VERIFIER_WORK",
    "TRACTABLE_TERMINAL_QUERY",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def flatten_strings(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            out.append(str(k))
            out.extend(flatten_strings(v))
    elif isinstance(value, list):
        for item in value:
            out.extend(flatten_strings(item))
    elif isinstance(value, (str, int, float, bool)) or value is None:
        out.append(str(value))
    return out


def text_surface(data: bytes, path: str) -> tuple[str, str]:
    raw = data.decode("utf-8", errors="replace")
    if path.endswith(".json"):
        try:
            obj = json.loads(raw)
            return "\n".join(flatten_strings(obj)).lower(), "JSON_STRUCTURAL_TEXT"
        except json.JSONDecodeError:
            return raw.lower(), "RAW_TEXT_JSON_PARSE_FAILED"
    return raw.lower(), "RAW_TEXT"


def has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(n in text for n in needles)


def assumption_evidence(text: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, needles in ASSUMPTION_RULES.items():
        hits = [n for n in needles if n in text]
        result[name] = {"present": bool(hits), "signals": hits[:8]}

    # POLYNOMIAL_DISCOVERY needs both a discovery-like primitive and an explicit
    # polynomial/resource-bound context; keyword presence alone is insufficient.
    discovery = result["POLYNOMIAL_DISCOVERY"]
    discovery["present"] = discovery["present"] and ("polynomial" in text or "fixed exponent" in text or "charged" in text)

    # Strict progress needs a progress primitive plus a bound/termination signal.
    progress = result["STRICT_WELL_FOUNDED_PROGRESS"]
    progress["present"] = progress["present"] and (
        "termination" in text or "step count" in text or "macrosteps" in text or "bounded" in text
    )

    # Exact certificate replay must show exactness and a checking mechanism.
    replay = result["INDEPENDENT_CERTIFICATE_REPLAY"]
    replay["present"] = replay["present"] and (
        "exact" in text and ("verification" in text or "verify" in text or "replay" in text)
    )

    # Terminal tractability needs terminal plus polynomial/tractable context.
    terminal = result["TRACTABLE_TERMINAL_QUERY"]
    terminal["present"] = terminal["present"] and ("polynomial" in text or "tractable" in text)
    return result


def formula_terms_from_axes(axes: dict[str, int]) -> list[str]:
    terms = [name for name in ("POLY_FIND", "POLY_HOLD", "POLY_ADVANCE", "EXACTNESS_CERTIFICATION", "DEBT_RESOURCE_ACCOUNTING") if axes.get(name, 0) > 0]
    return terms


def generic_attack_library() -> list[dict[str, Any]]:
    n = 4
    steps = 8
    exponent = 2 ** steps
    digits = math.floor(exponent * math.log10(n)) + 1
    return [
        {
            "id": "ITERATED_LOCAL_POLY_BLOWUP",
            "witness": f"s0=N, s(i+1)=s(i)^2; with N={n}, after {steps} locally quadratic steps s=N^{exponent}, about {digits} decimal digits",
            "kills": "LOCAL_POLY_IMPLIES_GLOBAL_POLY",
        },
        {
            "id": "DISCOVERY_VS_VERIFICATION_GAP",
            "witness": "A short exact certificate may be cheap to verify while locating one among exponentially many candidates remains unbounded unless discovery is separately charged.",
            "kills": "EXISTS_CHEAP_CERTIFICATE_IMPLIES_CHEAP_ALGORITHM",
        },
        {
            "id": "COMPACT_REPRESENTATION_VS_OPERATIONAL_DEBT",
            "witness": "A small deferred representation can encode an operation whose later exact evaluation enumerates 2^k extensions; at k=20 that is 1,048,576 extensions.",
            "kills": "SMALL_IR_IMPLIES_CHEAP_FUTURE",
        },
        {
            "id": "STRICT_PROGRESS_WITH_EXPONENTIAL_INITIAL_POTENTIAL",
            "witness": "Strict decrement alone is insufficient: mu(S0)=2^N and mu decreases by one gives exponentially many committed steps.",
            "kills": "STRICT_PROGRESS_IMPLIES_POLY_STEP_COUNT",
        },
        {
            "id": "MACRO_PROGRESS_WITH_UNBOUNDED_MICRO_NORMALIZATION",
            "witness": "A macrostep can decrease a rank while its internal normalizer loops or performs superpolynomially many rewrites unless a microstep bound is proved.",
            "kills": "MACRO_PROGRESS_IMPLIES_POLY_RUNTIME",
        },
        {
            "id": "CERTIFICATE_EXISTS_WITH_UNCHARGED_VERIFIER_BYTES",
            "witness": "Certificate existence is not free: proof bytes and deterministic checking work must be included in the original-N budget.",
            "kills": "PROOF_OBJECT_EXISTS_IMPLIES_CHEAP_CERTIFICATION",
        },
        {
            "id": "FAMILY_SCOPE_TO_UNIVERSAL_SCOPE_LEAP",
            "witness": "A lane proved for a recognized tractable family does not transfer to arbitrary CNF without a polynomial recognizer/reduction and a universal composition bridge.",
            "kills": "FAMILY_ROUTE_IMPLIES_GENERAL_SAT_ROUTE",
        },
        {
            "id": "DEFERRED_WORK_WRAPPER_DEBT",
            "witness": "Deferring exact work preserves representation size only if the future operation cost is booked as debt and later discharged within the same global envelope.",
            "kills": "DEFERRED_WORK_DISAPPEARS",
        },
    ]


def attack_candidate(text: str, assumptions: dict[str, dict[str, Any]], axes: dict[str, int]) -> list[dict[str, str]]:
    attacks: list[dict[str, str]] = []

    def missing(name: str) -> bool:
        return not assumptions[name]["present"]

    if ("local polynomial" in text or "polynomial in current" in text or "current state size" in text) and missing("ORIGINAL_N_POLYNOMIAL_ENVELOPE"):
        attacks.append({"id": "ITERATED_LOCAL_POLY_BLOWUP", "reason": "local/current-size polynomiality appears without an original-N invariant"})
    if axes.get("EXACTNESS_CERTIFICATION", 0) and missing("POLYNOMIAL_DISCOVERY"):
        attacks.append({"id": "DISCOVERY_VS_VERIFICATION_GAP", "reason": "certificate/exactness signals exist but polynomial discovery is not established"})
    if ("compression" in text or "quotient" in text or "representation" in text) and missing("TRACTABLE_TERMINAL_QUERY"):
        attacks.append({"id": "COMPACT_REPRESENTATION_VS_OPERATIONAL_DEBT", "reason": "representation compression appears without an explicit tractable terminal interface"})
    if axes.get("POLY_ADVANCE", 0) and missing("STRICT_WELL_FOUNDED_PROGRESS"):
        attacks.append({"id": "STRICT_PROGRESS_WITH_EXPONENTIAL_INITIAL_POTENTIAL", "reason": "advance/progress signals lack a sufficiently explicit bounded well-founded schedule"})
    if axes.get("POLY_ADVANCE", 0) and missing("POLYNOMIAL_MICRO_NORMALIZATION"):
        attacks.append({"id": "MACRO_PROGRESS_WITH_UNBOUNDED_MICRO_NORMALIZATION", "reason": "macro progress does not establish polynomial normalization microsteps"})
    if axes.get("EXACTNESS_CERTIFICATION", 0) and missing("POLYNOMIAL_VERIFIER_WORK"):
        attacks.append({"id": "CERTIFICATE_EXISTS_WITH_UNCHARGED_VERIFIER_BYTES", "reason": "exact/certificate surface lacks an explicit polynomial verifier-work obligation"})
    if missing("ARBITRARY_CNF_SCOPE"):
        attacks.append({"id": "FAMILY_SCOPE_TO_UNIVERSAL_SCOPE_LEAP", "reason": "arbitrary-CNF universal scope is not explicit"})
    if ("deferred" in text or "lazy" in text or "exists_set" in text or "opaque exists" in text) and missing("HIDDEN_DEBT_CHARGED"):
        attacks.append({"id": "DEFERRED_WORK_WRAPPER_DEBT", "reason": "deferred/lazy work appears without explicit debt accounting"})
    return attacks


def candidate_terminal(assumptions: dict[str, dict[str, Any]], attacks: list[dict[str, str]], terms: list[str]) -> tuple[str, list[str]]:
    if len(terms) < 2:
        return "INSUFFICIENT_SEMANTIC_SIGNAL", []
    missing = [name for name in CRITICAL_ASSUMPTIONS if not assumptions[name]["present"]]
    if "ARBITRARY_CNF_SCOPE" in missing:
        return "TRANSFER_BLOCKED_SCOPE", missing
    if missing:
        return "TRANSFER_BLOCKED_MISSING_ASSUMPTIONS", missing
    if attacks:
        return "COUNTEREXAMPLE_ATTACK_FOUND", []
    return "CONDITIONAL_ROUTE_SURVIVOR_NOT_THEOREM", []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first-pass", required=True)
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--limit", type=int, default=150)
    args = ap.parse_args()

    first = json.loads(Path(args.first_pass).read_text(encoding="utf-8"))
    source_dir = Path(args.source_dir)
    candidates = first["trump_mechanic_projection"]["top_candidates"][: max(1, args.limit)]

    rows: list[dict[str, Any]] = []
    integrity_errors: list[dict[str, str]] = []
    terminal_counts: dict[str, int] = {}

    for rank, cand in enumerate(candidates, 1):
        rel = cand["path"]
        p = source_dir / rel
        if not p.exists() or not p.is_file():
            integrity_errors.append({"path": rel, "error": "SOURCE_FILE_MISSING"})
            continue
        data = p.read_bytes()
        actual = sha256(data)
        expected = cand.get("sha256")
        if expected and actual != expected:
            integrity_errors.append({"path": rel, "error": "SOURCE_SHA256_MISMATCH"})
            continue

        text, parse_mode = text_surface(data, rel)
        assumptions = assumption_evidence(text)
        axes = cand.get("axes", {})
        terms = formula_terms_from_axes(axes)
        attacks = attack_candidate(text, assumptions, axes)
        terminal, missing = candidate_terminal(assumptions, attacks, terms)
        terminal_counts[terminal] = terminal_counts.get(terminal, 0) + 1

        rows.append({
            "rank": rank,
            "path": rel,
            "source_sha256": actual,
            "first_pass_score": cand.get("score", 0),
            "first_pass_axes": axes,
            "parse_mode": parse_mode,
            "mechanic": {
                "instantiated_terms": terms,
                "interpretation": "Terms are canonical audit translations triggered by source mechanics; they are not quoted or asserted as the source's proved theorem."
            },
            "formula": {
                "terms": {name: FORMULAS[name] for name in terms},
                "pcner_gpei_candidate_formula": FORMULAS["PCNER_GPEI"] if len(terms) == 5 else None,
                "status": "AUDIT_TRANSLATION_ONLY"
            },
            "required_assumptions": assumptions,
            "sat_transfer_test": {
                "terminal": terminal,
                "missing_critical_assumptions": missing,
                "conditional_implication": "If all universal PCNER_GPEI premises are independently proved for one fixed arbitrary-CNF algorithm and an exact polynomial terminal query, SAT is in P.",
                "universal_premise_proved_here": False
            },
            "counterexample_attack": {
                "attack_count": len(attacks),
                "attacks": attacks,
                "survival_is_universal_proof": False
            },
        })

    survivors = [r for r in rows if r["sat_transfer_test"]["terminal"] == "CONDITIONAL_ROUTE_SURVIVOR_NOT_THEOREM"]
    attack_found = [r for r in rows if r["counterexample_attack"]["attack_count"] > 0]

    out = {
        "schema": SCHEMA,
        "terminal": TERMINAL,
        "mode": "MECHANIC_TO_FORMULA_TO_ASSUMPTIONS_TO_SAT_TRANSFER_TO_COUNTEREXAMPLE_ATTACK",
        "source": {
            "repository": first["source"]["repository"],
            "source_commit": first["source"]["catalog_source_commit"],
            "catalog_digest": first["source"]["catalog_digest"],
            "first_pass_terminal": first["terminal"],
            "ranked_candidates_requested": args.limit,
            "ranked_candidates_processed": len(rows),
        },
        "integrity": {
            "errors": integrity_errors,
            "all_candidate_hashes_match": not integrity_errors,
        },
        "canonical_formula_translation": FORMULAS,
        "counterexample_library": generic_attack_library(),
        "summary": {
            "terminal_counts": terminal_counts,
            "conditional_survivor_count": len(survivors),
            "counterexample_attack_candidate_count": len(attack_found),
            "survivor_paths": [r["path"] for r in survivors],
            "highest_ranked_survivors": [
                {"rank": r["rank"], "path": r["path"], "first_pass_score": r["first_pass_score"]}
                for r in survivors[:20]
            ],
        },
        "candidates": rows,
        "authority": {
            "proof_authority": False,
            "scientific_claim_promotion_authority": False,
            "command_authority": False,
            "registry_write_authority": False,
        },
        "hard_firewalls": [
            "MECHANIC_MATCH != FORMULA_PROOF",
            "FORMULA_TRANSLATION != SOURCE_THEOREM",
            "SAT_TRANSFER_CONDITIONAL != SAT_IN_P_PROOF",
            "FINITE_COUNTEREXAMPLE_SURVIVAL != UNIVERSAL_PROOF",
            "COUNTEREXAMPLE_TO_ONE_ROUTE != SAT_HARDNESS_PROOF",
            "UNKNOWN_IS_NOT_PASS",
        ],
        "scientific_boundary": {
            "TRUMP_finished": False,
            "polynomial_time_SAT_proved": False,
            "P_equals_NP_proved": False,
            "P_VS_NP": "OPEN",
        },
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "terminal": TERMINAL,
        "processed": len(rows),
        "integrity_errors": len(integrity_errors),
        "terminal_counts": terminal_counts,
        "conditional_survivors": len(survivors),
        "attack_candidates": len(attack_found),
        "P_VS_NP": "OPEN",
    }, ensure_ascii=False, sort_keys=True))
    return 0 if not integrity_errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
