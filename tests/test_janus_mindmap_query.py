"""Source-verified offline JANUS agent memory navigation tests."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import janus_json_constellation as builder
import janus_mindmap_query as nav

COMMIT="a"*40

@pytest.fixture
def catalog(tmp_path):
    snapshots=[]
    for repo in [builder.REGISTRY]+[f"{builder.OWNER}/{name}" for name in builder.PUBLIC_REPOS]:
        paths=["data/rowan/fn1_structural_receipt.json","data/rowan/fn1_mutation_gate.json",
               "data/architecture/hrain_context.json"] if repo==builder.REGISTRY else [
                "data/rowan/fn1_mutation_predictions.json" if repo.endswith("/tranception") else "docs/other.json"]
        snap={"repository":repo,"commit":COMMIT,
              "records":[builder.record(repo,x,COMMIT,"c"*40,100) for x in paths],
              "sourceMode":"TEST_ONLY","catalogCoverageComplete":True}
        snapshots.append(snap)
    manifest,shards=builder.assemble(snapshots,"2026-10-26T10:00:00Z")
    builder.write_index(tmp_path,manifest,shards)
    return tmp_path

def test_search_and_canonical_pinned_link(catalog):
    m,rows=nav.load_catalog(catalog)
    out=nav.navigate(m,rows,query="fn1 Rowan",limit=10,related=4)
    assert out["status"]=="SOURCE_INDEX_VERIFIED_READ_ONLY"
    assert out["hits"]>=3
    assert out["focus"]["githubRef"].startswith("Hawkar-usls/")
    assert all("/blob/"+COMMIT+"/" in item["source"] for item in out["results"])
    assert out["registryWrites"]==0

def test_focus_and_path_based_candidates_are_not_evidence(catalog):
    m,rows=nav.load_catalog(catalog)
    focus=builder.REGISTRY+":data/rowan/fn1_mutation_gate.json"
    out=nav.navigate(m,rows,focus=focus,related=5)
    assert out["focus"]["githubRef"]==builder.REGISTRY+"@"+COMMIT+":data/rowan/fn1_mutation_gate.json"
    assert all(x["verifiedScientificRelation"] is False for x in out["mindmap"]["related"])
    assert all(x["truthAuthority"] is False for x in out["mindmap"]["edges"])

def test_tampered_shard_is_fail_closed(catalog):
    m,rows=nav.load_catalog(catalog)
    f=catalog/"shards/0000.json"
    f.write_bytes(f.read_bytes()+b"\n")
    with pytest.raises(nav.Hold,match="SHARD_SHA256_MISMATCH"):nav.load_catalog(catalog)

def test_private_repo_and_nonexistent_focus_never_resolved(catalog):
    m,rows=nav.load_catalog(catalog)
    with pytest.raises(nav.Hold,match="FOCUS_SOURCE_NOT_INDEXED"):
        nav.navigate(m,rows,focus="Hawkar-usls/JanusMMORPG:secrets.json")
    assert all(x["repository"]!="Hawkar-usls/JanusMMORPG" for x in rows)

def test_no_argument_abuse_or_mutation():
    with pytest.raises(nav.Hold,match="UNBOUNDED_NAVIGATION_REQUEST"):
        nav.navigate({"generatedAt":"now","repositoryCount":1,"jsonCount":1},[],limit=10**9)
    assert all("sourceMutation" not in name for name in dir(nav))

def test_remote_catalog_pins_every_shard_to_one_immutable_manifest_commit(catalog):
    import json
    calls=[]
    def get(url):
        calls.append(url)
        if url==nav.ATLAS_REVISION_API:
            return json.dumps([{"sha":COMMIT}]).encode("utf8")
        prefix=f"https://raw.githubusercontent.com/Hawkar-usls/Hrain/{COMMIT}/assets/janus-json-atlas/"
        assert url.startswith(prefix), "mutable main ref forbidden"
        return (catalog/url[len(prefix):]).read_bytes()
    manifest,records=nav.load_catalog(fetch=get)
    assert manifest["catalogRevision"]==COMMIT
    assert len(records)==manifest["jsonCount"]
    assert all("/main/assets/janus-json-atlas/" not in call for call in calls)

def test_remote_catalog_api_missing_commit_fails_closed(catalog):
    def get(url):
        assert url==nav.ATLAS_REVISION_API
        return b"[]"
    with pytest.raises(nav.Hold,match="ATLAS_COMMIT_PIN_UNAVAILABLE"):
        nav.load_catalog(fetch=get)
