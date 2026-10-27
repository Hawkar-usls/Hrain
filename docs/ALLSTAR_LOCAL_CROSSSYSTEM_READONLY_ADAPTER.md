# JANUS · read-only cross-system adapter recovered from All Star

Owner-authorized source: `E:\Janus_Love\Janus_Titan\All Star\ecosystem_bridges.py` (13,579 bytes; SHA-256 `7191d8fd29755b40a78576d7744cf40e0c3b1c28c24ace027f3490ecfea9830b`).

## Why the old bridge is NOT safe to transplant

Original `ecosystem_bridges.py` implements `import_hrain_seed`, `sync_genesis_state` and `sync_bfain_state` by creating or replacing HRAiN role nodes and modifying `autonomy.graph` and runtime. `read_bfain_snapshot` calls `http://127.0.0.1:1139/api/pvp/state` and `/api/pvp/progress` without a demonstrated authentication contract. That might perturb already restored state or incorrectly imply simulation progress demonstrates scientific results. Original `_integration_sources/Hrain/janus_v20.3.json` is missing from expected location; do not fabricate the seed.

## Safe implemented subset

`tools/janus_allstar_local_projection.py` is a fully standalone Python 3.12+ **private, file-based, no-network** adapter. It only reads specifically allowlisted JSON snapshots from the owner's `raw_logs`:

- `hrain_graph_state.json` — count nodes, edges and tick, not graph contents.
- `janus_world_state.json` — whitelisted numeric sandbox state and *counts*, no self-model prose or narrative.
- `janus_world_agents.json` — population/memory lengths and tick, not agents or conversations.
- `bfain_snapshot.json` — optional **offline manually captured** state+progress; absent in the inspected All Star tree, explicitly `MISSING_LOCAL_SOURCE`. The old 1139 HTTP service is never queried.

All present input files must fit per-file size caps, parse as valid JSON, and have SHA-256 reported in a separate **owner-private local receipt**. Every derived node is `readOnly`, `synthAuthority:false`; every edge is `LOCAL_DERIVED_STRUCTURE`, never `EXPLICIT_SOURCE_REFERENCE`. This does not certify Genesis simulation or solve P vs NP. An invalid source fails closed without altering the original.

### Run on the owner's authorized local Windows PC

From a trusted HRAiN checkout:

```powershell
python tools/janus_allstar_local_projection.py --root "E:\Janus_Love\Janus_Titan\All Star" --output "E:\Janus_Love\Janus_Titan\All Star\artifacts\audits\JANUS-CROSSSYSTEM-LOCAL-READONLY-PROJECTION-v1.json"
```

Only the derived receipt is created; an existing receipt is never overwritten. Its path must stay within `artifacts/audits`. No input file, original HRAiN graph or private logs are copied to GitHub.

### Admission barriers for future integration

To turn these into clickable native HRAiN/iNaiHR graph context, an authenticated local-only bridge must explicitly carry a separate *local source class* and ephemeral overlay, without conflating its edges with the public SHA-indexed JSON references or iNaiHR semantic hypotheses. No live remote API, device queue, SYNTH call or science promotion is authorized by this adapter. `TOPA` must independently adjudicate any actual scientific claim.

CI: `python -m unittest discover -v -s tests -p 'test_janus_allstar_local_projection.py'`.
