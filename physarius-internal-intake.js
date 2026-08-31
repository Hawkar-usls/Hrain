(function (root) {
  'use strict';
  const DEFAULT_SOURCE = 'https://raw.githubusercontent.com/Hawkar-usls/Janus-Fundamentum/main/registry/PHYSARIUS_INTERNAL_REPO_HRAIN_LIVE_v1.json';

  function assertGraph(graph) {
    if (!graph || graph.schema !== 'janus.hrain.physarius_internal_graph.v1') throw new Error('Unsupported internal Physarius graph schema');
    const m=graph.mutationPolicy||{}, c=graph.contentPolicy||{};
    if (m.write!==false || m.delete!==false || m.sourceMutation!==false) throw new Error('Internal Physarius intake rejects mutation authority');
    if (c.contentExposed!==false) throw new Error('Internal trunk graph must be tree-first');
    if (c.selectivePullRequiresBinding!==true) throw new Error('Selective pull must require binding');
    return graph;
  }

  function normalize(graph) {
    assertGraph(graph);
    return Object.freeze({
      schema:'hrain.physarius.internal_intake.v1',
      sourceNetwork:graph.source_network,
      graphSha256:graph.graph_sha256,
      authority:'READ_ONLY_INTERNAL_DISCOVERY_PROJECTION',
      contentExposed:false,
      pathNamesExposed:graph.contentPolicy.pathNamesExposed===true,
      nodes:Object.freeze((graph.nodes||[]).map(n=>Object.freeze({...n,readOnly:true,sourceMutationAllowed:false,contentAuthority:false}))),
      links:Object.freeze((graph.edges||[]).map(e=>Object.freeze({...e,readOnly:true}))),
      claimCeiling:Object.freeze([...(graph.claim_ceiling||[])])
    });
  }

  async function load(source=DEFAULT_SOURCE) {
    const r=await fetch(source,{cache:'no-store'});
    if(!r.ok) throw new Error(`Internal Physarius uplink HTTP ${r.status}`);
    const intake=normalize(await r.json());
    if (typeof root.dispatchEvent==='function' && typeof root.CustomEvent==='function') root.dispatchEvent(new root.CustomEvent('hrain:physarius-internal-ready',{detail:intake}));
    return intake;
  }

  function mergeReadOnly(baseGraph,intake) {
    const baseNodes=Array.isArray(baseGraph?.nodes)?baseGraph.nodes:[], baseLinks=Array.isArray(baseGraph?.links)?baseGraph.links:[];
    const ids=new Set(baseNodes.map(n=>n.id)); const nodes=[...baseNodes];
    for(const n of intake.nodes) if(!ids.has(n.id)){nodes.push(n);ids.add(n.id)}
    const keys=new Set(baseLinks.map(e=>`${e.source}|${e.target}|${e.type||''}`)); const links=[...baseLinks];
    for(const e of intake.links){const k=`${e.source}|${e.target}|${e.type||''}`;if(!keys.has(k)){links.push(e);keys.add(k)}}
    return {nodes,links,physariusInternal:{readOnly:true,graphSha256:intake.graphSha256,sourceNetwork:intake.sourceNetwork}};
  }

  const API=Object.freeze({version:'1.0.0',DEFAULT_SOURCE,assertGraph,normalize,load,mergeReadOnly,laws:Object.freeze([
    'META_REGISTRY_MEMORY_NE_EXTERNAL_EVIDENCE',
    'LAPIS_MECHANISM_NE_TRUTH_AUTHORITY',
    'ALL_BRANCH_HEADS_PRESERVE_PROVENANCE',
    'BLOB_DEDUP_NE_LINEAGE_ERASURE',
    'SELECTIVE_PULL_REQUIRES_EXACT_BINDING',
    'HRAIN_INTERNAL_INTAKE_HAS_NO_WRITE_DELETE_OR_SOURCE_MUTATION_AUTHORITY'
  ])});
  root.JANUS_PHYSARIUS_INTERNAL_INTAKE=API;
  if(typeof module!=='undefined' && module.exports) module.exports=API;
})(typeof window!=='undefined'?window:globalThis);
