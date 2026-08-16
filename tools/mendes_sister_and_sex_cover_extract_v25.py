#!/usr/bin/env python3
import html as htmlmod
import json, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ARK='bpt6k5774000v'
TARGETS=[str(n) for n in range(53464,53476)] + ['53745','53746','53747','53790','53791','53792','53793','53794']
UA='JANUS-HRain-Mendes-Sister-SexCover/2.5'
OUT=Path('/tmp/mendes-sister-v25'); OUT.mkdir(parents=True,exist_ok=True)

def fetch(url,timeout=45):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.status,r.headers.get('content-type',''),r.read()

def text_of(data): return data.decode('utf-8','replace')

def alto_to_text(xml_text):
    try: root=ET.fromstring(xml_text)
    except ET.ParseError: return ''
    words=[]
    for el in root.iter():
        if el.tag.rsplit('}',1)[-1]=='String':
            val=el.attrib.get('CONTENT') or el.attrib.get('content')
            if val: words.append(htmlmod.unescape(val))
    return re.sub(r'\s+',' ',' '.join(words)).strip()

def contexts(text,needle,radius=1000):
    out=[]
    for m in re.finditer(re.escape(needle),text,re.I):
        out.append(text[max(0,m.start()-radius):min(len(text),m.end()+radius)])
    return out

def main():
    out={'schema':'hrain.mendes_sister_sex_cover_extract.v2_5','ark':ARK,'targets':TARGETS,'page_map':{},'pages':{},'entries':{},'errors':[]}
    pages=set()
    for n in TARGETS:
        url='https://gallica.bnf.fr/services/ContentSearch?'+urllib.parse.urlencode({'ark':ARK,'query':n})
        try:
            st,ct,data=fetch(url); raw=text_of(data)
            ids=sorted(set(int(x) for x in re.findall(r'<p_id>PAG_(\d+)</p_id>',raw)))
            out['page_map'][n]=ids; pages.update(ids)
        except Exception as e: out['errors'].append({'stage':'ContentSearch','target':n,'error':repr(e)})
    for p in sorted(pages):
        url=f'https://gallica.bnf.fr/RequestDigitalElement?O={ARK}&E=ALTO&Deb={p}'
        try:
            st,ct,data=fetch(url); xml=text_of(data); plain=alto_to_text(xml)
            out['pages'][str(p)]={'url':url,'status':st,'text':plain}
            (OUT/f'PAG_{p}_OCR.txt').write_text(plain+'\n',encoding='utf-8')
        except Exception as e: out['errors'].append({'stage':'ALTO','page':p,'error':repr(e)})
    for n in TARGETS:
        hits=[]
        for p in out['page_map'].get(n,[]):
            txt=(out['pages'].get(str(p)) or {}).get('text','')
            for c in contexts(txt,n): hits.append({'page':p,'context':c})
        out['entries'][n]={'page_ids':out['page_map'].get(n,[]),'contexts':hits}
    (OUT/'MENDES_SISTER_AND_SEX_COVER_EXTRACT_v2_5.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'RESOLVED_CONTEXTS.txt').open('w',encoding='utf-8') as f:
        for n in TARGETS:
            f.write(f'===== CG {n} =====\n')
            hs=out['entries'][n]['contexts']
            if not hs: f.write('NO CONTEXT\n\n')
            else:
                for h in hs: f.write(f"[PAG_{h['page']}] {h['context']}\n\n")
    print(json.dumps({'ok':True,'pages':sorted(pages),'errors':len(out['errors'])},ensure_ascii=False))

if __name__=='__main__': main()
