from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "hrain.inverse_semantic_oracle.v1"


def load_case(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"Unsupported schema: {data.get('schema')!r}")
    if not data.get("nodes"):
        raise ValueError("nodes are required")
    return data


def _source_entities(case: dict[str, Any], domain: str) -> set[str]:
    out: set[str] = set()
    for node in case["nodes"]:
        if node.get("domain") == domain and node.get("evidence_state") == "SOURCE_BOUND":
            out.update(node.get("entities", []))
    return out


def analyze(case: dict[str, Any]) -> dict[str, Any]:
    custody = _source_entities(case, "CUSTODY")
    recovery = _source_entities(case, "RECOVERY")
    intersection = sorted(custody & recovery)
    entity_types = case.get("entity_types", {})
    named_agent_bridge = sorted(
        entity for entity in intersection if entity_types.get(entity) == "DIVINE_AGENT"
    )

    source_node_ids = {
        node["id"] for node in case["nodes"] if node.get("evidence_state") == "SOURCE_BOUND"
    }
    claims = []
    for claim in case.get("target_claims", []):
        support = [node_id for node_id in claim.get("support_node_ids", []) if node_id in source_node_ids]
        contradiction = [node_id for node_id in claim.get("contradiction_node_ids", []) if node_id in source_node_ids]
        if support and contradiction:
            state = "CONTESTED"
        elif support:
            state = "SUPPORTED_BY_BOUND_SOURCES"
        elif contradiction:
            state = "CONTRADICTED_BY_BOUND_SOURCES"
        else:
            state = "UNRESOLVED"
        claims.append({
            "claim_id": claim["claim_id"],
            "state": state,
            "support_node_ids": support,
            "contradiction_node_ids": contradiction,
        })

    return {
        "schema": "hrain.inverse_semantic_oracle.result.v1",
        "case_id": case["case_id"],
        "source_bound_intersection_entities": intersection,
        "first_named_agent_bridge": named_agent_bridge,
        "custody_domain_entities": sorted(custody),
        "recovery_domain_entities": sorted(recovery),
        "target_claims": claims,
        "last_source_bound_witness_before_sobek_phallus_search": None,
        "last_witness_status": "NOT_ESTABLISHED_BECAUSE_PHALLUS_SPECIFIC_SOBEK_SEARCH_IS_NOT_SOURCE_BOUND",
        "sobek_failure_accusation": "NOT_ADMITTED",
        "sobek_competence_signal": "SUPPORTED_IN_WATER_RECOVERY_CONTEXT",
        "custody_handoff_status": "UNRESOLVED",
        "search_consequence": (
            "Prioritize the named bridge agents DUAMUTEF and QEBEHSENUEF, then trace their "
            "Osiris-protection/reassembly contexts toward Anubis-associated embalming, chests, "
            "shrines, sealed or nested objects, while separately tracing Sobek's water-recovery "
            "context. Do not infer phallus custody without a source or object."
        ),
        "claim_ceiling": (
            "The graph can reject an unsupported failure accusation against Sobek in the "
            "source-bound model, but it cannot prove innocence, supernatural testimony, phallus "
            "custody, or that the Book of the Dead was physically authored backwards."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a source-bound HRain inverse semantic graph pass.")
    parser.add_argument("case", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(load_case(args.case))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
