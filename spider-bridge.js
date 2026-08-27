(() => {
  'use strict';
  const DB_NAME = 'hrain_spider_v1';
  const STORE = 'packages';
  const KEY = 'latest';

  function openDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE);
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function putPackage(pkg) {
    const db = await openDB();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put(pkg, KEY);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
    db.close();
    return pkg;
  }

  async function getPackage() {
    const db = await openDB();
    const value = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const req = tx.objectStore(STORE).get(KEY);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
    db.close();
    return value;
  }

  async function clearPackage() {
    const db = await openDB();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).delete(KEY);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  }

  function validatePackage(pkg) {
    if (!pkg || typeof pkg !== 'object') throw new Error('Package must be an object');
    if (pkg.schema !== 'hawkar.topa.spider.hrain_package.v1') throw new Error('Unsupported SPIDER package schema');
    if (!Array.isArray(pkg.nodes) || !Array.isArray(pkg.edges)) throw new Error('Package nodes/edges missing');
    return pkg;
  }

  function importFile(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = async () => {
        try {
          const pkg = validatePackage(JSON.parse(r.result));
          await putPackage(pkg);
          resolve(pkg);
        } catch (e) { reject(e); }
      };
      r.onerror = () => reject(r.error);
      r.readAsText(file);
    });
  }

  function passIds(pkg) {
    const seen = new Set();
    const out = [];
    for (const e of pkg.edges || []) {
      for (const h of e.history || []) {
        const p = String(h.pass_id ?? '');
        if (p && !seen.has(p)) { seen.add(p); out.push(p); }
      }
    }
    return out;
  }

  function edgeAtPass(edge, passId) {
    if (!passId || passId === 'CURRENT') return edge;
    const hit = (edge.history || []).filter(h => String(h.pass_id) === String(passId)).pop();
    if (!hit) return null;
    return {
      ...edge,
      weight: Number(hit.weight ?? edge.weight ?? 0),
      previous_weight: Number(hit.previous_weight ?? edge.previous_weight ?? 0),
      target_weight: hit.target_weight,
      movement: hit.movement || edge.movement,
      observed_this_pass: hit.observed_this_pass,
      pass_id: hit.pass_id
    };
  }

  function visibleGraph(pkg, opts = {}) {
    const passId = opts.passId || 'CURRENT';
    const minWeight = Number(opts.minWeight ?? 0.30);
    const relation = opts.relation || 'ALL';
    const query = String(opts.query || '').trim().toLowerCase();
    const maxEdges = Math.max(50, Number(opts.maxEdges ?? 4000));
    const nodeById = new Map((pkg.nodes || []).map(n => [String(n.id), n]));
    let edges = [];
    for (const original of pkg.edges || []) {
      const e = edgeAtPass(original, passId);
      if (!e) continue;
      if (Number(e.weight || 0) < minWeight) continue;
      if (relation !== 'ALL' && e.relation !== relation) continue;
      edges.push(e);
    }
    edges.sort((a,b) => Number(b.weight||0) - Number(a.weight||0));
    if (edges.length > maxEdges) edges = edges.slice(0, maxEdges);
    let keep = new Set();
    for (const e of edges) { keep.add(String(e.source)); keep.add(String(e.target)); }
    let nodes = [...keep].map(id => nodeById.get(id) || {id, label:id, type:'unknown'});
    if (query) {
      const match = new Set(nodes.filter(n => `${n.label||''} ${n.id||''} ${n.type||''}`.toLowerCase().includes(query)).map(n => String(n.id)));
      const expanded = new Set(match);
      for (const e of edges) {
        if (match.has(String(e.source)) || match.has(String(e.target))) {
          expanded.add(String(e.source)); expanded.add(String(e.target));
        }
      }
      edges = edges.filter(e => expanded.has(String(e.source)) && expanded.has(String(e.target)));
      nodes = [...expanded].map(id => nodeById.get(id) || {id,label:id,type:'unknown'});
    }
    return {nodes, edges, passId, minWeight, relation, truncatedEdges: Math.max(0, (pkg.edges||[]).length - edges.length)};
  }

  function relations(pkg) {
    return [...new Set((pkg.edges || []).map(e => e.relation).filter(Boolean))].sort();
  }

  function edgeHistory(edge) {
    return (edge.history || []).map(h => ({
      pass_id: h.pass_id,
      weight: h.weight,
      delta: h.delta,
      movement: h.movement,
      observed_this_pass: h.observed_this_pass,
      fresh_evidence_signature: h.fresh_evidence_signature,
      independence_count: h.independence_count,
      topology_support: h.topology_support
    }));
  }

  function nodeFur(node) {
    if (!node || typeof node !== 'object') return null;
    if (!node.context_fur) return null;
    return {
      coverage: node.fur_coverage || {score:0},
      facets: node.context_fur || {},
      history: node.fur_history || [],
      acquisitionQueue: node.fur_acquisition_queue || []
    };
  }

  function furSummary(node) {
    const f=nodeFur(node);
    if(!f) return {available:false,coverage:0,statusCounts:{},pending:0,conflicts:0};
    const statusCounts={}; let conflicts=0;
    for(const facet of Object.values(f.facets||{})) {
      const s=facet.status||'UNKNOWN'; statusCounts[s]=(statusCounts[s]||0)+1;
      conflicts += (facet.conflicts||[]).length;
    }
    return {available:true,coverage:Number(f.coverage?.score||0),statusCounts,pending:(f.acquisitionQueue||[]).length,conflicts};
  }

  function furFacet(node, name) {
    const f=nodeFur(node); return f?.facets?.[name] || null;
  }

  window.HRainSpiderBridge = {
    laws: [
      'HRAIN_VISUAL_WEIGHT_IS_NOT_TRUTH',
      'GRAPH_EDGE_IS_NOT_CAUSATION',
      'REPLAY_IS_NOT_NEW_EVIDENCE',
      'HRAIN_DOES_NOT_WRITE_BACK_TO_ARCHIVE_SOURCE',
      'CONTEXT_COMPLETENESS_IS_NOT_CLAIM_STRENGTH',
      'UNKNOWN_STAYS_UNKNOWN'
    ],
    importFile, validatePackage, putPackage, getPackage, clearPackage,
    passIds, edgeAtPass, visibleGraph, relations, edgeHistory,
    nodeFur, furSummary, furFacet
  };
})();
