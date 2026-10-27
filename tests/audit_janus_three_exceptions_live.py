#!/usr/bin/env python3
"""Read-only proof for the three exceptional public JSON blobs in a frozen JANUS atlas.

Source bytes are SHA/Git-blob checked, not changed. Normalized parse candidates
are diagnostic projections only, never a replacement source or TOPA verdict.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import janus_full_json_relations as rel

BROKEN_DEMI=("Hawkar-usls/Janus-Demiurge","Janus-Module-Registry-Expanded-v3.2.json")
BROKEN_RECEIPT=("Hawkar-usls/janus-meta-registry",
                "registry/myth_busted/MATHERSHIP-BIRTHDAY-ALIEN-FORENSICS-PUBLICATION-RECEIPT-v3.6.json")
LARGE_EYE=("Hawkar-usls/janus-meta-registry","EYE/generated/EYE-REGISTRY-INDEX.json")

def diagnostic():
    manifest,digest,records=rel.read_catalog(ROOT)
    by_pair={(r["repository"],r["path"]):r for r in records.values()}
    first=by_pair[BROKEN_DEMI]
    second=by_pair[BROKEN_RECEIPT]
    large=by_pair[LARGE_EYE]
    for item in (first,second,large):
        assert item["sourceCommit"] in item["sourceUrl"]
        assert item["deleteAllowed"] is False and item["readOnly"] is True
    assert rel.source_cap(first)==rel.SIZE_CAP
    assert rel.source_cap(second)==rel.SIZE_CAP
    assert rel.source_cap(large)==16_000_000
    assert 12_000_000 < large["sizeBytes"] <= rel.OVERSIZE_CAP

    # 1. Preserve raw source; repair is only a diagnostic projection.
    demi_body=rel.get_bytes(first)
    demi_text=demi_body.decode("utf-8")
    try:json.loads(demi_text)
    except json.JSONDecodeError as exc:
        assert "escape" in exc.msg.lower(),exc
    else:raise AssertionError("DEMI_SOURCE_ALREADY_VALID_DIFFERENT_PROVENANCE")
    rx=re.compile(r"\\U([0-9a-fA-F]{8})")
    locations=list(rx.finditer(demi_text))
    assert len(locations)==61,len(locations)
    candidate=rx.sub(lambda m:chr(int(m.group(1),16)),demi_text)
    patched=json.loads(candidate)
    assert set(patched)>={"meta","nodes","links"}
    demi={"rawBlobVerified":True,"rawJSONValid":False,
          "invalidUppercaseUnicodeEscapes":len(locations),
          "candidateParseValid":True,
          "candidateIsOriginal":False,
          "restoration":"DIAGNOSTIC_UNICODE_U8_TRANSCRIPTION_NOT_SOURCE_MUTATION",
          "nodeCount":len(patched["nodes"]),"linkCount":len(patched["links"])}

    # 2. Valid initial JSON was accidentally terminated one brace early;
    # check exact parse boundary and extra field before reconstructing.
    receipt_body=rel.get_bytes(second)
    receipt_text=receipt_body.decode("utf-8")
    decoder=json.JSONDecoder()
    first_obj,end=decoder.raw_decode(receipt_text)
    remaining=receipt_text[end:]
    assert set(first_obj)>={"execution_boundary","publication_commits"}
    assert receipt_text[end-1]=="}" and remaining.startswith(',"formal_rules":'),repr(remaining[:80])
    repaired=receipt_text[:end-1]+remaining
    final=json.loads(repaired)
    assert set(final)>={"formal_rules","next_gates","canonical_freeze"}
    assert len(final["formal_rules"])>=1
    receipt={"rawBlobVerified":True,"rawJSONValid":False,
             "prematureRootClosingBraceAt":end-1,
             "candidateParseValid":True,"candidateIsOriginal":False,
             "restoration":"DIAGNOSTIC_SINGLE_BRACE_REMOVAL_NOT_SOURCE_MUTATION",
             "normalizedRootKeys":len(final)}

    # 3. The current EYE blob is pinned to its frozen catalog commit and
    # Git blob SHA and is fully checked even when the generator rotates daily.
    large_scan=rel.scan(large)
    assert large_scan["status"]=="VERIFIED",large_scan  # Full traversal, no silent partial coverage
    if large.get("sourceSha256"):
        assert large_scan["sha256"]==large["sourceSha256"]
    assert large_scan["blob"]==large["gitBlobSha"]
    assert rel.source_cap({**large,"gitBlobSha":"invalid-sha"})==rel.SIZE_CAP
    assert rel.source_cap({**large,"sourceCommit":"0"*40})==rel.SIZE_CAP
    eye={"status":large_scan["status"],"byteCount":large["sizeBytes"],
         "sha256":large_scan["sha256"],
         "gitBlobSha":large["gitBlobSha"],
         "candidateReferences":len(large_scan.get("refs",[])),
         "sourceBytesVerified":True,"sourceDataMutated":False}
    return {"schema":"janus.three_json_exception_readonly_audit.v1",
            "status":"PASS_WITH_TWO_UNMODIFIED_MALFORMED_SOURCES",
            "frozenCatalogSha256":digest,"catalogObjects":manifest["jsonCount"],
            "invalidDemiurge":demi,"invalidMetaReceipt":receipt,
            "oversizeEye":eye,
            "evidenceLevels":{"verifiedSourceBytes":True,"rawMalformedJsonAdmitted":False,
                              "normalizedCandidateScientificTruth":False,
                              "topaAdjudication":"NOT_PERFORMED"}}

if __name__=="__main__":
    print(json.dumps(diagnostic(),ensure_ascii=False,sort_keys=True))
