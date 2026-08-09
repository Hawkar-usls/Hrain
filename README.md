# HRain — Local-First Cognitive Graph Workspace

**HRain** is a browser-based visual workspace for turning notes, ideas, and short inputs into an explorable graph.

It combines a D3.js force-directed interface with optional AI-assisted expansion, per-node context, JSON import/export, and a local-first operating mode.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Demo-Live-00ffa3.svg)](https://hawkar-usls.github.io/Hrain/)

## What it is

HRain is an **interaction and visualization project**. It is useful as a mind-mapping interface, an experimental low-bandwidth input workspace, and a front end for local or self-hosted language-model workflows.

The project does not claim to decode neural activity, provide a clinically validated BCI interface, or satisfy medical/regulatory compliance requirements by itself.

## Operating modes

| Mode | Network | Model access | Data path |
| --- | --- | --- | --- |
| **Pure Offline** | Not required | AI disabled | Browser-local state |
| **Direct Model Provider** | Required | User-configured provider | Depends on provider |
| **Self-Hosted Proxy** | Depends on deployment | Local/self-hosted or routed models | Under operator control |

Local operation can reduce unnecessary data exposure, but privacy and compliance depend on the complete deployment, configuration, provider, logging, and organizational controls.

## Features

- **Force-directed graph workspace** with draggable nodes and links.
- **DIVE / ASCEND navigation** for moving through idea clusters.
- **Optional AI suggestions** for node expansion and synthesis.
- **Per-node context** for focused exploration.
- **Dynamic visualization** with particles, impulses, grids, and semantic status cues.
- **JSON export/import** for portable local backups.
- **Touch and mouse support** for desktop and mobile browsers.
- **Offline-first mode** with browser-local storage and no mandatory model dependency.

## Low-bandwidth / BCI research direction

HRain can be used to prototype workflows in which a small number of symbols or short decoded messages are expanded into a richer graph that the user can inspect and edit.

That is a **research direction**, not an established performance claim. The repository currently does not establish:

```text
NEURAL_DECODING = NOT_IMPLEMENTED
CLINICAL_BCI_VALIDATION = NOT_PERFORMED
MEDICAL_DEVICE_STATUS = NOT_CLAIMED
REGULATORY_COMPLIANCE = DEPLOYMENT_DEPENDENT_NOT_CLAIMED_BY_REPOSITORY
MEASURED_COMMUNICATION_GAIN = NOT_ESTABLISHED
```

## Quick start

Clone the repository and open `index.html` in a modern browser.

For pure offline use, leave external model configuration empty. If AI features are enabled, configure the selected provider or self-hosted endpoint and keep credentials out of committed source files.

## Related project

[iNaiHR](https://github.com/Hawkar-usls/iNaiHR) explores AI-assisted semantic expansion for short user inputs. HRain remains the cleaner local-first visualization surface.

## Author

Oleksandr Ahapov (Hawkar) — Ukraine

## License

MIT License. See `LICENSE`.
