#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, re, sys, time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

VERSION = "A15.5_HRAIN_LIVE_TERMINAL_POOLSTREAM_20260625"
SENTINEL = "A15_5_HRAIN_LIVE_OBSERVER_POOLSTREAM_WIRE_HASH_SUBMIT_FROZEN_MIRROR_UNTOUCHED"

EXT = {".log", ".txt", ".jsonl", ".json"}
ROUTE_WORDS = ["bitrev","linear","zim_reverse","zim_bandit","knight","dual_lock","janus_dispatcher","linear_proof","zim_reverse_s6","randomized_traversal_mirror","random_mirror","random"]
CONCEPTS = {
    "ORDER": ["janus","accepted","proof","truth","canonical","nav_lock","commit","lock","temple","shrine","order","поряд"],
    "ENTROPY": ["random","mirror","rollback","reject","rejected","stale","chaos","entropy","хаос","энтроп"],
    "BRIDGE": ["pool","stratum","job","route","map","bridge","link","rescue","a14_nav","a12_arc"],
    "PROOF": ["accepted","submit","pool_pass","nonce","hash","z=","best_z","share","proof"],
    "GLYPH": ["glyph","symbol","linear_message","open_word","coinbase","merkle","weird"],
    "MIND": ["hrain","inaihr","mind","concept","essence","meaning","смысл","понят","kernel","indexeddb","canvas"],
    "TAIL": ["z28","z29","z30","z31","z32","rare_tail","best_z=30","best_z=29","best_z=28"],
}

def now(): return time.time()
def sha8(s): return hashlib.sha256(str(s).encode("utf-8","ignore")).hexdigest()[:8]
def safe(prefix, val, limit=88):
    raw = str(val if val is not None else "none")
    x = re.sub(r"[^a-zA-Z0-9_.:/@+-]+","_",raw.strip())[:limit].strip("_") or "node"
    return f"{prefix}:{x}:{sha8(raw)}"

def write_atomic(path: Path, obj: Any):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def read_json(path: Path, default):
    try: return json.loads(path.read_text("utf-8"))
    except Exception: return default

def status(path: Path, **kw):
    try: write_atomic(path, {"version": VERSION, "sentinel": SENTINEL, "mtime": now(), **kw})
    except Exception as e: print(f"[A15.5 status] failed: {e}", flush=True)

@dataclass
class Graph:
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    links: Dict[Tuple[str,str,str], Dict[str, Any]] = field(default_factory=dict)
    counters: Counter = field(default_factory=Counter)
    route_stats: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    seen: set = field(default_factory=set)

    def node(self, id, label, kind, group, score=1.0, **data):
        n = self.nodes.get(id)
        if n is None:
            n = {"id": id, "label": label, "kind": kind, "group": group, "score": 0.0, "data": {}}
            self.nodes[id] = n
        n["label"], n["kind"], n["group"] = label or n["label"], kind or n["kind"], group or n["group"]
        n["score"] = float(n.get("score",0)) + float(score or 0)
        for k,v in data.items():
            if v is not None:
                if k in ("z","priority"): n[k]=v
                else: n.setdefault("data",{})[k]=v
        return id

    def link(self, a,b,kind,weight=1.0,**data):
        if not a or not b or a==b: return
        key=(a,b,kind)
        l=self.links.get(key)
        if l is None:
            l={"source":a,"target":b,"kind":kind,"weight":0.0,"data":{}}
            self.links[key]=l
        l["weight"]=float(l.get("weight",0))+float(weight or 0)
        for k,v in data.items():
            if v is not None: l.setdefault("data",{})[k]=v

def init_graph(g: Graph):
    g.node("HRAIN_LIVE","HRAIN LIVE TEMPLE","core","core",50, mode="observer poolstream; not stratum proxy")
    g.node("JANUS_ORDER","JANUS / ORDER","axis","janus",25)
    g.node("CHAOS_MIRROR","CHAOS / MIRROR RANDOM","axis","mirror",25)
    g.node("POOLSTREAM","POOLSTREAM LOG BRIDGE","pool","pool",15)
    g.node("WIRE_HASH_SUBMIT_FROZEN","WIRE/HASH/SUBMIT FROZEN","doctrine","safety",10)
    g.node("OBSERVER_ONLY","OBSERVER ONLY","doctrine","safety",10)
    g.link("HRAIN_LIVE","JANUS_ORDER","axis",8)
    g.link("HRAIN_LIVE","CHAOS_MIRROR","axis",8)
    g.link("HRAIN_LIVE","POOLSTREAM","observer_bridge",5)
    g.link("HRAIN_LIVE","WIRE_HASH_SUBMIT_FROZEN","doctrine",5)
    g.link("HRAIN_LIVE","OBSERVER_ONLY","doctrine",5)
    for c in CONCEPTS:
        cid=f"concept:{c}"
        group="concept_chaos" if c=="ENTROPY" else ("concept_proof" if c in ("PROOF","TAIL") else "concept_order")
        g.node(cid,c,"concept",group,8)
        g.link("CHAOS_MIRROR" if c=="ENTROPY" else "JANUS_ORDER", cid, "concept_axis",3)
    for r in ROUTE_WORDS:
        group="mirror" if "random" in r else "janus"
        rid=safe("route",r)
        g.node(rid,r,"route",group,5)
        g.link("CHAOS_MIRROR" if group=="mirror" else "JANUS_ORDER", rid, "route_axis",3)

def explicit_group(text: str) -> Optional[str]:
    low = text.lower()
    m = re.search(r"\bgroup=([a-zA-Z0-9_:-]+)", text)
    if m:
        val=m.group(1).lower()
        if "mirror" in val or "random" in val: return "mirror"
        if "janus" in val: return "janus"
    if "randomized_traversal_mirror" in low or "group=random" in low: return "mirror"
    if "group=janus_broad_mixture" in low: return "janus"
    return None

def classify(text: str, route: Optional[str]) -> str:
    ex = explicit_group(text)
    if ex: return ex
    low = ((text or "")+" "+(route or "")).lower()
    # Crucial fix: a14_navigator is always Janus control unless explicit group says mirror.
    if "a14_navigator:" in low or "nav_lock route=a14_navigator" in low: return "janus"
    if "randomized_traversal_mirror" in low or "random_mirror" in low or re.search(r"\brandom/s\d+", low): return "mirror"
    if any(k in low for k in ("janus","bitrev","linear","zim","knight","dual_lock")): return "janus"
    if any(k in low for k in ("stratum","new job","pool","submit","candidate")): return "pool"
    return "event"

def route_of(text: str) -> Optional[str]:
    m=re.search(r"\bchoice=([^\s,;]+)", text)
    if m: return m.group(1)
    m=re.search(r"\broute=([^\s,;]+)", text)
    if m: return m.group(1)
    m=re.search(r"(a14_navigator:[^\s,;\"']+)", text)
    if m: return m.group(1)
    m=re.search(r"([a-zA-Z0-9_:-]+::[a-zA-Z0-9_/-]+/s?\d+/canonical)", text)
    if m: return m.group(1)
    m=re.search(r"\b(bitrev|linear|zim_reverse|zim_bandit|knight|random)/s?\d+\b", text)
    if m: return m.group(0)
    for r in ROUTE_WORDS:
        if r in text: return r
    return None

def zbits(text: str) -> Optional[int]:
    m=re.search(r"\bz=(\d+)\b|\bz(\d+)\b|\bbest_z=(\d+)\b|_z(\d+)_", text)
    if not m: return None
    for x in m.groups():
        if x:
            try: return int(x)
            except Exception: pass
    return None

def job_of(text):
    m=re.search(r"\bjob=([a-zA-Z0-9_:-]+)|new job=([a-zA-Z0-9_:-]+)", text)
    return next((x for x in m.groups() if x), None) if m else None

def nonce_of(text):
    m=re.search(r"\bnonce(?:_submit|_int)?=?(?:0x)?([0-9a-fA-F]{6,16})", text)
    return m.group(1) if m else None

def concepts(text):
    low=text.lower()
    out=[c for c, keys in CONCEPTS.items() if any(k in low for k in keys)]
    return out or ["ORDER"]

def add_event(g: Graph, text: str, source: str):
    key=sha8(source+"|"+text)
    if key in g.seen: return False
    g.seen.add(key)
    low=text.lower()
    if not any(k in low for k in ("accepted","submit","truth","stratum","new job","a14","a12_arc","scoreboard","v31_rates","glyph","random","mirror","janus","bitrev","linear","zim","knight","rollback","nav_lock","proof")):
        return False
    route=route_of(text) or ("pool_job" if "new job" in low or "stratum" in low else "event")
    group=classify(text, route)
    z=zbits(text)
    accepted=bool(re.search(r"\bACCEPTED\b|accepted[\"'=:\s]+true|pool_pass[\"'=:\s]+true|accepted z=", text, re.I))
    rollback="rollback" in low
    nav="nav_lock" in low or "a14_nav" in low
    glyph="glyph" in low or "symbol" in low
    job=job_of(text); nonce=nonce_of(text)
    rid=safe("route",route)
    axis="CHAOS_MIRROR" if group=="mirror" else ("JANUS_ORDER" if group=="janus" else "POOLSTREAM")
    g.node(rid, route, "route" if group in ("janus","mirror") else "pool_event", group, .5)
    g.link(axis, rid, "route_axis", .8)
    kind="accepted" if accepted else ("rollback" if rollback else ("nav_lock" if nav else ("glyph" if glyph else ("pool_job" if "new job" in low or "stratum" in low else "event"))))
    eid=safe(kind, f"{text[:200]}|{source}")
    score=1+(z or 0)/8+(7 if accepted else 0)+(2 if nav else 0)
    g.node(eid, f"{kind} z{z}" if z else kind, kind, group if group in ("janus","mirror") else ("pool" if kind=="pool_job" else "event"), score, z=z, excerpt=text[:380], source=source)
    g.link(rid,eid,kind,max(.4,score/3))
    g.link("POOLSTREAM",eid,"live_event",.20)
    if job:
        jid=safe("job",job)
        g.node(jid,job,"job","pool",2)
        g.link("POOLSTREAM",jid,"stratum_job",.7)
        g.link(jid,eid,"job_event",.6)
    if nonce:
        nid=safe("nonce",nonce)
        g.node(nid,nonce,"nonce","proof" if accepted else "pool",1+(z or 0)/20)
        g.link(eid,nid,"nonce",.7)
    for c in concepts(text):
        cid=f"concept:{c}"
        g.node(cid,c,"concept","concept_chaos" if c=="ENTROPY" else "concept_order",.3)
        g.link(eid,cid,"concept_atom",.45+(z or 0)/80)
    if z and z>=28:
        tid=f"tail:z{z}"
        g.node(tid,f"RARE TAIL z{z}","tail","tail",z/2,z=z)
        g.link(eid,tid,"rare_tail",3+z/10)
        g.counters["rare_tail"] += 1
    st=g.route_stats[route]
    st["seen"] += 1
    st["best_z"] = max(st["best_z"], z or 0)
    st["accepted"] += int(accepted)
    st["rollback"] += int(rollback)
    st["nav_lock"] += int(nav)
    st["glyph"] += int(glyph)
    st["janus"] += int(group=="janus")
    st["mirror"] += int(group=="mirror")
    for c in concepts(text): st[f"concept_{c}"] += 1
    if accepted:
        if group=="janus": g.counters["accepted_janus"] += 1
        elif group=="mirror": g.counters["accepted_mirror"] += 1
        else: g.counters["accepted_pool"] += 1
    g.counters["events_seen"] += 1
    return True

def discover(root: Path, max_files: int):
    bases=[]
    for p in [
        root/"janus_io_o1_runs"/"A14_2_PURE_ROUTE_LOCK_V1",
        root/"janus_io_o1_runs",
        root/"A15_4_JANUS_SHRINE_PROMO_FUSION_PACK"/"imports"/"promo",
        root/"A15_3_JANUS_SHRINE_SEMANTIC_CORE_PACK"/"imports"/"promo",
        root
    ]:
        if p.exists() and p not in bases: bases.append(p)
    found=[]; seen=set()
    for base in bases:
        print(f"[A15.5 discover] base={base}", flush=True)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in {'.git','node_modules','__pycache__','venv','.venv','dist','build'} and not d.startswith(".")]
            for fn in filenames:
                p=Path(dirpath)/fn
                if p.suffix.lower() not in EXT: continue
                sp=str(p.resolve())
                if sp in seen: continue
                seen.add(sp)
                low=sp.lower()
                if base == root and not any(k in low for k in ("rblganul","janus","a10","a11","a12","a13","a14","glyph","nonce","open_sweep","live_console","fresh_all_time","dashboard","summary")):
                    continue
                found.append(p)
    def prio(p):
        low=str(p).lower(); name=p.name.lower()
        try: st=p.stat(); m=-st.st_mtime; size=st.st_size
        except Exception: m=0; size=0
        live=0 if any(k in name for k in ("live_console","dashboard","summary","navigator","rates")) else 1
        run=0 if "a14_2_pure_route_lock" in low else 1
        proof=0 if "proof" in low or "accepted_" in name else 1
        glyph=0 if "glyph" in name else 1
        return (run, live, proof, glyph, m, size)
    found.sort(key=prio)
    return found[:max_files]

def read_new(path: Path, offsets: Dict[str,int], initial_tail_bytes: int, max_read_bytes: int):
    key=str(path.resolve())
    try:
        size=path.stat().st_size
        old=int(offsets.get(key,0))
        if old > size: old=0
        with path.open("rb") as f:
            if old == 0 and size > initial_tail_bytes:
                f.seek(max(0,size-initial_tail_bytes))
                data=f.read(initial_tail_bytes)
                if b"\n" in data: data=data.split(b"\n",1)[1]
            else:
                f.seek(old); data=f.read(max_read_bytes)
        offsets[key]=size
        return data.decode("utf-8","ignore")
    except Exception:
        return ""

def add_text_blob(g: Graph, text: str, source: str, max_lines: int):
    count=0
    for line in text.splitlines()[-max_lines:]:
        s=line.strip()
        if not s: continue
        if s.startswith("{") and s.endswith("}"):
            try: s=json.dumps(json.loads(s), ensure_ascii=False)
            except Exception: pass
        if add_event(g,s,source): count += 1
    return count

def add_json_file(g: Graph, path: Path):
    try:
        if path.stat().st_size > 18_000_000: return 0
        obj=json.loads(path.read_text("utf-8", errors="ignore"))
        s=json.dumps(obj, ensure_ascii=False)
    except Exception:
        return 0
    return int(add_event(g,s[:22000],path.name))

def compact(g: Graph, max_nodes: int, max_links: int):
    if len(g.nodes) > max_nodes:
        keep={n["id"] for n in sorted(g.nodes.values(), key=lambda x: float(x.get("score",0)), reverse=True)[:max_nodes]}
        keep.update(["HRAIN_LIVE","JANUS_ORDER","CHAOS_MIRROR","POOLSTREAM","WIRE_HASH_SUBMIT_FROZEN","OBSERVER_ONLY"])
        keep.update([f"concept:{c}" for c in CONCEPTS])
        g.nodes={k:v for k,v in g.nodes.items() if k in keep}
        g.links={k:v for k,v in g.links.items() if v["source"] in keep and v["target"] in keep}
    if len(g.links) > max_links:
        kept=sorted(g.links.values(), key=lambda x: float(x.get("weight",0)), reverse=True)[:max_links]
        g.links={(l["source"],l["target"],l["kind"]):l for l in kept}

def make_bias(g: Graph):
    accepted={}; rejected={}
    for route, st in g.route_stats.items():
        low=route.lower()
        if "random" in low or "mirror" in low:
            rejected[route]={"reason":"mirror/random route", **dict(st)}
            continue
        # Critical safety: do not export route if its evidence was mostly mirror-classified.
        if st["mirror"] > 0 and st["janus"] <= st["mirror"]:
            rejected[route]={"reason":"mirror-polluted evidence; not safe for Janus bias", **dict(st)}
            continue
        if not any(x in low for x in ("a14_navigator","janus","bitrev","linear","zim","knight","dual_lock")):
            rejected[route]={"reason":"not a pure/Janus route", **dict(st)}
            continue
        score=1 + st["accepted"]*2.5 + st["best_z"]*.25 + st["nav_lock"]*.4 + (st["concept_ORDER"]+st["concept_BRIDGE"]+st["concept_MIND"])*.04 - st["rollback"]*.12
        accepted[route]=max(.05, score)
    total=sum(accepted.values()) or 1
    norm={k:round(v/total,6) for k,v in sorted(accepted.items(), key=lambda x:x[1], reverse=True)}
    return {
        "version": VERSION,
        "sentinel": SENTINEL,
        "observer_only": True,
        "bias_file_output_only": True,
        "miner_not_modified": True,
        "wire_hash_submit_frozen": True,
        "mirror_untouched": True,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "janus_route_bias": norm,
        "rejected_routes_due_to_mirror_pollution": rejected,
        "mirror_control": {"random":"untouched","randomized_traversal_mirror":"untouched"},
        "note": "A15.5 exports only routes whose evidence is Janus-classified. A14.2 does not read this file."
    }

def save_outputs(g: Graph, graph_path: Path, bias_path: Path, status_path: Path, files_count: int):
    compact(g, 4200, 8500)
    bias=make_bias(g)
    for idx,(route,val) in enumerate(list(bias["janus_route_bias"].items())[:20],1):
        bid=safe("bias",route)
        rid=safe("route",route)
        g.node(bid,f"bias {idx}: {route}","bias","bias",1+val*15,weight=val)
        g.link("JANUS_ORDER",bid,"bias_output",1+val*12)
        g.link(bid,rid,"bias_route",1+val*10)
    graph={
        "meta":{
            "version":VERSION,
            "sentinel":SENTINEL,
            "built_at":time.strftime("%Y-%m-%d %H:%M:%S"),
            "policy":{"observer_only":True,"poolstream_log_bridge":True,"stratum_proxy":False,"wire_hash_submit_frozen":True,"mirror_untouched":True,"miner_not_modified":True,"bias_file_output_only":True},
            "counters":dict(g.counters),
            "files_watched":files_count,
            "top_bias_routes":list(bias["janus_route_bias"].items())[:8]
        },
        "nodes":list(g.nodes.values()),
        "links":list(g.links.values())
    }
    write_atomic(graph_path, graph)
    write_atomic(bias_path, bias)
    status(status_path, stage="live", message=f"events={g.counters.get('events_seen',0)} nodes={len(graph['nodes'])} links={len(graph['links'])}", complete=False, events_seen=int(g.counters.get("events_seen",0)), accepted_janus=int(g.counters.get("accepted_janus",0)), accepted_mirror=int(g.counters.get("accepted_mirror",0)), graph_nodes=len(graph["nodes"]), graph_links=len(graph["links"]), files_watched=files_count, top_bias_routes=list(bias["janus_route_bias"].items())[:6])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root", default="..")
    ap.add_argument("--graph", default="hrain_live_graph.json")
    ap.add_argument("--bias", default="temple_route_bias.json")
    ap.add_argument("--status", default="hrain_live_status.json")
    ap.add_argument("--state", default="hrain_live_offsets.json")
    ap.add_argument("--poll", type=float, default=3.0)
    ap.add_argument("--max-files", type=int, default=180)
    ap.add_argument("--initial-tail-bytes", type=int, default=1_200_000)
    ap.add_argument("--max-read-bytes", type=int, default=900_000)
    ap.add_argument("--max-lines-per-file", type=int, default=4500)
    args=ap.parse_args()
    root=Path(args.root).resolve(); graph_path=Path(args.graph).resolve(); bias_path=Path(args.bias).resolve(); status_path=Path(args.status).resolve(); state_path=Path(args.state).resolve()
    g=Graph(); init_graph(g)
    offsets=read_json(state_path,{})
    print(f"[A15.5] root={root}", flush=True)
    print("[A15.5] poolstream log bridge active; NOT a stratum proxy; submit path untouched", flush=True)
    last_discover=0; files=[]
    cycle=0
    while True:
        cycle += 1
        if not files or time.time()-last_discover > 20:
            files=discover(root, args.max_files)
            last_discover=time.time()
            print(f"[A15.5] watching files={len(files)}", flush=True)
        added=0
        for p in files:
            if p.suffix.lower()==".json":
                # json proofs can be static; read only once by offset marker.
                key=str(p.resolve())+":json_once"
                if key not in offsets:
                    added += add_json_file(g,p)
                    offsets[key]=1
                continue
            blob=read_new(p, offsets, args.initial_tail_bytes, args.max_read_bytes)
            if blob:
                added += add_text_blob(g, blob, p.name, args.max_lines_per_file)
        if added or cycle % 5 == 0:
            save_outputs(g, graph_path, bias_path, status_path, len(files))
            write_atomic(state_path, offsets)
            print(f"[A15.5 live] cycle={cycle} added={added} events={g.counters.get('events_seen',0)} janus={g.counters.get('accepted_janus',0)} mirror={g.counters.get('accepted_mirror',0)} nodes={len(g.nodes)} routes={len(g.route_stats)}", flush=True)
        time.sleep(args.poll)

if __name__=="__main__":
    raise SystemExit(main())
