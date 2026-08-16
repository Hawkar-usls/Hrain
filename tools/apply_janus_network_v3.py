from pathlib import Path

PATH=Path('janus.html')
s=PATH.read_text(encoding='utf-8')

old_href='href="https://hawkar-usls.github.io/iNaiHR/"'
new_href='href="https://hawkar-usls.github.io/iNaiHR/janus.html"'
if old_href in s:
    s=s.replace(old_href,new_href,1)

anchor='''    if(node.surfaceUrl){
      const a=document.createElement('a');a.href=node.surfaceUrl;a.target='_blank';a.rel='noopener';a.textContent='OPEN SURFACE ↗';buttons.appendChild(a);
    }
'''
insert='''    if(node.surfaceUrl){
      const a=document.createElement('a');a.href=node.surfaceUrl;a.target='_blank';a.rel='noopener';a.textContent='OPEN SURFACE ↗';buttons.appendChild(a);
    }
    if(node.path && node.path.endsWith('.json')){
      const a=document.createElement('a');
      a.href='https://hawkar-usls.github.io/iNaiHR/janus.html?object='+encodeURIComponent(node.path);
      a.target='_blank';a.rel='noopener';a.dataset.semanticSynth='true';a.textContent='SYNTH → iNaiHR';
      buttons.appendChild(a);
    }
'''
if "dataset.semanticSynth='true'" not in s:
    if anchor not in s:
        raise SystemExit('openPanel anchor changed; refusing unsafe patch')
    s=s.replace(anchor,insert,1)

script='  <script src="./janus-network-v3.js"></script>\n'
if script.strip() not in s:
    if '</body>' not in s:
        raise SystemExit('body close missing')
    s=s.replace('</body>',script+'</body>',1)

PATH.write_text(s,encoding='utf-8')
