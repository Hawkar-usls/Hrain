#!/usr/bin/env python3
"""JANUS's read-only GitHub JSON mindmap query adapter.

Source navigation through the *existing* HRAiN/iNaiHR public constellation.
Mandatory SHA-256 verification of EVERY loaded shard and pinned GitHub source.
No provider key, no user profile, no repository changes or command authority.
Run:
  python tools/janus_mindmap_query.py --query "Rowan FN1" --related 5
  python tools/janus_mindmap_query.py --repo Hawkar-usls/tranception
  python tools/janus_mindmap_query.py --focus 'Hawkar-usls/Janus:portfolio-visibility.json'
"""
import argparse
import hashlib
import json
import re
import concurrent.futures
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.parse import quote,urlsplit
from janus_verified_source import read_exact_pointer, SourceHold

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_INDEX="https://raw.githubusercontent.com/Hawkar-usls/Hrain/main/assets/janus-json-atlas"
SCHEMA="janus.hrain.github_json_constellation_manifest.v1"
ATLAS_REVISION_API="https://api.github.com/repos/Hawkar-usls/Hrain/commits?path=assets/janus-json-atlas/manifest.json&per_page=1"
STOP={"janus","json","data","assets","2026","2025","repo","source","registry","meta","main","true","false"}
class Hold(RuntimeError):pass

def _get(url):
    parts=urlsplit(url)
    prefix="/Hawkar-usls/Hrain/"
    if (parts.scheme!="https" or parts.netloc!="raw.githubusercontent.com"
        or parts.query or parts.fragment or not parts.path.startswith(prefix)
        or "/assets/janus-json-atlas/" not in parts.path):
        raise Hold("SOURCE_HOST_OR_PATH_NOT_ALLOWED")
    revision=parts.path[len(prefix):].split("/",1)[0]
    if not re.fullmatch(r"[0-9a-f]{40}",revision):
        raise Hold("UNPINNED_ATLAS_READ_FORBIDDEN")
    with urlopen(Request(url,headers={"User-Agent":"JANUS-HRAiN-readonly-navigator/1"}),timeout=30) as r:
        return r.read(8_000_001)

def pin_atlas_revision(fetch=None):
    if fetch is None:
        with urlopen(Request(ATLAS_REVISION_API,headers={
            "User-Agent":"JANUS-HRAiN-atomic-catalog-reader/1",
            "Accept":"application/vnd.github+json"
        }),timeout=25) as r:
            raw=r.read(100_001)
    else:
        raw=fetch(ATLAS_REVISION_API)
    if len(raw)>100_000:raise Hold("ATLAS_COMMIT_API_SIZE_LIMIT")
    try:
        commits=json.loads(raw)
        revision=commits[0]["sha"]
    except (ValueError,IndexError,KeyError,TypeError) as exc:
        raise Hold("ATLAS_COMMIT_PIN_UNAVAILABLE") from exc
    if not isinstance(revision,str) or not re.fullmatch(r"[0-9a-f]{40}",revision):
        raise Hold("ATLAS_COMMIT_SHA_NOT_AUTHENTICATED")
    return revision
def tokens(path):
    return {x for x in re.split(r"[^a-zа-яіїєґ0-9]+",path.casefold()) if len(x)>=3 and x not in STOP}
def load_catalog(index_root=DEFAULT_INDEX,fetch=None):
    local = isinstance(index_root,Path)
    revision=None
    if not local:
        if index_root!=DEFAULT_INDEX:raise Hold("ATLAS_URL_OVERRIDE_NOT_ALLOWED")
        revision=pin_atlas_revision(fetch=fetch)
        index_root=DEFAULT_INDEX.replace("/main/assets/","/"+revision+"/assets/")
    def read(path):
        if local:
            f=(index_root/path)
            if not f.is_file():raise Hold("SHARD_OR_MANIFEST_NOT_FOUND:"+path)
            data=f.read_bytes()
        else:
            if fetch is not None:data=fetch(index_root+"/"+path)
            else:data=_get(index_root+"/"+path)
        if len(data)>8_000_000:raise Hold("SHARD_LIMIT_EXCEEDED")
        return data
    m=json.loads(read("manifest.json"))
    if revision:m["catalogRevision"]=revision
    policy=m.get("authority") or {}
    if (m.get("schema")!=SCHEMA or m.get("privateRepositoriesIncluded") is not False
        or m.get("metadataOnly") is not True or policy.get("writeAuthority") is not False
        or policy.get("sourceMutationAllowed") is not False or policy.get("readOnly") is not True):
        raise Hold("PUBLIC_SOURCE_OR_AUTHORITY_VIOLATION")
    if m.get("shardCount")!=len(m.get("shards",[])):raise Hold("INCOMPLETE_SHARD_MANIFEST")
    def load_verified_shard(shard):
        path=shard.get("path","")
        if not path.startswith("assets/janus-json-atlas/shards/") or ".." in path:
            raise Hold("PATH_TRAVERSAL_OR_INVALID_SHARD")
        data=read(path.replace("assets/janus-json-atlas/",""))
        if hashlib.sha256(data).hexdigest()!=shard["sha256"]:
            raise Hold("SHARD_SHA256_MISMATCH:"+path)
        doc=json.loads(data)
        if (doc.get("schema")!="janus.hrain.github_json_constellation_shard.v1"
            or doc.get("readOnly") is not True or doc.get("repository")!=shard["repository"]
            or doc.get("sourceCommit") not in {x["commit"] for x in m["repositories"] if x["repository"]==shard["repository"]}
            or len(doc.get("records",[]))!=shard["count"]):
            raise Hold("SOURCE_SHARD_INTEGRITY_MISMATCH")
        for rec in doc["records"]:
            expected=f"https://github.com/{rec['repository']}/blob/{rec['sourceCommit']}/{quote(rec['path'],safe='/')}"
            if (rec.get("sourceUrl")!=expected or not rec["repository"].startswith("Hawkar-usls/")
                or rec.get("readOnly") is not True or rec.get("deleteAllowed") is not False
                or not rec["path"].endswith(".json")):
                raise Hold("UNTRUSTED_GITHUB_SOURCE_POINTER")
        return doc["records"]
    # Immutable catalog revision is pinned BEFORE parallel work. executor.map
    # preserves original manifest shard order, including deterministic ranking.
    # If even ONE shard fails its SHA/commit/source contract, FAIL CLOSED.
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        batches=list(pool.map(load_verified_shard,m["shards"]))
    records=[rec for batch in batches for rec in batch]
    if len(records)!=m["jsonCount"] or len({x["id"] for x in records})!=len(records):
        raise Hold("INCOMPLETE_OR_DUPLICATED_PUBLIC_SOURCE_CATALOG")
    return m,records

def navigate(m,records,query="",repository="",focus="",limit=12,related=6):
    if limit<1 or limit>50 or related<0 or related>20:raise Hold("UNBOUNDED_NAVIGATION_REQUEST")
    candidates=[r for r in records if not repository or r["repository"]==repository]
    q=tokens(query)
    if query:
        raw=query.casefold().strip()
        def score(r):
            txt=(r["repository"]+"/"+r["path"]).casefold()
            overlap=tokens(txt)&q
            return 5*len(overlap)+int(raw in txt)
        matches=[r for r in candidates if score(r)>0]
        matches.sort(key=lambda x:(-score(x),x["repository"],x["path"]))
    else:matches=sorted(candidates,key=lambda x:(x["repository"],x["path"]))
    if focus:
        key=next((x for x in records if x["id"]==focus or
                  x["repository"]+":"+x["path"]==focus),None)
        if key is None:raise Hold("FOCUS_SOURCE_NOT_INDEXED")
    else:key=matches[0] if matches else None
    edges=[]
    neighbour=[]
    if key:
        base=tokens(key["path"])
        out=[]
        for rec in records:
            if rec["id"]==key["id"]:continue
            shared=sorted(base&tokens(rec["path"]))
            if len(shared)<2:continue
            out.append((len(shared),rec,shared))
        out.sort(key=lambda v:(-v[0],v[1]["repository"],v[1]["path"]))
        for weight,rec,shared in out[:related]:
            neighbour.append({
                "id":rec["id"],"source":rec["sourceUrl"],
                "repository":rec["repository"],"path":rec["path"],
                "sharedPathTokens":shared,
                "edgeType":"UNVERIFIED_SEMANTIC_PATH_ASSOCIATION",
                "verifiedScientificRelation":False,
            })
            edges.append({"source":key["id"],"target":rec["id"],
                          "kind":"ASSOCIATIVE_CANDIDATE","truthAuthority":False})
    return {
      "schema":"janus.hrain.inaihr.json_navigation_receipt.v1",
      "status":"SOURCE_INDEX_VERIFIED_READ_ONLY",
      "snapshotAt":m["generatedAt"],
      "catalogRevision":m.get("catalogRevision"),
      "snapshotRepositoryCount":m["repositoryCount"],
      "snapshotJSONCount":m["jsonCount"],
      "query":query,"repositoryFilter":repository,
      "hits":len(matches),
      "results":[{"id":r["id"],"repository":r["repository"],"path":r["path"],
                  "source":r["sourceUrl"],"sourceCommit":r["sourceCommit"],
                  "metadataOnly":True} for r in matches[:limit]],
      "focus":({"id":key["id"],"source":key["sourceUrl"],
                "githubRef":key["repository"]+"@"+key["sourceCommit"]+":"+key["path"]}
                if key else None),
      "mindmap":{
        "HRAiN":"STRUCTURAL_REPO_PATH_TREE",
        "iNaiHR":"ASSOCIATIVE_CANDIDATES_NOT_EVIDENCE",
        "related":neighbour,"edges":edges,
      },
      "claimCeiling":["SOURCE_INDEX != SOURCE_JSON_CONTENT",
                       "ASSOCIATION != FACT","READ_ONLY != COMMAND_PERMISSION",
                       "PINNED_GITHUB_COMMIT_MUST_BE_READ_FOR_CLAIMS"],
      "newActionsTriggered":0,
      "registryWrites":0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--query",default="")
    p.add_argument("--repo",default="")
    p.add_argument("--focus",default="")
    p.add_argument("--limit",type=int,default=12)
    p.add_argument("--related",type=int,default=6)
    p.add_argument("--local-index",type=Path)
    p.add_argument("--read-source",action="store_true",help="Download and verify one exact public JSON by Git blob hash")
    p.add_argument("--pointer",default="",help="RFC 6901 pointer, e.g. /status or /results/0/metric")
    args=p.parse_args()
    m,rows=load_catalog(args.local_index or DEFAULT_INDEX)
    output=navigate(m,rows,args.query,args.repo,args.focus,args.limit,args.related)
    if args.read_source:
        focus=output["focus"]
        if not focus:raise Hold("SOURCE_READ_REQUIRES_EXACT_MATCH_OR_FOCUS")
        selected=next((r for r in rows if r["id"]==focus["id"]),None)
        if selected is None:raise Hold("UNINDEXED_SOURCE")
        try:output["verifiedSourceField"]=read_exact_pointer(selected,args.pointer)
        except SourceHold as exc:raise Hold(str(exc)) from exc
    elif args.pointer:
        raise Hold("JSON_POINTER_REQUIRES_READ_SOURCE")
    print(json.dumps(output,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
