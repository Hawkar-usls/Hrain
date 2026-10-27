# HRAiN v77 · local All Star recovery

## What is included
The original JANUS HRAiN v77 D3 graph is restored in `hrain-v77.html`. The exact owner's `hrain_janus.html` source remains on their local disk; a newline-normalized archival source copy is available in `legacy/hrain-v77-allstar-original.html`. Existing modern `index.html` (v10.5) and `janus.html` continue working separately.

The local reader `tools/hrain_v77_readonly_bridge.py` binds **only to 127.0.0.1**, accepts **only GET/HEAD**, blocks all POST/PUT/PATCH/DELETE and validates the `Host` header. It serves only `hrain-v77.html` and two required Atlas scripts, never browses arbitrary disk paths. No local graph JSON enters Git or public GitHub Pages.

## Use the real saved All Star graph
From a trusted local checkout of this HRAiN repo, with Python 3.12+:

```powershell
python tools/hrain_v77_readonly_bridge.py --verify-snapshot --snapshot "E:\Janus_Love\Janus_Titan\All Star\raw_logs\hrain_graph_state.json"
python tools/hrain_v77_readonly_bridge.py --snapshot "E:\Janus_Love\Janus_Titan\All Star\raw_logs\hrain_graph_state.json" --port 8812
```

Then open **http://127.0.0.1:8812/hrain-v77.html**. Close the terminal to stop the service.

A separate preassembled preview is also present on the owner's machine at:
`E:\Janus_Love\Janus_Titan\All Star\artifacts\hrain_v77_safe_preview\`.
It has `START_HRAIN_V77_READONLY.bat`, the restored HTML, the Atlas scripts and the loopback reader. The source All Star files are untouched.

### Independently tested on actual local memory

The verified source `raw_logs/hrain_graph_state.json` had SHA-256
`991c5866f8c49610b039127a5117a1de1729beae94d7579e2a3f4284aa942979`, **100 nodes, 9,737 directed edge records, tick 31,625**. A real local headless Chrome browser confirmed 100/9,737 loaded from the private snapshot through the loopback bridge, no mutations, read-only status API PASS, original v77 D3 PASS. At the top of that graph, the active hierarchical view exposed 12/12 visible edges. Separately, Chromium stress-tested 100 synthetic root nodes and 9,737 synthetic edges, retaining the full graph while rendering 750 at once.

### Distinguish three kinds of knowledge

- **Original graph**: private local server data (read-only snapshot).
- **JANUS Atlas**: temporary, verified public JSON edges with exact source pointer and immutable catalog provenance; never saved to v89, never SYNTH authority.
- **Manual v77 draft**: tab-scoped `sessionStorage` with explicit local JSON export/import; browser draft is NOT server authority.

SYNTH POST and `/api/hrain/save` POST are intentionally absent from the restored public viewer because the All Star server's `handle_save_state` REPLACES the full graph. The original v89 autonomy and WebSocket event stream were not deployed or modified here.

## Still blocked
An authenticated, transaction-safe v89 editing bridge (optimistic concurrency, versioned patches, immutable backup/rollback, protected-role policy, explicit authorization) remains **not implemented**. Do not directly expose `server.py` to the public internet; its current `0.0.0.0` bind and mutating routes need independent security review.

The 483-file source audit is saved locally to `artifacts\audits\janus_allstar_readonly_inventory_20261027.json`. Private graph bodies, logs, tokens, device data, backups, source model weights and runtime secrets were not uploaded.
