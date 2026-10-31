"""Tests of read-only legacy graph import. Never read owner NAS or private DB."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[1] / "tools" / "legacy_graph_sanitizer.py"
spec = importlib.util.spec_from_file_location("legacy_graph_sanitizer", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SHA = hashlib.sha256(b"synthetic").hexdigest()

class LegacyGraphPrivacyTests(unittest.TestCase):
    def test_private_fields_never_project_and_no_phantom_core(self):
        original = {"nodes":[
            {"id":"alpha","kind":"concept","label":"very-secret-label",
             "description":"private body text","chatHistory":["private-chat"],
             "data":{"email":"private@example.test","key":"private-key"}},
            {"id":"beta","type":"unknown-private-type","tags":["sensitive"]}
        ],"links":[{"source":"alpha","target":"beta","kind":"related",
                     "content":"secret-edge-payload"}]}
        result=mod.project(original,SHA)
        serialized=json.dumps(result)
        for private in ["very-secret-label","private body text","private-chat",
                        "private@example.test","private-key","secret-edge-payload",
                        "unknown-private-type"]:
            self.assertNotIn(private,serialized)
        self.assertEqual(result["nodes"],[{"n":0,"kind":"concept"},{"n":1,"kind":"other"}])
        self.assertEqual(result["edges"],[[0,1,"related"]])
        self.assertEqual(result["stats"]["nodes_kept"],2)

    def test_no_generated_nodes_or_dangling_links(self):
        result=mod.project({"nodes":[{"id":"a"},{}],
                            "links":[{"source":"a","target":"ghost"},
                                     {"source":"ghost","target":"a"}]},SHA)
        self.assertEqual(result["nodes"],[{"n":0,"kind":"other"}])
        self.assertEqual(result["edges"],[])
        self.assertEqual(result["stats"]["nodes_skipped_missing_id"],1)
        self.assertEqual(result["stats"]["edges_skipped_dangling"],2)

    def test_legacy_fusion_edges_and_duplicate_dedupe(self):
        old={"nodes":[{"id":"core"},{"id":"one"}],
             "edges":[{"src":"core","dst":"one","kind":"observed"},
                      {"src":"core","dst":"one","kind":"observed"}]}
        result=mod.project(old,SHA)
        self.assertEqual(result["edges"],[[0,1,"observed"]])
        self.assertEqual(result["stats"]["edges_collapsed_exact_duplicate"],1)
        self.assertEqual(result["stats"]["nodes_kept"],2)

    def test_node_map_and_prism_adj(self):
        graph={"nodes":{"m":{"label":"do-not-copy","type":"memory"},
                        "n":{"type":"root"}},
               "adj":{"m":{"n":5.7},"n":{}}}
        result=mod.project(graph,SHA)
        self.assertEqual(result["nodes"],[{"n":0,"kind":"memory"},{"n":1,"kind":"root"}])
        self.assertEqual(result["edges"],[[0,1,"other"]])

    def test_mapping_link_format(self):
        result=mod.project({"nodes":[{"id":"x"},{"id":"y"}],
                            "links":{"x->y":{"type":"hypothesized"},
                                     "x->ghost":{"private":"value"}}},SHA)
        self.assertEqual(result["edges"],[[0,1,"hypothesized"]])
        self.assertEqual(result["stats"]["edges_skipped_dangling"],1)

    def test_duplicate_ids_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"LEGACY_DUPLICATE_NODE_ID"):
            mod.project({"nodes":[{"id":"a"},{"id":"a"}]},SHA)

    def test_bounded_file_inspection_is_read_only(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"private_graph.json"
            original={"nodes":[{"id":"x","chatHistory":["secret"]}],"links":[]}
            content=json.dumps(original).encode("utf-8")
            path.write_bytes(content)
            before=path.read_bytes()
            result=mod.inspect_file(path)
            self.assertEqual(result["source_sha256"],hashlib.sha256(content).hexdigest())
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(len(list(Path(t).iterdir())),1)
            self.assertNotIn("secret",json.dumps(result))

    def test_oversized_source_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"too_big.json"
            with path.open("wb") as stream:
                stream.truncate(mod.MAX_INPUT_BYTES + 1)
            with self.assertRaisesRegex(ValueError,"LEGACY_SOURCE_TOO_LARGE"):
                mod.inspect_file(path)

    def test_invalid_node_and_edge_structures_rejected(self):
        for graph in ({"nodes":"plain text"},{"nodes":[],"links":"unknown"},
                      {"nodes":{},"adj":{"a":["b"]}}):
            with self.subTest(g=graph):
                with self.assertRaises(ValueError):
                    mod.project(graph,SHA)

if __name__ == "__main__":
    unittest.main()
