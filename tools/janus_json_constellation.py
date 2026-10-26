#!/usr/bin/env python3
"""JANUS/HRAiN/iNaiHR public GitHub JSON constellation; metadata only.

Consumes the existing SHA-verified Meta Registry FULL_CURRENT shard catalog and
the pinned Git trees of an explicit allowlist of PUBLIC JANUS repositories.
Does not fetch contents of foreign JSONs, access private repos, infer facts,
grant command/write authority, or rewrite existing HRAiN/iNaiHR workspaces.

The output is immutable, hash-verified browser-readable navigation metadata.
HRAiN is structural context; iNaiHR may propose ASSOCIATIONS, never evidence.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen

OWNER = "Hawkar-usls"
REGISTRY = f"{OWNER}/janus-meta-registry"
PUBLIC_REPOS = (
    "Hrain", "iNaiHR", "Janus", "Janus_Genesis", "Janus-Demiurge",
    "Janus-Fundamentum", "TOPA", "Janus-Cosmos", "aura-oracle-tg",
    "tranception", "janus-lapis", "janus-distributed-ai-swarm",
    "Janus-HELIOS",
)
EXCLUDED_PREFIXES = ("assets/janus-json-atlas/",)
META_FULL_URL = (
    f"https://raw.githubusercontent.com/{REGISTRY}/main/"
    "assets/hrain-full-memory/manifest.json"
)
META_RAW = f"https://raw.githubusercontent.com/{REGISTRY}/main/"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "assets/janus-json-atlas"
SHARD_SIZE = 250
MAX_READ = 18_000_000
SCHEMA = "janus.hrain.github_json_constellation_manifest.v1"
ROOT_AUTHORITY = {
    "readOnly": True,
    "sourceMutationAllowed": False,
    "deleteAllowed": False,
    "writeAuthority": False,
    "scientificAuthority": False,
    "semanticAssociationIsEvidence": False,
    "credentialRequiredInBrowser": False,
}

class GateError(RuntimeError):
    pass

def encoded(data):
    return (json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_url(url):
    if not (url.startswith("https://raw.githubusercontent.com/") or url.startswith("https://api.github.com/")):
        raise GateError("URL_NOT_ALLOWLISTED")
    headers={"Accept":"application/vnd.github+json","User-Agent":"JANUS-public-json-readonly/1"}
    token=os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"]="Bearer "+token
    req=Request(url,headers=headers)
    try:
        with urlopen(req,timeout=40) as resp: body=resp.read(MAX_READ+1)
    except Exception as exc:
        raise GateError("PUBLIC_SOURCE_UNAVAILABLE:"+url) from exc
    if len(body)>MAX_READ:raise GateError("UNBOUNDED_PUBLIC_SOURCE")
    return body

def get_json(url):
    try: return json.loads(read_url(url))
    except (ValueError,UnicodeError) as exc: raise GateError("INVALID_REMOTE_JSON:"+url) from exc

def record(repo,path,commit,blob_sha,size,sha256=None,memory_class=None):
    if not path.endswith(".json") or path.startswith(EXCLUDED_PREFIXES):
        raise GateError("NON_JSON_OR_RECURSIVE_INDEX")
    if not repo.startswith(f"{OWNER}/") or "/" not in path and not path:
        raise GateError("INVALID_SOURCE_REPOSITORY_OR_PATH")
    if not (len(commit)==40 and all(c in "0123456789abcdef" for c in commit)):
        raise GateError("SOURCE_COMMIT_INVALID")
    url=f"https://github.com/{repo}/blob/{commit}/{quote(path,safe='/')}"
    return {
        "id":"json:"+sha((repo+"\n"+path).encode())[:24],
        "repository":repo,
        "path":path,
        "sourceCommit":commit,
        "gitBlobSha":blob_sha,
        "sourceSha256":sha256,
        "sizeBytes":size,
        "memoryClass":memory_class or "PUBLIC_JSON",
        "sourceUrl":url,
        "readOnly":True,
        "deleteAllowed":False,
        "authority":"SOURCE_METADATA_ONLY",
    }

def read_meta_catalog(fetch=read_url):
    raw=fetch(META_FULL_URL)
    manifest=json.loads(raw)
    if (manifest.get("schema")!="janus.hrain.full_memory_manifest.v1"
        or manifest.get("coverage",{}).get("coverage_complete") is not True
        or manifest.get("authority",{}).get("source_mutation_allowed") is not False):
        raise GateError("META_FULL_MEMORY_MANIFEST_INCOMPLETE_OR_AUTHORITY_INVALID")
    commit=manifest.get("source_commit","")
    if len(commit)!=40:raise GateError("META_COMMIT_MISSING")
    shards=manifest.get("sharding",{}).get("shards") or []
    if len(shards)!=manifest["sharding"]["shard_count"]:raise GateError("META_SHARDS_INCOMPLETE")
    def load_one(s):
        uri=META_RAW+s["path"]
        data=fetch(uri)
        if sha(data)!=s["sha256"]:raise GateError("META_SHARD_HASH_MISMATCH:"+s["path"])
        content=json.loads(data)
        if (content.get("source_commit")!=commit
            or content.get("object_count")!=s["object_count"]
            or len(content.get("objects",[]))!=s["object_count"]):
            raise GateError("META_SHARD_OBJECT_COUNT_OR_COMMIT_MISMATCH")
        return s["index"],content["objects"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        chunks=sorted(pool.map(load_one,shards))
    rawrecords=[o for _,items in chunks for o in items]
    if len(rawrecords)!=manifest["coverage"]["cataloged_blob_count"]:
        raise GateError("META_CATALOG_COVERAGE_MISMATCH")
    records=[
        record(REGISTRY,o["path"],commit,o["git_blob_sha"],o["size_bytes"],
               sha256=o.get("sha256"),memory_class=o.get("memory_class"))
        for o in rawrecords if o.get("path","").endswith(".json")
        and not o["path"].startswith(EXCLUDED_PREFIXES)
    ]
    return {"repository":REGISTRY,"commit":commit,"records":records,
            "sourceMode":"HASH_VERIFIED_FULL_CURRENT_META_REGISTRY",
            "catalogCoverageComplete":True}

def read_public_tree(name,fetch=read_url):
    if name not in PUBLIC_REPOS:raise GateError("REPOSITORY_NOT_IN_STATIC_PUBLIC_ALLOWLIST")
    repo=f"{OWNER}/{name}"
    base=f"https://api.github.com/repos/{repo}"
    metadata=json.loads(fetch(base))
    if metadata.get("private") is not False or metadata.get("archived") is True:
        raise GateError("ONLY_PUBLIC_ACTIVE_REPOSITORY_ALLOWED:"+repo)
    branch=metadata.get("default_branch")
    if not branch:raise GateError("MISSING_DEFAULT_BRANCH:"+repo)
    revision=json.loads(fetch(base+"/commits/"+quote(branch,safe="")))
    commit=revision.get("sha","")
    if len(commit)!=40:raise GateError("UNPINNED_PUBLIC_TREE_COMMIT:"+repo)
    tree=json.loads(fetch(base+"/git/trees/"+commit+"?recursive=1"))
    if tree.get("truncated") is not False or not isinstance(tree.get("tree"),list):
        raise GateError("INCOMPLETE_REPOSITORY_TREE:"+repo)
    records=[
        record(repo,o["path"],commit,o.get("sha"),o.get("size",0))
        for o in tree["tree"] if o.get("type")=="blob"
        and isinstance(o.get("path"),str) and o["path"].endswith(".json")
        and not o["path"].startswith(EXCLUDED_PREFIXES)
    ]
    return {"repository":repo,"commit":commit,"records":records,
            "sourceMode":"GITHUB_PUBLIC_COMMIT_PINNED_TREE",
            "catalogCoverageComplete":True}

def assemble(snapshots,now):
    names={o["repository"] for o in snapshots}
    expected={REGISTRY}|{f"{OWNER}/{n}" for n in PUBLIC_REPOS}
    if names!=expected:raise GateError("REPOSITORY_ALLOWLIST_NOT_FULLY_SCANNED")
    records=[]
    scopes=[]
    for snap in sorted(snapshots,key=lambda o:o["repository"]):
        local=sorted(snap["records"],key=lambda x:x["path"])
        if len({x["id"] for x in local})!=len(local):raise GateError("DUPLICATE_ID_WITHIN_REPO")
        records.extend(local)
        scopes.append({
            "repository":snap["repository"],
            "commit":snap["commit"],
            "jsonCount":len(local),
            "sourceMode":snap["sourceMode"],
            "complete":snap["catalogCoverageComplete"],
        })
    if len({r["id"] for r in records})!=len(records):raise GateError("DUPLICATE_GRAPH_NODE_ID")
    grouped=[]
    for scope in scopes:
        repo=scope["repository"]
        obj=[x for x in records if x["repository"]==repo]
        for i in range(0,len(obj),SHARD_SIZE):
            seq=len(grouped)
            name=f"shards/{seq:04d}.json"
            data=encoded({
                "schema":"janus.hrain.github_json_constellation_shard.v1",
                "repository":repo,
                "sourceCommit":scope["commit"],
                "records":obj[i:i+SHARD_SIZE],
                "readOnly":True,
            })
            grouped.append((name,data,{
                "index":seq,"path":"assets/janus-json-atlas/"+name,
                "repository":repo,"count":len(obj[i:i+SHARD_SIZE]),
                "sha256":sha(data),
            }))
    manifest={
        "schema":SCHEMA,
        "status":"READ_ONLY_SOURCE_PINNED_PUBLIC_JSON_NAVIGATION_SNAPSHOT",
        "generatedAt":now,
        "root":"JANUS",
        "repositoryCount":len(scopes),
        "jsonCount":len(records),
        "shardCount":len(grouped),
        "sourceCoverage":"EXACTLY_ALLOWLISTED_PUBLIC_REPOSITORY_CURRENT_TREE_AND_VERIFIED_META_SHARDS",
        "privateRepositoriesIncluded":False,
        "historicalGitVersionsIncluded":False,
        "metadataOnly":True,
        "authority":dict(ROOT_AUTHORITY),
        "repositories":scopes,
        "shards":[x[2] for x in grouped],
        "mindmapRoles":{"HRAiN":"STRUCTURAL_CONTEXT",
                        "iNaiHR":"ASSOCIATIVE_CANDIDATES_ONLY",
                        "JANUS":"READ_ONLY_RETRIEVAL_ORCHESTRATOR",
                        "MetaRegistry":"AUTHORITATIVE_SOURCE_DATA"},
        "epistemicCeilings":[
           "GITHUB_FILE_PRESENT != SCIENTIFIC_TRUTH",
           "SEMANTIC_SIMILARITY != EVIDENCE",
           "READ_ONLY_INDEX != MUTATION_AUTHORITY",
           "SOURCE_REVISIONS_REQUIRE_REFRESH",
           "PUBLIC_ALLOWLIST != PRIVATE_GITHUB_ACCESS",
        ],
    }
    return manifest,grouped

def validate(manifest,grouped):
    if manifest["schema"]!=SCHEMA or manifest["authority"]!=ROOT_AUTHORITY:
        raise GateError("ROOT_MANIFEST_CONTRACT_VIOLATION")
    if manifest["repositoryCount"]!=len(PUBLIC_REPOS)+1:
        raise GateError("REPOSITORY_COUNT_DRIFT")
    if manifest["shardCount"]!=len(grouped):
        raise GateError("SHARD_COUNT_DRIFT")
    records=0
    for name,data,summary in grouped:
        if summary["sha256"]!=sha(data):raise GateError("OUTPUT_SHARD_CORRUPT")
        doc=json.loads(data)
        if len(doc["records"])!=summary["count"] or doc["repository"]!=summary["repository"]:
            raise GateError("OUTPUT_SHARD_METADATA_MISMATCH")
        for r in doc["records"]:
            if not(r["readOnly"] and r["deleteAllowed"] is False
                   and r["sourceUrl"].startswith("https://github.com/"+OWNER+"/")
                   and r["sourceCommit"] in r["sourceUrl"]):
                raise GateError("UNSAFE_SOURCE_RECORD")
        records+=summary["count"]
    if records!=manifest["jsonCount"]:raise GateError("TOTAL_JSON_COUNT_DRIFT")

def write_index(output,manifest,grouped):
    output.mkdir(parents=True,exist_ok=True)
    # Never remove anything outside the dedicated generated output directory.
    sharddir=output/"shards"
    sharddir.mkdir(exist_ok=True)
    for existing in sharddir.glob("*.json"):existing.unlink()
    for name,data,_ in grouped:
        target=output/name
        target.parent.mkdir(exist_ok=True,parents=True)
        target.write_bytes(data)
    (output/"manifest.json").write_bytes(encoded(manifest))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    p.add_argument("--check-only",action="store_true")
    args=p.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        remotes=list(pool.map(read_public_tree,PUBLIC_REPOS))
    all_sources=[read_meta_catalog()]+remotes
    manifest,grouped=assemble(all_sources,datetime.now(timezone.utc).isoformat(timespec="seconds"))
    validate(manifest,grouped)
    if not args.check_only:write_index(args.output,manifest,grouped)
    print(json.dumps({
      "status":"PASS","public_repositories":manifest["repositoryCount"],
      "public_JSON":manifest["jsonCount"],
      "hashed_shards":manifest["shardCount"],
      "github_source_pinned":True,"write_authority":False,
      "private_included":False
    },sort_keys=True))
if __name__=="__main__":main()
