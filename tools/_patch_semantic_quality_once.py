#!/usr/bin/env python3
"""One-shot feature-branch patch: keep TOPA semantic degree for cross-concept edges."""
from pathlib import Path

path = Path('tools/hrain_topa_semantic_overlay.py')
text = path.read_text(encoding='utf-8')

object_anchor = (
    '    object_ids = {str(node["id"]) for node in _object_nodes(projection)}\n'
    '    hierarchy = _hierarchy_pairs(projection)\n'
)
object_new = (
    '    object_nodes = {str(node["id"]): node for node in _object_nodes(projection)}\n'
    '    object_ids = set(object_nodes)\n'
    '    hierarchy = _hierarchy_pairs(projection)\n'
)
if 'object_nodes = {str(node["id"]): node' not in text:
    if object_anchor not in text:
        raise SystemExit('OBJECT_MAP_ANCHOR_NOT_FOUND')
    text = text.replace(object_anchor, object_new, 1)

candidate_anchor = (
    '        if source == target:\n'
    '            rejected["self_loop"] += 1\n'
    '            continue\n'
    '        pair = tuple(sorted((source, target)))\n'
)
candidate_new = (
    '        if source == target:\n'
    '            rejected["self_loop"] += 1\n'
    '            continue\n'
    '        source_label = re.sub(r"\\W+", "", str(object_nodes[source].get("label") or "").casefold(), flags=re.UNICODE)\n'
    '        target_label = re.sub(r"\\W+", "", str(object_nodes[target].get("label") or "").casefold(), flags=re.UNICODE)\n'
    '        if source_label and source_label == target_label:\n'
    '            rejected["same_normalized_label"] += 1\n'
    '            continue\n'
    '        pair = tuple(sorted((source, target)))\n'
)
if 'rejected["same_normalized_label"]' not in text:
    if candidate_anchor not in text:
        raise SystemExit('CANDIDATE_FILTER_ANCHOR_NOT_FOUND')
    text = text.replace(candidate_anchor, candidate_new, 1)

law_anchor = '            "SEMANTIC_NEIGHBOR_IS_NOT_CLAIM_VERIFICATION",\n'
law_new = (
    '            "SEMANTIC_NEIGHBOR_IS_NOT_CLAIM_VERIFICATION",\n'
    '            "IDENTICAL_LABEL_LINEAGE != SEMANTIC_CROSS_CONCEPT_EDGE",\n'
)
if '"IDENTICAL_LABEL_LINEAGE != SEMANTIC_CROSS_CONCEPT_EDGE"' not in text:
    if law_anchor not in text:
        raise SystemExit('LAW_ANCHOR_NOT_FOUND')
    text = text.replace(law_anchor, law_new, 1)

path.write_text(text, encoding='utf-8')
print('HRAIN_TOPA_CROSS_CONCEPT_FILTER_PATCH=PASS')
