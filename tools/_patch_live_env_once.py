#!/usr/bin/env python3
from pathlib import Path

wf = Path('.github/workflows/hrain-topa-continuous-semantic-flywheel.yml')
text = wf.read_text(encoding='utf-8')
if 'export TOPA_HEAD REGISTRY_SOURCE' not in text:
    anchor = '          REGISTRY_SOURCE="$(python - <<\'PY\'\n'
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit('REGISTRY_SOURCE_ANCHOR_NOT_FOUND')
    end = text.find('          echo "TOPA_HEAD=$TOPA_HEAD" >> "$GITHUB_ENV"', idx)
    if end < 0:
        raise SystemExit('TOPA_ENV_ECHO_ANCHOR_NOT_FOUND')
    text = text[:end] + '          export TOPA_HEAD REGISTRY_SOURCE\n' + text[end:]
if 'export NEEDS_WEAVE' not in text:
    anchor = '          echo "NEEDS_WEAVE=$NEEDS_WEAVE" >> "$GITHUB_ENV"\n'
    if anchor not in text:
        raise SystemExit('NEEDS_WEAVE_ECHO_ANCHOR_NOT_FOUND')
    text = text.replace(anchor, '          export NEEDS_WEAVE\n' + anchor, 1)
wf.write_text(text, encoding='utf-8')

test = Path('tests/test_hrain_topa_semantic_overlay.py')
t = test.read_text(encoding='utf-8')
needle = '        self.assertIn("REPLAY != NEW_EVIDENCE", contract["laws"])\n'
addition = (
    '        workflow = (ROOT / ".github" / "workflows" / "hrain-topa-continuous-semantic-flywheel.yml").read_text(encoding="utf-8")\n'
    '        self.assertIn("export TOPA_HEAD REGISTRY_SOURCE", workflow)\n'
    '        self.assertIn("export NEEDS_WEAVE", workflow)\n'
    '        adapter = (TOOLS / "hrain_topa_semantic_overlay.py").read_text(encoding="utf-8")\n'
    '        self.assertIn("same_normalized_label", adapter)\n'
)
if 'self.assertIn("export TOPA_HEAD REGISTRY_SOURCE", workflow)' not in t:
    if needle not in t:
        raise SystemExit('TEST_ANCHOR_NOT_FOUND')
    t = t.replace(needle, needle + addition, 1)
test.write_text(t, encoding='utf-8')
print('LIVE_WEAVE_ENV_PATCH=PASS')
