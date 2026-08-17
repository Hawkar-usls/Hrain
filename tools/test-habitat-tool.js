'use strict';
const assert = require('assert');
const tool = require('../habitat-tool.js');
const goldprompt = require('../goldprompt-handshake.js');

assert.equal(goldprompt.contractDigest(), goldprompt.EXPECTED_CONTRACT_DIGEST);

const response = tool.handle({
  schema: tool.REQUEST_SCHEMA,
  request_id: 'HABITAT-HRAIN-0001',
  operation: 'STRUCTURE_CONTEXT',
  captured_at: '2026-08-16T00:00:00Z',
  source_revision: 'TEST-REV',
  workspace: {
    nodes: [
      { id: 'a', label: 'Origin', origin: 'USER' },
      { id: 'b', label: 'Hypothesis', origin: 'LOCAL_FALLBACK' }
    ],
    links: [{ source: 'a', target: 'b' }]
  }
});
assert.equal(response.status, 'STRUCTURE_READY_OPTIONAL');
assert.equal(response.tool_id, 'JANUS.HRAIN.STRUCTURE.LOCAL');
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
assert.equal(receipt.source_revision, 'TEST-REV');
assert.equal(receipt.authority_weight, 0);
assert.equal(receipt.compliance_state, 'COMPLIANT');
assert.equal(goldprompt.verifyReceipt(receipt), true);

const tampered = { ...receipt, authority_weight: 1 };
assert.equal(goldprompt.verifyReceipt(tampered), false);

assert.throws(() => tool.handle({
  schema: tool.REQUEST_SCHEMA,
  request_id: 'HABITAT-HRAIN-0002',
  operation: 'STRUCTURE_CONTEXT',
  workspace: { nodes: [{ id: 'a', label: 'A' }], links: [{ source: 'a', target: 'missing' }] }
}), /Dangling link/);

console.log('HRAIN_HABITAT_TOOL=PASS');
console.log('HRAIN_GOLDPROMPT_HANDSHAKE=PASS');
console.log('HRAIN_SOURCE_MUTATION=FALSE');
console.log('HRAIN_NETWORK_USED=FALSE');
