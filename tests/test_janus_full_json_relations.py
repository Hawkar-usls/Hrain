"""Fail-closed tests for resumable full-corpus JSON→JSON metadata edges."""
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("relations",ROOT/"tools/janus_full_json_relations.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Relations(unittest.TestCase):
    def test_pointer_and_untrusted_link_policy(self):
        sha="a"*40
        a="https://github.com/Hawkar-usls/TOPA/blob/main/data/a.json"
        b="https://raw.githubusercontent.com/Hawkar-usls/TOPA/"+sha+"/data/b.json"
        d={"sources/path":[a,b,"https://github.com/Hawkar-usls/TOPA/blob/master/data/x.json"]}
        refs,truncated=m.extract_references(d)
        self.assertFalse(truncated)
        self.assertEqual([x["jsonPointer"] for x in refs],["/sources~1path/0","/sources~1path/1"])
        self.assertEqual(m.decode_reference(a),("Hawkar-usls/TOPA","main","data/a.json"))
        self.assertEqual(m.decode_reference(b),("Hawkar-usls/TOPA",sha,"data/b.json"))
        for invalid in ("http://github.com/Hawkar-usls/TOPA/blob/main/data/a.json",
                        "https://github.com/Others/TOPA/blob/main/data/a.json",
                        "https://github.com/Hawkar-usls/TOPA/blob/main/../data/a.json",
                        "https://github.com/Hawkar-usls/TOPA/blob/main/%2e%2e/data/a.json"):
            self.assertIsNone(m.decode_reference(invalid))

    def fixture(self,root):
        repos=["Hawkar-usls/Hrain","Hawkar-usls/Janus","Hawkar-usls/Janus-Cosmos",
               "Hawkar-usls/Janus-Demiurge","Hawkar-usls/Janus-Fundamentum",
               "Hawkar-usls/Janus-HELIOS","Hawkar-usls/Janus_Genesis",
               "Hawkar-usls/TOPA","Hawkar-usls/aura-oracle-tg","Hawkar-usls/iNaiHR",
               "Hawkar-usls/janus-distributed-ai-swarm","Hawkar-usls/janus-lapis",
               "Hawkar-usls/janus-meta-registry","Hawkar-usls/tranception"]
        files={}
        scopes=[]
        summaries=[]
        for i,repo in enumerate(repos):
            commit=f"{i+1:040x}"
            path="data/test.json";rid=f"json:{i:024x}"
            raw={"source":"https://github.com/Hawkar-usls/TOPA/blob/main/data/test.json"} if i==0 else {"value":i}
            b=m.encoded(raw);files[rid]=b
            row={"id":rid,"repository":repo,"path":path,"sourceCommit":commit,
                "gitBlobSha":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\x00"+b).hexdigest(),
                "sourceSha256":m.sha(b),"sizeBytes":len(b),
                "readOnly":True,"deleteAllowed":False,
                "sourceUrl":f"https://github.com/{repo}/blob/{commit}/{path}"}
            shardpath=f"assets/janus-json-atlas/shards/{i:04d}.json"
            body=m.encoded({"schema":"janus.hrain.github_json_constellation_shard.v1",
                "repository":repo,"sourceCommit":commit,"readOnly":True,"records":[row]})
            p=root/shardpath;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
            scopes.append({"repository":repo,"commit":commit,"jsonCount":1})
            summaries.append({"path":shardpath,"repository":repo,"count":1,"sha256":m.sha(body)})
        manifest={"schema":m.CATALOG_SCHEMA,"privateRepositoriesIncluded":False,
                  "authority":{"readOnly":True,"sourceMutationAllowed":False},
                  "shardCount":14,"repositoryCount":14,"repositories":scopes,"shards":summaries,
                  "jsonCount":14,"generatedAt":"fixture"}
        (root/"assets/janus-json-atlas/manifest.json").write_bytes(m.encoded(manifest))
        return files

    def test_incremental_cache_and_explicit_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);files=self.fixture(root);out=root/"assets/janus-json-relations"
            with patch.object(m,"get_bytes",side_effect=lambda r:files[r["id"]]):
                result,parts,cache,rows=m.build(root,out,workers=2,max_new=2)
                self.assertEqual(result["pendingFiles"],12)
                self.assertEqual(result["scannedVerifiedFiles"],2)
                m.save(out,result,parts,cache,rows)
                result2,parts2,cache2,rows2=m.build(root,out,workers=2,max_new=0)
            self.assertEqual(result2["pendingFiles"],0)
            self.assertEqual(result2["directEdges"],1)
            self.assertEqual(result2["semanticHypothesisEdges"],0)
            self.assertEqual(result2["topaAdjudicatedClaims"],0)
            edge=json.loads(parts2[0][2])["edges"][0]
            self.assertEqual(edge["jsonPointer"],"/source")
            self.assertEqual(edge["referenceMode"],"BRANCH_MAIN_REBOUND_TO_SNAPSHOT")
            self.assertEqual(edge["relationClass"],"EXPLICIT_SOURCE_REFERENCE")
            self.assertEqual(edge["scientificVerdict"],"NOT_TOPA_ADJUDICATED")
            self.assertEqual(edge["targetId"],f"json:{7:024x}")
            self.assertTrue(result2["complete"])

    def test_corrupt_shard_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);self.fixture(root)
            f=root/"assets/janus-json-atlas/shards/0001.json"
            f.write_bytes(f.read_bytes()+b"X")
            with self.assertRaisesRegex(ValueError,"CATALOG_SHARD_SHA_MISMATCH"):
                m.read_catalog(root)

if __name__=="__main__":unittest.main()
