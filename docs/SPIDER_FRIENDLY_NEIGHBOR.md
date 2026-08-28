# HRAiN SPIDER — Friendly Neighbor

HRAiN gives the SPIDER a permanent home as its relationship-weaving sidecar.

The friendly-neighbor / "Oscorp spider" name is a user-facing metaphor. The software role is precise: **SPIDER is the graph relationship weaver**.

## Residence

```text
Hawkar-usls/Hrain
├── spider.html                         # visual web / inspection room
├── spider-bridge.js                    # browser-local package bridge
├── .janus/SPIDER_HOME.json             # residence + responsibility contract
└── .janus/TOPA_SPIDER_LINK.json        # read-only source-engine binding
```

The graph engine itself remains sourced from `Hawkar-usls/TOPA`:

```text
tools/topa_spider_v2.py
tools/topa_spider_flywheel.py
tools/topa_spider_context_fur.py
tools/topa_spider_hrain_pack.py
```

This is intentionally a split between **home** and **engine source**. HRain is where the Spider lives and presents its web; TOPA supplies evidence-calibration and falsification machinery used by the Spider pipeline.

## Responsibility split

```text
RAW / ARCHIVAL / UAP DATA
        ↓
      SPIDER
  nodes + typed edges
  provenance + history
  candidate relationships
  missing-context queue
        ↓
       TOPA
  calibration / attack
  replay firewall
  falsification boundaries
        ↓
      HRAiN
  inspect / navigate / compare
  browser-local visualization
```

### SPIDER

- surveys candidate material and selectively pulls records connected to the current web;
- builds document, tag, date, keyword and other graph nodes;
- creates typed relationship edges;
- keeps provenance, evidence counts and edge history;
- uses Context Fur to expose missing context and acquisition tasks;
- ranks relationships for discovery without promoting them to truth.

### TOPA

- calibrates relationship weights;
- prevents repeated replay from masquerading as fresh evidence;
- weakens unsupported relationships without treating a single absence as disproof;
- keeps semantic similarity, topology and graph density below evidence authority.

### HRAiN

- is the Spider's permanent visualization and inspection home;
- stores imported SPIDER packages only in browser-local IndexedDB;
- provides filters, pass history, relation filters and Context Fur inspection;
- does not write back into archive sources or elevate visual weight into truth.

## Core law

```text
SPIDER_WEAVES__TOPA_TESTS__HRAIN_HOSTS
TOPA_IS_NOT_THE_SPIDER
GRAPH_EDGE_IS_NOT_CAUSATION
SPIDER_DISCOVERY_PRIORITY_IS_NOT_TRUTH
REPLAY_IS_NOT_NEW_EVIDENCE
UNKNOWN_STAYS_UNKNOWN
```

The distinction matters: finding a relationship is a discovery operation. Surviving calibration or falsification makes that relationship more useful to inspect, but still does not by itself establish causation or truth.

## Live room

`https://hawkar-usls.github.io/Hrain/spider.html`
