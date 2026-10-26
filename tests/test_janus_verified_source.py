"""All JANUS source reading must be SHA-verified, pinned and fail closed."""
import hashlib
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from janus_verified_source import (
 git_blob_sha,source_url,verified_json,pointer_get,read_exact_pointer,SourceHold,
)

REV="b"*40
REPO="Hawkar-usls/janus-meta-registry"
P="data/rowan/provenance/test.json"
CONTENT=b'{"a":{"b":[42,{"a/b":"proof"}]},"status":"HOLD"}\n'
EXPECTED_BLOB=git_blob_sha(CONTENT)

@pytest.fixture
def record():
 return {"repository":REPO,"path":P,"sourceCommit":REV,
         "sourceUrl":f"https://github.com/{REPO}/blob/{REV}/{P}",
         "gitBlobSha":EXPECTED_BLOB,"sourceSha256":hashlib.sha256(CONTENT).hexdigest(),
         "sizeBytes":len(CONTENT),"readOnly":True,"deleteAllowed":False,
         "authority":"SOURCE_METADATA_ONLY"}

def test_real_git_blob_algorithm_against_known_git_example():
 assert git_blob_sha(b"test content\n")==hashlib.sha1(b"blob 13\x00test content\n").hexdigest()

def test_field_pointer_sha_and_provenance(record):
 receipt=read_exact_pointer(record,"/a/b/1/a~1b",lambda url: CONTENT)
 assert receipt["status"]=="VERIFIED_SOURCE_BYTES_AND_JSON_POINTER"
 assert receipt["valueExcerpt"]=='"proof"'
 assert receipt["source"]["sourceCommit"]==REV
 assert receipt["source"]["gitBlobSha"]==EXPECTED_BLOB
 assert receipt["epistemic"]["source_fact_scientifically_verified"] is False
 assert receipt["epistemic"]["no_registry_mutations"] is True

def test_array_and_rfc6901_pointer():
 d={"a/b":{"~token":["zero",{"x":2}]},"0":"zero"}
 assert pointer_get(d,"/a~1b/~0token/1/x")==2
 assert pointer_get(d,"")==d
 for invalid in ["/a~2b","/a~","/a~1b/~0token/01","/a~1b/~0token/-"]:
  with pytest.raises(SourceHold): pointer_get(d,invalid)

def test_source_tampering_rejected_by_git_blob_even_without_registry_sha(record):
 bad=dict(record)
 bad["sourceSha256"]=None
 with pytest.raises(SourceHold,match="SOURCE_GIT_BLOB_SHA_MISMATCH"):
  verified_json(bad,lambda url: CONTENT.replace(b'HOLD',b'PASS'))

def test_meta_hash_tamper_fail_closed(record):
 bad=dict(record);bad["sourceSha256"]="0"*64
 with pytest.raises(SourceHold,match="SOURCE_SHA256_MISMATCH"):
  verified_json(bad,lambda url: CONTENT)

def test_url_or_untrusted_record_cannot_expand_permissions(record):
 for replacement in [
  {"sourceCommit":"main"},
  {"repository":"Hawkar-usls/../private"},
  {"path":"../secrets.json"},
  {"path":"data/../secrets.json"},
  {"sourceUrl":"https://evil.example/"},
  {"sizeBytes":2_000_001},
  {"readOnly":False},
  {"authority":"WRITE"}
 ]:
  with pytest.raises(SourceHold): source_url({**record,**replacement})

def test_no_hidden_credentials_or_write_api():
 import inspect,janus_verified_source as m
 s=inspect.getsource(m)
 assert 'method="POST"' not in s
 assert 'Authorization' not in s
 assert "gh auth token" not in s
 assert "ROWAN_API_KEY" not in s
