# HRAiN SPIDER — Friendly Neighbor

HRAiN gives the SPIDER a permanent home as its relationship-weaving sidecar.

The friendly-neighbor / "Oscorp spider" name is a user-facing metaphor. The software role is precise: **SPIDER is the graph relationship weaver**.

## Identity and activation

TOPA keeps its Spider powers. The default operational identity is **TOPA Detective Spider**:

```text
TOPA request with no explicit profile
        ↓
DETECTIVE
        ↓
TOPA CORE + SPIDER
```

The components remain separately addressable, so the same system also supports:

```text
DETECTIVE          = TOPA CORE + SPIDER   # default
TOPA_CORE_ONLY     = TOPA CORE only       # explicit opt-out
SPIDER_STANDALONE  = SPIDER only          # independent web weaving
```

This means Spider is both a permanent HRAiN resident and a default capability of TOPA Detective mode. Separability is preserved for debugging, focused research and reuse.

## Residence

```text
Hawkar-usls/Hrain
├── spider.html                         # visual web / inspection room
├── spider-bridge.js                    # browser-local package bridge
├── .janus/SPIDER_HOME.json             # residence + activation contract
└── .janus/TOPA_SPIDER_LINK.json        # read-only TOPA source binding
```

The graph engine and activation resolver are sourced from `Hawkar-usls/TOPA`:

```text
protocols/TOPA_DETECTIVE_SPIDER_ACTIVATION_v1.0.json
tools/topa_detective_spider.py
tools/topa_spider_v2.py
tools/topa_spider_flywheel.py
tools/topa_spider_context_fur.py
tools/topa_spider_hrain_pack.py
```

This is intentionally a split between **home** and **engine source**. HRAiN is where the Spider lives and presents its web. TOPA Detective mode activates Spider by default while TOPA core retains falsification, provenance and claim-discipline responsibility.

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
    TOPA CORE
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

### TOPA CORE

- calibrates relationship weights;
- prevents repeated replay from masquerading as fresh evidence;
- weakens unsupported relationships without treating a single absence as disproof;
- keeps semantic similarity, topology and graph density below evidence authority.

### TOPA DETECTIVE SPIDER

- is the default combined profile;
- activates both TOPA core and Spider unless an explicit profile says otherwise;
- uses Spider discoveries as leads and TOPA falsification as the adversarial check;
- never treats the presence of a web edge as proof.

### HRAiN

- is the Spider's permanent visualization and inspection home;
- stores imported SPIDER packages only in browser-local IndexedDB;
- provides filters, pass history, relation filters and Context Fur inspection;
- does not write back into archive sources or elevate visual weight into truth.

## Core law

```text
TOPA_DETECTIVE_DEFAULT_INCLUDES_SPIDER
TOPA_CORE_IS_NOT_THE_SPIDER_ENGINE
SPIDER_CAN_RUN_WITHOUT_TOPA_CORE
TOPA_CORE_CAN_RUN_WITHOUT_SPIDER_WHEN_EXPLICITLY_REQUESTED
GRAPH_EDGE_IS_NOT_CAUSATION
SPIDER_DISCOVERY_PRIORITY_IS_NOT_TRUTH
REPLAY_IS_NOT_NEW_EVIDENCE
UNKNOWN_STAYS_UNKNOWN
```

The distinction matters: finding a relationship is a discovery operation. Surviving calibration or falsification makes that relationship more useful to inspect, but still does not by itself establish causation or truth.

## Live room

`https://hawkar-usls.github.io/Hrain/spider.html`
