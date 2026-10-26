/* JANUS JSON Constellation – one bounded, read-only HRAiN/iNaiHR mindmap.
   Source-of-truth remains immutable commit-pinned GitHub JSON. Path-token
   neighbours in iNaiHR are ASSOCIATIVE_CANDIDATES, never verified evidence.
   All generated shards are SHA-256 verified before appearing as navigable.
*/
(()=>{'use strict';
const BASE='https://raw.githubusercontent.com/Hawkar-usls/Hrain/main/assets/janus-json-atlas/';
const SCHEMA='janus.hrain.github_json_constellation_manifest.v1';
const SEMANTIC=document.body.dataset.lens==='semantic';
const state={manifest:null,records:new Map(),loaded:new Set(),current:null,repo:'',query:'',busy:false};
const $=id=>document.getElementById(id);
const svgNS='http://www.w3.org/2000/svg';
const fmt=n=>new Intl.NumberFormat().format(n||0);
function status(v,bad=false){const e=$('status');e.textContent=v;e.classList.toggle('error',!!bad)}
function element(tag,text,cls){const e=document.createElement(tag);if(text!=null)e.textContent=String(text);if(cls)e.className=cls;return e}
function safeURL(u){try{const x=new URL(u);if(x.origin==='https://github.com'&&x.pathname.startsWith('/Hawkar-usls/'))return x.href;}catch(_){}
  return null}
async function sha(text){const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
return [...new Uint8Array(b)].map(v=>v.toString(16).padStart(2,'0')).join('')}
async function getText(url){const x=await fetch(url,{cache:'no-store'});if(!x.ok)throw Error('HTTP_'+x.status);return x.text()}
function verifyRoot(m){if(m.schema!==SCHEMA||m.authority?.readOnly!==true||m.authority?.sourceMutationAllowed!==false||
 m.authority?.writeAuthority!==false||m.privateRepositoriesIncluded!==false||m.metadataOnly!==true||
 !Array.isArray(m.repositories)||!Array.isArray(m.shards)||m.shardCount!==m.shards.length)throw Error('CONSTELLATION_AUTHORITY_OR_SCHEMA_FAIL_CLOSED')}
async function boot(){
 try{status('Loading immutable public catalog index…');const m=JSON.parse(await getText(BASE+'manifest.json'));verifyRoot(m);state.manifest=m;
 const select=$('repositories');m.repositories.forEach(r=>{const o=element('option',r.repository+' · '+fmt(r.jsonCount));o.value=r.repository;select.appendChild(o)});
 $('count').textContent=fmt(m.jsonCount)+' JSON · '+fmt(m.repositoryCount)+' public repos';
 $('stamp').textContent='Snapshot: '+(m.generatedAt||'unknown');
 $('lens-title').textContent=SEMANTIC?'iNaiHR · ASSOCIATIVE CONTEXT':'HRAiN · STRUCTURAL CONTEXT';
 status('Read-only snapshot · select a repository or search all');
 const p=new URLSearchParams(location.search), repo=p.get('repo'),id=p.get('focus');
 if(repo&&m.repositories.some(r=>r.repository===repo)){select.value=repo;await loadRepo(repo);if(id&&state.records.has(id))selectRecord(state.records.get(id));}
 draw();
 }catch(e){status('HOLD: '+e.message,true)}
}
async function verifyShard(shard){
 if(state.loaded.has(shard.index))return;
 const t=await getText(BASE+shard.path.replace('assets/janus-json-atlas/',''));
 if(await sha(t)!==shard.sha256)throw Error('SHARD_HASH_MISMATCH:'+shard.index);
 const d=JSON.parse(t);
 if(d.schema!=='janus.hrain.github_json_constellation_shard.v1'||d.repository!==shard.repository||
 d.records?.length!==shard.count||d.readOnly!==true)throw Error('SHARD_CONTRACT_MISMATCH:'+shard.index);
 const meta=state.manifest.repositories.find(r=>r.repository===shard.repository);
 if(!meta||d.sourceCommit!==meta.commit)throw Error('SHARD_COMMIT_MISMATCH:'+shard.index);
 for(const x of d.records){if(!x.readOnly||x.deleteAllowed!==false||x.repository!==shard.repository||
 !safeURL(x.sourceUrl)||!x.sourceUrl.includes('/blob/'+x.sourceCommit+'/')||!x.path.endsWith('.json'))
 throw Error('UNSAFE_SOURCE_RECORD:'+shard.index);
 if(state.records.has(x.id))throw Error('DUPLICATE_NODE_ID:'+x.id);
 }
 for(const x of d.records)state.records.set(x.id,x);
 state.loaded.add(shard.index);
}
async function loadRepo(repo){
 if(state.busy)return;
 if(!state.manifest)return;
 const name=repo==='ALL'?'':repo;
 state.busy=true;const b=$('load');b.disabled=true;
 try{const shards=state.manifest.shards.filter(s=>!name||s.repository===name);
 for(let i=0;i<shards.length;i+=5){
  await Promise.all(shards.slice(i,i+5).map(verifyShard));
  status('Verified '+state.loaded.size+'/'+state.manifest.shardCount+' shards · '+fmt(state.records.size)+' JSON');
 }
 state.repo=name;
 fillResults();draw();
 }catch(e){status('FAIL CLOSED: '+e.message,true)}
 finally{state.busy=false;b.disabled=false}
}
function split(p){return p.toLowerCase().replace(/([a-z])([A-Z])/g,'$1 $2').split(/[^a-zа-яіїєґ0-9]+/iu)
 .filter(x=>x.length>=3&&!new Set(['json','data','2026','v1','janus','github','meta','registry','tools','assets','source','true','false']).has(x))}
function associations(record,cap=8){
 const base=new Set(split(record.path));
 const pool=[];
 for(const r of state.records.values()){
  if(r.id===record.id)continue;
  const overlap=[...new Set(split(r.path))].filter(x=>base.has(x));
  if(overlap.length<2)continue;
  const score=overlap.length/(Math.sqrt(base.size||1)*Math.sqrt(new Set(split(r.path)).size||1));
  pool.push({record:r,score,overlap});
 }
 return pool.sort((a,b)=>b.score-a.score||a.record.path.localeCompare(b.record.path)).slice(0,cap)
}
function fillResults(){
 const list=$('results');list.replaceChildren();
 const q=state.query.trim().toLowerCase();
 const rows=[...state.records.values()].filter(x=>(!state.repo||x.repository===state.repo)
  &&(!q||(x.path+' '+x.repository+' '+(x.memoryClass||'')).toLowerCase().includes(q)))
  .sort((a,b)=>a.repository.localeCompare(b.repository)||a.path.localeCompare(b.path));
 $('visible').textContent=fmt(rows.length)+' matching files';
 for(const r of rows.slice(0,180)){
  const b=element('button',null,'result');b.type='button';
  b.append(element('span',r.path,'path'));
  b.append(element('small',r.repository,'source'));
  b.onclick=()=>selectRecord(r);
  list.appendChild(b);
 }
 if(rows.length>180)list.append(element('p','Showing first 180 results — refine search.','hint'));
 if(!rows.length)list.append(element('p','No verified JSON files match. Select a repository or load all.','hint'));
}
function selectRecord(record){
 state.current=record;const det=$('detail');det.replaceChildren();
 det.append(element('h2',record.path.split('/').pop()));
 const meta=element('p',record.repository+' · '+(record.memoryClass||'PUBLIC_JSON')+' · '+fmt(record.sizeBytes)+' bytes','meta');
 det.append(meta);
 const provenance=element('code',record.repository+'@'+record.sourceCommit+':'+record.path,'provenance');det.append(provenance);
 const warning=element('p','Source metadata only. A semantic neighbour is a candidate, not evidence or authorization.','warning');det.append(warning);
 const href=safeURL(record.sourceUrl);
 if(href){const link=element('a','OPEN EXACT GITHUB JSON ↗','source-link');link.href=href;link.target='_blank';link.rel='noopener noreferrer';det.append(link)}
 const candidates=associations(record);
 det.append(element('h3',SEMANTIC?'iNaiHR · candidate connections':'Neighbouring JSONs · candidate only'));
 const related=element('div',null,'related');
 for(const x of candidates){const b=element('button',null,'related-item');b.type='button';
  b.append(element('span',x.record.path,'path'));
  b.append(element('small',x.overlap.join(' · ')+' · candidate (unverified)','source'));
  b.onclick=()=>selectRecord(x.record);related.append(b);
 }
 if(!candidates.length)related.append(element('p','Load more source shards to inspect cross-repository neighbours.','hint'));
 det.append(related);
 const other=element('a',SEMANTIC?'OPEN HRAiN STRUCTURAL VIEW ↗':'OPEN iNaiHR SEMANTIC VIEW ↗','lens-link');
 other.href=(SEMANTIC?'https://hawkar-usls.github.io/Hrain/janus-map.html':'https://hawkar-usls.github.io/iNaiHR/janus-map.html')+
 '?repo='+encodeURIComponent(record.repository)+'&focus='+encodeURIComponent(record.id);
 other.rel='noopener noreferrer';other.target='_blank';det.append(other);
 draw();
}
function addSvg(tag,attrs,parent,text){
 const n=document.createElementNS(svgNS,tag);
 for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,String(v));
 if(text!=null)n.textContent=String(text);
 (parent||$('graph')).appendChild(n);return n
}
function draw(){
 const svg=$('graph');svg.replaceChildren();
 const nodes=[];
 const edge=(ax,ay,bx,by,dashed)=>addSvg('line',{x1:ax,y1:ay,x2:bx,y2:by,stroke:dashed?'#bc83e8':'#4bcbae',
 'stroke-width':dashed?1.4:2.3,'stroke-dasharray':dashed?'6 6':''},svg);
 const node=(x,y,label,kind,onClick)=>{
 const g=addSvg('g',{'class':'map-node '+kind,transform:`translate(${x},${y})`},svg);
 addSvg('circle',{r:kind==='core'?43:27},g);
 const short=String(label).slice(0,25);
 addSvg('text',{'text-anchor':'middle',y:5},g,short);
 if(onClick)g.addEventListener('click',onClick);
 };
 if(!state.manifest){node(480,280,'JANUS','core');return}
 if(!state.current){
  node(480,280,'JANUS','core');
  state.manifest.repositories.forEach((r,i)=>{
   const angle=2*Math.PI*i/state.manifest.repositories.length;
   const x=480+Math.cos(angle)*340,y=280+Math.sin(angle)*220;
   edge(480,280,x,y,false);
   node(x,y,r.repository.split('/')[1],'repo',()=>{$('repositories').value=r.repository;loadRepo(r.repository)})
  });
  return
 }
 const r=state.current;
 const segments=r.path.split('/');
 const folder=segments.slice(0,2).join('/')||'(root)';
 edge(145,280,365,280,false);edge(365,280,615,280,false);
 node(145,280,r.repository.split('/')[1],'repo',()=>loadRepo(r.repository));
 node(365,280,folder,'folder');
 node(615,280,r.path.split('/').pop(),'focus');
 const near=associations(r,5);
 near.forEach((c,i)=>{
  const theta=(i-(near.length-1)/2)*0.35;
  const x=850,y=280+Math.sin(theta)*430;
  edge(650,280,x-27,y,SEMANTIC);
  node(x,y,c.record.path.split('/').pop(),'candidate',()=>selectRecord(c.record));
 });
}
function wire(){
 $('repositories').addEventListener('change',async e=>{const repo=e.target.value;if(repo)await loadRepo(repo);else{state.repo='';fillResults();draw()}});
 $('load').addEventListener('click',()=>loadRepo($('repositories').value||'ALL'));
 $('all').addEventListener('click',()=>loadRepo('ALL'));
 $('query').addEventListener('input',e=>{state.query=e.target.value;fillResults()});
 $('query').addEventListener('keydown',e=>{if(e.key==='Enter')loadRepo('ALL')});
 $('reset').addEventListener('click',()=>{state.current=null;draw();$('detail').replaceChildren(element('p','Choose a JSON node.','hint'))});
}
document.addEventListener('DOMContentLoaded',()=>{wire();boot()});
})();