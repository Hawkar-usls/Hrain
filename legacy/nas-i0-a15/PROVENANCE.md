# JANUS NAS Archaeology · Historical Shrines A15/A15.3/A15.5

**Origin:** owner-operated QNAP `Janus/All Janus/I0`, recovered 2026-10-31. Original files stay on NAS.

This directory preserves **historical, untrusted, observer-only reference sources**:
- `temple_build_graph.py`: A15 Temple graph builder — original NAS SHA-256 `0b9e065024458151c6ea58b0d6f9ee3c6d577efe59aa17a150a37595aea4ec73`.
- `shrine_build_semantic_core.py`: A15.3 semantic atoms, essence families, source→concept and route pressure builder — SHA-256 `48bb2ad18cfbef3d85cb14173de0aee13c5f739afcdbccf6247a6ad556c10754`.
- `hrain_live_watcher.py`: A15.5 log observer and mirror-evidence guard — SHA-256 `cce474a0536d5c378591c97bd53e0efb43e27ad7188b0d38e6f5b67e0d2e6a96`.
- Historical README and graph-schema files.

These are **textual copies with normalized line endings**, not bit-identical restorations of Python source. The SHA-256 above refers to the original bytes on NAS. Do not silently change their runtime semantics or execute them in deployed HRAiN.

## Historical graphs

| Historical artifact | Original NAS SHA-256 | Observed |
|---|---|---|
| A15 `janus_temple_graph.json` | `9d74f3eedf35c111dc7050e187b01b52a1752891182e284eeed1c8017c1f6e48` | 19 nodes, 17 links |
| A15.3 `janus_shrine_graph.json` | `8414ec62c70fad9453fec5105e986b3684adfeee26a289173a419616d5ebd742` | 559 nodes, 3996 links |
| A15.5 `hrain_live_graph.json` | `376d8cdacee376b2affe15c509e9cf489e381299b0f6367b0ebb456d3370444d` | 8 nodes, 7 links |

The raw 1.3 MB Shrine graph was **not** copied to public GitHub: it includes text labels, evidence and paths. The `projection/` directory contains a deliberately **label-stripped structural view** of 559 nodes and 3996 links, with compact `n` indices, allowlisted node kind names and link kind names. Original IDs, labels, `data`, source paths, timestamps, weights and evidence do **not** appear. This is **not a formal privacy/anonymization guarantee** against topology correlation; restrict re-use accordingly.

## Important truth & safety boundaries

The A15/A15.3/A15.5 packs were built around historical I0/A14 miner observations. Per original readmes: `WIRE/HASH/SUBMIT` were frozen, mirror was untouched and bias outputs were observer-only. These design choices are useful as JANUS **separation-of-concerns and evidence-contamination guards**; neither mined hashes nor graph connections constitute scientific evidence of AI superiority, intelligence, or P=NP.

No production HRAiN graph, model weight, memory database, miner or Keymaster queue has been modified. These archival files are for interpretation and explicitly reviewed future porting only.

The historical SQLite databases have been enumerated **schema-only** separately in JANUS Meta Registry. Their raw rows include chat, memory, vector and `vault` content; do not publish unredacted DBs or serialized models. Test via `python -m unittest discover -s tests -p test_nas_legacy_shrine_archive.py -v`.

**Next engineering gate:** compare the archived A15.3 graph schema with current HRAiN/iNaiHR parsers, implement a read-only adapter with synthetic fixtures, and validate provenance before treating legacy edges as first-class memory.
