#!/usr/bin/env python3
from pathlib import Path
p=Path('tools/hrain_conversation_context.py')
s=p.read_text(encoding='utf-8')
old='''from hrain_topa_semantic_overlay import (\n    expand_selected_with_semantic_neighbors,\n    load_default_overlay,\n)\n'''
new='''try:\n    from tools.hrain_topa_semantic_overlay import (\n        expand_selected_with_semantic_neighbors,\n        load_default_overlay,\n    )\nexcept ModuleNotFoundError:\n    from hrain_topa_semantic_overlay import (\n        expand_selected_with_semantic_neighbors,\n        load_default_overlay,\n    )\n'''
if old not in s and new not in s:
    raise SystemExit('IMPORT_BLOCK_NOT_FOUND')
if old in s:
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('HRAIN_SEMANTIC_DUAL_IMPORT=PASS')
