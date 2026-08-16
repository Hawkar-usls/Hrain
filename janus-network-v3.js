(() => {
  'use strict';
  const LANG_KEY='janus-site-language-v1';
  const L={
    en:{grid:'GRID',origin:'ORIGIN',wipe:'WIPE LOCAL DESK',ascend:'▲ ASCEND',dive:'DIVE',mode:'REGISTRY MODE',detail:'READ ONLY · APPEND-ONLY SOURCE',loading:'CONNECTING TO JANUS META REGISTRY…',source:'OPEN SOURCE ↗',surface:'OPEN SURFACE ↗',semantic:'SYNTH → iNaiHR',boundary:'<b>HRAIN_GRAPH != REGISTRY_AUTHORITY.</b> WIPE clears only this local view. No HRaiN control can delete, rewrite, or mutate JANUS Meta Registry source objects.'},
    ua:{grid:'СІТКА',origin:'ПОЧАТОК',wipe:'ОЧИСТИТИ ЛОКАЛЬНИЙ СТІЛ',ascend:'▲ ВИЩЕ',dive:'ЗАНУРИТИСЯ',mode:'РЕЖИМ РЕЄСТРУ',detail:'ЛИШЕ ЧИТАННЯ · ДЖЕРЕЛО ДОДАЄТЬСЯ, НЕ СТИРАЄТЬСЯ',loading:'ПІДКЛЮЧЕННЯ ДО JANUS META REGISTRY…',source:'ВІДКРИТИ ДЖЕРЕЛО ↗',surface:'ВІДКРИТИ НАПРЯМ ↗',semantic:'СИНТЕЗ → iNaiHR',boundary:'<b>HRAIN_GRAPH != REGISTRY_AUTHORITY.</b> Очищення стосується лише локального виду. HRaiN не може видаляти, переписувати або змінювати вихідні об’єкти JANUS Meta Registry.'},
    ru:{grid:'РЕШЁТКА ИЗ ПОДВАЛА',origin:'ВЕРНУТЬСЯ К ТАБУРЕТКЕ',wipe:'СМАХНУТЬ КРОШКИ С ЛОКАЛЬНОГО СТОЛА',ascend:'▲ ВЫЛЕЗТИ ИЗ НОРЫ',dive:'НЫРНУТЬ В JSON ПО ПОЯС',mode:'СВЯТОКРИНЖОВЫЙ РЕЕСТР',detail:'ТОЛЬКО ЧТЕНИЕ · ИСТОЧНИК НЕ ТРОГАТЬ ЖИРНЫМИ ПАЛЬЦАМИ',loading:'ПОДКЛЮЧАЕМ JANUS К УДЛИНИТЕЛЮ, НЕ ДЫШИ…',source:'ОТКРЫТЬ СЕРЬЁЗНЫЙ ИСТОЧНИК ↗',surface:'ОТКРЫТЬ ЕЩЁ ОДИН ПОДВАЛ ↗',semantic:'СИНТЕЗНУТЬ ЭТО В iNaiHR ↗',boundary:'<b>HRAIN_GRAPH != REGISTRY_AUTHORITY.</b> Это пародийный ru-слой: граф может выглядеть так, будто его собирали ночью на табуретке, но WIPE по-прежнему чистит только локальный вид. Исходные JSON, receipts и claim ceilings остаются нетронутыми. Где-то рядом вымышленная Ванесса Шевченко из localStorage держит пакет provenance и делает вид, что так и было задумано.'}
  };
  let lang=readLang();
  function readLang(){const v=localStorage.getItem(LANG_KEY);return v==='ua'||v==='ru'?v:'en'}
  function text(id,value){const n=document.getElementById(id);if(n)n.textContent=value}
  function ensureUi(){
    if(document.querySelector('.janus-langbar'))return;
    const style=document.createElement('style');
    style.textContent='.janus-langbar{position:absolute;top:112px;left:28px;z-index:25;display:flex;gap:4px;pointer-events:auto}.janus-langbar button{border:0;background:transparent;color:#536a64;font:700 .68rem Orbitron;cursor:pointer;padding:3px 5px}.janus-langbar button.active{color:#7cf0c6;text-shadow:0 0 10px rgba(0,255,163,.35)}.janus-holy-cringe-badge{position:absolute;left:28px;bottom:66px;z-index:26;padding:5px 8px;border:1px solid rgba(210,220,230,.35);border-radius:999px;background:linear-gradient(135deg,rgba(180,190,200,.12),rgba(5,10,14,.9));color:#c9d3da;font:700 .62rem Orbitron;letter-spacing:.06em;pointer-events:none}@media(max-width:760px){.janus-langbar{top:100px;left:12px}.janus-holy-cringe-badge{left:12px;bottom:58px;font-size:.52rem}}';
    document.head.appendChild(style);
    const bar=document.createElement('div');bar.className='janus-langbar ui-interactive';
    [['en','EN'],['ua','UA'],['ru','ru']].forEach(([k,label])=>{const b=document.createElement('button');b.type='button';b.dataset.lang=k;b.textContent=label;b.onclick=()=>{lang=k;localStorage.setItem(LANG_KEY,k);apply()};bar.appendChild(b)});
    const layer=document.querySelector('.ui-layer');if(layer)layer.appendChild(bar);
  }
  function ensureRuBadge(){
    const layer=document.querySelector('.ui-layer');if(!layer)return;
    let badge=document.querySelector('.janus-holy-cringe-badge');
    if(lang!=='ru'){if(badge)badge.remove();return;}
    if(!badge){badge=document.createElement('div');badge.className='janus-holy-cringe-badge';badge.textContent='△ ru · СВЯТОЙ КРИНЖ · ПАРОДИЙНЫЙ СЛОЙ';badge.title='Presentation only. Registry source remains authoritative and unchanged.';layer.appendChild(badge)}
  }
  function translatePanel(){
    const P=L[lang];
    const buttons=document.getElementById('panel-buttons');if(!buttons)return;
    buttons.querySelectorAll('a').forEach(a=>{
      if(a.dataset.semanticSynth==='true')a.textContent=P.semantic;
      else if(a.href.includes('/janus-meta-registry/blob/'))a.textContent=P.source;
      else if(a.href.includes('hawkar-usls.github.io/janus-meta-registry/'))a.textContent=P.surface;
    });
  }
  function apply(){
    const P=L[lang];document.documentElement.lang=lang==='ua'?'uk':lang;
    document.querySelectorAll('.janus-langbar button').forEach(b=>b.classList.toggle('active',b.dataset.lang===lang));
    text('btn-grid',P.grid);text('btn-home',P.origin);text('btn-wipe',P.wipe);text('btn-ascend',P.ascend);text('btn-dive',P.dive);text('loading',P.loading);
    const m=document.querySelector('.mode b');if(m)m.textContent=P.mode;const d=document.querySelector('.mode i');if(d)d.textContent=P.detail;
    const boundary=document.querySelector('.boundary');if(boundary)boundary.innerHTML=P.boundary;
    ensureRuBadge();translatePanel();
  }
  ensureUi();apply();
  const panelButtons=document.getElementById('panel-buttons');if(panelButtons)new MutationObserver(translatePanel).observe(panelButtons,{childList:true,subtree:true});
  window.addEventListener('storage',e=>{if(e.key===LANG_KEY){lang=readLang();apply()}});
})();
