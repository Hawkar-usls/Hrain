"""Offline fail-closed tests for JANUS public GitHub JSON constellation."""
import json
import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import janus_json_constellation as c

HASH="a"*40

def test_meta_catalog_only_verified_shards(monkeypatch):
    body={"schema":"janus.hrain.full_memory_shard.v1","source_commit":HASH,"object_count":2,
          "objects":[
            {"path":"data/alpha.json","git_blob_sha":"123","size_bytes":30,"sha256":"e"*64,"memory_class":"REGISTRY_OBJECT"},
            {"path":"README.md","git_blob_sha":"456","size_bytes":40,"memory_class":"DOCUMENT"}
          ]}
    content=c.encoded(body)
    manifest={
       "schema":"janus.hrain.full_memory_manifest.v1",
       "coverage":{"coverage_complete":True,"cataloged_blob_count":2},
       "authority":{"source_mutation_allowed":False},
       "source_commit":HASH,
       "sharding":{"shard_count":1,"shards":[{"index":0,"path":"assets/hrain-full-memory/shards/0000.json","object_count":2,"sha256":c.sha(content)}]}
    }
    def fetch(url):
        return c.encoded(manifest) if url==c.META_FULL_URL else content
    o=c.read_meta_catalog(fetch)
    assert o["sourceMode"]=="HASH_VERIFIED_FULL_CURRENT_META_REGISTRY"
    assert len(o["records"])==1
    assert o["records"][0]["path"]=="data/alpha.json"
    assert o["records"][0]["sourceSha256"]=="e"*64

def test_changed_meta_shard_hash_fails_closed():
    shard=c.encoded({"source_commit":HASH,"object_count":1,"objects":[{"path":"x.json"}]})
    manifest={"schema":"janus.hrain.full_memory_manifest.v1","coverage":{"coverage_complete":True,"cataloged_blob_count":1},
              "authority":{"source_mutation_allowed":False},"source_commit":HASH,
              "sharding":{"shard_count":1,"shards":[{"index":0,"path":"s.json","object_count":1,"sha256":"0"*64}]}}
    def fetch(url):return c.encoded(manifest) if url==c.META_FULL_URL else shard
    try:c.read_meta_catalog(fetch)
    except c.GateError as e:assert "SHARD_HASH_MISMATCH" in str(e)
    else:assert False,"Tampered meta shard must be rejected"

def test_only_explicitly_allowlisted_public_repo_is_readable():
    name="Hrain"; repo=c.OWNER+"/"+name
    def mock(url):
        if url.endswith("/commits/main"):return c.encoded({"sha":HASH})
        if "/git/trees/" in url:
            return c.encoded({"truncated":False,"tree":[
                {"type":"blob","path":"data/A.json","sha":"b"*40,"size":12},
                {"type":"blob","path":"assets/janus-json-atlas/shards/0000.json","sha":"b"*40,"size":12},
                {"type":"blob","path":"README.md","size":22}]})
        return c.encoded({"private":False,"archived":False,"default_branch":"main"})
    x=c.read_public_tree(name,mock)
    assert x["repository"]==repo
    assert len(x["records"])==1
    assert x["records"][0]["sourceUrl"]==f"https://github.com/{repo}/blob/{HASH}/data/A.json"
    try:c.read_public_tree("JanusMMORPG",mock)
    except c.GateError as e:assert "NOT_IN_STATIC_PUBLIC_ALLOWLIST" in str(e)
    else:assert False,"private repo name rejected"

def test_truncated_tree_and_private_repos_fail_closed():
    def private(url):return c.encoded({"private":True,"default_branch":"main"})
    try:c.read_public_tree("Hrain",private)
    except c.GateError as e:assert "ONLY_PUBLIC" in str(e)
    else:assert False
    def truncated(url):
        if url.endswith("/commits/main"):return c.encoded({"sha":HASH})
        if "/git/trees/" in url:return c.encoded({"truncated":True,"tree":[]})
        return c.encoded({"private":False,"archived":False,"default_branch":"main"})
    try:c.read_public_tree("Hrain",truncated)
    except c.GateError as e:assert "INCOMPLETE_REPOSITORY_TREE" in str(e)
    else:assert False

def test_assemble_exact_federation_and_hashes(tmp_path):
    repos=[c.REGISTRY]+[f"{c.OWNER}/{n}" for n in c.PUBLIC_REPOS]
    snapshots=[]
    for repo in repos:
        r=c.record(repo,"data/test.json",HASH,"b"*40,10)
        snapshots.append({"repository":repo,"commit":HASH,"records":[r],
                          "sourceMode":"FIXTURE","catalogCoverageComplete":True})
    manifest,groups=c.assemble(snapshots,"2026-10-26T12:00:00+00:00")
    c.validate(manifest,groups)
    assert manifest["jsonCount"]==len(repos)
    assert manifest["privateRepositoriesIncluded"] is False
    assert manifest["authority"]["writeAuthority"] is False
    c.write_index(tmp_path,manifest,groups)
    verified=json.loads((tmp_path/"manifest.json").read_text())
    assert verified["jsonCount"]==len(repos)
    assert all(c.sha((tmp_path/g["path"].replace("assets/janus-json-atlas/","")).read_bytes())==g["sha256"]
               for g in manifest["shards"])

def test_semantic_candidate_is_not_evidence_or_command():
    assert c.ROOT_AUTHORITY["scientificAuthority"] is False
    assert c.ROOT_AUTHORITY["semanticAssociationIsEvidence"] is False
    assert c.ROOT_AUTHORITY["deleteAllowed"] is False
    assert c.ROOT_AUTHORITY["sourceMutationAllowed"] is False
    assert c.ROOT_AUTHORITY["credentialRequiredInBrowser"] is False
