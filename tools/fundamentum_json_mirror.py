#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, urllib.request
from pathlib import Path

API="https://api.github.com/repos/Hawkar-usls/Janus-Fundamentum"
RAW="https://raw.githubusercontent.com/Hawkar-usls/Janus-Fundamentum/main"
UA="JANUS-HRAiN-Fundamentum-Mirror/1.0"
KEY_PATHS=[
    "README.md",
    "docs/CURRENT_RESEARCH_STATUS.md",
    "docs/A3_PUBLICATION_TRACK.md",
    "docs/C023_FORMULA_CACHING_CALCULUS.md",
]

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req,timeout=45) as r:
        return json.load(r)

def get_text(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/plain,*/*"})
    with urllib.request.urlopen(req,timeout=45) as r:
        return r.read().decode("utf-8","replace")

def sh(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def write(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    out=Path(a.out)
    branch=get_json(API+"/branches/main")
    head=branch["commit"]["sha"]
    tree=get_json(API+f"/git/trees/{head}?recursive=1")
    blobs=[]
    for row in tree.get("tree",[]):
        if row.get("type")!="blob": continue
        blobs.append({
            "path":row.get("path"),
            "blob_sha":row.get("sha"),
            "size":row.get("size",0),
            "raw_url":RAW+"/"+row.get("path",""),
            "content_embedded":False,
        })
    full={
        "schema":"janus.hrain.fundamentum_full_index.v1",
        "source_repository":"Hawkar-usls/Janus-Fundamentum",
        "source_ref":"main",
        "source_commit":head,
        "source_history_authoritative":True,
        "entry_count":len(blobs),
        "entries":blobs,
        "authority":{"truth":False,"proof":False,"source_mutation":False},
        "claim_ceiling":"READ_ONLY_STRUCTURAL_INDEX__SOURCE_CONTENT_REMAINS_AUTHORITATIVE",
    }
    docs=[]
    for path in KEY_PATHS:
        try:
            text=get_text(RAW+"/"+path)
            docs.append({"path":path,"sha256":sh(text),"bytes":len(text.encode("utf-8")),"content":text,"status":"PRESENT"})
        except Exception as e:
            docs.append({"path":path,"status":"UNAVAILABLE","error":type(e).__name__+":"+str(e)})
    key={
        "schema":"janus.hrain.fundamentum_key_research.v1",
        "source_repository":"Hawkar-usls/Janus-Fundamentum",
        "source_commit":head,
        "documents":docs,
        "authority":{"truth":False,"proof":False,"independent_replication":False},
        "laws":["SOURCE_TEXT != HRAIN_VERDICT","MIRROR != INDEPENDENT_REPLICATION"],
    }
    latest={
        "schema":"janus.hrain.fundamentum_memory_pointer.v1",
        "status":"READY",
        "source_commit":head,
        "full_index_sha256":sh(json.dumps(full,ensure_ascii=False,sort_keys=True,separators=(",",":"))),
        "key_research_sha256":sh(json.dumps(key,ensure_ascii=False,sort_keys=True,separators=(",",":"))),
        "entry_count":len(blobs),
        "janus_access":"READ_DERIVE_CANDIDATES_ONLY",
        "source_mutation":False,
        "claim_promotion":False,
    }
    write(out/"FULL_INDEX.json",full)
    write(out/"KEY_RESEARCH.json",key)
    write(out/"LATEST.json",latest)
    print(json.dumps(latest,ensure_ascii=False,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
