"""JANUS All Star read-only typed cross-system source projection regression."""
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("allstar_local",ROOT/"tools/janus_allstar_local_projection.py")
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

class AllStarSnapshotTests(unittest.TestCase):
    def fixture(self,root):
        logs=root/"raw_logs";logs.mkdir()
        (root/"artifacts"/"audits").mkdir(parents=True)
        files={
            "hrain_graph_state.json":{"nodes":{"n1":{},"n2":{}},"edges":{"n1->n2":{}},"tick":7},
            "janus_world_state.json":{"level":4,"gold":22,"record_count":31,
               "inventory":["sword"],"limbs":[{"id":"limb-a"}],
               "base_upgrades":{"wall":{}},"faction_reputation":{"alpha":2},
               "self_model":{"name":"PRIVATE_OWNER_NAME","goal":"never leak this"}},
            "janus_world_agents.json":{"tick":123,"population":[{},{}],"memory":[{},{}]},
        }
        for name,body in files.items():
            (logs/name).write_text(json.dumps(body),encoding="utf8")
        return files

    def test_current_systems_without_bfain_http(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);self.fixture(root)
            result=tool.build(root)
            self.assertEqual(result["schema"],tool.SCHEMA)
            self.assertTrue(result["authority"]["readOnly"])
            self.assertFalse(result["authority"]["writeAuthority"])
            self.assertFalse(result["authority"]["topaAutoAdjudication"])
            self.assertFalse(result["authority"]["pEqualsNpClaim"])
            self.assertEqual(len(result["sources"]),4)
            self.assertEqual(len(result["nodes"]),4)
            self.assertEqual(len(result["edges"]),3)
            self.assertEqual(result["sources"][-1]["status"],"MISSING_LOCAL_SOURCE")
            world=result["sources"][1]["metadata"]
            self.assertEqual(world["level"],4)
            self.assertEqual(world["inventoryCount"],1)
            self.assertEqual(result["sources"][0]["metadata"]["nodes"],2)
            self.assertEqual(result["sources"][0]["metadata"]["edges"],1)
            self.assertNotIn("PRIVATE_OWNER_NAME",json.dumps(result))
            self.assertTrue(all(e["relationClass"]=="LOCAL_DERIVED_STRUCTURE"
                                for e in result["edges"]))
            self.assertTrue(all(n["readOnly"] for n in result["nodes"]))
            destination=root/"artifacts"/"audits"/"projection.json"
            sha=tool.save_private(root,destination,result)
            self.assertEqual(sha,hashlib.sha256(destination.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError):
                tool.save_private(root,destination,result)

    def test_optional_bfain_offline_snapshot_is_not_scientific_proof(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);self.fixture(root)
            (root/"raw_logs"/"bfain_snapshot.json").write_text(json.dumps({
                 "state":{"agents":[{"id":"game_a"}]},
                 "progress":{"np_progress":0.99,"winning":"NOT_A_PROOF"}}))
            r=tool.build(root)
            self.assertEqual(len(r["nodes"]),5)
            self.assertEqual(r["sources"][-1]["metadata"]["agentCount"],1)
            self.assertEqual(r["sources"][-1]["metadata"]["gameProgressNotNPProof"],0.99)
            self.assertFalse(r["authority"]["pEqualsNpClaim"])
            self.assertNotIn("NOT_A_PROOF",json.dumps(r))

    def test_no_filesystem_escape_or_invalid_schema(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);self.fixture(root)
            data=tool.build(root)
            with self.assertRaisesRegex(ValueError,"PRIVATE_LOCAL_OUTPUT_PATH_REQUIRED"):
                tool.save_private(root,root/"raw_logs"/"stolen.json",data)
            with self.assertRaisesRegex(ValueError,"PRIVATE_LOCAL_OUTPUT_PATH_REQUIRED"):
                tool.save_private(root,root.parent/"unapproved.json",data)
            world=root/"raw_logs"/"janus_world_state.json"
            world.write_text('{"level":')
            with self.assertRaises(json.JSONDecodeError):
                tool.build(root)
            world.write_text(json.dumps({"limbs":"bad-type"}))
            with self.assertRaisesRegex(ValueError,"LOCAL_SOURCE_SCHEMA_HOLD"):
                tool.build(root)

    def test_source_size_cap_and_sensitive_name_block(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);self.fixture(root)
            with self.assertRaisesRegex(ValueError,"UNLISTED_LOCAL_SOURCE_HOLD"):
                tool._checked_read(root,"secret.txt")
            src=root/"raw_logs"/"janus_world_agents.json"
            src.write_bytes(b" "* (tool.MAX_BYTES[src.name]+1))
            with self.assertRaisesRegex(ValueError,"SOURCE_BYTES_CAP_HOLD"):
                tool.build(root)

if __name__=="__main__":unittest.main()
