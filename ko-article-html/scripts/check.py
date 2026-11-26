#!/usr/bin/env python3
"""Pre-flight checks for a generated single-file article.

    python3 check.py article-ko.html

Errors (exit 1) are things a teammate would notice immediately: unresolved
placeholders, media that still points at the network, broken internal links,
unbalanced markup. Warnings are judgement calls worth a look.
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter
from html.parser import HTMLParser

VOID = {"br", "img", "meta", "link", "hr", "input", "source", "path", "circle",
        "area", "base", "col", "embed", "track", "wbr", "stop", "rect", "line",
        "polyline", "polygon", "use", "ellipse"}


class Balance(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, tuple[int, int]]] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"stray </{tag}> at line {self.getpos()[0]}")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
            return
        self.errors.append(
            f"</{tag}> at line {self.getpos()[0]} closes <{self.stack[-1][0]}> "
            f"from line {self.stack[-1][1][0]}"
        )
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    doc = open(path, encoding="utf-8").read()

    errors: list[str] = []
    warnings: list[str] = []

    if "{{" in doc:
        errors.append("unresolved placeholders: " + ", ".join(sorted(set(re.findall(r"\{\{[^}]*\}\}", doc))))[:400])

    for src in re.findall(r'(?:src|poster)="(https?://[^"]+)"', doc):
        errors.append(f"network media left in the file: {src[:90]}")

    for tag in re.findall(r"<(?:img|video)\b[^>]*>", doc):
        if 'src=""' in tag or ("<img" in tag and " src=" not in tag):
            errors.append(f"empty media source: {tag[:90]}")

    if not re.search(r'<html[^>]+lang="ko"', doc):
        errors.append('missing lang="ko" on <html>')
    if "name=\"viewport\"" not in doc:
        errors.append("missing viewport meta")
    if re.search(r"<title>\s*</title>", doc):
        errors.append("empty <title>")

    parser = Balance()
    parser.feed(doc)
    errors.extend(parser.errors[:5])
    if parser.stack:
        errors.append("unclosed: " + ", ".join(t for t, _ in parser.stack[:5]))

    ids = re.findall(r'\bid="([^"]+)"', doc)
    dupes = [i for i, n in Counter(ids).items() if n > 1]
    if dupes:
        errors.append("duplicate ids: " + ", ".join(dupes[:8]))

    for anchor in set(re.findall(r'href="#([^"]+)"', doc)):
        if anchor not in ids:
            errors.append(f'broken internal link: #{anchor}')

    figures = doc.count("<figure")
    captions = doc.count("<figcaption")
    if figures != captions:
        warnings.append(f"{figures} figure blocks but {captions} captions")

    videos = re.findall(r'<video[^>]*data-key="([^"]+)"', doc)
    payload_m = re.search(r'<script id="media-data"[^>]*>(.*?)</script>', doc, re.S)
    payload = {}
    if payload_m:
        try:
            import json
            payload = json.loads(payload_m.group(1) or "{}")
        except Exception:
            warnings.append("media payload is not valid JSON")
    if videos and not payload:
        warnings.append("videos present but payload is empty (preview build?)")
    for key in videos:
        if payload and key not in payload:
            errors.append(f"video {key} has no embedded payload")
    if videos and not any('poster="' in v for v in re.findall(r"<video[^>]*>", doc)):
        warnings.append("no video posters; the first paint may look empty")

    for src in re.findall(r"<img\b[^>]*>", doc):
        if "alt=" not in src:
            warnings.append("image without alt text")

    size = os.path.getsize(path) / 1024 / 1024
    b64 = len(re.findall(r"base64,", doc))
    if size > 12:
        warnings.append(f"{size:.1f}MB: re-encode videos with a higher CRF")

    print(f"{os.path.basename(path)}  {size:.2f} MB  {b64} embedded asset(s)")
    print(f"figures {figures}  videos {len(videos)}  links {doc.count('<a ')}")
    for w in warnings:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    print("OK" if not errors else f"{len(errors)} error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
