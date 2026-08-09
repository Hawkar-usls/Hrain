<div align="center">

# HRain
### Local-first cognitive graph workspace

`browser-based` · `offline-capable` · `optional AI assistance`

</div>

HRain is a browser workspace for turning notes, ideas and short inputs into an editable visual graph.

It is an **interaction prototype**, not a neural decoder or clinically validated BCI system.

- **Live demo:** https://hawkar-usls.github.io/Hrain/
- **Machine-readable status:** [`PROJECT_STATUS.json`](PROJECT_STATUS.json)
- **Related AI-assisted prototype:** [iNaiHR](https://github.com/Hawkar-usls/iNaiHR)

## Implemented scope

- D3.js force-directed graph interaction;
- draggable nodes and links;
- per-node context;
- JSON import/export;
- touch/mouse interaction;
- browser-local/offline mode;
- optional model-assisted suggestions when configured.

## Boundary

```text
NEURAL_DECODING = NOT_IMPLEMENTED
CLINICAL_BCI_VALIDATION = NOT_PERFORMED
MEDICAL_DEVICE_STATUS = NOT_CLAIMED
REPOSITORY_LEVEL_REGULATORY_COMPLIANCE = NOT_CLAIMED
MEASURED_COMMUNICATION_GAIN = NOT_ESTABLISHED
```

Local operation can reduce unnecessary data exposure, but privacy/compliance depends on the full deployment, provider, logging and organizational controls.

## Run

Open `index.html` in a modern browser. Leave external model configuration empty for local/offline use.

## License

MIT. See [LICENSE](LICENSE).
