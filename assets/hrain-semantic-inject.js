(() => {
  'use strict';

  const OVERLAY_URL = 'https://raw.githubusercontent.com/Hawkar-usls/Hrain/janus/hrain-semantic-state/assets/hrain-semantic-overlay.json';
  const EXPECTED_SCHEMA = 'janus.hrain.topa_semantic_overlay.v1';
  const SEMANTIC_COLOR = '#54d6ff';
  const MAX_WAIT_MS = 20000;
  const startedAt = Date.now();
  let semanticPairs = new Set();
  let semanticEdgeCount = 0;
  let installed = false;

  const edgeKey = (a, b) => [String(a), String(b)].sort().join('::');

  function nodeDegreeMap() {
    const degree = new Map();
    for (const n of globalNodes || []) degree.set(String(n.id), 0);
    for (const l of globalLinks || []) {
      const a = String(l.source && l.source.id ? l.source.id : l.source);
      const b = String(l.target && l.target.id ? l.target.id : l.target);
      degree.set(a, (degree.get(a) || 0) + 1);
      degree.set(b, (degree.get(b) || 0) + 1);
    }
    return degree;
  }

  function degreeExtra(d, degree) {
    const value = Math.max(0, degree.get(String(d.id)) || 0);
    const cap = nodeKind(d) === 'object' ? 18 : 24;
    return Math.min(cap, Math.sqrt(value) * 2.8);
  }

  function coreRadius(d, degree) {
    const rootId = currentRoot();
    const base = d.id === rootId ? 36 : nodeKind(d) === 'surface' ? 28 : 24;
    return base + degreeExtra(d, degree);
  }

  function applyDegreeSizing() {
    if (typeof d3 === 'undefined' || !globalNodes || !globalLinks) return;
    const degree = nodeDegreeMap();
    const nodes = d3.select('#chart').selectAll('.node-group');
    nodes.select('.neuron-core').attr('r', d => coreRadius(d, degree));
    nodes.select('.neuron-aura').attr('r', d => coreRadius(d, degree) * 1.9);
    nodes.select('.neuron-membrane').attr('r', d => coreRadius(d, degree) * 2.28);
    nodes.select('.label').attr('dy', d => coreRadius(d, degree) + 20);

    d3.select('#chart').selectAll('.link')
      .style('stroke', d => semanticPairs.has(edgeKey(d.source.id || d.source, d.target.id || d.target)) ? SEMANTIC_COLOR : null)
      .style('color', d => semanticPairs.has(edgeKey(d.source.id || d.source, d.target.id || d.target)) ? SEMANTIC_COLOR : null)
      .style('stroke-dasharray', d => semanticPairs.has(edgeKey(d.source.id || d.source, d.target.id || d.target)) ? '3 4' : null)
      .style('opacity', d => semanticPairs.has(edgeKey(d.source.id || d.source, d.target.id || d.target)) ? 0.52 : null);

    if (typeof sim !== 'undefined') {
      sim.force('collide', d3.forceCollide()
        .radius(d => {
          const r = coreRadius(d, degree);
          return Math.max(nodeKind(d) === 'root' ? 95 : nodeKind(d) === 'surface' ? 82 : 68, r * 2.45);
        })
        .strength(1)
        .iterations(3));
    }
  }

  function installRenderHook() {
    if (installed) return;
    installed = true;
    const baseRender = render;
    render = function semanticAwareRender(...args) {
      const value = baseRender.apply(this, args);
      applyDegreeSizing();
      return value;
    };
  }

  function validateOverlay(overlay) {
    if (!overlay || overlay.schema !== EXPECTED_SCHEMA || overlay.status !== 'READY') throw new Error('TOPA overlay schema/status mismatch');
    if (!sourceIndex || overlay.sourceCommit !== sourceIndex.sourceCommit) throw new Error('TOPA overlay is stale for current registry sourceCommit');
    if (!Array.isArray(overlay.edges)) throw new Error('TOPA overlay edges missing');
    if (Number(overlay.edgeCount || 0) !== overlay.edges.length) throw new Error('TOPA overlay edgeCount mismatch');
    if (!overlay.authority || overlay.authority.readOnly !== true || overlay.authority.registryWriteAuthority !== false || overlay.authority.claimPromotionAuthority !== false) {
      throw new Error('TOPA overlay authority contract violated');
    }
    const ids = new Set((sourceIndex.nodes || []).filter(n => String(n.id).startsWith('obj:')).map(n => String(n.id)));
    const basePairs = new Set((sourceIndex.links || []).map(l => edgeKey(l.source, l.target)));
    const seen = new Set();
    const degree = new Map();
    const cap = Number(overlay.maxSemanticDegree || 0);
    for (const edge of overlay.edges) {
      const a = String(edge.source || ''), b = String(edge.target || '');
      const key = edgeKey(a, b);
      if (!ids.has(a) || !ids.has(b) || a === b || seen.has(key) || basePairs.has(key)) throw new Error('TOPA overlay invalid endpoint/duplicate');
      if (edge.relation !== 'TOPA_SEMANTIC_SIMILARITY' || edge.readOnly !== true || edge.claimVerified !== false || Number(edge.evidenceWeight) !== 0) throw new Error('TOPA overlay semantic authority violation');
      seen.add(key);
      degree.set(a, (degree.get(a) || 0) + 1);
      degree.set(b, (degree.get(b) || 0) + 1);
    }
    if (cap < 1 || [...degree.values()].some(v => v > cap)) throw new Error('TOPA overlay degree cap violation');
  }

  async function attachOverlay() {
    const response = await fetch(`${OVERLAY_URL}?t=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`TOPA overlay unavailable: HTTP ${response.status}`);
    const overlay = await response.json();
    validateOverlay(overlay);

    semanticPairs = new Set(overlay.edges.map(e => edgeKey(e.source, e.target)));
    semanticEdgeCount = overlay.edges.length;
    sourceIndex.links = [...sourceIndex.links, ...overlay.edges.map(e => ({ source: e.source, target: e.target }))];
    cloneRuntime();
    installRenderHook();
    updateView();
    applyDegreeSizing();
    sim.alpha(0.9).restart();

    const sourceState = document.getElementById('source-state');
    const stats = document.getElementById('stats-text');
    if (sourceState) sourceState.textContent = 'JANUS UPLINK · TOPA WEAVE';
    if (stats) stats.textContent = `${sourceIndex.objectCount || 0} objects · ${sourceIndex.nodeCount || globalNodes.length} nodes · +${semanticEdgeCount} semantic · ${String(overlay.topaHeadSha || '').slice(0, 8)}`;
    console.info('[HRAiN/TOPA] semantic overlay attached', {
      sourceCommit: overlay.sourceCommit,
      topaHeadSha: overlay.topaHeadSha,
      edgeCount: semanticEdgeCount,
      overlayHash: overlay.overlayHash,
    });
  }

  async function waitAndAttach() {
    if (typeof sourceIndex === 'undefined' || sourceIndex === null || typeof cloneRuntime !== 'function' || typeof updateView !== 'function' || typeof render !== 'function') {
      if (Date.now() - startedAt < MAX_WAIT_MS) return void setTimeout(waitAndAttach, 200);
      console.warn('[HRAiN/TOPA] base graph did not become ready before timeout');
      return;
    }
    try {
      await attachOverlay();
    } catch (error) {
      // Fail closed to the verified hierarchy projection. Semantic overlay is optional enrichment.
      console.warn('[HRAiN/TOPA] overlay ignored fail-closed:', error && error.message ? error.message : error);
    }
  }

  waitAndAttach();
})();
