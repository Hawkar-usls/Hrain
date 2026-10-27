"""Live published GitHub Pages native JANUS source-graph smoke test.
Requires playwright + Chromium. No fixtures, no writes, no synthetic relations.
"""
from playwright.sync_api import sync_playwright

URLS=[
 "https://hawkar-usls.github.io/Hrain/janus.html",
 "https://hawkar-usls.github.io/iNaiHR/janus.html",
]
NEEDLE="COSMOS-ALI-V2-LATTICE-TOF-PROTOCOL-2026-10-18"
def run():
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for url in URLS:
   page=browser.new_page(viewport={"width":1440,"height":900})
   errors=[];page.on("pageerror",lambda err:errors.append(str(err)))
   page.goto(url,wait_until="domcontentloaded",timeout=45000)
   page.wait_for_selector(".janus-native-atlas-launch",timeout=30000)
   page.wait_for_function("document.querySelector('#loading')?.classList.contains('hidden')",timeout=30000)
   assert page.locator("svg").count(),url+": ORIG_D3_MISSING"
   page.locator(".janus-native-atlas-launch").click()
   page.wait_for_function("!document.querySelector('#janus-atlas-drawer').hidden",timeout=10000)
   page.wait_for_function("document.querySelector('#janus-atlas-repo').options.length>=15",timeout=25000)
   page.select_option("#janus-atlas-repo","Hawkar-usls/Janus-Cosmos")
   page.wait_for_function("document.querySelectorAll('#janus-atlas-results .janus-atlas-hit').length>=2",timeout=25000)
   page.locator("#janus-atlas-query").fill(NEEDLE)
   page.wait_for_function("document.querySelector('#janus-atlas-shown').textContent.startsWith('1 matching')",timeout=10000)
   page.locator("#janus-atlas-results .janus-atlas-hit").first.click()
   page.get_by_role("button",name="INDEXED LINKS · FULL PUBLIC CATALOG").click()
   page.wait_for_function("document.querySelector('#janus-atlas-focus')?.textContent.includes('DIRECT edges') || document.querySelector('#janus-atlas-focus')?.textContent.includes('RELATION INDEX HOLD')",timeout=30000)
   text=page.locator("#janus-atlas-focus").inner_text()
   assert "RELATION INDEX HOLD" not in text,(url,text[:1500])
   assert "19,621 / 19,624" in text,(url,text[:1500])
   assert "5,838 DIRECT edges" in text,(url,text[:1500])
   assert "/sources/prior_v1/url" in text,(url,text[:1500])
   assert "TOPA scientific claims remain NOT ADJUDICATED" in text,(url,text[:1500])
   page.get_by_role("button",name="VERIFY ALL TARGET SHARDS & PROJECT SOURCE EDGES").click()
   page.wait_for_function("document.querySelector('#janus-atlas-drawer').hidden",timeout=40000)
   page.wait_for_function("document.querySelectorAll('.link[data-source-pointer=\"/sources/prior_v1/url\"]').length>0",timeout=25000)
   if "iNaiHR" in url:
    assert page.locator("#btn-synth").evaluate("(e)=>!e.classList.contains('active')"),"SYNTH_AUTHORITY_DRIFT"
   page.evaluate("window.JANUSAtlasNativeRestore()")
   assert not errors,(url,errors)
   print("JANUS_FULL_PUBLIC_LIVE_BROWSER_PASS",url,flush=True)
   page.close()
  browser.close()
if __name__=="__main__":run()
