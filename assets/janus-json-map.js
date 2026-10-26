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

// Explicit opt-in byte-verification: data is untrusted, never executed or
// promoted to evidence. Only HTTPS raw content at the exact indexed commit.
const SOURCE_MAX_BYTES=2_000_000;
function sourceRawUrl(r){
 const owner=/^Hawkar-usls\/[a-zA-Z0-9_.-]+$/;
 const revision=/^[0-9a-f]{40}$/;
 if(!owner.test(r.repository)||!revision.test(r.sourceCommit)||typeof r.path!=='string'||
    r.path.length>512||!r.path.endsWith('.json')||
    r.path.split('/').some(p=>!p||p==='.'||p==='..'||p.includes('\\'))||
    !/^https:\/\/github\.com\/Hawkar-usls\//.test(r.sourceUrl||'')||
    !r.readOnly||r.deleteAllowed!==false)throw Error('UNTRUSTED_SOURCE_POINTER');
 const uri=r.path.split('/').map(encodeURIComponent).join('/');
 const expected='https://github.com/'+r.repository+'/blob/'+r.sourceCommit+'/'+uri;
 if(r.sourceUrl!==expected)throw Error('UNTRUSTED_OR_UNPINNED_ORIGIN');
 if(!Number.isSafeInteger(r.sizeBytes)||r.sizeBytes<1||r.sizeBytes>SOURCE_MAX_BYTES)throw Error('SOURCE_TOO_LARGE_TO_DIVE');
 return 'https://raw.githubusercontent.com/'+r.repository+'/'+r.sourceCommit+'/'+uri;
}
async function bytesDigest(algorithm,buf){
 const hashed=await crypto.subtle.digest(algorithm,buf);
 return [...new Uint8Array(hashed)].map(b=>b.toString(16).padStart(2,'0')).join('');
}
async function loadVerifiedSourceJSON(record){
 const raw=sourceRawUrl(record);
 const response=await fetch(raw,{cache:'no-store',headers:{Accept:'application/json'}});
 if(!response.ok)throw Error('PINNED_SOURCE_HTTP_'+response.status);
 const contentLength=Number(response.headers.get('content-length')||'0');
 if(contentLength>SOURCE_MAX_BYTES)throw Error('SOURCE_HTTP_LENGTH_EXCEEDS_CAP');
 const reader=response.body?.getReader();
 const pieces=[];let total=0;
 if(reader){
  while(true){const {done,value}=await reader.read();if(done)break;
   total+=value.byteLength;
   if(total>SOURCE_MAX_BYTES){await reader.cancel();throw Error('SOURCE_STREAM_EXCEEDS_CAP')}
   pieces.push(value);
  }
 }else{
  const ab=await response.arrayBuffer();total=ab.byteLength;
  if(total>SOURCE_MAX_BYTES)throw Error('SOURCE_RESPONSE_EXCEEDS_CAP');
  pieces.push(new Uint8Array(ab));
 }
 if(total!==record.sizeBytes)throw Error('SOURCE_LENGTH_CHANGED_FROM_GITHUB_TREE');
 const bytes=new Uint8Array(total);let at=0;
 for(const part of pieces){bytes.set(part,at);at+=part.byteLength}
 // Git blob prefix uses the NUL separator of Git's loose blob representation.
 const truePrefix=new TextEncoder().encode('blob '+total+String.fromCharCode(0));
 const blob=new Uint8Array(truePrefix.byteLength+total);
 blob.set(truePrefix);blob.set(bytes,truePrefix.byteLength);
 const actualGit=await bytesDigest('SHA-1',blob);
 if(!/^[0-9a-f]{40}$/.test(record.gitBlobSha||'')||record.gitBlobSha!==actualGit)
  throw Error('PINNED_GIT_BLOB_SHA_MISMATCH');
 const actualSha=await bytesDigest('SHA-256',bytes);
 if(record.sourceSha256!==null&&record.sourceSha256!==undefined){
  if(!/^[0-9a-f]{64}$/.test(record.sourceSha256)||record.sourceSha256!==actualSha)
   throw Error('META_REGISTRY_SHA256_MISMATCH');
 }
 const decoded=new TextDecoder('utf-8',{fatal:true}).decode(bytes);
 return {value:JSON.parse(decoded),sha256:actualSha,blob:actualGit,bytes:total,url:raw};
}
function jsonPointerSegments(root){
 const out=[];const visited=new Set();
 function rec(v,path,depth){
  if(out.length>=160||depth>7)return;
  if(v===null||typeof v!=='object'){
   out.push({pointer:path,type:v===null?'null':typeof v,
             value:JSON.stringify(v)});return;
  }
  if(visited.has(v))return;visited.add(v);
  const entries=Array.isArray(v)?v.map((x,i)=>[String(i),x]):Object.entries(v);
  if(entries.length===0)out.push({pointer:path,type:Array.isArray(v)?'array':'object',value:'(empty)'});
  for(const [key,x] of entries.slice(0,100)){
   if(out.length>=160)break;
   rec(x,path+'/'+key.replaceAll('~','~0').replaceAll('/','~1'),depth+1);
  }
 }
 rec(root,'',0);return out;
}
async function showVerifiedFields(record,box){
 box.replaceChildren(element('p','Fetching exact commit-pinned JSON and validating Git blob identity…','hint'));
 try{
  const v=await loadVerifiedSourceJSON(record);
  if(state.current?.id!==record.id)return;
  const fields=jsonPointerSegments(v.value);
  box.replaceChildren();
  box.append(element('p','VERIFIED SOURCE BYTES · SHA-256 '+v.sha256.slice(0,20)+'… · '+fmt(v.bytes)+' bytes','verified'));
  box.append(element('p',fields.length+' displayed JSON leaf pointers · exact Git blob '+v.blob.slice(0,16)+'…','hint'));
  const q=element('input',null,'field-filter');q.type='search';q.placeholder='Filter source JSON keys/values…';
  q.setAttribute('aria-label','Filter verified JSON pointer records');box.append(q);
  const results=element('div',null,'verified-records');box.append(results);
  function render(){
   results.replaceChildren();
   const needle=q.value.toLowerCase();
   for(const row of fields.filter(r=>(r.pointer+' '+r.value).toLowerCase().includes(needle)).slice(0,60)){
    const el=element('div',null,'verified-field');
    el.append(element('code',row.pointer||'(root)','verified-pointer'));
    el.append(element('div',(row.value||'').slice(0,450),'verified-value'));
    results.append(el);
   }
   if(!results.childElementCount)results.append(element('p','No matching verified field in the bounded preview.','hint'));
  }
  q.addEventListener('input',render);render();
 }catch(err){
  if(state.current?.id===record.id){
   box.replaceChildren(element('p','FAIL CLOSED · '+err.message+' — source not displayed.','warning'));
  }
 }
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
 const verifyBtn=element('button','VERIFY + DIVE INTO SOURCE JSON','source-dive');verifyBtn.type='button';
 const verifiedPane=element('div',null,'verified-pane');
 verifyBtn.onclick=()=>{verifyBtn.disabled=true;showVerifiedFields(record,verifiedPane).finally(()=>{verifyBtn.disabled=false})};
 det.append(verifyBtn,verifiedPane);
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