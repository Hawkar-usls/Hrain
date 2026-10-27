"""Live Chromium regression of authentic HRAiN v77; no JANUS server writes."""
import http.server
import socketserver
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PORT=8943
def run():
    server=subprocess.Popen([sys.executable,"-m","http.server",str(PORT),"--bind","127.0.0.1",
                             "--directory",str(ROOT)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(0.75)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":1440,"height":900})
            errors=[]
            request_writes=[]
            page.on("pageerror",lambda err:errors.append(str(err)))
            page.on("request",lambda req:request_writes.append((req.method,req.url))
                    if req.method in ("POST","PUT","PATCH","DELETE") else None)
            page.goto(f"http://127.0.0.1:{PORT}/hrain-v77.html",wait_until="domcontentloaded",timeout=30000)
            page.wait_for_function("window.App?.globalNodes?.length>=4 || typeof App!=='undefined'&&App.globalNodes.length>=4",timeout=30000)
            page.wait_for_function("document.querySelectorAll('svg .node-group').length>=2",timeout=30000)
            assert "v77" in page.title().lower(),page.title()
            # ASCEND is deliberately hidden until DIVE; locator still exists.
            assert page.locator("#btn-ascend").count()==1
            assert page.get_by_role("button",name="✨ SYNTH · GATED").count()>=1
            assert page.get_by_role("button",name="↓ EXPORT DRAFT").count()>=1
            assert page.locator(".janus-native-atlas-launch").count()==1
            assert page.evaluate("App.globalNodes.length")==4
            page.evaluate("App.selectedNode=App.globalNodes.find(x=>x.id==='janus');App.dive()")
            page.wait_for_function("document.querySelectorAll('svg .node-group').length>=3",timeout=10000)
            page.evaluate("App.ascend()")
            page.wait_for_function("App.contextStack.length===0",timeout=10000)
            # Stress source-compatible v89 density without leaking private graph.
            page.evaluate("""() => {
              window.JANUSTestOriginal={nodes:App.globalNodes,links:App.globalLinks};
              const nodes=Array.from({length:100},(_,i)=>({id:'synthetic_'+i,label:'Node '+i,
                  parentId:null,type:'ally',emoji:'🤖',x:100+i*4,y:150+i*3}));
              const links=[];
              for(let i=0;i<100;i++)for(let j=0;j<100;j++){
                if(i!==j&&links.length<9737)links.push({source:'synthetic_'+i,target:'synthetic_'+j,weight:1});
              }
              App.globalNodes=nodes;App.globalLinks=links;App.contextStack=[];
              App.selectedNode=null;App.updateView();
            }""")
            page.wait_for_function("document.querySelectorAll('#chart .link').length===750",timeout=22000)
            assert page.evaluate("App.globalLinks.length")==9737
            assert page.evaluate("App.viewLinks.length")==750
            assert page.locator("#hrain-render-status").inner_text().find("9,737 total in memory")>=0
            page.evaluate("""() => {
              App.globalNodes=window.JANUSTestOriginal.nodes;
              App.globalLinks=window.JANUSTestOriginal.links;
              App.updateView();
            }""")
            before=page.evaluate("App.globalNodes.length")
            page.evaluate("App.createNode()")
            assert page.evaluate("App.globalNodes.length")==before+1
            assert page.evaluate("!!sessionStorage.getItem('janus_hrain_v77_local_draft_v1')")
            # Original live backend commands must be gated despite UI affordances.
            page.evaluate("Nerve.synthNode()")
            assert not request_writes,request_writes
            page.evaluate("App.log('<img src=x onerror=alert(1)>','info')")
            assert page.locator("#neural-log img").count()==0
            old_count=page.evaluate("App.globalNodes.length")
            page.evaluate("""() => {
                window.JANUSAtlasNativeFocus([
                    {id:'json:a',path:'source.json',repository:'Hawkar-usls/Hrain',
                     sourceCommit:'a'.repeat(40),readOnly:true,deleteAllowed:false},
                    {id:'json:b',path:'target.json',repository:'Hawkar-usls/TOPA',
                     sourceCommit:'b'.repeat(40),readOnly:true,deleteAllowed:false}],
                    [{sourceId:'json:a',targetId:'json:b',pointer:'/research/source~1json',
                     evidence:'explicit-json-url'}]);
            }""")
            page.wait_for_function("document.querySelectorAll('.link[data-source-pointer]').length===1",timeout=14000)
            assert page.evaluate("window.JANUSAtlasViewActive")
            page.evaluate("App.createNode();Nerve.push(true)")
            assert page.evaluate("App.globalNodes.length")==2
            page.evaluate("window.JANUSAtlasNativeRestore()")
            assert page.evaluate("App.globalNodes.length")==old_count
            assert not page.evaluate("window.JANUSAtlasViewActive")
            assert not request_writes,request_writes
            # Prove the v77 D3 renderer accepts a TRUE SHA-indexed Cosmos edge,
            # not only a hand-written graph fixture.
            # The original v77 create-node gesture opens a modal; close it
            # before invoking the separate Atlas navigation control.
            page.evaluate("document.getElementById('rename-modal').style.display='none'")
            page.locator(".janus-native-atlas-launch").click()
            page.wait_for_function("!document.querySelector('#janus-atlas-drawer').hidden",timeout=10000)
            page.wait_for_function("document.querySelector('#janus-atlas-repo').options.length>=15",timeout=30000)
            page.select_option("#janus-atlas-repo","Hawkar-usls/Janus-Cosmos")
            page.wait_for_function("document.querySelectorAll('#janus-atlas-results .janus-atlas-hit').length>=2",timeout=30000)
            page.locator("#janus-atlas-query").fill("COSMOS-ALI-V2-LATTICE-TOF-PROTOCOL-2026-10-18")
            page.wait_for_function("document.querySelector('#janus-atlas-shown').textContent.startsWith('1 matching')",timeout=12000)
            page.locator("#janus-atlas-results .janus-atlas-hit").first.click()
            page.get_by_role("button",name="INDEXED LINKS · FULL PUBLIC CATALOG").click()
            page.wait_for_function("document.querySelector('#janus-atlas-focus')?.textContent.includes('DIRECT edges')||document.querySelector('#janus-atlas-focus')?.textContent.includes('RELATION INDEX HOLD')",timeout=32000)
            panel=page.locator("#janus-atlas-focus").inner_text()
            assert "RELATION INDEX HOLD" not in panel,panel[:1800]
            assert "/sources/prior_v1/url" in panel,panel[:1800]
            assert "TOPA scientific claims remain NOT ADJUDICATED" in panel
            page.get_by_role("button",name="VERIFY ALL TARGET SHARDS & PROJECT SOURCE EDGES").click()
            page.wait_for_function("document.querySelector('#janus-atlas-drawer').hidden",timeout=45000)
            page.wait_for_function("document.querySelectorAll('.link[data-source-pointer=\"/sources/prior_v1/url\"]').length>0",timeout=18000)
            assert page.evaluate("window.JANUSAtlasViewActive")
            page.evaluate("window.JANUSAtlasNativeRestore()")
            assert page.evaluate("App.globalNodes.length")==old_count
            assert not request_writes,request_writes
            assert not errors,errors
            print("HRAIN_V77_AUTHENTIC_D3_DIVE_LOCAL_DRAFT_ATLAS_READONLY_AND_REAL_CORPUS_PASS",flush=True)
            page.close()
            browser.close()
    finally:
        server.terminate()

if __name__=="__main__":run()
