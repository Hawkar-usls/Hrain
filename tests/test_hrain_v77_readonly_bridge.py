"""All Star v89 -> restored v77 GET-only loopback bridge regression."""
import hashlib
import http.client
import importlib.util
import json
import pathlib
import tempfile
import threading
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("v77_bridge",ROOT/"tools/hrain_v77_readonly_bridge.py")
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

class SourceBridge(unittest.TestCase):
    def sample(self,path):
        nodes={f"n{i}":{"id":f"n{i}","type":"ally",
            "data":{"label":f"Synthetic {i}","x":i*2,"y":i*4,"parentId":None}} for i in range(100)}
        edges={}
        for i in range(100):
            for j in range(100):
                if i!=j and len(edges)<9737:
                    edges[f"n{i}->n{j}"]={"weight":0.75,"direction":"bidir"}
        body=json.dumps({"nodes":nodes,"edges":edges,"tick":31625}).encode()
        path.write_bytes(body)
        return hashlib.sha256(body).hexdigest()

    def test_exact_counts_sha_and_loopback_readonly(self):
        with tempfile.TemporaryDirectory() as td:
            path=pathlib.Path(td)/"private.json";digest=self.sample(path)
            doc=v.load_snapshot(path)
            self.assertEqual(len(doc["nodes"]),100)
            self.assertEqual(len(doc["links"]),9737)
            self.assertEqual(doc["meta"]["sourceSha256"],digest)
            self.assertFalse(doc["meta"]["authoritativeWritesEnabled"])
            from http.server import ThreadingHTTPServer
            srv=ThreadingHTTPServer(("127.0.0.1",0),v.make_handler(ROOT,path))
            thread=threading.Thread(target=srv.serve_forever,daemon=True)
            thread.start()
            try:
                def req(method,target,host=None):
                    conn=http.client.HTTPConnection("127.0.0.1",srv.server_port,timeout=15)
                    conn.request(method,target,headers={"Host":host or f"127.0.0.1:{srv.server_port}"})
                    r=conn.getresponse();content=r.read();conn.close()
                    return r.status,content
                status,body=req("GET","/api/hrain/state")
                self.assertEqual(status,200)
                obj=json.loads(body)
                self.assertEqual((len(obj["nodes"]),len(obj["links"])),(100,9737))
                self.assertEqual(req("POST","/api/hrain/save")[0],405)
                self.assertEqual(req("POST","/api/janus/action")[0],405)
                self.assertEqual(req("POST","/api/hrain/event")[0],405)
                self.assertEqual(req("GET","/api/hrain/state","evil.example")[0],403)
                self.assertEqual(req("GET","/../raw_logs/hrain_graph_state.json")[0],404)
                self.assertEqual(req("GET","/")[0],200)
                self.assertEqual(req("GET","/assets/janus-native-atlas.js")[0],200)
            finally:
                srv.shutdown();srv.server_close();thread.join(timeout=3)

    def test_no_unvalidated_transforms(self):
        with tempfile.TemporaryDirectory() as td:
            path=pathlib.Path(td)/"test.json"
            path.write_text(json.dumps({"nodes":{"n":{"type":"ally","data":{}}},
                                        "edges":{"n->missing":{"weight":1}}}))
            with self.assertRaisesRegex(v.SnapshotError,"EDGE_TARGET_MISSING"):
                v.load_snapshot(path)
            path.write_text(json.dumps({"nodes":{},"links":[]}))
            with self.assertRaisesRegex(v.SnapshotError,"EXPECTED_ENGINE"):
                v.load_snapshot(path)
            self.assertLess(v.MAX_NODES,10000)
            self.assertEqual(v.make_handler(ROOT,None).__name__,"Handler")

if __name__=="__main__":unittest.main()
