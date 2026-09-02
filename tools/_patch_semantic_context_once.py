#!/usr/bin/env python3
"""One-shot feature-branch patcher for HRAiN conversation semantic enrichment."""
from pathlib import Path

path = Path("tools/hrain_conversation_context.py")
text = path.read_text(encoding="utf-8")

import_anchor = "from typing import Any, Dict, Iterable, Mapping\n"
import_line = (
    "\nfrom hrain_topa_semantic_overlay import (\n"
    "    expand_selected_with_semantic_neighbors,\n"
    "    load_default_overlay,\n"
    ")\n"
)
if "from hrain_topa_semantic_overlay import" not in text:
    if import_anchor not in text:
        raise SystemExit("IMPORT_ANCHOR_NOT_FOUND")
    text = text.replace(import_anchor, import_anchor + import_line, 1)

old_selection = (
    "    selected = select_nodes(projection, query, limit=limit)\n"
    "    memories = hydrate_selected(selected, registry_root=registry_root) if hydrate else selected\n"
)
new_selection = (
    "    selected = select_nodes(projection, query, limit=limit)\n"
    "    overlay, overlay_sha256, overlay_status = load_default_overlay(projection)\n"
    "    if overlay is not None:\n"
    "        selected = expand_selected_with_semantic_neighbors(selected, projection, overlay, limit=limit)\n"
    "    semantic_neighbor_count = sum(1 for row in selected if row.get(\"semantic_relation\") == \"TOPA_SEMANTIC_SIMILARITY\")\n"
    "    memories = hydrate_selected(selected, registry_root=registry_root) if hydrate else selected\n"
)
if "semantic_neighbor_count = sum(" not in text:
    if old_selection not in text:
        raise SystemExit("SELECTION_ANCHOR_NOT_FOUND")
    text = text.replace(old_selection, new_selection, 1)

field_anchor = (
    '        "selection_limit": limit,\n'
    '        "selection_limit_is_target_count": False,\n'
    '        "selected_memory_count": len(memories),\n'
)
field_new = (
    '        "selection_limit": limit,\n'
    '        "selection_limit_is_target_count": False,\n'
    '        "semantic_overlay_status": overlay_status,\n'
    '        "semantic_overlay_sha256": overlay_sha256,\n'
    '        "semantic_neighbor_count": semantic_neighbor_count,\n'
    '        "selected_memory_count": len(memories),\n'
)
if '"semantic_overlay_status": overlay_status' not in text:
    if field_anchor not in text:
        raise SystemExit("BODY_FIELD_ANCHOR_NOT_FOUND")
    text = text.replace(field_anchor, field_new, 1)

law_anchor = '            "HASH_VERIFIED_OBJECT != CLAIM_VERIFIED",\n'
law_new = (
    '            "HASH_VERIFIED_OBJECT != CLAIM_VERIFIED",\n'
    '            "TOPA_SEMANTIC_NEIGHBOR != EVIDENCE",\n'
    '            "SEMANTIC_SIMILARITY_IS_NOT_MECHANISM",\n'
    '            "EMPTY_LEXICAL_ANCHOR_SET != SEMANTIC_FILL",\n'
)
if '"TOPA_SEMANTIC_NEIGHBOR != EVIDENCE"' not in text:
    if law_anchor not in text:
        raise SystemExit("LAW_ANCHOR_NOT_FOUND")
    text = text.replace(law_anchor, law_new, 1)

path.write_text(text, encoding="utf-8")
print("HRAIN_TOPA_CONTEXT_PATCH=PASS")
