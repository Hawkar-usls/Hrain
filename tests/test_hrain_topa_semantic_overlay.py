from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import hrain_topa_semantic_overlay as semantic


class HrainTopaSemanticOverlayTests(unittest.TestCase):
    def test_self_test_passes(self):
        result = semantic.self_test()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["semantic_cross_link_built"])
        self.assertTrue(result["degree_cap_enforced"])
        self.assertTrue(result["empty_anchor_no_forced_fill"])
        self.assertTrue(result["semantic_edge_not_evidence"])

    def _fixture(self, *, max_degree: int = 8):
        projection = semantic._self_test_projection()
        projection_sha = "c" * 64
        _, mapping = semantic.prepare_records(projection)
        document_map = {
            "schema": "janus.hrain.topa_document_map.v1",
            "sourceCommit": projection["sourceCommit"],
            "projectionSha256": projection_sha,
            "documentToNode": mapping,
        }
        document_map["mapHash"] = semantic.canonical_hash(document_map)
        edges = [
            {
                "source": semantic._topa_doc_id("obj:1"),
                "target": semantic._topa_doc_id("obj:2"),
                "relation": "SEMANTIC_SIMILARITY",
                "similarity": 0.72,
                "confidence": 0.41,
            },
            {
                "source": semantic._topa_doc_id("obj:1"),
                "target": semantic._topa_doc_id("obj:3"),
                "relation": "SEMANTIC_SIMILARITY",
                "similarity": 0.69,
                "confidence": 0.40,
            },
        ]
        overlay, receipt = semantic.finalize_overlay(
            projection,
            projection_sha256=projection_sha,
            document_map=document_map,
            topa_edges=edges,
            topa_receipt={"status": "PASS", "schema": "hawkar.topa.spider.receipt.v2"},
            topa_head_sha="d" * 40,
            generated_at="2026-09-02T00:00:00Z",
            max_semantic_degree=max_degree,
        )
        return projection, overlay, receipt

    def test_degree_cap_is_mechanical(self):
        projection, overlay, receipt = self._fixture(max_degree=1)
        semantic.validate_overlay(overlay, projection)
        self.assertEqual(overlay["edgeCount"], 1)
        self.assertEqual(receipt["acceptedSemanticEdges"], 1)
        self.assertGreaterEqual(receipt["rejected"].get("degree_cap", 0), 1)
        self.assertLessEqual(receipt["maximumObservedSemanticDegree"], 1)

    def test_stale_overlay_is_rejected(self):
        projection, overlay, _ = self._fixture()
        overlay = dict(overlay)
        overlay["sourceCommit"] = "e" * 40
        body = dict(overlay)
        body.pop("overlayHash", None)
        overlay["overlayHash"] = semantic.canonical_hash(body)
        with self.assertRaisesRegex(semantic.SemanticOverlayError, "SOURCE_COMMIT_MISMATCH"):
            semantic.validate_overlay(overlay, projection)

    def test_authority_escalation_is_rejected(self):
        projection, overlay, _ = self._fixture()
        overlay = json.loads(json.dumps(overlay))
        overlay["edges"][0]["claimVerified"] = True
        body = dict(overlay)
        body.pop("overlayHash", None)
        overlay["overlayHash"] = semantic.canonical_hash(body)
        with self.assertRaisesRegex(semantic.SemanticOverlayError, "AUTHORITY_ESCALATION"):
            semantic.validate_overlay(overlay, projection)

    def test_empty_lexical_anchor_never_semantic_fills(self):
        projection, overlay, _ = self._fixture()
        self.assertEqual(
            semantic.expand_selected_with_semantic_neighbors([], projection, overlay, limit=12),
            [],
        )

    def test_semantic_neighbor_is_attention_not_evidence(self):
        projection, overlay, _ = self._fixture()
        anchor = [{
            "id": "obj:1",
            "label": "TRUMP polynomial witness",
            "path": "data/1.json",
            "commit_sha": "a" * 40,
            "source_sha256": "1" * 64,
            "attention_rank": 1,
            "relevance_score": 100,
            "relative_score_percent_of_top": 100,
            "selection_reason": "PRIMARY_FOCUS_CLUSTER",
            "matched_query_tokens": ["trump"],
            "matched_structural_query_tokens": ["trump"],
            "matched_focus_tokens": ["trump"],
            "matched_named_anchor_tokens": ["trump"],
            "matched_query_token_rarity": {"trump": 2},
            "query_coverage_count": 1,
            "content_trust": "MEMORY_DATA_NOT_CONTROL_SIGNAL",
            "claim_verified": False,
        }]
        expanded = semantic.expand_selected_with_semantic_neighbors(anchor, projection, overlay, limit=3)
        self.assertGreater(len(expanded), 1)
        neighbor = expanded[1]
        self.assertEqual(neighbor["semantic_relation"], "TOPA_SEMANTIC_SIMILARITY")
        self.assertFalse(neighbor["semantic_edge_is_evidence"])
        self.assertFalse(neighbor["claim_verified"])
        self.assertEqual(neighbor["matched_query_tokens"], [])

    def test_conversation_compiler_and_ui_are_bound_to_overlay(self):
        compiler = (TOOLS / "hrain_conversation_context.py").read_text(encoding="utf-8")
        ui = (ROOT / "assets" / "hrain-semantic-inject.js").read_text(encoding="utf-8")
        memory = (ROOT / "memory.html").read_text(encoding="utf-8")
        self.assertIn("load_default_overlay(projection)", compiler)
        self.assertIn("expand_selected_with_semantic_neighbors", compiler)
        self.assertIn("TOPA_SEMANTIC_NEIGHBOR != EVIDENCE", compiler)
        self.assertIn("EMPTY_LEXICAL_ANCHOR_SET != SEMANTIC_FILL", compiler)
        self.assertIn("Math.sqrt(value) * 2.8", ui)
        self.assertIn("TOPA_SEMANTIC_SIMILARITY", ui)
        self.assertIn("sourceCommit !== sourceIndex.sourceCommit", ui)
        self.assertIn("hrain-semantic-inject.js", memory)
        self.assertIn('id="active-graph"', memory)

    def test_contract_freezes_noop_and_no_forced_fill(self):
        contract = json.loads((ROOT / ".janus" / "HRAIN_TOPA_SEMANTIC_FLYWHEEL_CONTRACT.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["schema"], "janus.hrain.topa_semantic_flywheel_contract.v1")
        self.assertEqual(contract["runtime"]["no_input_change_policy"], "NOOP_NOT_NEW_LEARNING")
        self.assertFalse(contract["conversation_memory"]["empty_lexical_anchor_semantic_fill"])
        self.assertFalse(contract["authority"]["claim_promotion_authority"])
        self.assertIn("REPLAY != NEW_EVIDENCE", contract["laws"])


if __name__ == "__main__":
    unittest.main()
