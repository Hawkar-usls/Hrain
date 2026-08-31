(function (global) {
  'use strict';

  const DEFAULT_SOURCE = 'https://raw.githubusercontent.com/Hawkar-usls/Janus-Fundamentum/main/registry/PHYSARIUS_NETWORK_HRAIN_LIVE_v1.json';

  function assertGraph(graph) {
    if (!graph || graph.schema !== 'janus.hrain.physarius_graph.v1') {
      throw new Error('Unsupported Physarius graph schema');
    }
    const m = graph.mutationPolicy || {};
    const c = graph.contentPolicy || {};
    if (m.write !== false || m.delete !== false || m.sourceMutation !== false) {
      throw new Error('Physarius intake rejects graph with mutation authority');
    }
    if (c.contentExposed !== false || c.memberNamesExposed !== false) {
      throw new Error('Physarius blind intake rejects already-unblinded graph');
    }
    return graph;
  }

  function normalize(graph) {
    assertGraph(graph);
    const nodes = (graph.nodes || []).map(n => Object.freeze({
      ...n,
      readOnly: true,
      deleteAllowed: false,
      sourceMutationAllowed: false,
      provenanceRoot: graph.source_network
    }));
    const links = (graph.edges || []).map(e => Object.freeze({
      ...e,
      readOnly: true
    }));
    return Object.freeze({
      schema: 'hrain.physarius.intake.v1',
      sourceNetwork: graph.source_network,
      graphSha256: graph.graph_sha256,
      authority: 'READ_ONLY_DISCOVERY_PROJECTION',
      contentExposed: false,
      nodes,
      links
    });
  }

  async function load(source = DEFAULT_SOURCE, options = {}) {
    const response = await fetch(source, { cache: options.cache || 'no-store' });
    if (!response.ok) throw new Error(`Physarius uplink HTTP ${response.status}`);
    const graph = assertGraph(await response.json());
    const intake = normalize(graph);
    global.dispatchEvent(new CustomEvent('hrain:physarius-ready', { detail: intake }));
    return intake;
  }

  function mergeReadOnly(baseGraph, intake) {
    const baseNodes = Array.isArray(baseGraph?.nodes) ? baseGraph.nodes : [];
    const baseLinks = Array.isArray(baseGraph?.links) ? baseGraph.links : [];
    const known = new Set(baseNodes.map(n => n.id));
    const nodes = [...baseNodes];
    for (const n of intake.nodes) if (!known.has(n.id)) { nodes.push(n); known.add(n.id); }
    const linkKey = new Set(baseLinks.map(e => `${e.source}|${e.target}|${e.type || ''}`));
    const links = [...baseLinks];
    for (const e of intake.links) {
      const k = `${e.source}|${e.target}|${e.type || ''}`;
      if (!linkKey.has(k)) { links.push(e); linkKey.add(k); }
    }
    return { nodes, links, physarius: { readOnly: true, graphSha256: intake.graphSha256 } };
  }

  global.JANUS_PHYSARIUS_INTAKE = Object.freeze({
    version: '1.0.0',
    DEFAULT_SOURCE,
    load,
    normalize,
    mergeReadOnly,
    laws: Object.freeze([
      'HRAIN_GRAPH_NE_SOURCE_AUTHORITY',
      'BLIND_MEMBER_NE_SCIENTIFIC_RESULT',
      'GRAPH_POSITION_NE_EVIDENCE_STRENGTH',
      'SAME_LINEAGE_NE_INDEPENDENT_REPLICATION',
      'HRAIN_PHYSARIUS_INTAKE_HAS_NO_WRITE_OR_DELETE_AUTHORITY'
    ])
  });
})(window);
