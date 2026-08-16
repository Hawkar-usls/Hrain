#!/usr/bin/env python3
import html as htmlmod
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ARK = "bpt6k5774000v"
TARGETS = ["53465", "53466", "53467", "53468", "53469"]
TARGET_PAGES = [82, 83, 84]
UA = "JANUS-HRain-Mendes-CG-Extract/1.1"


def fetch(url, timeout=35):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("content-type", ""), r.read()


def text_of(data):
    return data.decode("utf-8", errors="replace")


def alto_to_text(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""
    words = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "String":
            val = el.attrib.get("CONTENT") or el.attrib.get("content")
            if val:
                words.append(htmlmod.unescape(val))
        elif tag == "SP":
            words.append(" ")
        elif tag == "TextLine" and words and words[-1] != "\n":
            words.append("\n")
    text = " ".join(w for w in words if w not in {" ", "\n"})
    return re.sub(r"\s+", " ", text).strip()


def extract_context(text, needle, radius=700):
    hits = []
    for m in re.finditer(re.escape(needle), text, flags=re.I):
        a = max(0, m.start() - radius)
        b = min(len(text), m.end() + radius)
        hits.append(text[a:b])
    return hits


def main():
    outdir = Path("/tmp/mendes-cg-extract")
    outdir.mkdir(parents=True, exist_ok=True)
    out = {
        "schema": "hrain.gallica.cg_extract.v2",
        "ark": ARK,
        "targets": TARGETS,
        "target_pages": TARGET_PAGES,
        "sources": {},
        "pages": {},
        "entries": {},
        "errors": [],
    }

    page_map = {n: [] for n in TARGETS}

    # 1) Resolve exact target numbers to Gallica page IDs.
    for n in TARGETS:
        url = "https://gallica.bnf.fr/services/ContentSearch?" + urllib.parse.urlencode({"ark": ARK, "query": n})
        try:
            status, ctype, data = fetch(url)
            txt = text_of(data)
            page_ids = sorted(set(int(x) for x in re.findall(r"<p_id>PAG_(\d+)</p_id>", txt)))
            page_map[n] = page_ids
            out["sources"][f"contentsearch_{n}"] = {
                "url": url,
                "status": status,
                "content_type": ctype,
                "page_ids": page_ids,
                "raw": txt[:10000],
            }
        except Exception as e:
            out["errors"].append({"stage": "ContentSearch", "target": n, "error": repr(e)})

    # 2) Pull ALTO OCR for the three resolved pages.
    combined_pages = []
    for p in TARGET_PAGES:
        url = f"https://gallica.bnf.fr/RequestDigitalElement?O={ARK}&E=ALTO&Deb={p}"
        try:
            status, ctype, data = fetch(url, timeout=45)
            xml_text = text_of(data)
            plain = alto_to_text(xml_text)
            out["pages"][str(p)] = {
                "url": url,
                "status": status,
                "content_type": ctype,
                "xml_bytes": len(data),
                "text": plain,
            }
            (outdir / f"PAG_{p}_ALTO.xml").write_text(xml_text, encoding="utf-8")
            (outdir / f"PAG_{p}_OCR.txt").write_text(plain + "\n", encoding="utf-8")
            combined_pages.append(f"[PAG_{p}] {plain}")
        except Exception as e:
            out["errors"].append({"stage": "ALTO", "page": p, "error": repr(e)})

    combined = "\n".join(combined_pages)
    (outdir / "MENDES_CG53465_53469_PAGES_82_84.txt").write_text(combined + "\n", encoding="utf-8")

    # 3) Extract bounded contexts from the actual page OCR.
    for n in TARGETS:
        contexts = []
        for p in page_map.get(n, []):
            ptxt = (out.get("pages", {}).get(str(p)) or {}).get("text", "")
            for ctx in extract_context(ptxt, n):
                contexts.append({"page": p, "context": ctx})
        out["entries"][n] = {"page_ids": page_map.get(n, []), "contexts": contexts}

    # 4) Keep pagination metadata for mapping PAG order to printed page number.
    pag_url = f"https://gallica.bnf.fr/services/Pagination?ark={ARK}"
    try:
        status, ctype, data = fetch(pag_url)
        raw = text_of(data)
        mapping = {}
        for block in re.findall(r"<page>(.*?)</page>", raw, flags=re.S):
            order = re.search(r"<ordre>(\d+)</ordre>", block)
            numero = re.search(r"<numero>(.*?)</numero>", block)
            if order and numero:
                mapping[int(order.group(1))] = numero.group(1)
        out["sources"]["pagination"] = {
            "url": pag_url,
            "status": status,
            "content_type": ctype,
            "target_mapping": {str(p): mapping.get(p) for p in TARGET_PAGES},
        }
    except Exception as e:
        out["errors"].append({"stage": "Pagination", "error": repr(e)})

    (outdir / "MENDES_CG53465_53469_GALLICA_EXTRACT.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "ok": True,
        "errors": len(out["errors"]),
        "page_map": page_map,
        "ocr_chars": {p: len((out.get('pages', {}).get(str(p)) or {}).get('text','')) for p in TARGET_PAGES},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
