#!/usr/bin/env python3
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

UA = 'JANUS-HRain-Vernier-Plate-LXXXVII/1.0'

def get(url, timeout=40):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {'status': r.status, 'content_type': r.headers.get('content-type',''), 'body': r.read()}
    except Exception as e:
        return {'status': 0, 'error': repr(e), 'body': b''}

def main():
    out = {'schema':'hrain.vernier.plate_lxxxvii_locator.v1','queries':{},'candidates':[],'errors':[]}

    # Gallica SRU broad title/author search.
    queries = [
        'dc.title all "Bijoux et orfevreries" and dc.creator all "Vernier"',
        'dc.title all "Bijoux et orfèvreries" and dc.creator all "Vernier"',
        'gallica all "Bijoux et orfèvreries"',
    ]
    for i,q in enumerate(queries):
        url='https://gallica.bnf.fr/SRU?' + urllib.parse.urlencode({
            'version':'1.2','operation':'searchRetrieve','query':q,
            'maximumRecords':'50','startRecord':'1'
        })
        r=get(url)
        txt=r['body'].decode('utf-8',errors='replace')
        out['queries'][f'gallica_sru_{i}']={'url':url,'status':r['status'],'raw':txt[:60000]}

    # Google Books API.
    gurl='https://www.googleapis.com/books/v1/volumes?' + urllib.parse.urlencode({
        'q':'intitle:"Bijoux et orfèvreries" inauthor:"Emile Vernier"','maxResults':'40'
    })
    r=get(gurl)
    gtxt=r['body'].decode('utf-8',errors='replace')
    out['queries']['google_books']={'url':gurl,'status':r['status'],'raw':gtxt[:120000]}
    try:
        gd=json.loads(gtxt)
        for item in gd.get('items',[]):
            vi=item.get('volumeInfo',{})
            out['candidates'].append({
                'provider':'google_books','id':item.get('id'),'title':vi.get('title'),
                'subtitle':vi.get('subtitle'),'publishedDate':vi.get('publishedDate'),
                'pageCount':vi.get('pageCount'),'infoLink':vi.get('infoLink'),
                'accessInfo':item.get('accessInfo',{}),
            })
    except Exception as e:
        out['errors'].append({'provider':'google_books','error':repr(e)})

    # Internet Archive Advanced Search.
    iaq='title:("Bijoux et orfevreries" OR "Bijoux et orfèvreries") AND creator:(Vernier)'
    iaurl='https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({
        'q':iaq,'fl[]':['identifier','title','creator','date','description'],
        'rows':'100','page':'1','output':'json'
    }, doseq=True)
    r=get(iaurl)
    iatxt=r['body'].decode('utf-8',errors='replace')
    out['queries']['internet_archive']={'url':iaurl,'status':r['status'],'raw':iatxt[:120000]}
    try:
        iad=json.loads(iatxt)
        for doc in iad.get('response',{}).get('docs',[]):
            doc['provider']='internet_archive'
            out['candidates'].append(doc)
    except Exception as e:
        out['errors'].append({'provider':'internet_archive','error':repr(e)})

    # Open Library search as another identifier bridge.
    olurl='https://openlibrary.org/search.json?' + urllib.parse.urlencode({'title':'Bijoux et orfèvreries','author':'Emile Vernier','limit':'50'})
    r=get(olurl)
    oltxt=r['body'].decode('utf-8',errors='replace')
    out['queries']['openlibrary']={'url':olurl,'status':r['status'],'raw':oltxt[:120000]}
    try:
        old=json.loads(oltxt)
        for doc in old.get('docs',[]):
            out['candidates'].append({'provider':'openlibrary','key':doc.get('key'),'title':doc.get('title'),'edition_key':doc.get('edition_key'),'ia':doc.get('ia'),'publish_year':doc.get('publish_year')})
    except Exception as e:
        out['errors'].append({'provider':'openlibrary','error':repr(e)})

    p=Path('/tmp/vernier-plate-locator')
    p.mkdir(parents=True, exist_ok=True)
    (p/'VERNIER_PLATE_LXXXVII_LOCATOR.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':True,'candidate_count':len(out['candidates']),'errors':len(out['errors'])}))

if __name__=='__main__':
    main()
