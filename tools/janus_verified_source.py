#!/usr/bin/env python3
"""JANUS exact-source GitHub JSON DIVE, SHA-confirmed (read only).

Independent of search confidence. Records MUST come from the verified HRAiN
public constellation. Reading a JSON value never validates its scientific truth,
and never creates new write, repo, provider or model authority.
"""
from __future__ import annotations
import hashlib
import json
import re
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

MAX_SOURCE_BYTES = 2_000_000
MAX_DISPLAY_CHARS = 2400
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY = re.compile(r"^Hawkar-usls/[A-Za-z0-9_.-]+$")
class SourceHold(RuntimeError):
    pass

def source_url(record: dict[str,Any]) -> str:
    repo = record.get("repository")
    revision = record.get("sourceCommit")
    path = record.get("path")
    if (not isinstance(repo,str) or not REPOSITORY.fullmatch(repo)
        or not isinstance(revision,str) or not SHA40.fullmatch(revision)
        or not isinstance(path,str) or not path.endswith(".json")
        or len(path)>512 or path.startswith("/") or "\\" in path
        or any(seg in ("", ".", "..") for seg in path.split("/"))):
        raise SourceHold("SOURCE_POINTER_FORMAT_REJECTED")
    expected = f"https://github.com/{repo}/blob/{revision}/{quote(path,safe='/')}"
    if (record.get("sourceUrl") != expected or record.get("readOnly") is not True
        or record.get("deleteAllowed") is not False
        or record.get("authority")!="SOURCE_METADATA_ONLY"):
        raise SourceHold("SOURCE_NOT_FROM_VERIFIED_CATALOG")
    size = record.get("sizeBytes")
    if not isinstance(size,int) or isinstance(size,bool) or size<1 or size>MAX_SOURCE_BYTES:
        raise SourceHold("SOURCE_SIZE_OUTSIDE_SAFE_BOUND")
    return f"https://raw.githubusercontent.com/{repo}/{revision}/{quote(path,safe='/')}"

def fetch_public(url: str) -> bytes:
    if not url.startswith("https://raw.githubusercontent.com/Hawkar-usls/"):
        raise SourceHold("UNEXPECTED_NETWORK_DESTINATION")
    req = Request(url,headers={"User-Agent":"JANUS-HRAiN-json-pointer-readonly/1",
                              "Accept":"application/json"})
    try:
        with urlopen(req,timeout=25) as res:
            raw = res.read(MAX_SOURCE_BYTES+1)
    except Exception as exc:
        raise SourceHold("COMMIT_PINNED_SOURCE_FETCH_FAILED") from exc
    return raw

def git_blob_sha(raw:bytes) -> str:
    prefix=b"blob "+str(len(raw)).encode("ascii")+b"\x00"
    return hashlib.sha1(prefix+raw).hexdigest()

def verified_json(record:dict[str,Any],fetch:Callable[[str],bytes]=fetch_public):
    url=source_url(record)
    raw=fetch(url)
    if not isinstance(raw,bytes) or len(raw)>MAX_SOURCE_BYTES:
        raise SourceHold("SOURCE_RESPONSE_TOO_LARGE")
    if len(raw)!=record["sizeBytes"]:
        raise SourceHold("SOURCE_BYTE_LENGTH_CHANGED")
    expected_blob=record.get("gitBlobSha")
    if not isinstance(expected_blob,str) or not SHA40.fullmatch(expected_blob):
        raise SourceHold("SOURCE_GIT_BLOB_SHA_MISSING")
    observed_blob=git_blob_sha(raw)
    if observed_blob!=expected_blob:
        raise SourceHold("SOURCE_GIT_BLOB_SHA_MISMATCH")
    digest=hashlib.sha256(raw).hexdigest()
    recorded_sha=record.get("sourceSha256")
    if recorded_sha is not None:
        if not isinstance(recorded_sha,str) or not SHA64.fullmatch(recorded_sha) or recorded_sha!=digest:
            raise SourceHold("SOURCE_SHA256_MISMATCH")
    try:
        doc=json.loads(raw.decode("utf-8"))
    except (UnicodeError,ValueError) as exc:
        raise SourceHold("SOURCE_IS_NOT_UTF8_JSON") from exc
    return doc,{"url":url,"gitBlobSha":observed_blob,"sha256":digest,
                "bytes":len(raw),"sourceCommit":record["sourceCommit"],
                "recordedRegistrySha256":recorded_sha,"integrity":"VERIFIED_EXACT_GIT_BLOB"}

def pointer_get(doc:Any,pointer:str):
    if pointer=="":
        return doc
    if not isinstance(pointer,str) or len(pointer)>1024 or not pointer.startswith("/"):
        raise SourceHold("INVALID_JSON_POINTER")
    cur=doc
    for raw in pointer.split("/")[1:]:
        # Strict RFC6901 unescape: an incomplete/unknown tilde escape is invalid.
        if re.search(r"~(?![01])",raw):
            raise SourceHold("INVALID_JSON_POINTER_ESCAPE")
        token=raw.replace("~1","/").replace("~0","~")
        if isinstance(cur,dict):
            if token not in cur:raise SourceHold("JSON_POINTER_KEY_ABSENT")
            cur=cur[token]
        elif isinstance(cur,list):
            if not re.fullmatch(r"0|[1-9][0-9]*",token):
                raise SourceHold("JSON_POINTER_ARRAY_INDEX_INVALID")
            idx=int(token)
            if idx>=len(cur):raise SourceHold("JSON_POINTER_ARRAY_INDEX_OUT_OF_RANGE")
            cur=cur[idx]
        else:
            raise SourceHold("JSON_POINTER_CANNOT_DESCEND_SCALAR")
    return cur

def read_exact_pointer(record:dict[str,Any],pointer="",fetch=fetch_public):
    doc,provenance=verified_json(record,fetch)
    value=pointer_get(doc,pointer)
    serialized=json.dumps(value,ensure_ascii=False,sort_keys=True,default=str)
    return {
        "schema":"janus.hrain.inaihr.verified_json_pointer.v1",
        "status":"VERIFIED_SOURCE_BYTES_AND_JSON_POINTER",
        "source":{
            "repository":record["repository"],"path":record["path"],
            **provenance,
            "browserUrl":record["sourceUrl"]
        },
        "jsonPointer":pointer,
        "valueType":("null" if value is None else "array" if isinstance(value,list)
                     else "object" if isinstance(value,dict) else type(value).__name__),
        "valueSha256":hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "valueExcerpt":serialized[:MAX_DISPLAY_CHARS],
        "excerptTruncated":len(serialized)>MAX_DISPLAY_CHARS,
        "epistemic":{
            "byte_identity_verified":True,
            "source_fact_scientifically_verified":False,
            "source_content_is_untrusted_data_not_instructions":True,
            "no_model_or_fact_promotion":True,
            "no_registry_mutations":True,
            "no_provider_calls":True,
            "semantic_links_not_evidence":True
        }
    }
