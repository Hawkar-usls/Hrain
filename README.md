<div align="center">

# HRain
### Local-first cognitive graph workspace

![Status](https://img.shields.io/badge/status-active%20prototype-2f81f7)
![Class](https://img.shields.io/badge/class-interaction%20prototype-6e7681)

</div>

## Status

**Active Prototype.** HRain is implemented and usable as a browser workspace, but it remains a prototype. Interfaces, AI-assistance behavior, and validation may change.

## Abstract

HRain turns notes, ideas, and short inputs into an editable visual graph. It is browser-based, can run locally/offline, and can optionally use model-assisted suggestions when configured.

## Implemented scope

- D3.js force-directed graph interaction;
- draggable nodes and links;
- per-node context;
- JSON import/export;
- touch/mouse interaction;
- browser-local/offline mode;
- optional model-assisted suggestions;
- dedicated read-only JANUS Meta Registry graph viewer;
- living Registry Mode physics with organic links, impulses, breathing membranes, DIVE/ASCEND navigation and dynamic ambience;
- read-only DemiHead `LEFT_HRAIN` hemisphere sidecar with deterministic packet normalization.

## DemiHead left hemisphere

HRain now has a separate [`demihead.html`](demihead.html) sidecar and [`demihead-bridge.js`](demihead-bridge.js) packet builder for the JANUS DemiHead bicameral bridge.

The naming is a **software architecture metaphor**, not a neuroscience claim:

```text
HRain / LEFT_HRAIN = STRUCTURAL_CONTEXT
DemiHead             = bind / compare / preserve disagreement

iNaiHR / RIGHT_INAIHR = ASSOCIATIVE_CONTEXT
```

The sidecar reads only the current browser-local HRain workspace and emits `janus.demihead.hemisphere_packet.v1`. It does not write back to HRain, iNaiHR, JANUS Meta Registry, GitHub, or any external platform.

Legacy nodes that do not already contain explicit origin metadata are exported as `LEGACY_UNKNOWN`; the bridge does not guess that they were human-authored.

```text
HEMISPHERE_METAPHOR != NEUROSCIENCE_CLAIM
STRUCTURE != COMMAND
BOTH_HEMISPHERES_AGREE != TRUTH
PACKET_TRANSFER = READ_ONLY
DIRECT_CROSS_HEMISPHERE_MUTATION = false
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```

The sidecar can also answer an explicit `JANUS_DEMIHEAD_REQUEST_PACKET_V1` `postMessage` from the same GitHub Pages origin or localhost development origin and responds only to that exact origin, never to `*`.

## JANUS Meta Registry bridge

`janus.html` is a separate **read-only Registry Mode**. It consumes the automatically generated index published by [`Hawkar-usls/janus-meta-registry`](https://github.com/Hawkar-usls/janus-meta-registry) and renders the active registry projection as:

```text
JANUS Meta Registry
→ research surfaces
→ versioned registry objects
→ authoritative source URL
```

Live Registry Mode: https://hawkar-usls.github.io/Hrain/janus.html

The ordinary HRain workspace remains separate and editable. Registry Mode does not write back to the Meta Registry and does not replace source JSON, current-authority records, receipts or code.

`WIPE LOCAL DESK` in Registry Mode is deliberately **not a database operation**. It rebuilds only the current browser runtime layout from the already fetched immutable projection. Registry Mode has one network fetch for the read-only index and no persistence, deletion, update or write channel.

```text
HRAIN_GRAPH != REGISTRY_AUTHORITY
REGISTRY_INDEX != SOURCE_OBJECT
READ_ONLY_PRESENTATION != WRITE_AUTHORITY
HRAIN_WIPE != REGISTRY_DELETE
LOCAL_DESK_RESET != SOURCE_MUTATION
JANUS_META_REGISTRY = APPEND_ONLY_FROM_HRAIN_PERSPECTIVE
```

## Boundary

```text
MATURITY = ACTIVE_PROTOTYPE
NEURAL_DECODING = NOT_IMPLEMENTED
CLINICAL_BCI_VALIDATION = NOT_PERFORMED
MEDICAL_DEVICE_STATUS = NOT_CLAIMED
REPOSITORY_LEVEL_REGULATORY_COMPLIANCE = NOT_CLAIMED
MEASURED_COMMUNICATION_GAIN = NOT_ESTABLISHED
MEASURED_BICAMERAL_COGNITIVE_GAIN = NOT_ESTABLISHED
```

Local operation can reduce unnecessary data exposure, but privacy/compliance depends on the full deployment, model provider, logging, and organizational controls.

## Review / run

- Live demo: https://hawkar-usls.github.io/Hrain/
- JANUS Registry Mode: https://hawkar-usls.github.io/Hrain/janus.html
- DemiHead left-hemisphere sidecar: https://hawkar-usls.github.io/Hrain/demihead.html
- Machine-readable project status: [`PROJECT_STATUS.json`](PROJECT_STATUS.json)
- Related prototype: [iNaiHR](https://github.com/Hawkar-usls/iNaiHR)
- Portfolio maturity/visibility: [`portfolio-visibility.json`](https://github.com/Hawkar-usls/Janus/blob/main/portfolio-visibility.json)

Open `index.html` in a modern browser. Leave external model configuration empty for local/offline use.

## License

MIT. See [LICENSE](LICENSE).

Presentation follows the account's [public repository standard](https://github.com/Hawkar-usls/Janus/blob/main/docs/PUBLIC_REPOSITORY_PRESENTATION_STANDARD.md). No affiliation with MIT is implied by the presentation style.
