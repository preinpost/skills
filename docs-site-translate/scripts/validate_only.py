#!/usr/bin/env python3
"""Read-only validator for translated/*.json files (safe for concurrent subagents).
Never modifies manifest.json.
"""

import json
import os
import re
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACTED_DIR = os.path.join(HERE, "extracted")
TRANSLATED_DIR = os.path.join(HERE, "translated")
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
PRE_BLOCK_RE = re.compile(r"<pre\b[^>]*>.*?</pre>", re.S)
TRACKED_ATTRS = ("href", "id", "class", "src", "role", "type", "for")


class TagSigParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.tokens: list[tuple] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        adict = dict(attrs)
        sig = tuple((k, adict[k]) for k in TRACKED_ATTRS if k in adict)
        self.tokens.append(("start", tag, sig))

    def handle_endtag(self, tag: str) -> None:
        self.tokens.append(("end", tag))


def tag_sig(html_str: str) -> list[tuple]:
    p = TagSigParser()
    p.feed(html_str)
    p.close()
    return p.tokens


def check_doc(docname: str) -> list[str]:
    e_path = os.path.join(EXTRACTED_DIR, f"{docname}.json")
    t_path = os.path.join(TRANSLATED_DIR, f"{docname}.json")
    errs: list[str] = []

    if not os.path.exists(e_path):
        return [f"Missing extracted JSON: {e_path}"]
    if not os.path.exists(t_path):
        return [f"Missing translated JSON: {t_path}"]

    ext = json.loads(open(e_path, encoding="utf-8").read())
    try:
        trn = json.loads(open(t_path, encoding="utf-8").read())
    except Exception as exc:
        return [f"Invalid JSON in {docname}: {exc}"]

    for k in ("docname", "depth", "static_prefix", "body_bytes", "chunk_count"):
        if trn.get(k) != ext.get(k):
            errs.append(f"{docname}: metadata '{k}' mismatch ({trn.get(k)!r} != {ext.get(k)!r})")

    for k in ("title", "sidebar_html", "chunks"):
        if k not in trn:
            errs.append(f"{docname}: missing key '{k}'")

    if errs:
        return errs

    if not HANGUL_RE.search(trn["title"]):
        errs.append(f"{docname}: title has no Hangul ({trn['title']!r})")
    if not HANGUL_RE.search(trn["sidebar_html"]):
        errs.append(f"{docname}: sidebar_html has no Hangul")

    if tag_sig(ext["sidebar_html"]) != tag_sig(trn["sidebar_html"]):
        errs.append(f"{docname}: sidebar_html tag/attribute structure mismatch")

    e_chunks = ext["chunks"]
    t_chunks = trn["chunks"]
    if len(e_chunks) != len(t_chunks):
        errs.append(f"{docname}: chunk count mismatch ({len(t_chunks)} != {len(e_chunks)})")
        return errs

    for ec, tc in zip(e_chunks, t_chunks):
        cid = ec["chunk_id"]
        if tc.get("chunk_id") != cid:
            errs.append(f"{docname}#chunk{cid}: chunk_id mismatch")
        if tc.get("wrapper_open", "") != ec.get("wrapper_open", ""):
            errs.append(f"{docname}#chunk{cid}: wrapper_open modified")
        if tc.get("wrapper_close", "") != ec.get("wrapper_close", ""):
            errs.append(f"{docname}#chunk{cid}: wrapper_close modified")

        eh = ec.get("html", "")
        th = tc.get("html", "")
        if not th.strip():
            errs.append(f"{docname}#chunk{cid}: empty html")
            continue

        e_pres = PRE_BLOCK_RE.findall(eh)
        t_pres = PRE_BLOCK_RE.findall(th)
        if e_pres != t_pres:
            errs.append(f"{docname}#chunk{cid}: <pre> block mismatch (expected {len(e_pres)}, got {len(t_pres)})")

        if tag_sig(eh) != tag_sig(th):
            errs.append(f"{docname}#chunk{cid}: html tag/attribute structure mismatch")

        plain_src = re.sub(r"<[^>]+>", "", eh).strip()
        if len(plain_src) > 40 and not HANGUL_RE.search(th):
            errs.append(f"{docname}#chunk{cid}: no Hangul found in body html")

    return errs


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: validate_only.py <docname> [<docname> ...]")
        sys.exit(2)
    all_errs: list[str] = []
    for docname in sys.argv[1:]:
        all_errs.extend(check_doc(docname))
    print(f"Checked {len(sys.argv) - 1} doc(s). Errors: {len(all_errs)}")
    for e in all_errs[:30]:
        print(" -", e)
    sys.exit(1 if all_errs else 0)


if __name__ == "__main__":
    main()
