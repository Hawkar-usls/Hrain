(function(root){
'use strict';

const LOCAL='LEFT_HRAIN';
const EYE='EYE';
const PEER='RIGHT_INAIHR';
const ROLE='STRUCTURAL_CONTEXT_GROUNDING_MEDIATOR';
const REQUEST_SCHEMA='janus.eye.hrain_request.v1';
const GROUNDED_SCHEMA='janus.eye.hrain_grounded_context.v1';
const ASSOCIATION_REQUEST_SCHEMA='janus.eye.inaihr_association_request.v1';
const ASSOCIATION_RESPONSE_SCHEMA='janus.eye.inaihr_association_response.v1';
const GROUNDING_STATUSES=new Set(['MATCH','MISMATCH','OPEN']);
const FORBIDDEN_DERIVATIVE_PREFIXES=['assets/hrain-full-memory/'];
const FORBIDDEN_DERIVATIVE_PATHS=new Set(['assets/hrain-registry-index.json']);

function stable(v){
  if(Array.isArray(v)) return v.map(stable);
  if(v&&typeof v==='object'){
    const o={};
    for(const k of Object.keys(v).sort()) o[k]=stable(v[k]);
    return o;
  }
  return v;
}
function bytes(v){return new TextEncoder().encode(JSON.stringify(stable(v)));}
async function sha256Hex(v){
  const b=bytes(v);
  if(globalThis.crypto&&globalThis.crypto.subtle){
    const d=await globalThis.crypto.subtle.digest('SHA-256',b);
    return [...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,'0')).join('');
  }
  if(typeof require==='function') return require('node:crypto').createHash('sha256').update(Buffer.from(b)).digest('hex');
  throw new Error('SHA-256 unavailable');
}
async function sealPacket(packet){
  const copy={...packet};
  delete copy.packet_sha256;
  return Object.freeze({...copy,packet_sha256:await sha256Hex(copy)});
}
async function verifyPacketHash(packet){
  if(!packet||typeof packet.packet_sha256!=='string') throw new Error('Missing packet SHA');
  const copy={...packet};
  delete copy.packet_sha256;
  const expected=await sha256Hex(copy);
  if(expected!==packet.packet_sha256) throw new Error('Packet SHA mismatch');
  return true;
}
function assertReadOnlyControl(control){
  const c=control||{};
  if(c.read_only_transfer!==true) throw new Error('read_only_transfer must be true');
  if(c.direct_mutation!==false) throw new Error('direct_mutation must be false');
  if(c.authority_delta!==0) throw new Error('authority_delta must be zero');
  if(c.claim_promotion!==false) throw new Error('claim_promotion must be false');
  if(c.proof_authority!==false) throw new Error('proof_authority must be false');
  if(c.external_effect_authority!==false) throw new Error('external_effect_authority must be false');
}
function defaultControl(){
  return Object.freeze({
    read_only_transfer:true,
    direct_mutation:false,
    authority_delta:0,
    claim_promotion:false,
    proof_authority:false,
    external_effect_authority:false
  });
}
function walkStrings(value,out=[]){
  if(typeof value==='string') out.push(value);
  else if(Array.isArray(value)) for(const x of value) walkStrings(x,out);
  else if(value&&typeof value==='object') for(const x of Object.values(value)) walkStrings(x,out);
  return out;
}
function assertNoDerivativeMemoryAsSource(value){
  for(const s of walkStrings(value)){
    const normalized=s.replace(/^\.\//,'');
    if(FORBIDDEN_DERIVATIVE_PATHS.has(normalized)) throw new Error('Derivative HRAiN index cannot be fresh EYE source evidence');
    if(FORBIDDEN_DERIVATIVE_PREFIXES.some(p=>normalized.startsWith(p))) throw new Error('Derivative HRAiN full-memory export cannot be fresh EYE source evidence');
  }
}
async function validateEyeRequest(packet){
  if(!packet||packet.schema!==REQUEST_SCHEMA) throw new Error('Unsupported EYE request schema');
  if(packet.channel!=='EYE_TO_HRAIN'||packet.source!==EYE||packet.target!==LOCAL) throw new Error('Wrong EYE->HRAiN route');
  if(!packet.representation_contract||typeof packet.representation_contract.target_invariant!=='string') throw new Error('Representation contract target invariant required');
  if(!packet.query||typeof packet.query!=='object') throw new Error('Structured EYE query required');
  assertReadOnlyControl(packet.control);
  assertNoDerivativeMemoryAsSource(packet);
  await verifyPacketHash(packet);
  return packet;
}
async function buildGroundedContext(eyeRequest,structuralContext,groundingStatus='OPEN'){
  await validateEyeRequest(eyeRequest);
  if(!GROUNDING_STATUSES.has(groundingStatus)) throw new Error('Invalid grounding status');
  if(!structuralContext||typeof structuralContext!=='object') throw new Error('Structural context object required');
  assertNoDerivativeMemoryAsSource(structuralContext);
  return sealPacket({
    schema:GROUNDED_SCHEMA,
    channel:'HRAIN_TO_EYE_GROUNDED_CONTEXT',
    source:LOCAL,
    target:EYE,
    role:ROLE,
    request_sha256:eyeRequest.packet_sha256,
    representation_contract:eyeRequest.representation_contract,
    grounding_status:groundingStatus,
    structural_context:structuralContext,
    accepted_as:'STRUCTURAL_QUERY_EXPANSION_ONLY',
    evidence_authority:false,
    independent_replication:false,
    control:defaultControl()
  });
}
async function validateGroundedContext(packet){
  if(!packet||packet.schema!==GROUNDED_SCHEMA) throw new Error('Unsupported grounded-context schema');
  if(packet.source!==LOCAL||packet.target!==EYE||packet.channel!=='HRAIN_TO_EYE_GROUNDED_CONTEXT') throw new Error('Wrong grounded-context route');
  if(!GROUNDING_STATUSES.has(packet.grounding_status)) throw new Error('Invalid grounding status');
  if(packet.accepted_as!=='STRUCTURAL_QUERY_EXPANSION_ONLY'||packet.evidence_authority!==false||packet.independent_replication!==false) throw new Error('Grounding authority leak');
  assertReadOnlyControl(packet.control);
  assertNoDerivativeMemoryAsSource(packet.structural_context);
  await verifyPacketHash(packet);
  return packet;
}
async function buildInaihrAssociationRequest(groundedContext,associationInput){
  await validateGroundedContext(groundedContext);
  if(!associationInput||typeof associationInput!=='object') throw new Error('Association input object required');
  return sealPacket({
    schema:ASSOCIATION_REQUEST_SCHEMA,
    channel:'EYE_TO_INAIHR_VIA_HRAIN',
    source:LOCAL,
    logical_source:EYE,
    target:PEER,
    via:LOCAL,
    grounded_context_sha256:groundedContext.packet_sha256,
    grounding_status:groundedContext.grounding_status,
    representation_contract:groundedContext.representation_contract,
    structural_context:groundedContext.structural_context,
    association_input:associationInput,
    accepted_as:'SEMANTIC_ASSOCIATION_INPUT_ONLY',
    evidence_authority:false,
    control:defaultControl()
  });
}
async function acceptInaihrAssociationResponse(packet){
  if(!packet||packet.schema!==ASSOCIATION_RESPONSE_SCHEMA) throw new Error('Unsupported iNaiHR response schema');
  if(packet.channel!=='INAIHR_TO_EYE_VIA_HRAIN'||packet.source!==PEER||packet.target!==EYE||packet.via!==LOCAL) throw new Error('Wrong iNaiHR->EYE mediated route');
  if(packet.accepted_as!=='ASSOCIATIVE_CONTEXT_ONLY'||packet.evidence_authority!==false||packet.independent_replication!==false) throw new Error('Associative response authority leak');
  assertReadOnlyControl(packet.control);
  await verifyPacketHash(packet);
  return Object.freeze({...packet,mediated_by:LOCAL,terminal_authority:false});
}

const API=Object.freeze({
  version:'1.0.0',LOCAL,EYE,PEER,ROLE,
  REQUEST_SCHEMA,GROUNDED_SCHEMA,ASSOCIATION_REQUEST_SCHEMA,ASSOCIATION_RESPONSE_SCHEMA,
  sealPacket,verifyPacketHash,validateEyeRequest,buildGroundedContext,validateGroundedContext,
  buildInaihrAssociationRequest,acceptInaihrAssociationResponse,sha256Hex,
  laws:Object.freeze([
    'HRAIN_GROUNDS',
    'EYE_BRIDGES',
    'INAIHR_ASSOCIATES',
    'VERIFY_DECIDES',
    'EYE_TO_HRAIN=STRUCTURAL_QUERY_EXPANSION_ONLY',
    'EYE_TO_INAIHR_VIA_HRAIN=SEMANTIC_ASSOCIATION_INPUT_ONLY',
    'DIRECT_EYE_TO_INAIHR_BYPASS_FORBIDDEN',
    'DERIVATIVE_HRAIN_MEMORY_EXPORT_NE_FRESH_SOURCE_EVIDENCE',
    'ASSOCIATION_NE_EVIDENCE',
    'GROUNDING_NE_TRUTH',
    'NO_DIRECT_MUTATION',
    'NO_CLAIM_PROMOTION'
  ])
});
root.JANUS_EYE_HRAIN_BRIDGE=API;
if(typeof module!=='undefined'&&module.exports) module.exports=API;
})(typeof window!=='undefined'?window:globalThis);
