#!/usr/bin/env python3
"""Deterministic gate for shared phallic mold/mandrel claims.

The gate is deliberately conservative. A pair is eligible for a shared-tooling
comparison only if both objects:
- belong to the same construction class,
- belong to the same material family,
- expose genital-specific length and width/diameter measurements.

A future SHARED_MANDREL candidate additionally requires close geometry plus a
manufacturing fingerprint (seam/fold/toolmark/socket evidence). Size alone is
never sufficient.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path


def _dims(obj):
    d = obj.get("genital_specific_dimensions_cm")
    if not isinstance(d, dict):
        return None
    length = d.get("length")
    width = d.get("width", d.get("height", d.get("thickness")))
    if not isinstance(length, (int, float)) or not isinstance(width, (int, float)):
        return None
    return float(length), float(width)


def eligible(a, b):
    return (
        a.get("construction_class") == b.get("construction_class")
        and a.get("material") == b.get("material")
        and _dims(a) is not None
        and _dims(b) is not None
    )


def rel_delta(x, y):
    return abs(x - y) / max(abs(x), abs(y))


def evaluate(data):
    objects = data["tests"]["PHALLIC_MANDREL_FORENSICS_PASS"]["objects"]
    pair_rows = []
    for a, b in itertools.combinations(objects, 2):
        row = {"a": a["id"], "b": b["id"], "eligible": eligible(a, b)}
        if row["eligible"]:
            da, db = _dims(a), _dims(b)
            row["relative_delta_length"] = rel_delta(da[0], db[0])
            row["relative_delta_width"] = rel_delta(da[1], db[1])
            fingerprints_a = set(a.get("manufacturing_fingerprints", []))
            fingerprints_b = set(b.get("manufacturing_fingerprints", []))
            row["shared_fingerprints"] = sorted(fingerprints_a & fingerprints_b)
            row["shared_mandrel_candidate"] = (
                row["relative_delta_length"] <= 0.02
                and row["relative_delta_width"] <= 0.02
                and bool(row["shared_fingerprints"])
            )
        pair_rows.append(row)

    eligible_rows = [r for r in pair_rows if r["eligible"]]
    candidates = [r for r in eligible_rows if r.get("shared_mandrel_candidate")]

    if candidates:
        status = "SHARED_MANDREL_CANDIDATE_REQUIRES_EXPERT_VALIDATION"
    elif eligible_rows:
        status = "NO_SHARED_MANDREL_SIGNAL_IN_ELIGIBLE_PAIRS"
    else:
        status = "BLOCKED_INSUFFICIENT_COMPARABLE_METROLOGY"

    return {
        "schema": "hrain.phallus_mandrel_gate.result.v1",
        "object_count": len(objects),
        "all_pairwise_combinations": len(pair_rows),
        "eligible_pair_count": len(eligible_rows),
        "shared_mandrel_candidate_count": len(candidates),
        "status": status,
        "rule": "SAME_SIZE != SAME_MOLD; SAME_MOLD != CAST_FROM_OSIRIS",
        "pairs": pair_rows,
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} INPUT_JSON")
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(evaluate(data), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
