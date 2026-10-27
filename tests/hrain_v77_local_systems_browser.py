"""Genuine v77 D3: locally projected Genesis/BFain, then full graph restore; no writes."""
import importlib.util
import json
import pathlib
import tempfile
import threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("safe_reader",ROOT/"tools/hrain_v77_readonly_bridge.py")
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)

def run():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td);logs=root/"raw_logs";logs.mkdir()
        nodes={f"n{i}":{"type":"ally","data":{"label":f"Source Node {i}","x":i*10,"y":i*10}} for i in range(4)}
        links={f"n0->n{i}":{"weight":1} for i in range(1,4)}
        snapshot=logs/"hrain_graph_state.json"
        snapshot.write_text(json.dumps({"nodes":nodes,"edges":links,"tick":15}))
        (logs/"janus_world_state.json").write_text(json.dumps({
            "level":7,"inventory":[],"limbs":[],"base_upgrades":{},
            "faction_reputation":{},"self_model":{"private":"SENSITIVE_DUMMY"}}))
        (logs/"janus_world_agents.json").write_text(json.dumps({
            "population":[{},{}],"memory":[{"private":"SENSITIVE_DUMMY"}],"tick":91}))
        server=ThreadingHTTPServer(("127.0.0.1",0),reader.make_handler(ROOT,snapshot))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                page=browser.new_page(viewport={"width":1440,"height":900})
                writes=[];errors=[]
                page.on("request",lambda r:writes.append(r.url) if r.method in ("POST","PUT","PATCH","DELETE") else None)
                page.on("pageerror",lambda e:errors.append(str(e)))
                page.goto(f"http://127.0.0.1:{server.server_port}/hrain-v77.html",
                          wait_until="domcontentloaded",timeout=30000)
                page.wait_for_function("typeof App!=='undefined'&&App.globalNodes.length===4&&App.globalLinks.length===3",
                                       timeout=30000)
                assert not page.evaluate("window.JANUSAtlasViewActive")
                assert page.locator("#btn-v77-local-systems").count()==1
                page.locator("#btn-v77-local-systems").click()
                page.wait_for_function("window.JANUSAtlasViewActive&&App.globalNodes.length===4&&" +
                                       "App.globalNodes.some(n=>n.id==='local:allstar')",timeout=20000)
                assert page.evaluate("App.globalLinks.every(e=>e.kind==='local-derived')")
                assert page.evaluate("App.globalLinks.length")==3
                assert not page.evaluate("App.globalNodes.some(n=>n.description?.includes('SENSITIVE_DUMMY'))")
                page.evaluate("App.createNode()")
                assert page.evaluate("App.globalNodes.length")==4
                page.locator("#btn-v77-return").click()
                page.wait_for_function("!window.JANUSAtlasViewActive&&App.globalNodes.length===4&&" +
                                       "App.globalNodes.some(n=>n.id==='n0')",timeout=14000)
                assert page.evaluate("App.globalLinks.length")==3
                assert not writes,writes
                assert not errors,errors
                print("JANUS_ORIGINAL_V77_LOCAL_GENESIS_CONTEXT_RESTORE_READONLY_BROWSER_PASS",flush=True)
                browser.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)

if __name__=="__main__":
    run()
