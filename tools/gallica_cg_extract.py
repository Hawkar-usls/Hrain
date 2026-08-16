#!/usr/bin/env python3
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ARK = "bpt6k5774000v"
TARGETS = ["53465", "53466", "53467", "53468", "53469"]
UA = "JANUS-HRain-Mendes-CG-Extract/1.0"


def fetch(url, timeout=35):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("content-type", ""), r.read()


def text_of(data):
    return data.decode("utf-8", errors="replace")


def extract_context(text, needle, radius=1200):
    hits = []
    for m in re.finditer(re.escape(needle), text, flags=re.I):
        a = max(0, m.start() - radius)
        b = min(len(text), m.end() + radius)
        hits.append(text[a:b])
    return hits


def main():
    out = {
        "schema": "hrain.gallica.cg_extract.v1",
        "ark": ARK,
        "targets": TARGETS,
        "sources": {},
        "entries": {},
        "errors": [],
    }

    # 1) Gallica ContentSearch per exact CG number.
    for n in TARGETS:
        url = "https://gallica.bnf.fr/services/ContentSearch?" + urllib.parse.urlencode({"ark": ARK, "query": n})
        try:
            status, ctype, data = fetch(url)
            txt = text_of(data)
            out["sources"][f"contentsearch_{n}"] = {"url": url, "status": status, "content_type": ctype, "raw": txt[:20000]}
        except Exception as e:
            out["errors"].append({"stage": "ContentSearch", "target": n, "error": repr(e)})

    # 2) Whole-document OCR text; this is the strongest fallback if ContentSearch XML is awkward.
    raw_url = f"https://gallica.bnf.fr/ark:/12148/{ARK}.texteBrut"
    whole = ""
    try:
        status, ctype, data = fetch(raw_url, timeout=60)
        whole = text_of(data)
        out["sources"]["texteBrut"] = {"url": raw_url, "status": status, "content_type": ctype, "bytes": len(data)}
        Path("/tmp/vernier_texteBrut.txt").write_text(whole, encoding="utf-8")
    except Exception as e:
        out["errors"].append({"stage": "texteBrut", "error": repr(e)})

    # 3) Context extraction. Accept OCR variants with spaces/punctuation around digits.
    if whole:
        for n in TARGETS:
            exact = extract_context(whole, n)
            # also look for spaced OCR form e.g. 53 465
            spaced = extract_context(whole, n[:2] + " " + n[2:])
            out["entries"][n] = {"exact_contexts": exact[:8], "spaced_contexts": spaced[:8]}

    # 4) Pagination endpoint for audit metadata.
    pag_url = f"https://gallica.bnf.fr/services/Pagination?ark={ARK}"
    try:
        status, ctype, data = fetch(pag_url)
        out["sources"]["pagination"] = {"url": pag_url, "status": status, "content_type": ctype, "raw": text_of(data)[:30000]}
    except Exception as e:
        out["errors"].append({"stage": "Pagination", "error": repr(e)})

    Path("/tmp/mendes-cg-extract").mkdir(parents=True, exist_ok=True)
    Path("/tmp/mendes-cg-extract/MENDES_CG53465_53469_GALLICA_EXTRACT.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if whole:
        # Keep a bounded companion around the target interval by searching the first and last exact hits.
        positions = []
        for n in TARGETS:
            positions += [m.start() for m in re.finditer(re.escape(n), whole)]
        if positions:
            a = max(0, min(positions) - 5000)
            b = min(len(whole), max(positions) + 12000)
            Path("/tmp/mendes-cg-extract/MENDES_CG53465_53469_OCR_WINDOW.txt").write_text(whole[a:b], encoding="utf-8")
    print(json.dumps({"ok": True, "errors": len(out["errors"]), "whole_text": bool(whole)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
