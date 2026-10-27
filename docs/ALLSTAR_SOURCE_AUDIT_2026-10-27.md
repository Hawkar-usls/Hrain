# JANUS HRAiN · All Star forensic source audit
Date: 2026-10-27 · Read-only source inspection

## Scope and provenance
Local owner-authorized source: `E:\Janus_Love\Janus_Titan\All Star`.
A **local** machine-readable inventory is saved at `artifacts\audits\janus_allstar_readonly_inventory_20261027.json`; it is NOT pushed publicly. Excludes runtime secrets, hidden Git metadata, compiled Python cache, and any file contents not required for source inspection.

Inventory: **483 files in 30 scanned directories**, approximately **213,952,308 bytes** of non-excluded files; **315 .py**, **65 .json**, 6 .html, 8 .jsonl, 12 .log, and other binary/model artifacts. This does NOT assert that all files are valid, independent or currently running.

Authentic source HRAiN v77: `hrain_janus.html` (**40,503 bytes**, SHA-256 `c36cb76a0c065ce9b59aeeab70819a7c6d1fce82277dcd061ae4d4ced9c79e6f`). A newline-normalized, readable archival copy is versioned as `legacy/hrain-v77-allstar-original.html`. Source screenshot, labels and control flow are distinct from `HRAIN v10.5`.

## What actually exists in All Star
- `hrain_janus.html`: D3 force-directed v77, **DIVE/ASCEND**, add/delete/rename, link/unlink, impulses, Nerve API and WebSocket; offline demo fallback.
- `server.py`: local **HRAiN server v89** (`aiohttp`), `/api/hrain/state`, `/api/hrain/save`, `/api/janus/action`, `/ws`, autonomous controls, local file persistence, device ingestion.
- `hrain_graph_engine.py`: Physarum-like edge energy, reinforcement, decay, clustering and state serialization; `hrain_autonomy.py`: autonomous growth, foundation nodes, public graph snapshot; `hrain_decision_core.py`: decision logic; `ecosystem_bridges.py`: legacy bridge hooks for Genesis/BFain.
- `raw_logs/hrain_graph_state.json` exists locally with **100 nodes and 9,737 directed edge records**, tick **31,625**, about 1.58 MB, SHA-256 `991c5866f8c49610b039127a5117a1de1729beae94d7579e2a3f4284aa942979`. It is PRIVATE local state: **never committed** or bundled in a public browser archive.
- Additional candidates: Genesis modules (`janus_genesis/`), BFain (`bfain_core.py`, `assets/bfain.js`), `Model_Zoo/` stored artifacts, `legacy_archive/` snapshots, local control/telemetry modules, hardware tools. Presence does not establish production health or scientific validity.

## Finding: real data-loss and authorization risk
In All Star's `server.py`, `handle_save_state()` does not apply a narrow patch: it sets `graph_engine.nodes=new_nodes` and `graph_engine.edges=new_edges` and persists the ENTIRE replacement state. The v77 browser originally auto-POSTed every ordinary graph edit to that route. `/api/janus/action` actively creates new autonomous nodes. The server's startup config binds `0.0.0.0`, and the inspected handlers do not establish an authenticated authorization boundary. It would be unsafe to bridge the PUBLIC GitHub Pages viewer directly to this server, or import public JSON relations into its mutable graph.

## Implemented recovery architecture
- `hrain-v77.html` restores the **original v77 D3 graph** and navigation as a dedicated, prominent accessible living view, without replacing modern v10.5/index or the Semantic Registry.
- Original v77's dangerous **automatic server POST routes are removed** from the public restored view. Edits become **browser-session drafts**; export/import is explicit, bounded, and does not rewrite private graph state. SYNTH stays gated pending authenticated server action design.
- Localhost-only GET/WS snapshots are optional, read-only, and held if a local draft is dirty or a verified Atlas view is active. The public GitHub Pages version falls back to clearly marked demo state; it is not misrepresented as a live v89 backend.
- Existing JANUS native Atlas `assets/janus-native-atlas.js` and `assets/janus-explicit-links.js` are loaded into v77; `JANUSAtlasNativeFocus` projects only source-verified read-only JSON references into the ORIGINAL v77 D3 rendering and restores original nodes without server writes or SYNTH escalation.
- No local secrets, logs, model weights, unfiltered network inventory, database rows or private graph structure are sent to this PUBLIC GitHub repo.

## Follow-on gates before claiming full live v89 HRAiN recovery
1. Build a **separately authenticated** backend bridge for exact versioned node/edge diffs with optimistic concurrency, explicit user confirmation, and protected-node policy. Never use existing full-state POST as an implicit save.
2. Benchmark 100 nodes / 9,737 edges in the live v77 renderer and add performance mode before enabling editing against a real v89 source.
3. Require a full byte-identical backup and tested restore of `raw_logs/hrain_graph_state.json` before any server-side change; keep it private.
4. Independently audit `server.py` access control, WebSocket origin policy, device routes and shared logs; limit binding to localhost before any remote connectivity.
5. Keep `EXPLICIT_SOURCE_REFERENCE` ≠ iNaiHR semantic candidate ≠ TOPA scientific truth. No automatic inference becomes a server command.

**Status:** recovery UI and local draft/verified Atlas pathway implemented. Remote authoritative writes intentionally NOT implemented or declared ready.
