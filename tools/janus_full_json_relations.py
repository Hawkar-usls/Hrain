#!/usr/bin/env python3
"""Incremental, fail-closed relation overlay for the existing HRAiN public JSON atlas.
This is metadata for navigation, NOT a second source of truth or TOPA verdict.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen

ATLAS = Path("assets/janus-json-atlas")
OUT = Path("assets/janus-json-relations")
CATALOG_SCHEMA = "janus.hrain.github_json_constellation_manifest.v1"
SCHEMA = "janus.hrain.json_explicit_relations.v1"
SHA40 = re.compile(r"^[a-f0-9]{40}$")
REF = re.compile(r"https://(?:github\.com/Hawkar-usls/[A-Za-z0-9_.-]+/blob/|raw\.githubusercontent\.com/Hawkar-usls/[A-Za-z0-9_.-]+/)(?:main|[a-f0-9]{40})/[A-Za-z0-9_.%/+~-]+\.json\b")
EXPECTED_REPOS = {"Hawkar-usls/"+name for name in (
    "Hrain","iNaiHR","Janus","Janus_Genesis","Janus-Demiurge",
    "Janus-Fundamentum","TOPA","Janus-Cosmos","aura-oracle-tg",
    "tranception","janus-lapis","janus-distributed-ai-swarm",
    "Janus-HELIOS","janus-meta-registry")}
SIZE_CAP = 4_000_000
FIELD_CAP = SIZE_CAP
NODE_CAP = 100_000
DEPTH_CAP = 24
REF_CAP = 1000
# Each daily EYE index gets a NEW immutable commit+blob. Enforce one exact
# repository/path, SHA-pinned URL, 16 MB byte limit and the original SHA1/SHA256
# checks rather than permanently whitelisting yesterday's Git blob.
OVERSIZE_EYE_REPO = "Hawkar-usls/janus-meta-registry"
OVERSIZE_EYE_PATH = "EYE/generated/EYE-REGISTRY-INDEX.json"
OVERSIZE_CAP = 16_000_000
def source_cap(row):
    commit=row.get("sourceCommit","")
    blob=row.get("gitBlobSha","")
    valid=(row.get("repository")==OVERSIZE_EYE_REPO and
           row.get("path")==OVERSIZE_EYE_PATH and
           isinstance(commit,str) and SHA40.fullmatch(commit) and
           isinstance(blob,str) and SHA40.fullmatch(blob) and
           isinstance(row.get("sizeBytes"),int) and
           0<row["sizeBytes"]<=OVERSIZE_CAP and
           row.get("sourceUrl")=="https://github.com/"+OVERSIZE_EYE_REPO+
                "/blob/"+commit+"/"+OVERSIZE_EYE_PATH)
    return OVERSIZE_CAP if valid else SIZE_CAP

# Hash-verified GENERATED relations are not source-authored evidence. Treat
# these as provenance-bearing derived artifacts rather than recursively mining
# today's relation edges from yesterday's relation edges (feedback inflation).
GENERATED_RELATIONS = re.compile(r"^assets/janus-json-relations/(?:shards/[0-9]{2}|cache/[A-Za-z0-9_.-]+)\.json$")
def is_derived_relation(row):
    return row.get("repository")=="Hawkar-usls/Hrain" and bool(
        GENERATED_RELATIONS.fullmatch(str(row.get("path",""))))
def encoded(x): return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
def sha(b): return hashlib.sha256(b).hexdigest()
def ensure(c,msg):
    if not c: raise ValueError(msg)
def read_catalog(root):
    base=root/ATLAS
    raw=(base/"manifest.json").read_bytes()
    m=json.loads(raw)
    ensure(m.get("schema")==CATALOG_SCHEMA and m.get("privateRepositoriesIncluded") is False,"CATALOG_POLICY")
    ensure(m.get("authority",{}).get("sourceMutationAllowed") is False and
           m.get("authority",{}).get("readOnly") is True,"CATALOG_AUTHORITY")
    ensure(m["shardCount"]==len(m["shards"]) and m["repositoryCount"]==len(m["repositories"]),"CATALOG_MANIFEST_COUNTS")
    repos={r["repository"]:r["commit"] for r in m["repositories"]}
    ensure(set(repos)==EXPECTED_REPOS,"PUBLIC_REPO_ALLOWLIST_DRIFT")
    records={}
    for s in m["shards"]:
        path=s["path"]
        ensure(re.fullmatch(r"assets/janus-json-atlas/shards/[0-9]{4}\.json",path),"CATALOG_SHARD_PATH")
        b=(root/path).read_bytes()
        ensure(sha(b)==s["sha256"],"CATALOG_SHARD_SHA_MISMATCH")
        d=json.loads(b)
        ensure(d["sourceCommit"]==repos[s["repository"]] and
               d["repository"]==s["repository"] and d["readOnly"] is True and
               len(d["records"])==s["count"],"CATALOG_SHARD_DRIFT")
        for r in d["records"]:
            ensure(r["id"] not in records and r["readOnly"] is True and r["deleteAllowed"] is False,"CATALOG_ROW_POLICY")
            ensure(r["sourceCommit"]==repos[r["repository"]] and SHA40.fullmatch(r["sourceCommit"]),"CATALOG_COMMIT")
            ensure(r["sourceUrl"].startswith("https://github.com/"+r["repository"]+"/blob/"+r["sourceCommit"]+"/"),"CATALOG_ROW_URL")
            records[r["id"]]=r
    ensure(len(records)==m["jsonCount"],"CATALOG_INCOMPLETE")
    return m,sha(raw),records

def decode_reference(raw):
    p=urlsplit(raw)
    if p.scheme!="https" or p.query or p.fragment: return None
    segments=p.path.strip("/").split("/")
    if p.netloc=="github.com":
        if len(segments)<5 or segments[0]!="Hawkar-usls" or segments[2]!="blob":return None
        repo="Hawkar-usls/"+segments[1];rev=segments[3];parts=segments[4:]
    elif p.netloc=="raw.githubusercontent.com":
        if len(segments)<4 or segments[0]!="Hawkar-usls":return None
        repo="Hawkar-usls/"+segments[1];rev=segments[2];parts=segments[3:]
    else:return None
    if rev!="main" and not SHA40.fullmatch(rev):return None
    try:decoded=[unquote(x,encoding="utf-8",errors="strict") for x in parts]
    except (UnicodeError,ValueError):return None
    if any(not x or x in (".","..") or "/" in x or "\\" in x or "\x00" in x for x in decoded):return None
    path="/".join(decoded)
    if not path.endswith(".json"):return None
    return repo,rev,path

def extract_references(document,max_nodes=NODE_CAP):
    out=[];seen=set();nodes=0;truncated=False
    def walk(v,pointer,depth):
        nonlocal nodes,truncated
        if nodes>=max_nodes or depth>DEPTH_CAP or len(out)>=REF_CAP:
            truncated=True;return
        nodes+=1
        if isinstance(v,str):
            if len(v)>FIELD_CAP:truncated=True;return
            for x in REF.findall(v):
                key=(pointer,x)
                if key in seen:continue
                seen.add(key)
                out.append({"jsonPointer":pointer,"authoredUrl":x})
                if len(out)>=REF_CAP:truncated=True;break
        elif isinstance(v,dict):
            for k,x in v.items():
                walk(x,pointer+"/"+str(k).replace("~","~0").replace("/","~1"),depth+1)
                if truncated:break
        elif isinstance(v,list):
            for i,x in enumerate(v):
                walk(x,pointer+"/"+str(i),depth+1)
                if truncated:break
    walk(document,"",0)
    return out,truncated

def get_bytes(row):
    seg="/".join(quote(x,safe="") for x in row["path"].split("/"))
    url="https://raw.githubusercontent.com/"+row["repository"]+"/"+row["sourceCommit"]+"/"+seg
    req=Request(url,headers={"User-Agent":"JANUS-JSON-relations-readonly/1"})
    cap=source_cap(row)
    with urlopen(req,timeout=35) as f:
        body=f.read(cap+1)
    ensure(len(body)<=cap,"BODY_OVER_LIMIT")
    ensure(len(body)==row["sizeBytes"],"BYTE_SIZE_DRIFT")
    blob=b"blob "+str(len(body)).encode()+b"\x00"+body
    ensure(hashlib.sha1(blob).hexdigest()==row["gitBlobSha"],"GIT_BLOB_MISMATCH")
    if row.get("sourceSha256"): ensure(sha(body)==row["sourceSha256"],"SOURCE_SHA256_MISMATCH")
    return body

def scan(row):
    if row["sizeBytes"]>source_cap(row):return {"status":"SKIPPED_SIZE_CAP","blob":row["gitBlobSha"]}
    try:
        body=get_bytes(row)
        if body.startswith((b"\xff\xfe",b"\xfe\xff")):
            decoded=body.decode("utf-16")
        elif body.startswith(b"\xef\xbb\xbf"):
            decoded=body.decode("utf-8-sig")
        else:
            decoded=body.decode("utf-8")
        doc=json.loads(decoded)
        if is_derived_relation(row):
            # Parsing and Git blob verification succeed, but derived source's
            # authored URLs are not re-imported as independent primary evidence.
            ensure(isinstance(doc,dict),"DERIVED_JSON_ROOT_HOLD")
            return {"status":"VERIFIED_DERIVED_EXCLUDED","blob":row["gitBlobSha"],
                    "sha256":sha(body),"refs":[],"exclusion":"SELF_GENERATED_NOT_PRIMARY_SOURCE"}
        refs,trunc=extract_references(doc,max_nodes=2_000_000 if source_cap(row)>SIZE_CAP else NODE_CAP)
        return {"status":"VERIFIED_TRUNCATED" if trunc else "VERIFIED","blob":row["gitBlobSha"],
                "sha256":sha(body),"refs":refs}
    except Exception as e:
        # Any failure is an unresolved gate, never a verified negative or success.
        return {"status":"HOLD","blob":row["gitBlobSha"],"reason":str(e)[:120]}

def cache_load(out,repos):
    old={}
    for repo in repos:
        p=out/"cache"/(repo.split("/")[-1]+".json")
        if p.is_file():
            try:
                d=json.loads(p.read_bytes())
                if d.get("schema")==SCHEMA and d.get("repository")==repo:
                    old.update(d["entries"])
            except (ValueError,KeyError):pass
    return old

def build(root,out,workers,max_new=0):
    manifest,manifest_hash,rows=read_catalog(root)
    by_pair={(r["repository"],r["path"]):r for r in rows.values()}
    repos=sorted({r["repository"] for r in rows.values()})
    cache=cache_load(out,repos)
    kept={}
    todo=[]
    for rid,r in sorted(rows.items()):
        v=cache.get(rid)
        if v and v.get("blob")==r["gitBlobSha"] and (v.get("status") in ("VERIFIED","VERIFIED_DERIVED_EXCLUDED") or
             (v.get("status")=="SKIPPED_SIZE_CAP" and r["sizeBytes"]>source_cap(r))):
            kept[rid]=v
        elif max_new==0 or len(todo)<max_new:
            todo.append((rid,r))
    print(json.dumps({"phase":"SOURCE_SCAN","catalog":len(rows),"cache_hits":len(kept),"new":len(todo),"pending":len(rows)-len(kept)-len(todo)},sort_keys=True),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for (rid,r),v in zip(todo,ex.map(lambda q:scan(q[1]),todo)):
            kept[rid]=v
    edges=defaultdict(list)
    kinds=Counter()
    for rid in sorted(kept):
        r=rows[rid];v=kept[rid];kinds[v["status"]]+=1
        if not v["status"].startswith("VERIFIED"):continue
        for ref in v.get("refs",[]):
            parsed=decode_reference(ref["authoredUrl"])
            if not parsed:continue
            repo,revision,path=parsed;target=by_pair.get((repo,path))
            if not target or target["id"]==rid or (revision!="main" and revision!=target["sourceCommit"]):continue
            e={"sourceId":rid,"targetId":target["id"],"jsonPointer":ref["jsonPointer"],
               "authoredUrl":ref["authoredUrl"],"sourceGitBlobSha":r["gitBlobSha"],
               "sourceSha256":v["sha256"],"targetSnapshotCommit":target["sourceCommit"],
               "referenceMode":"BRANCH_MAIN_REBOUND_TO_SNAPSHOT" if revision=="main" else "PINNED_SAME_COMMIT",
               "relationClass":"EXPLICIT_SOURCE_REFERENCE",
               "scientificVerdict":"NOT_TOPA_ADJUDICATED"}
            edges[r["repository"]].append(e)
    expected=sum(s["jsonCount"] for s in manifest["repositories"])
    ensure(expected==len(rows),"REPOSITORY_COVERAGE_MISMATCH")
    grouped=[]
    for i,repo in enumerate(repos):
        a=sorted(edges[repo],key=lambda e:(e["sourceId"],e["jsonPointer"],e["targetId"]))
        b=encoded({"schema":SCHEMA,"repository":repo,"catalogSha256":manifest_hash,"edges":a,
                  "readOnly":True,"semanticHypothesesAreEvidence":False,"topaScientificVerdict":"NOT_ADJUDICATED"})
        grouped.append((repo,f"shards/{i:02d}.json",b))
    result={"schema":SCHEMA,"authority":{"readOnly":True,"writeAuthority":False,
                "sourceMutationAllowed":False,"semanticHypothesesAreEvidence":False,"topaVerdictsAreAutoInferred":False},
            "sourceCatalogSha256":manifest_hash,"sourceCatalogGeneratedAt":manifest.get("generatedAt"),
            "sourceCatalogJsonCount":len(rows),"publicRepositoryCount":len(repos),
            "scannedVerifiedFiles":kinds["VERIFIED"]+kinds["VERIFIED_TRUNCATED"]+kinds["VERIFIED_DERIVED_EXCLUDED"],
            "derivedExcludedFiles":kinds["VERIFIED_DERIVED_EXCLUDED"],
            "truncatedFiles":kinds["VERIFIED_TRUNCATED"],"skippedSizeFiles":kinds["SKIPPED_SIZE_CAP"],
            "heldFiles":kinds["HOLD"],"pendingFiles":len(rows)-len(kept),
            "complete":len(kept)==len(rows) and not kinds["HOLD"] and not kinds["VERIFIED_TRUNCATED"]
                       and not kinds["SKIPPED_SIZE_CAP"] and not kinds["VERIFIED_DERIVED_EXCLUDED"],
            "directEdges":sum(len(edges[repo]) for repo in repos),"semanticHypothesisEdges":0,
            "topaAdjudicatedClaims":0,
            "shards":[{"repository":repo,"path":"assets/janus-json-relations/"+name,"sha256":sha(b),
                        "count":len(json.loads(b)["edges"])} for repo,name,b in grouped]}
    return result,grouped,kept,rows

def save(out,result,grouped,cache,rows):
    (out/"shards").mkdir(parents=True,exist_ok=True)
    (out/"cache").mkdir(parents=True,exist_ok=True)
    for repo,name,b in grouped:
        (out/name).write_bytes(b)
    for repo in sorted({r["repository"] for r in rows.values()}):
        entries={rid:cache[rid] for rid,r in sorted(rows.items()) if r["repository"]==repo and rid in cache}
        (out/"cache"/(repo.split("/")[-1]+".json")).write_bytes(encoded({
            "schema":SCHEMA,"repository":repo,"entries":entries}))
    (out/"manifest.json").write_bytes(encoded(result))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--output",type=Path)
    p.add_argument("--workers",type=int,default=16)
    p.add_argument("--max-new",type=int,default=0,help="New verified-file attempts, 0=all")
    p.add_argument("--check-only",action="store_true")
    x=p.parse_args()
    ensure(1<=x.workers<=40 and x.max_new>=0,"ARGUMENT_BOUNDARY")
    out=x.output or x.root/OUT
    t=time.monotonic()
    r,g,c,rows=build(x.root,out,x.workers,x.max_new)
    if not x.check_only:save(out,r,g,c,rows)
    print(json.dumps({"status":"PASS","seconds":round(time.monotonic()-t,1),
                      "manifest":r},sort_keys=True),flush=True)
if __name__=="__main__":main()
