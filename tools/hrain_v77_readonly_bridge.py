#!/usr/bin/env python3
"""Local-only, GET-only reader of an owner's All Star HRAiN v89 graph snapshot.

No proxy to the mutable v89 endpoints. No remote service, credentials, writes,
or publishing of actual nodes. Served HTML is the original HRAiN v77 D3 UI
hardened with browser-local draft and read-only JANUS source relations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
MAX_SNAPSHOT=32_000_000
MAX_NODES=5000
MAX_LINKS=20000
ALLOWED_FILES={
    "/":"hrain-v77.html",
    "/hrain-v77.html":"hrain-v77.html",
    "/assets/janus-native-atlas.js":"assets/janus-native-atlas.js",
    "/assets/janus-explicit-links.js":"assets/janus-explicit-links.js",
}
VALID_TYPES={"janus","ally","threat","intel","sleeper","plug","info"}

class SnapshotError(ValueError):pass

def finite(value, default=0.0):
    try:
        x=float(value)
        return x if math.isfinite(x) else default
    except (ValueError,TypeError,OverflowError):return default

def load_snapshot(path:Path):
    """Read only the owner's selected snapshot; reject ambiguous/oversized graphs."""
    if not path or not path.is_file():raise SnapshotError("SNAPSHOT_NOT_FOUND")
    size=path.stat().st_size
    if size<=0 or size>MAX_SNAPSHOT:raise SnapshotError("SNAPSHOT_SIZE_HOLD")
    body=path.read_bytes()
    if len(body)!=size:raise SnapshotError("SNAPSHOT_CHANGED_DURING_READ")
    digest=hashlib.sha256(body).hexdigest()
    try:doc=json.loads(body)
    except (UnicodeError,ValueError) as e:raise SnapshotError("INVALID_SNAPSHOT_JSON") from e
    raw_nodes=doc.get("nodes")
    raw_edges=doc.get("edges")
    if not isinstance(raw_nodes,dict) or not isinstance(raw_edges,dict):
        raise SnapshotError("EXPECTED_ENGINE_NODES_AND_EDGES_DICT")
    if len(raw_nodes)>MAX_NODES or len(raw_edges)>MAX_LINKS:
        raise SnapshotError("SOURCE_TOO_DENSE_FOR_V77_CLIENT")
    nodes=[];known=set()
    for node_id,entry in raw_nodes.items():
        if not isinstance(node_id,str) or not node_id or node_id.startswith("json:") or node_id in known:
            raise SnapshotError("UNTRUSTED_NODE_ID")
        if not isinstance(entry,dict) or not isinstance(entry.get("data"),dict):
            raise SnapshotError("UNTRUSTED_NODE_FORMAT")
        known.add(node_id)
        data=entry["data"]
        typ=entry.get("type","ally")
        if typ not in VALID_TYPES:typ="ally"
        nodes.append({
            "id":node_id,"type":typ,
            "label":str(data.get("label",node_id))[:200],
            "emoji":str(data.get("emoji","🧬"))[:12],
            "description":str(data.get("description",""))[:2000],
            "x":finite(data.get("x",0)),"y":finite(data.get("y",0)),
            "parentId":data.get("parentId") if isinstance(data.get("parentId"),str) else None,
            "level":finite(data.get("level",1),1),"score":finite(data.get("score",0.5),0.5),
        })
    links=[]
    for key,entry in raw_edges.items():
        if not isinstance(key,str) or "->" not in key:raise SnapshotError("MALFORMED_EDGE_KEY")
        src,dst=key.split("->",1)
        if src not in known or dst not in known:raise SnapshotError("EDGE_TARGET_MISSING")
        if not isinstance(entry,dict):raise SnapshotError("MALFORMED_EDGE_PAYLOAD")
        links.append({"source":src,"target":dst,"weight":finite(entry.get("weight",1),1)})
    return {"nodes":nodes,"links":links,"meta":{
        "schema":"janus.hrain.v89.readonly_snapshot.v1","readOnly":True,"authoritativeWritesEnabled":False,
        "sourceSha256":digest,"sourceBytes":size,"nodeCount":len(nodes),"linkCount":len(links),
        "tick":doc.get("tick") if isinstance(doc.get("tick"),int) else None,
        "notice":"LOCAL SNAPSHOT ONLY · NO SERVER MUTATIONS · NOT SCIENTIFIC PROOF",
    }}

def load_local_systems(snapshot:Path):
    """Local-only typed projection, NEVER call v89 or BFain HTTP."""
    if snapshot is None:
        raise SnapshotError("NO_PRIVATE_SNAPSHOT_CONFIGURED")
    p=snapshot.resolve(strict=True)
    if p.name!="hrain_graph_state.json" or p.parent.name!="raw_logs":
        raise SnapshotError("PRIVATE_SOURCE_NOT_APPROVED")
    import importlib.util
    path=Path(__file__).with_name("janus_allstar_local_projection.py")
    spec=importlib.util.spec_from_file_location("janus_private_typed_projection",path)
    if spec is None or spec.loader is None:
        raise SnapshotError("PROJECTION_MODULE_MISSING")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    obj=module.build(p.parent.parent)
    if obj.get("schema")!="janus.allstar.private_local_crosssystem_projection.v1" or (
            obj.get("authority",{}).get("readOnly") is not True):
        raise SnapshotError("LOCAL_SOURCE_AUTHORITY_HOLD")
    return obj

def make_handler(root:Path,snapshot:Path|None):
    root=root.resolve()
    class Handler(BaseHTTPRequestHandler):
        server_version="JANUS-V77-SafeReader/1"
        def _headers(self,status,size=0,mime="application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(size))
            self.send_header("Cache-Control","no-store, max-age=0")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("X-Frame-Options","DENY")
            self.send_header("Referrer-Policy","no-referrer")
            self.end_headers()
        def _body(self,status,body,mime="application/json; charset=utf-8"):
            self._headers(status,len(body),mime)
            if self.command!="HEAD":self.wfile.write(body)
        def _respond(self):
            # DNS rebinding guard: only literal local Host headers, no aliases.
            host=self.headers.get("Host","")
            if host not in (f"127.0.0.1:{self.server.server_port}",
                            f"localhost:{self.server.server_port}"):
                self._body(403,b'{"error":"LOCAL_HOST_ONLY"}')
                return
            p=urlsplit(self.path).path
            if p=="/api/janus/local-systems":
                if snapshot is None:
                    self._body(404,b'{"error":"NO_PRIVATE_SNAPSHOT_CONFIGURED"}')
                    return
                try:
                    obj=load_local_systems(snapshot)
                    payload=json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode("utf-8")
                    if len(payload)>64_000:raise SnapshotError("LOCAL_PROJECTION_SIZE_HOLD")
                    self._body(200,payload)
                except (OSError,ValueError,TypeError,ImportError,AttributeError):
                    self._body(422,b'{"error":"LOCAL_PROJECTION_INTEGRITY_HOLD"}')
                return
            if p=="/api/hrain/state":
                if snapshot is None:
                    self._body(404,b'{"error":"NO_PRIVATE_SNAPSHOT_CONFIGURED"}')
                    return
                try:
                    obj=load_snapshot(snapshot)
                    self._body(200,json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode("utf-8"))
                except (SnapshotError,OSError):
                    self._body(422,b'{"error":"SNAPSHOT_INTEGRITY_HOLD"}')
                return
            if p=="/api/hrain/status":
                try:
                    obj=load_snapshot(snapshot) if snapshot else None
                    payload={"readOnly":True,"available":bool(obj),
                             "nodeCount":len(obj["nodes"]) if obj else 0,
                             "linkCount":len(obj["links"]) if obj else 0}
                    self._body(200,json.dumps(payload).encode())
                except (OSError,SnapshotError):
                    self._body(422,b'{"error":"SNAPSHOT_INTEGRITY_HOLD"}')
                return
            relative=ALLOWED_FILES.get(p)
            if relative is None:
                self._body(404,b'{"error":"NOT_FOUND"}');return
            item=(root/relative).resolve()
            if not item.is_relative_to(root) or not item.is_file():
                self._body(404,b'{"error":"STATIC_NOT_FOUND"}');return
            mime="text/html; charset=utf-8" if item.suffix==".html" else "application/javascript; charset=utf-8"
            self._body(200,item.read_bytes(),mime)
        def do_GET(self):self._respond()
        def do_HEAD(self):self._respond()
        def do_POST(self):self._body(405,b'{"error":"METHOD_FORBIDDEN"}')
        def do_PUT(self):self._body(405,b'{"error":"METHOD_FORBIDDEN"}')
        def do_DELETE(self):self._body(405,b'{"error":"METHOD_FORBIDDEN"}')
        def do_PATCH(self):self._body(405,b'{"error":"METHOD_FORBIDDEN"}')
        def do_OPTIONS(self):self._body(405,b'{"error":"METHOD_FORBIDDEN"}')
        def log_message(self,format,*args):pass # Never log graph bodies or private paths.
    return Handler

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",type=Path,help="private All Star raw_logs/hrain_graph_state.json; NEVER uploaded")
    p.add_argument("--port",type=int,default=8812)
    p.add_argument("--verify-snapshot",action="store_true",help="read-only fingerprint and counts, no listener")
    args=p.parse_args()
    if not 1024<=args.port<=65535:raise SystemExit("INVALID_PORT")
    if args.verify_snapshot:
        if args.snapshot is None:raise SystemExit("SNAPSHOT_REQUIRED")
        obj=load_snapshot(args.snapshot)
        print(json.dumps({"status":"PASS","nodes":len(obj["nodes"]),
                          "links":len(obj["links"]),"sourceSha256":obj["meta"]["sourceSha256"]},
                         sort_keys=True))
        return
    host="127.0.0.1"
    server=ThreadingHTTPServer((host,args.port),make_handler(ROOT,args.snapshot))
    print(f"JANUS_V77_LOCAL_READONLY http://{host}:{args.port}/hrain-v77.html")
    try:server.serve_forever(poll_interval=0.5)
    finally:server.server_close()

if __name__=="__main__":main()
