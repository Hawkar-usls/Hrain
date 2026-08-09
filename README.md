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
- optional model-assisted suggestions.

## Boundary

```text
MATURITY = ACTIVE_PROTOTYPE
NEURAL_DECODING = NOT_IMPLEMENTED
CLINICAL_BCI_VALIDATION = NOT_PERFORMED
MEDICAL_DEVICE_STATUS = NOT_CLAIMED
REPOSITORY_LEVEL_REGULATORY_COMPLIANCE = NOT_CLAIMED
MEASURED_COMMUNICATION_GAIN = NOT_ESTABLISHED
```

Local operation can reduce unnecessary data exposure, but privacy/compliance depends on the full deployment, model provider, logging, and organizational controls.

## Review / run

- Live demo: https://hawkar-usls.github.io/Hrain/
- Machine-readable project status: [`PROJECT_STATUS.json`](PROJECT_STATUS.json)
- Related prototype: [iNaiHR](https://github.com/Hawkar-usls/iNaiHR)
- Portfolio maturity/visibility: [`portfolio-visibility.json`](https://github.com/Hawkar-usls/Janus/blob/main/portfolio-visibility.json)

Open `index.html` in a modern browser. Leave external model configuration empty for local/offline use.

## License

MIT. See [LICENSE](LICENSE).

Presentation follows the account's [public repository standard](https://github.com/Hawkar-usls/Janus/blob/main/docs/PUBLIC_REPOSITORY_PRESENTATION_STANDARD.md). No affiliation with MIT is implied by the presentation style.
