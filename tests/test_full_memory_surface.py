from html.parser import HTMLParser
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])


def test_memory_surface_has_active_and_full_current_modes():
    html = (ROOT / "memory.html").read_text(encoding="utf-8")
    assert 'data-mode="active"' in html
    assert 'data-mode="full"' in html
    assert 'src="./janus.html"' in html
    assert "FULL CURRENT" in html


def test_full_current_source_is_meta_registry_and_shards_are_verified():
    js = (ROOT / "assets/hrain-memory.js").read_text(encoding="utf-8")
    assert "Hawkar-usls/janus-meta-registry/main" in js
    assert "assets/hrain-full-memory/manifest.json" in js
    assert "crypto.subtle.digest('SHA-256'" in js
    assert "SHARD_HASH_MISMATCH" in js
    assert "SHARD_SOURCE_COMMIT_MISMATCH" in js
    assert "coverage_complete" in js


def test_surface_is_read_only_and_does_not_claim_history_or_truth():
    contract = json.loads((ROOT / ".janus/HRAIN_FULL_MEMORY_SURFACE_CONTRACT.json").read_text(encoding="utf-8"))
    assert contract["authority"]["read_only"] is True
    assert contract["authority"]["delete_allowed"] is False
    assert contract["authority"]["source_mutation_allowed"] is False
    assert contract["authority"]["scientific_authority_granted"] is False
    assert "FULL_CURRENT != COMPLETE_GIT_HISTORY" in contract["laws"]
    assert "CATALOG_PRESENCE != SCIENTIFIC_VALIDITY" in contract["laws"]


def test_terminal_dataflow_law_is_explicit():
    contract = json.loads((ROOT / ".janus/HRAIN_FULL_MEMORY_SURFACE_CONTRACT.json").read_text(encoding="utf-8"))
    assert "TERMINAL_MEMORY_READOUT_MUST_PASS_THROUGH_HRAIN" in contract["laws"]
    assert contract["source_database"] == "Hawkar-usls/janus-meta-registry"


def test_no_duplicate_dom_ids():
    parser = IdCollector()
    parser.feed((ROOT / "memory.html").read_text(encoding="utf-8"))
    duplicates = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
    assert duplicates == []
