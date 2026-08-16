#!/usr/bin/env node
'use strict';

const bridge = require('./demihead-bridge.js');

const REQUEST_SCHEMA = 'janus.habitat.hrain.request.v1';
const RESPONSE_SCHEMA = 'janus.habitat.hrain.response.v1';
const TOOL_ID = 'JANUS.HRAIN.STRUCTURE.LOCAL';
const REQUEST_ID_RE = /^[A-Za-z0-9._:-]{8,128}$/;

function fail(message) {
  const err = new Error(message);
  err.code = message;
  throw err;
}

function handle(request) {
  if (!request || typeof request !== 'object' || Array.isArray(request)) fail('HRAIN_HABITAT_REQUEST_OBJECT_REQUIRED');
  if (request.schema !== REQUEST_SCHEMA) fail('HRAIN_HABITAT_REQUEST_SCHEMA_MISMATCH');
  const requestId = String(request.request_id || '');
  if (!REQUEST_ID_RE.test(requestId)) fail('HRAIN_HABITAT_REQUEST_ID_INVALID');
  if (request.operation !== 'STRUCTURE_CONTEXT') fail('HRAIN_HABITAT_OPERATION_UNSUPPORTED');
  if (!request.workspace || typeof request.workspace !== 'object') fail('HRAIN_HABITAT_WORKSPACE_REQUIRED');

  const packet = bridge.buildPacket(request.workspace, {
    packetId: `habitat-hrain-${requestId}`,
    capturedAt: request.captured_at || new Date().toISOString(),
    sourceRevision: typeof request.source_revision === 'string' ? request.source_revision : null
  });

  return {
    schema: RESPONSE_SCHEMA,
    request_id: requestId,
    tool_id: TOOL_ID,
    tool: 'HRaiN',
    role: 'STRUCTURAL_CONTEXT',
    status: 'STRUCTURE_READY_OPTIONAL',
    packet,
    may_be_ignored: true,
    authority_delta: 0,
    mass_effect_budget_delta: 0,
    world_effect_requested: false,
    source_mutation_allowed: false,
    network_used_by_tool: false
  };
}

function runCli() {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { raw += chunk; });
  process.stdin.on('end', () => {
    try {
      const request = JSON.parse(raw || '{}');
      process.stdout.write(JSON.stringify(handle(request)) + '\n');
    } catch (err) {
      process.stderr.write(JSON.stringify({
        schema: 'janus.habitat.hrain.error.v1',
        status: 'REJECTED',
        error: String(err && (err.code || err.message) || 'UNKNOWN')
      }) + '\n');
      process.exitCode = 2;
    }
  });
}

if (require.main === module) runCli();

module.exports = Object.freeze({ REQUEST_SCHEMA, RESPONSE_SCHEMA, TOOL_ID, handle });
