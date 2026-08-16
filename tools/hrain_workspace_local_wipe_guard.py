#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
LOCAL_KEY = "hrain_v10_4_restore"


def transform(text: str) -> str:
    replacements = {
        '<button id="btn-wipe" class="btn" onclick="wipeData(this)">WIPE</button>':
            '<button id="btn-wipe" class="btn" onclick="wipeData(this)" title="Clears only this browser workspace. JANUS Registry is untouched.">WIPE LOCAL DESK</button>',
        'btn.innerText = "BYE";': 'btn.innerText = "LOCAL CLEARED";',
        'btn.innerText = "WIPE";': 'btn.innerText = "WIPE LOCAL DESK";',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def wipe_function(text: str) -> str:
    start = text.index("function wipeData(btn)")
    end = text.index("// --- DRAG REVISED ---", start)
    return text[start:end]


def validate(text: str) -> None:
    assert '>WIPE LOCAL DESK</button>' in text
    assert 'Clears only this browser workspace. JANUS Registry is untouched.' in text
    assert '>WIPE</button>' not in text
    fn = wipe_function(text)
    assert f"localStorage.removeItem('{LOCAL_KEY}')" in fn
    assert 'location.reload()' in fn
    forbidden = [
        'fetch(', 'XMLHttpRequest', 'indexedDB', '/api/', 'janus-meta-registry',
        'github.com', 'DELETE', 'PATCH', 'PUT', 'POST'
    ]
    for marker in forbidden:
        assert marker not in fn, f"wipeData contains forbidden marker: {marker}"
    assert 'LOCAL CLEARED' in fn
    assert 'WIPE LOCAL DESK' in fn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    original = INDEX.read_text(encoding='utf-8')
    candidate = transform(original)
    validate(candidate)

    if args.apply and candidate != original:
        INDEX.write_text(candidate, encoding='utf-8')
        print('HRAIN_WORKSPACE_LOCAL_WIPE_PATCH=APPLIED')
    else:
        print('HRAIN_WORKSPACE_LOCAL_WIPE_PATCH=' + ('NO_CHANGE' if candidate == original else 'READY'))

    print('HRAIN_WORKSPACE_WIPE=LOCAL_STORAGE_ONLY')
    print('HRAIN_WORKSPACE_REGISTRY_MUTATION=ABSENT')
    print('HRAIN_WORKSPACE_WIPE_GUARD=PASS')


if __name__ == '__main__':
    main()
