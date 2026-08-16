#!/usr/bin/env python3
from __future__ import annotations
import json, re, urllib.request
from pathlib import Path

ARK='bpt6k5774000v'
OUT=Path('/tmp/vernier-genital-v25')
OUT.mkdir(parents=True,exist_ok=True)
UA='JANUS-HRain-Vernier-Genital-Corpus/2.5'

TERMS=[
    r'phall\w*', r'p[ée]nis', r'testic\w*', r'scrot\w*', r'g[ée]nital\w*',
    r'cache\s*[- ]?sexe', r'sexe\s+f[ée]minin', r'enveloppe', r'parties?\s+g[ée]nital\w*'
]
MENDES_NUMS=[str(n) for n in range(53464,53476)]
JE_TERMS=[str(n) for n in range(35418,35431)]

def fetch(url, timeout=90):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read().decode('utf-8','replace')

def contexts(text, pattern, radius=900):
    out=[]
    for m in re.finditer(pattern,text,re.I):
        a=max(0,m.start()-radius); b=min(len(text),m.end()+radius)
        out.append(text[a:b])
    return out

def first_context(text, needle, radius=1300):
    m=re.search(re.escape(needle),text,re.I)
    if not m: return None
    return text[max(0,m.start()-radius):min(len(text),m.end()+radius)]

def clean(s):
    return re.sub(r'\s+',' ',s).strip() if s else None

def main():
    url=f'https://gallica.bnf.fr/ark:/12148/{ARK}.texteBrut'
    text=fetch(url)
    result={
      'schema':'hrain.vernier_genital_gold_corpus.v2_5',
      'source':{'ark':ARK,'url':url,'chars':len(text)},
      'term_hits':{},
      'mendes_53464_53475':{},
      'je_neighborhood':{},
      'explicit_controls':{},
      'derived_findings':[],
      'claim_ceiling':'CATALOGUE_CORPUS_ONLY__NO_RELIC_IDENTITY_INFERENCE'
    }
    for pat in TERMS:
        result['term_hits'][pat]=[clean(x) for x in contexts(text,pat)[:30]]

    for num in MENDES_NUMS:
        result['mendes_53464_53475'][num]=clean(first_context(text,num))
    for je in JE_TERMS:
        result['je_neighborhood'][je]=clean(first_context(text,je,800))

    for num in ['53469','53745']:
        result['explicit_controls'][num]=clean(first_context(text,num,1800))

    tnorm=re.sub(r'\s+',' ',text)
    if re.search(r'53745.{0,160}Cache sexe.{0,100}f[ée]minin.{0,100}or',tnorm,re.I):
        result['derived_findings'].append({
          'id':'CG53745_GOLD_FEMALE_GENITAL_COVER',
          'status':'OCR_SUPPORTED',
          'statement':'CG 53745 is indexed as a gold female genital cover/cache-sexe from Saqqara.'
        })
    if re.search(r'53469.{0,200}Enveloppe.{0,100}phall',tnorm,re.I):
        result['derived_findings'].append({
          'id':'CG53469_GOLD_PHALLUS_SHEATH',
          'status':'OCR_SUPPORTED',
          'statement':'CG 53469 is indexed as a gold phallus sheath/envelope from Mendes.'
        })
    result['derived_findings'].append({
      'id':'MENDES_SISTER_OBJECT_NEIGHBORHOOD',
      'status':'EXTRACTED_FOR_MANUAL_RESOLUTION',
      'statement':'CG 53464–53475 and JE 35418–35430 contexts were extracted to test whether companion gold genital elements were separately catalogued under neutral labels.'
    })

    (OUT/'VERNIER_GENITAL_GOLD_CORPUS_v2_5.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'MENDES_SISTER_OBJECT_CONTEXTS.txt').open('w',encoding='utf-8') as f:
        for n,c in result['mendes_53464_53475'].items():
            f.write(f'===== CG {n} =====\n{c or "NOT FOUND"}\n\n')
        for je,c in result['je_neighborhood'].items():
            f.write(f'===== JE {je} =====\n{c or "NOT FOUND"}\n\n')
    print('VERNIER_GENITAL_CORPUS_OK')
    print('OUT='+str(OUT))

if __name__=='__main__':
    main()
