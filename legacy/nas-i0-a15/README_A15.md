# A15 JANUS TEMPLE GRAPH

Observer-only D3.js graph temple for Janus / I0 route memory.

It turns A14/A13/A12 JSON + JSONL corpus files into a force-directed semantic route map:

- accepted shares
- proof files
- routes / lanes
- NAV_LOCK / rollback / commit / rescue context
- glyph observer anchors
- mirror-control nodes
- Janus-only route memory

## Doctrine

```text
WIRE/HASH/SUBMIT frozen
mirror untouched
observer-only by default
no direct submit-byte mutation
no proof substitution
JSON corpus is memory/context, not a claim by itself
```

## Quick start

Put this folder into your I0 workspace, near `janus_io_o1_runs`.

Run:

```bat
Yaksa_A15_JANUS_TEMPLE_GRAPH.bat
```

It will:

1. scan current folder and nearby `janus_io_o1_runs` for `.json` / `.jsonl` corpus,
2. build `janus_temple_graph.json`,
3. start a local HTTP server,
4. open `index.html` in your browser.

## Manual build

```bat
Yaksa_A15_BUILD_GRAPH_ONLY.bat
```

or:

```powershell
python temple_build_graph.py --root . --out janus_temple_graph.json
python serve_temple.py --host 127.0.0.1 --port 8787
```

## Important

The graph is allowed to create meaning and memory.
It is **not** allowed to change miner wire bytes or submit behavior.
Future A15.1 may export `temple_route_bias.json`, but that must remain scheduler-only and Janus-half-only.

## Main files

- `index.html` — D3.js temple UI
- `temple_build_graph.py` — JSON/JSONL corpus scanner
- `serve_temple.py` — local HTTP server
- `config.example.json` — scanner/view config
- `schemas/janus_temple_graph.schema.json` — graph schema
- `samples/janus_temple_graph.sample.json` — fallback sample graph

## Recommended test loop

1. Keep A14.2 miner-only running.
2. Periodically copy/export corpus or point A15 at I0.
3. Rebuild graph.
4. Look for routes that consistently produce tail/accepted clusters:
   - `bitrev`
   - `linear`
   - `zim_reverse`
   - `zim_bandit`
   - `knight`
   - `dual_lock`
5. Do not treat glyph nodes as proof. Treat them as observer anchors.
