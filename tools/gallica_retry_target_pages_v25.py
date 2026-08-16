#!/usr/bin/env python3
import html as htmlmod, json, re, time, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
ARK='bpt6k5774000v'
PAGES=[86,117,118,126,127]
OUT=Path('/tmp/gallica-retry-v25'); OUT.mkdir(parents=True,exist_ok=True)
UA='JANUS-HRain-Gallica-Paced-Retry/2.5'

def fetch(url):
    last=None
    for attempt in range(5):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':UA})
            with urllib.request.urlopen(req,timeout=45) as r: return r.status,r.read()
        except Exception as e:
            last=e; time.sleep(4+attempt*3)
    raise last

def alto_to_text(x):
    root=ET.fromstring(x)
    words=[]
    for el in root.iter():
        if el.tag.rsplit('}',1)[-1]=='String':
            v=el.attrib.get('CONTENT') or el.attrib.get('content')
            if v: words.append(htmlmod.unescape(v))
    return re.sub(r'\s+',' ',' '.join(words)).strip()

def main():
    out={'schema':'hrain.gallica_paced_retry.v2_5','pages':{},'errors':[]}
    for p in PAGES:
        url=f'https://gallica.bnf.fr/RequestDigitalElement?O={ARK}&E=ALTO&Deb={p}'
        try:
            st,data=fetch(url); txt=alto_to_text(data.decode('utf-8','replace'))
            out['pages'][str(p)]={'status':st,'url':url,'text':txt}
            (OUT/f'PAG_{p}_OCR.txt').write_text(txt+'\n',encoding='utf-8')
        except Exception as e: out['errors'].append({'page':p,'error':repr(e)})
        time.sleep(4)
    (OUT/'GALLICA_RETRY_TARGET_PAGES_v2_5.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':not out['errors'],'errors':out['errors']},ensure_ascii=False))
if __name__=='__main__': main()
