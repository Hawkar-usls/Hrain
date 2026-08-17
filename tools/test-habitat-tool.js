'use strict';
const assert = require('assert');
const tool = require('../habitat-tool.js');
const goldprompt = require('../goldprompt-handshake.js');

const TEST_SHA = 'a'.repeat(40);
process.env.JANUS_SOURCE_REVISION = process.env.GITHUB_SHA || TEST_SHA;

assert.equal(goldprompt.contractDigest(), goldprompt.EXPECTED_CONTRACT_DIGEST);
assert.equal(goldprompt.STARTUP_CONTRACT_DIGEST, goldprompt.EXPECTED_CONTRACT_DIGEST);
assert.equal(goldprompt.dependencyManifestDigest(), goldprompt.EXPECTED_DEPENDENCY_MANIFEST_DIGEST);
assert.equal(goldprompt.STARTUP_DEPENDENCY_MANIFEST_DIGEST, goldprompt.EXPECTED_DEPENDENCY_MANIFEST_DIGEST);

const request = {
  schema: tool.REQUEST_SCHEMA,
  request_id: 'HABITAT-HRAIN-0001',
  operation: 'STRUCTURE_CONTEXT',
  captured_at: '2026-08-16T00:00:00Z',
  workspace: {
    nodes: [
      { id: 'a', label: 'Origin', origin: 'USER' },
      { id: 'b', label: 'Hypothesis', origin: 'LOCAL_FALLBACK' }
    ],
    links: [{ source: 'a', target: 'b' }]
  }
};
const response = tool.handle(request);
assert.equal(response.status, 'STRUCTURE_READY_OPTIONAL');
assert.equal(response.tool_id, 'JANUS.HRAIN.STRUCTURE.LOCAL');
assert.equal(response.packet.schema, 'janus.demihead.hemisphere_packet.v2');
assert.equal(response.packet.hemisphere, 'LEFT_HRAIN');
assert.equal(response.packet.role, 'STRUCTURAL_CONTEXT');
assert.equal(response.packet.graph.nodes.length, 2);
assert.equal(response.packet.graph.links.length, 1);
assert.equal(response.source_mutation_allowed, false);
assert.equal(response.world_effect_requested, false);
assert.equal(response.authority_delta, 0);

const receipt = response.goldprompt_receipt;
assert.equal(receipt.schema, goldprompt.RECEIPT_SCHEMA);
assert.equal(receipt.face_id, 'LEFT_HRAIN');
assert.equal(receipt.face_role, 'STRUCTURAL_CONTEXT');
assert.equal(receipt.goldprompt_foundation_id, goldprompt.GOLDPROMPT_FOUNDATION_ID);
assert.equal(receipt.goldprompt_version, '0.9.2');
assert.equal(receipt.emergence_contract_version, 'JANUS_TRIADIC_EMERGENCE@0.9.2');
assert.equal(receipt.contract_digest_sha256, goldprompt.EXPECTED_CONTRACT_DIGEST);
assert.equal(receipt.dependency_manifest_reference, goldprompt.DEPENDENCY_MANIFEST_REFERENCE);
assert.equal(receipt.dependency_manifest_digest_sha256, goldprompt.EXPECTED_DEPENDENCY_MANIFEST_DIGEST);
assert.equal(receipt.source_revision, (process.env.GITHUB_SHA || TEST_SHA).toLowerCase());
assert.equal(receipt.authority_weight, 0);
assert.equal(receipt.compliance_state, 'COMPLIANT');
assert.equal(response.packet.source.source_revision, receipt.source_revision);
assert.equal(response.packet.source.goldprompt_receipt_sha256, receipt.receipt_sha256);
assert.deepEqual(response.packet.goldprompt_receipt, receipt);
assert.equal(goldprompt.verifyReceipt(receipt), true);

function rehash(candidate) {
  const payload = { ...candidate };
  delete payload.receipt_sha256;
  return { ...payload, receipt_sha256: goldprompt.sha256(payload) };
}
assert.equal(goldprompt.verifyReceipt(rehash({ ...receipt, authority_weight: 1 })), false);
assert.equal(goldprompt.verifyReceipt(rehash({ ...receipt, user_exit_and_release_control_accepted: false })), false);
assert.equal(goldprompt.verifyReceipt(rehash({ ...receipt, capability_scope: ['PROPOSE_STRUCTURAL_CONTEXT'] })), false);
assert.equal(goldprompt.verifyReceipt(rehash({ ...receipt, dependency_manifest_digest_sha256: '0'.repeat(64) })), false);
assert.equal(goldprompt.verifyReceipt(rehash({ ...receipt, extra_authority_hint: true })), false);
assert.throws(() => goldprompt.resolveRuntimeSourceRevision({}), /TRUSTED_SOURCE_REVISION_REQUIRED/);
assert.throws(() => goldprompt.resolveRuntimeSourceRevision({ JANUS_SOURCE_REVISION: 'TEST-REV' }), /JANUS_SOURCE_REVISION_INVALID/);

assert.throws(() => tool.handle({ ...request, request_id: 'HABITAT-HRAIN-0002', source_revision: 'b'.repeat(40) }), /CALLER_SOURCE_REVISION_FORBIDDEN/);
assert.throws(() => tool.handle({
  schema: tool.REQUEST_SCHEMA,
  request_id: 'HABITAT-HRAIN-0003',
  operation: 'STRUCTURE_CONTEXT',
  workspace: { nodes: [{ id: 'a', label: 'A' }], links: [{ source: 'a', target: 'missing' }] }
}), /Dangling link/);

console.log('HRAIN_HABITAT_TOOL=PASS');
console.log('HRAIN_GOLDPROMPT_HANDSHAKE_V1_1=PASS');
console.log('HRAIN_GOLDPROMPT_TRANSITIVE_PIN_BINDING=PASS');
console.log('HRAIN_PACKET_EMBEDS_UPSTREAM_RECEIPT=PASS');
console.log('HRAIN_GOLDPROMPT_CALLER_REVISION_OVERRIDE=REJECTED');
console.log('HRAIN_GOLDPROMPT_FULL_POLICY_VERIFY=PASS');
console.log('HRAIN_SOURCE_MUTATION=FALSE');
console.log('HRAIN_NETWORK_USED=FALSE');
