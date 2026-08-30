from __future__ import annotations

import copy
import unittest

from tools.hrain_conversation_context import (
    HRaiNConversationContextError,
    build_context,
    select_context,
)


def active_fixture():
    return {
        "schema": "janus.hrain.registry_graph_index.v1_0",
        "status": "AUTO_GENERATED_READ_ONLY_ACTIVE_REGISTRY_PROJECTION",
        "sourceCommit": "a" * 40,
        "objectCount": 3,
        "mutationPolicy": {
            "interfaceWriteAuthority": False,
            "interfaceDeleteAuthority": False,
        },
        "nodes": [
            {"id": "registry:janus-meta-registry", "label": "JANUS Meta Registry"},
            {"id": "obj:1", "label": "TRUMP candidate runtime", "path": "registry/TRUMP.json", "lineageKey": "TRUMP", "status": "CANDIDATE", "summary": "TRUMP may wake but P vs NP remains OPEN.", "surface": "proof", "modifiedAt": "2026-08-30T22:00:00Z", "sourceSha256": "1" * 64, "sourceUrl": "https://example/1", "readOnly": True},
            {"id": "obj:2", "label": "HRaiN memory", "path": "data/HRAIN.json", "lineageKey": "HRAIN", "status": "ACTIVE", "summary": "Meta Registry memory is projected through HRaiN.", "surface": "memory", "modifiedAt": "2026-08-30T21:00:00Z", "sourceSha256": "2" * 64, "sourceUrl": "https://example/2", "readOnly": True},
            {"id": "obj:3", "label": "Other", "path": "data/OTHER.json", "lineageKey": "OTHER", "status": "FROZEN", "summary": "Unrelated item.", "surface": "other", "modifiedAt": "2026-08-30T20:00:00Z", "sourceSha256": "3" * 64, "sourceUrl": "https://example/3", "readOnly": True},
        ],
    }


def full_fixture():
    return {
        "mode": "FULL_CURRENT",
        "source_commit": "b" * 40,
        "catalog_digest": "c" * 64,
        "historical_lineage_included": False,
        "coverage": {"coverage_complete": True, "cataloged_blob_count": 777},
        "authority": {"read_only": True, "source_mutation_allowed": False},
    }


class HRaiNConversationContextTests(unittest.TestCase):
    def test_builds_read_only_mediated_context(self):
        ctx = build_context(active_fixture(), full_fixture(), generated_at=100.0)
        self.assertEqual(ctx["schema"], "janus.hrain.conversation_context.v1")
        self.assertEqual(ctx["source_database"], "Hawkar-usls/janus-meta-registry")
        self.assertEqual(ctx["mediating_organ"], "Hawkar-usls/Hrain")
        self.assertEqual(ctx["object_count"], 3)
        self.assertTrue(ctx["full_current_coverage_complete"])
        self.assertFalse(ctx["authority"]["command_authority_granted"])
        self.assertFalse(ctx["authority"]["world_truth_authority_granted"])
        self.assertEqual(len(ctx["context_digest"]), 64)

    def test_query_selects_relevant_hrain_memory_without_authority(self):
        ctx = build_context(active_fixture(), full_fixture(), generated_at=100.0)
        selected = select_context(ctx, "Can TRUMP wake now and what is P vs NP?", limit=2)
        self.assertEqual(selected["schema"], "janus.hrain.selected_conversation_context.v1")
        self.assertEqual(selected["selected_objects"][0]["lineage_key"], "TRUMP")
        self.assertFalse(selected["authority"]["scientific_evidence_authority_granted"])
        self.assertEqual(len(selected["selection_digest"]), 64)

    def test_active_projection_write_authority_is_rejected(self):
        active = active_fixture()
        active["mutationPolicy"]["interfaceWriteAuthority"] = True
        with self.assertRaisesRegex(HRaiNConversationContextError, "AUTHORITY_CEILING"):
            build_context(active, full_fixture())

    def test_incomplete_full_current_is_rejected(self):
        full = full_fixture()
        full["coverage"]["coverage_complete"] = False
        with self.assertRaisesRegex(HRaiNConversationContextError, "COVERAGE_NOT_PROVEN"):
            build_context(active_fixture(), full)

    def test_context_tamper_is_rejected_before_selection(self):
        ctx = build_context(active_fixture(), full_fixture(), generated_at=100.0)
        ctx["objects"][0]["summary"] = "tamper"
        with self.assertRaisesRegex(HRaiNConversationContextError, "DIGEST_INVALID"):
            select_context(ctx, "TRUMP")

    def test_generation_clock_does_not_change_context_digest(self):
        a = build_context(active_fixture(), full_fixture(), generated_at=100.0)
        b = build_context(active_fixture(), full_fixture(), generated_at=999.0)
        self.assertNotEqual(a["generated_at"], b["generated_at"])
        self.assertEqual(a["context_digest"], b["context_digest"])


if __name__ == "__main__":
    unittest.main()
