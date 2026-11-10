/* JANUS Unified Memory v2: local/read-only HRain staging adapter.
 * Never modifies the original JANUS graph, SQLite, NAS state or JSON files.
 */
(function () {
  "use strict";
  var LIMIT = 120;
  function elem(tag, text, css) {
    var x = document.createElement(tag);
    if (text !== null && text !== undefined) x.textContent = String(text);
    if (css) x.className = css;
    return x;
  }
  function verify(g) {
    if (!g || g.schema !== "janus.unified_memory.hrain_readonly_projection.v1" ||
        g.read_only !== true || !g.coverage || !g.coverage.coverage_complete ||
        !g.coverage.read_only || g.coverage.scientific_authority_granted !== false ||
        !Array.isArray(g.nodes) || !Array.isArray(g.links) ||
        g.nodes.length !== g.coverage.indexed_json ||
        g.links.length !== g.coverage.explicit_relations ||
        !/^[a-f0-9]{40}$/.test(String(g.source_commit)) ||
        g.coverage.source_commit !== g.source_commit) {
      throw new Error("UNIFIED_MEMORY_V2_CONTRACT_HOLD");
    }
    var nodes = new Map();
    var prefix = "https://github.com/Hawkar-usls/janus-meta-registry/blob/" + g.source_commit + "/";
    for (var i = 0; i < g.nodes.length; i++) {
      var n = g.nodes[i];
      if (!Number.isInteger(n.id) || nodes.has(n.id) ||
          typeof n.path !== "string" || typeof n.namespace !== "string" ||
          typeof n.title !== "string" || typeof n.source_url !== "string" ||
          n.source_url !== prefix + n.path || !/^[a-f0-9]{64}$/.test(n.sha256)) {
        throw new Error("UNIFIED_MEMORY_V2_NODE_HOLD");
      }
      nodes.set(n.id, n);
    }
    var neighbors = new Map();
    for (var j = 0; j < g.links.length; j++) {
      var edge = g.links[j];
      if (!nodes.has(edge.source) || !nodes.has(edge.target) ||
          (edge.kind !== "EXPLICIT_PATH" && edge.kind !== "EXPLICIT_URL")) {
        throw new Error("UNIFIED_MEMORY_V2_EDGE_HOLD");
      }
      if (!neighbors.has(edge.source)) neighbors.set(edge.source, new Set());
      neighbors.get(edge.source).add(edge.target);
    }
    return {nodes:nodes,neighbors:neighbors};
  }
  function mount(root, graph) {
    if (!root) throw new Error("MOUNT_POINT_MISSING");
    var indexes = verify(graph);
    root.replaceChildren();
    var status = elem("p","READ ONLY · Current Git commit " + graph.source_commit.slice(0,12) +
                     " · " + graph.nodes.length.toLocaleString() + " JSON / " +
                     graph.links.length.toLocaleString() + " explicit references","umv2-status");
    root.appendChild(status);
    var toolbar = elem("section",null,"umv2-toolbar");
    var input = elem("input");
    input.type = "search";
    input.placeholder = "Поиск пути или заголовка JSON";
    input.setAttribute("aria-label","Поиск JSON");
    var select = elem("select");
    select.setAttribute("aria-label","Раздел");
    var groups = ["ВСЕ"].concat(Array.from(new Set(graph.nodes.map(function(n){return n.namespace;}))).sort());
    groups.forEach(function(group){
      var opt=elem("option",group); opt.value=group; select.appendChild(opt);
    });
    toolbar.append(input,select); root.appendChild(toolbar);
    var summary = elem("p",null,"umv2-summary");
    var list=elem("div",null,"umv2-docs");
    root.append(summary,list);
    function render(){
      var q=input.value.trim().toLocaleLowerCase();
      var selected=select.value;
      var filtered=graph.nodes.filter(function(n){
        return (selected==="ВСЕ" || selected===n.namespace) &&
            (!q || n.path.toLocaleLowerCase().includes(q) || n.title.toLocaleLowerCase().includes(q));
      });
      summary.textContent="Найдено " + filtered.length.toLocaleString() +
        " документов, показано " + Math.min(LIMIT,filtered.length) +
        ". Исходные JSON и память NAS не изменяются.";
      list.replaceChildren();
      filtered.slice(0,LIMIT).forEach(function(n){
        var item=elem("article",null,"umv2-doc");
        var link=elem("a",n.title || n.path);
        link.href=n.source_url; link.target="_blank";link.rel="noopener noreferrer";
        var refs=indexes.neighbors.get(n.id);
        var info=elem("small",n.path + " · " + n.parse_status + " · исходящих ссылок: " + (refs?refs.size:0));
        item.append(link,info);
        if (refs && refs.size) {
          var expand=elem("button","Показать связанные файлы");
          expand.type="button";
          expand.addEventListener("click",function(){
            if (expand.nextSibling) {expand.nextSibling.remove();return;}
            var panel=elem("div",null,"umv2-related");
            Array.from(refs).slice(0,30).forEach(function(id){
              var dst=indexes.nodes.get(id);
              var a=elem("a",dst.title || dst.path);
              a.href=dst.source_url;a.rel="noopener noreferrer";a.target="_blank";
              panel.appendChild(a);
            });
            item.appendChild(panel);
          });
          item.appendChild(expand);
        }
        list.appendChild(item);
      });
    }
    input.addEventListener("input",render);
    select.addEventListener("change",render);
    render();
    return {status:"PASS",nodes:graph.nodes.length,links:graph.links.length,source_commit:graph.source_commit};
  }
  async function fromFile(file,root){
    if (!file || file.size>75*1024*1024) throw new Error("GRAPH_FILE_SIZE_HOLD");
    return mount(root,JSON.parse(await file.text()));
  }
  window.JANUSUnifiedMemoryV2=Object.freeze({mount:mount,fromFile:fromFile});
}());
