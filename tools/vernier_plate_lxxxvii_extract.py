#!/usr/bin/env python3
import io
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

IDENT='VernierBijouxII'
UA='JANUS-HRain-Vernier-LXXXVII-Extract/1.0'
OUT=Path('/tmp/vernier-lxxxvii')
OUT.mkdir(parents=True, exist_ok=True)

def get(url, timeout=90):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.status,r.headers.get('content-type',''),r.read()

def main():
    meta_url=f'https://archive.org/metadata/{IDENT}'
    status,ctype,data=get(meta_url)
    meta=json.loads(data.decode('utf-8'))
    files=meta.get('files',[])
    listing=[]
    for f in files:
        name=f.get('name','')
        if any(x in name.lower() for x in ['pdf','djvu','scandata','text','abbyy']):
            listing.append({k:f.get(k) for k in ['name','size','format','md5','sha1']})
    (OUT/'IA_FILE_LIST.json').write_text(json.dumps({'identifier':IDENT,'metadata_url':meta_url,'files':listing},indent=2)+'\n')

    # Prefer a text/pdf derivative; fall back to any PDF.
    pdfs=[f for f in files if f.get('name','').lower().endswith('.pdf')]
    preferred=None
    for suffix in ['_text.pdf','_bw.pdf','.pdf']:
        cand=[f for f in pdfs if f.get('name','').lower().endswith(suffix)]
        if cand:
            preferred=sorted(cand,key=lambda x:int(x.get('size') or 10**18))[0]
            break
    if not preferred:
        raise SystemExit('NO_PDF_DERIVATIVE')
    pdfname=preferred['name']
    pdf_url=f'https://archive.org/download/{IDENT}/{pdfname}'
    status,ctype,pdf=get(pdf_url,timeout=180)
    pdfpath=OUT/'VernierBijouxII.pdf'
    pdfpath.write_bytes(pdf)

    # Basic PDF info.
    info=subprocess.run(['pdfinfo',str(pdfpath)],capture_output=True,text=True,check=True).stdout
    m=re.search(r'^Pages:\s+(\d+)',info,re.M)
    pages=int(m.group(1)) if m else None
    (OUT/'PDFINFO.txt').write_text(info)

    # Extract all text cheaply; often plate captions/roman numerals are OCRed.
    subprocess.run(['pdftotext','-layout',str(pdfpath),str(OUT/'all.txt')],check=True)
    text=(OUT/'all.txt').read_text(errors='replace')
    hits=[]
    for pat in [r'LXXXVII',r'53469',r'5346[5-9]',r'Mend[eè]s']:
        for mm in re.finditer(pat,text,re.I):
            hits.append({'pattern':pat,'start':mm.start(),'context':text[max(0,mm.start()-500):mm.start()+1200]})
    (OUT/'TEXT_HITS.json').write_text(json.dumps(hits,ensure_ascii=False,indent=2)+'\n')

    # Plate 87 should be in the latter portion. Render a broad candidate window.
    # The volume has introductory index pages before the plates; use text hits if pdftotext exposes page form-feeds.
    candidate_pages=set()
    chunks=text.split('\f')
    for idx,ch in enumerate(chunks, start=1):
        if re.search(r'LXXXVII|53469|5346[5-9]',ch,re.I):
            candidate_pages.update(range(max(1,idx-2),min((pages or idx)+1,idx+3)+1))
    if not candidate_pages and pages:
        # Heuristic: plate 87 near frontmatter + 87; render a generous 20-page window around likely location.
        center=max(1,pages-113+87)
        candidate_pages.update(range(max(1,center-8),min(pages,center+8)+1))

    render_dir=OUT/'renders'; render_dir.mkdir(exist_ok=True)
    rendered=[]
    for p in sorted(candidate_pages):
        prefix=render_dir/f'p{p:03d}'
        subprocess.run(['pdftoppm','-f',str(p),'-singlefile','-jpeg','-jpegopt','quality=92','-r','180',str(pdfpath),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        jpg=str(prefix)+'.jpg'
        if Path(jpg).exists(): rendered.append(Path(jpg).name)
    result={
        'identifier':IDENT,'pdf_file':pdfname,'pdf_url':pdf_url,'pdf_bytes':len(pdf),'pages':pages,
        'text_hits':hits,'candidate_pdf_pages':sorted(candidate_pages),'rendered':rendered,
    }
    (OUT/'VERNIER_PLATE_LXXXVII_EXTRACT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'ok':True,'pdf':pdfname,'bytes':len(pdf),'pages':pages,'candidates':sorted(candidate_pages),'hits':len(hits)}))

if __name__=='__main__': main()
