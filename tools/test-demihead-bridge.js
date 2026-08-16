'use strict';

const fs = require('fs');
const path = require('path');
const bridge = require(path.join('..', 'demihead-bridge.js'));

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const workspace = {
  nodes: [
    {id: 1, label: 'Context', type: 'default'},
    {id: 2, label: 'Evidence', type: 'info', origin: 'USER'}
  ],
  links: [{source: 1, target: 2}]
};

const packet = bridge.buildPacket(workspace, {
  capturedAt: '2026-08-16T08:53:00Z',
  packetId: 'hrain-ci-left'
});

assert(packet.schema === 'janus.demihead.hemisphere_packet.v1', 'wrong packet schema');
assert(packet.hemisphere === 'LEFT_HRAIN', 'wrong hemisphere');
assert(packet.role === 'STRUCTURAL_CONTEXT', 'wrong role');
assert(packet.source.repository === 'Hawkar-usls/Hrain', 'wrong repository');
assert(packet.source.bridge_contract === 'JANUS_DEMIHEAD_BICAMERAL_BRIDGE_V1', 'wrong bridge contract');
assert(packet.graph.nodes[0].origin === 'LEGACY_UNKNOWN', 'legacy node origin must remain unknown');
assert(packet.graph.nodes[1].origin === 'USER', 'explicit origin must be preserved');
assert(packet.control.read_only_transfer === true, 'transfer must be read-only');
assert(packet.control.direct_cross_hemisphere_mutation === false, 'direct mutation must be false');
assert(packet.control.authority_delta === 0, 'authority delta must remain zero');
assert(packet.control.mass_effect_budget_delta === 0, 'mass effect delta must remain zero');

let failedClosed = false;
try {
  bridge.buildPacket({nodes: [{id: 1, label: 'A'}], links: [{source: 1, target: 2}]});
} catch (_) {
  failedClosed = true;
}
assert(failedClosed, 'dangling link must fail closed');

const sidecar = fs.readFileSync(path.join(__dirname, '..', 'demihead.html'), 'utf8');
for (const forbidden of [
  'localStorage.setItem',
  'localStorage.removeItem',
  'localStorage.clear',
  'fetch(',
  'XMLHttpRequest',
  'api.github.com/repos/'
]) {
  assert(!sidecar.includes(forbidden), `sidecar contains forbidden write/network surface: ${forbidden}`);
}
assert(sidecar.includes('JANUS_DEMIHEAD_REQUEST_PACKET_V1'), 'request message contract missing');
assert(sidecar.includes('JANUS_DEMIHEAD_HEMISPHERE_PACKET_V1'), 'response message contract missing');
assert(!sidecar.includes("postMessage({type: 'JANUS_DEMIHEAD_HEMISPHERE_PACKET_V1', packet: current}, '*')"), 'wildcard packet postMessage forbidden');

console.log('HRAIN_DEMIHEAD_LEFT_HEMISPHERE_BRIDGE=PASS');
console.log('LEGACY_UNKNOWN_PRESERVED=true');
console.log('DIRECT_CROSS_HEMISPHERE_MUTATION=false');
console.log('AUTHORITY_DELTA=0');
