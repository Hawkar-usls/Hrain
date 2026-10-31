"""Static/structural tests for quarantined historical Shrine recovery.

Do not execute archived Python source, do not open external files or network.
"""
import ast
from collections import Counter
import json
from pathlib import Path
import unittest

BASE=Path(__file__).resolve().parents[1]/"legacy"/"nas-i0-a15"
SHA="8414ec62c70fad9453fec5105e986b3684adfeee26a289173a419616d5ebd742"
KINDS={"accepted","json","route","old_shrine_html","semantic_event",
       "concept","essence","doctrine","bias","core","mirror"}


class LegacyShrineRecoveryTests(unittest.TestCase):
    def test_legacy_sources_are_parseable_not_executed(self):
        names=["shrine_build_semantic_core.py","temple_build_graph.py",
               "hrain_live_watcher.py"]
        for name in names:
            source=(BASE/name).read_text(encoding="utf-8")
            with self.subTest(source=name):
                ast.parse(source,filename=name)
                self.assertNotIn("-----BEGIN OPENSSH PRIVATE KEY-----",source)
                self.assertNotIn("github_pat_",source)
                self.assertNotIn("ghp_",source)

    def test_graph_contracts_parse_without_network(self):
        for name in ["janus_shrine_graph.schema.json",
                     "janus_temple_graph.schema.json",
                     "hrain_live_graph.schema.json",
                     "temple_route_bias.schema.json"]:
            schema=json.loads((BASE/"schemas"/name).read_text())
            self.assertIsInstance(schema,dict)
            self.assertTrue(schema)

    def test_projection_preserves_all_edges_without_original_labels(self):
        idx=json.loads((BASE/"projection"/"index.json").read_text())
        self.assertEqual(idx["source_sha256"],SHA)
        self.assertEqual(idx["raw_node_count"],559)
        self.assertEqual(idx["raw_edge_count"],3996)
        self.assertEqual(idx["projected_node_count"],559)
        self.assertEqual(idx["projected_edge_count"],3996)
        self.assertEqual(idx["dangling_raw_links_excluded"],0)
        self.assertEqual({tuple(n) for n in []},set())
        nodes=idx["nodes"]
        self.assertEqual(len(nodes),559)
        self.assertEqual([n["n"] for n in nodes],list(range(559)))
        self.assertTrue(all(set(n)=={"n","kind"} and n["kind"] in KINDS
                            for n in nodes))
        seen=0
        types=Counter()
        for part_spec in idx["parts"]:
            part=json.loads((BASE/"projection"/part_spec["file"]).read_text())
            self.assertEqual(part["source_sha256"],SHA)
            self.assertEqual(part["schema"],"janus.legacy_shrine.topology_part.v1")
            self.assertEqual(len(part["edges"]),part_spec["edge_count"])
            for src,dest,kind in part["edges"]:
                self.assertIs(type(src),int)
                self.assertIs(type(dest),int)
                self.assertTrue(0<=src<559 and 0<=dest<559)
                self.assertRegex(kind,r"^[a-z_]+$")
                types[kind]+=1
                seen+=1
        self.assertEqual(seen,3996)
        self.assertEqual(dict(types),idx["edge_kind_counts"])
        text=json.dumps(idx)
        for forbidden in ['"label"','"data"','"source_path"','"evidence"','"weight"']:
            self.assertNotIn(forbidden,text)


if __name__=="__main__":
    unittest.main()
