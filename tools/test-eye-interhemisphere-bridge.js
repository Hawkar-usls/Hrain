'use strict';
const assert=require('node:assert/strict');
const bridge=require('../eye-interhemisphere-bridge.js');

function control(){return {read_only_transfer:true,direct_mutation:false,authority_delta:0,claim_promotion:false,proof_authority:false,external_effect_authority:false};}
async function rejects(fn,pattern){
  let failed=false;
  try{await fn();}catch(err){failed=true;if(pattern) assert.match(String(err.message||err),pattern);}
  if(!failed) throw new Error('Expected rejection');
}

(async()=>{
  const request=await bridge.sealPacket({
    schema:bridge.REQUEST_SCHEMA,
    channel:'EYE_TO_HRAIN',source:'EYE',target:'LEFT_HRAIN',
    query:{text:'find contextual bridges for sealed object',candidate_id:'fixture-1'},
    representation_contract:{target_invariant:'SEMANTIC_IDENTITY',must_preserve:['provenance','source identity'],metric:'bridge consistency'},
    provenance_refs:['data/source-fixture.json'],
    control:control()
  });
  await bridge.validateEyeRequest(request);

  const grounded=await bridge.buildGroundedContext(request,{
    source_refs:['data/source-fixture.json'],
    source_sha256:['0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'],
    structural_facts:{language:'ru',byte_length:427}
  },'MATCH');
  assert.equal(grounded.accepted_as,'STRUCTURAL_QUERY_EXPANSION_ONLY');
  assert.equal(grounded.evidence_authority,false);
  await bridge.validateGroundedContext(grounded);

  const assocRequest=await bridge.buildInaihrAssociationRequest(grounded,{
    bridge_invariants:['question','language','claim_ceiling'],
    requested_output:'ASSOCIATIVE_CONTEXT_ONLY'
  });
  assert.equal(assocRequest.channel,'EYE_TO_INAIHR_VIA_HRAIN');
  assert.equal(assocRequest.via,'LEFT_HRAIN');
  assert.equal(assocRequest.evidence_authority,false);

  const response=await bridge.sealPacket({
    schema:bridge.ASSOCIATION_RESPONSE_SCHEMA,
    channel:'INAIHR_TO_EYE_VIA_HRAIN',source:'RIGHT_INAIHR',target:'EYE',via:'LEFT_HRAIN',
    request_sha256:assocRequest.packet_sha256,
    associations:{semantic_region:'AFFIRMATIVE_CREATIVE_CONTINUITY',ambiguities:['exact plaintext unknown'],contradictions:[]},
    accepted_as:'ASSOCIATIVE_CONTEXT_ONLY',evidence_authority:false,independent_replication:false,
    control:control()
  });
  const accepted=await bridge.acceptInaihrAssociationResponse(response);
  assert.equal(accepted.mediated_by,'LEFT_HRAIN');
  assert.equal(accepted.terminal_authority,false);

  await rejects(async()=>bridge.buildGroundedContext(request,{source_refs:['assets/hrain-full-memory/shards/0000.json']},'OPEN'),/Derivative HRAiN full-memory/);
  await rejects(async()=>bridge.buildGroundedContext(request,{source_refs:['assets/hrain-registry-index.json']},'OPEN'),/Derivative HRAiN index/);

  const leaked=await bridge.sealPacket({...request,control:{...control(),claim_promotion:true}});
  await rejects(async()=>bridge.validateEyeRequest(leaked),/claim_promotion/);

  const tampered={...response,associations:{semantic_region:'EXACT_TRUTH'}};
  await rejects(async()=>bridge.acceptInaihrAssociationResponse(tampered),/Packet SHA mismatch/);

  const bypass=await bridge.sealPacket({...response,via:'EYE'});
  await rejects(async()=>bridge.acceptInaihrAssociationResponse(bypass),/Wrong iNaiHR->EYE mediated route/);

  console.log('EYE_HRAIN_INTERHEMISPHERE=PASS');
  console.log('STRUCTURAL_QUERY_EXPANSION_ONLY=PASS');
  console.log('DIRECT_EYE_TO_INAIHR_BYPASS_REJECTED=PASS');
  console.log('DERIVATIVE_MEMORY_SELF_TRAINING_REJECTED=PASS');
  console.log('AUTHORITY_LEAK_REJECTED=PASS');
  console.log('TAMPER_DETECTED=PASS');
})().catch(err=>{console.error(err);process.exit(1);});
