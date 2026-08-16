#!/usr/bin/env python3
"""Deterministic terracotta-phallus morphometry gate.

Claim ceiling:
- dimensional similarity is not same-mould proof;
- same mould is not proof of a master taken from Osiris;
- whole-figurine dimensions are never substituted for genital measurements.
"""
import json, itertools, sys
from pathlib import Path

def rel_diff(a, b):
    return abs(a-b)/((a+b)/2.0)

def main(inp, out):
    d=json.loads(Path(inp).read_text(encoding="utf-8"))
    core=[]
    allowed={
        "STANDALONE_OR_APPLIED_PHALLUS","SEPARATE_INSERT_PHALLUS",
        "STANDALONE_PHALLUS","PHALLUS_FRAGMENT","WINGED_PHALLUS"
    }
    for r in d["direct_audited_records"]:
        dims=r.get("dimensions_cm") or {}
        if r["class"] in allowed and "length" in dims and "transverse" in dims:
            core.append(r)
    pairs=[]
    for a,b in itertools.combinations(core,2):
        ad=a["dimensions_cm"]; bd=b["dimensions_cm"]
        ar=ad["length"]/ad["transverse"]; br=bd["length"]/bd["transverse"]
        lscale=bd["length"]/ad["length"]
        tscale=bd["transverse"]/ad["transverse"]
        pairs.append({
            "a":a["id"],"b":b["id"],
            "slenderness_a":ar,"slenderness_b":br,
            "slenderness_relative_difference":rel_diff(ar,br),
            "length_scale":lscale,"transverse_scale":tscale,
            "scale_consistency_difference":rel_diff(lscale,tscale),
            "axis_a":ad.get("axis_label"),"axis_b":bd.get("axis_label"),
        })
    pairs.sort(key=lambda x:x["scale_consistency_difference"])
    result={
        "schema":"hrain.terracotta_phallus_morphometry.result.v1",
        "core_metric_objects":len(core),
        "pair_count":len(pairs),
        "pairs":pairs,
        "decision":"NO_SHARED_MASTER_FORM_ADMITTED_FROM_DIMENSIONS_ALONE",
        "reason":"No pair has calibrated 3D genital geometry + homologous axis semantics + tooling/seam/fabric evidence."
    }
    Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":
    main(sys.argv[1],sys.argv[2])
