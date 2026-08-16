#!/usr/bin/env python3
import html as htmlmod, json, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
ARK='bpt6k5774000v'
TERMS=['phallus','testicule','testicules','scrotum','bourse','bourses','parties génitales','parties genitales','cache-sexe','sexe féminin','sexe feminin','pénis','penis']
OUT=Path('/tmp/vernier-genital-terms-v25'); OUT.mkdir(parents=True,exist_ok=True)
UA='JANUS-HRain-Vernier-Genital-Term-Locator/2.5'

def fetch(url,timeout=45):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=timeout) as r: return r.read().decode('utf-8','replace')

def alto_text(xml):
    root=ET.fromstring(xml); w=[]
    for el in root.iter():
        if el.tag.rsplit('}',1)[-1]=='String':
            v=el.attrib.get('CONTENT') or el.attrib.get('content')
            if v: w.append(htmlmod.unescape(v))
    return re.sub(r'\s+',' ',' '.join(w)).strip()

def main():
    out={'schema':'hrain.vernier_genital_term_locator.v2_5','ark':ARK,'terms':{},'pages':{},'errors':[]}
    pages=set()
    for term in TERMS:
        try:
            url='https://gallica.bnf.fr/services/ContentSearch?'+urllib.parse.urlencode({'ark':ARK,'query':term})
            raw=fetch(url); ids=sorted(set(int(x) for x in re.findall(r'<p_id>PAG_(\d+)</p_id>',raw)))
            out['terms'][term]={'page_ids':ids}; pages.update(ids)
        except Exception as e: out['errors'].append({'stage':'search','term':term,'error':repr(e)})
        time.sleep(2)
    for p in sorted(pages):
        try:
            url=f'https://gallica.bnf.fr/RequestDigitalElement?O={ARK}&E=ALTO&Deb={p}'
            txt=alto_text(fetch(url)); out['pages'][str(p)]={'url':url,'text':txt}
        except Exception as e: out['errors'].append({'stage':'alto','page':p,'error':repr(e)})
        time.sleep(3)
    for term,d in out['terms'].items():
        hits=[]
        pat=re.compile(re.escape(term),re.I)
        for p in d['page_ids']:
            txt=(out['pages'].get(str(p)) or {}).get('text','')
            for m in pat.finditer(txt):
                hits.append({'page':p,'context':txt[max(0,m.start()-800):min(len(txt),m.end()+800)]})
        d['contexts']=hits
    (OUT/'VERNIER_GENITAL_TERM_LOCATOR_v2_5.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'TERM_HITS.txt').open('w',encoding='utf-8') as f:
        for term,d in out['terms'].items():
            f.write(f'===== {term} pages={d["page_ids"]} =====\n')
            for h in d['contexts']: f.write(f'[PAG_{h["page"]}] {h["context"]}\n\n')
    print(json.dumps({'ok':True,'terms':{k:v['page_ids'] for k,v in out['terms'].items()},'errors':len(out['errors'])},ensure_ascii=False))
if __name__=='__main__': main()
