(() => {
  'use strict';
  const LANG_KEY='janus-site-language-v1';
  const L={
    en:{grid:'GRID',origin:'ORIGIN',wipe:'WIPE LOCAL DESK',ascend:'▲ ASCEND',dive:'DIVE',mode:'REGISTRY MODE',detail:'READ ONLY · APPEND-ONLY SOURCE',loading:'CONNECTING TO JANUS META REGISTRY…',source:'OPEN SOURCE ↗',surface:'OPEN SURFACE ↗',semantic:'SYNTH → iNaiHR',boundary:'<b>HRAIN_GRAPH != REGISTRY_AUTHORITY.</b> WIPE clears only this local view. No HRaiN control can delete, rewrite, or mutate JANUS Meta Registry source objects.'},
    ua:{grid:'СІТКА',origin:'ПОЧАТОК',wipe:'ОЧИСТИТИ ЛОКАЛЬНИЙ СТІЛ',ascend:'▲ ВИЩЕ',dive:'ЗАНУРИТИСЯ',mode:'РЕЖИМ РЕЄСТРУ',detail:'ЛИШЕ ЧИТАННЯ · ДЖЕРЕЛО ДОДАЄТЬСЯ, НЕ СТИРАЄТЬСЯ',loading:'ПІДКЛЮЧЕННЯ ДО JANUS META REGISTRY…',source:'ВІДКРИТИ ДЖЕРЕЛО ↗',surface:'ВІДКРИТИ НАПРЯМ ↗',semantic:'СИНТЕЗ → iNaiHR',boundary:'<b>HRAIN_GRAPH != REGISTRY_AUTHORITY.</b> Очищення стосується лише локального виду. HRaiN не може видаляти, переписувати або змінювати вихідні об’єкти JANUS Meta Registry.'},
    ru:{grid:'СЕТКА',origin:'НАЧАЛО',wipe:'ОЧИСТИТЬ ЛОКАЛЬНЫЙ СТОЛ',ascend:'▲ ВЫШЕ',dive:'ПОГРУЗИТЬСЯ',mode:'РЕЖИМ РЕЕСТРА',detail:'ТОЛЬКО ЧТЕНИЕ · ИСТОЧНИК ДОПОЛНЯЕТСЯ, НЕ СТИРАЕТСЯ',loading:'ПОДКЛЮЧЕНИЕ К JANUS META REGISTRY…',source:'ОТКРЫТЬ ИСТОЧНИК ↗',surface:'ОТКРЫТЬ НАПРАВЛЕНИЕ ↗',semantic:'СИНТЕЗ → iNaiHR',boundary:'<b>HRAIN_GRAPH != REGISTRY_AUTHORITY.</b> Очистка касается только локального вида. HRaiN не может удалять, переписывать или изменять исходные объекты JANUS Meta Registry.'}
  };
  let lang=readLang();
  function readLang(){const v=localStorage.getItem(LANG_KEY);return v==='ua'||v==='ru'?v:'en'}
  function text(id,value){const n=document.getElementById(id);if(n)n.textContent=value}
  function ensureUi(){
    if(document.querySelector('.janus-langbar'))return;
    const style=document.createElement('style');
    style.textContent='.janus-langbar{position:absolute;top:112px;left:28px;z-index:25;display:flex;gap:4px;pointer-events:auto}.janus-langbar button{border:0;background:transparent;color:#536a64;font:700 .68rem Orbitron;cursor:pointer;padding:3px 5px}.janus-langbar button.active{color:#7cf0c6;text-shadow:0 0 10px rgba(0,255,163,.35)}@media(max-width:760px){.janus-langbar{top:100px;left:12px}}';
    document.head.appendChild(style);
    const bar=document.createElement('div');bar.className='janus-langbar ui-interactive';
    [['en','EN'],['ua','UA'],['ru','ru']].forEach(([k,label])=>{const b=document.createElement('button');b.type='button';b.dataset.lang=k;b.textContent=label;b.onclick=()=>{lang=k;localStorage.setItem(LANG_KEY,k);apply()};bar.appendChild(b)});
    const layer=document.querySelector('.ui-layer');if(layer)layer.appendChild(bar);
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
    translatePanel();
  }
  ensureUi();apply();
  const panelButtons=document.getElementById('panel-buttons');if(panelButtons)new MutationObserver(translatePanel).observe(panelButtons,{childList:true,subtree:true});
  window.addEventListener('storage',e=>{if(e.key===LANG_KEY){lang=readLang();apply()}});
})();
