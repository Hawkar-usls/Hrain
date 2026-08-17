'use strict';

const fs = require('fs');
const path = require('path');
const bridge = require(path.join('..', 'demihead-bridge.js'));
const apply = require(path.join('..', 'demihead-apply.js'));

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

async function makeEnvelope(workspace, overrides = {}) {
  const graph = bridge.normalizeWorkspace(workspace);
  const proposal = {
    schema: apply.PROPOSAL_SCHEMA,
    proposal_id: 'proposal-hrain-test-0001',
    created_at: '2026-08-16T10:00:00Z',
    target: {hemisphere: 'LEFT_HRAIN', repository: 'Hawkar-usls/Hrain'},
    base_graph_sha256: await apply.sha256Json(graph),
    operation: {
      type: 'ADD_NODE',
      node: {id: 'dh-node-hrain-test-0001', label: 'Candidate context', origin: 'SYSTEM'}
    },
    control: {
      auto_apply: false,
      requires_explicit_local_accept: true,
      direct_cross_hemisphere_write: false,
      external_effect_permitted: false,
      authority_delta: 0,
      mass_effect_budget_delta: 0
    }
  };
  Object.assign(proposal, overrides.proposal || {});
  if (overrides.target) proposal.target = overrides.target;
  if (overrides.control) proposal.control = overrides.control;
  if (overrides.operation) proposal.operation = overrides.operation;
  return {
    type: apply.ENVELOPE_TYPE,
    proposal_sha256: await apply.sha256Json(proposal),
    proposal
  };
}

async function expectRefusal(fn, expectedPart) {
  let error = null;
  try { await fn(); } catch (err) { error = err; }
  assert(error, `expected refusal containing ${expectedPart}`);
  assert(String(error.message).includes(expectedPart), `wrong refusal: ${error.message}`);
}

async function main() {
  const workspace = {
    nodes: [
      {id: 1, label: 'Context', emoji: '🧩', type: 'default', x: 10, y: 20, parentId: null, chatHistory: []},
      {id: 2, label: 'Evidence', emoji: '🔎', type: 'info', x: 30, y: 40, parentId: null, chatHistory: [], origin: 'USER'}
    ],
    links: [{source: 1, target: 2}]
  };
  const graph = bridge.normalizeWorkspace(workspace);
  const envelope = await makeEnvelope(workspace);
  await apply.verifyEnvelope(envelope);

  const original = clone(workspace);
  const prepared = await apply.prepareAcceptedMutation(workspace, graph, envelope);
  assert(JSON.stringify(workspace) === JSON.stringify(original), 'pure adapter mutated input workspace');
  assert(prepared.workspace.nodes.length === workspace.nodes.length + 1, 'accepted mutation must add exactly one node');
  assert(prepared.workspace.links.length === workspace.links.length, 'ADD_NODE v1 must not create links');
  const added = prepared.workspace.nodes.at(-1);
  assert(added.id === 'dh-node-hrain-test-0001', 'node id drifted');
  assert(added.label === 'Candidate context', 'node label drifted');
  assert(added.origin === 'SYSTEM', 'DemiHead proposal provenance must remain SYSTEM');
  assert(added.demiheadProposalId === envelope.proposal.proposal_id, 'proposal id binding lost');
  assert(added.demiheadProposalSha256 === envelope.proposal_sha256, 'proposal hash binding lost');
  assert(added.parentId === null, 'v1 proposal must add a top-level HRain node');
  assert(Array.isArray(added.chatHistory) && added.chatHistory.length === 0, 'HRain compatibility fields missing');

  const afterGraph = bridge.normalizeWorkspace(prepared.workspace);
  const afterSha = await apply.sha256Json(afterGraph);
  const receipt = apply.buildReceipt({
    proposalId: prepared.proposal_id,
    proposalSha256: prepared.proposal_sha256,
    beforeGraphSha256: prepared.before_graph_sha256,
    afterGraphSha256: afterSha,
    nodeId: added.id
  });
  assert(receipt.acceptance_event === 'EXPLICIT_LOCAL_ACCEPT_BUTTON', 'receipt must record local accept event');
  assert(receipt.before_graph_sha256 !== receipt.after_graph_sha256, 'accepted add-node mutation must change graph hash');
  assert(receipt.control.direct_cross_hemisphere_write === false, 'direct cross-hemisphere write must remain false');
  assert(receipt.control.external_effect_permitted === false, 'external effect must remain false');
  assert(receipt.control.authority_delta === 0, 'authority delta must remain zero');
  assert(receipt.control.mass_effect_budget_delta === 0, 'mass-effect delta must remain zero');
  assert(receipt.claim_ceiling.click_event_is_verified_human_identity === false, 'click cannot become verified identity');
  assert(receipt.claim_ceiling.sha256_binding_is_signature === false, 'hash binding cannot become a signature claim');

  const tampered = clone(envelope);
  tampered.proposal.operation.node.label = 'Tampered label';
  await expectRefusal(() => apply.verifyEnvelope(tampered), 'proposal hash mismatch');

  const wrongTarget = await makeEnvelope(workspace, {target:{hemisphere:'RIGHT_INAIHR',repository:'Hawkar-usls/iNaiHR'}});
  await expectRefusal(() => apply.verifyEnvelope(wrongTarget), 'proposal target mismatch');

  const autoApply = await makeEnvelope(workspace, {control:{
    auto_apply: true,
    requires_explicit_local_accept: true,
    direct_cross_hemisphere_write: false,
    external_effect_permitted: false,
    authority_delta: 0,
    mass_effect_budget_delta: 0
  }});
  await expectRefusal(() => apply.verifyEnvelope(autoApply), 'proposal control boundary drifted');

  const changedWorkspace = clone(workspace);
  changedWorkspace.nodes[0].label = 'Context changed after proposal';
  const changedGraph = bridge.normalizeWorkspace(changedWorkspace);
  await expectRefusal(() => apply.prepareAcceptedMutation(changedWorkspace, changedGraph, envelope), 'BASE_WORKSPACE_CHANGED_REPROPOSE_REQUIRED');

  const duplicateWorkspace = clone(workspace);
  duplicateWorkspace.nodes.push({id:'dh-node-hrain-test-0001', label:'Already here', x:0, y:0});
  const duplicateGraph = bridge.normalizeWorkspace(duplicateWorkspace);
  const duplicateEnvelope = await makeEnvelope(duplicateWorkspace);
  await expectRefusal(() => apply.prepareAcceptedMutation(duplicateWorkspace, duplicateGraph, duplicateEnvelope), 'PROPOSED_NODE_ID_ALREADY_EXISTS');

  const page = fs.readFileSync(path.join(__dirname, '..', 'demihead-apply.html'), 'utf8');
  for (const forbidden of ['postMessage(', 'fetch(', 'XMLHttpRequest', 'api.github.com/repos/']) {
    assert(!page.includes(forbidden), `apply page contains forbidden remote/write channel: ${forbidden}`);
  }
  const writeNeedle = 'localStorage.setItem(apply.STORAGE_KEY, JSON.stringify(prepared.workspace))';
  assert((page.match(/localStorage\.setItem/g) || []).length === 1, 'apply page must contain exactly one localStorage write');
  assert(page.includes(writeNeedle), 'expected local accepted mutation write missing');
  const declineStart = page.indexOf("decline.addEventListener('click'");
  const acceptStart = page.indexOf("accept.addEventListener('click'");
  assert(declineStart >= 0 && acceptStart > declineStart, 'decline/accept handlers missing');
  assert(!page.slice(declineStart, acceptStart).includes('localStorage.setItem'), 'DECLINE path must not write local workspace');
  const prepareIndex = page.indexOf('await apply.prepareAcceptedMutation', acceptStart);
  const writeIndex = page.indexOf(writeNeedle, acceptStart);
  assert(prepareIndex > acceptStart && writeIndex > prepareIndex, 'write must occur only after accepted mutation preparation/recheck');
  assert(page.includes("const workspace = readWorkspace();\n      const beforeGraph = normalizedGraph(workspace);"), 'accept path must freshly reread and normalize workspace');
  assert(page.includes('DEMIHEAD_PROPOSAL != WORKSPACE_MUTATION'), 'proposal/mutation law missing');
  assert(page.includes('NO_ACCEPT_EVENT => NO_MUTATION'), 'no-accept law missing');
  assert(page.includes('CLICK_EVENT != VERIFIED_HUMAN_IDENTITY'), 'identity claim ceiling missing');
  assert(page.includes('GITHUB_PAGES_PROJECT_PATH != ORIGIN_ISOLATION'), 'same-origin threat-model law missing');

  console.log('HRAIN_DEMIHEAD_LOCAL_ACCEPT_GATE=PASS');
  console.log('ADD_NODE_ONLY=true');
  console.log('DECLINE_WRITES_WORKSPACE=false');
  console.log('NO_ACCEPT_EVENT_NO_MUTATION=true');
  console.log('PROPOSAL_HASH_TAMPER_REFUSED=true');
  console.log('BASE_GRAPH_DRIFT_REFUSED=true');
  console.log('SYSTEM_PROVENANCE_PRESERVED=true');
  console.log('DIRECT_CROSS_HEMISPHERE_WRITE=false');
  console.log('EXTERNAL_EFFECT=false');
  console.log('AUTHORITY_DELTA=0');
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
