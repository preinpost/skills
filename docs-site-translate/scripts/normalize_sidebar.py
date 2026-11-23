#!/usr/bin/env python3
"""Normalize sidebar_html text nodes in translated/*.json to sidebar_glossary.json.

Aligns text nodes of the translated sidebar with the extracted (English) sidebar
by position (tag structure must match). For each English text node that has a
glossary entry, replaces the translated text node with the glossary value.
Usage: normalize_sidebar.py [--apply] [docname ...]
"""
import glob, json, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "sidebar_glossary.json"), encoding="utf-8"))
TOKEN = re.compile(r"(<script\b.*?</script>|<[^>]+>)", re.S)


def split(html):
    return TOKEN.split(html)  # even idx = text, odd idx = tag


def tags(parts):
    return [re.sub(r"\s+", " ", p) for p in parts[1::2]]


def normalize(doc, apply):
    e = json.load(open(os.path.join(HERE, "extracted", doc + ".json"), encoding="utf-8"))
    tp = os.path.join(HERE, "translated", doc + ".json")
    t = json.load(open(tp, encoding="utf-8"))
    ep, tp_parts = split(e["sidebar_html"]), split(t["sidebar_html"])
    if len(ep) != len(tp_parts) or tags(ep) != tags(tp_parts):
        return None, []
    changes = []
    for i in range(0, len(ep), 2):
        en = ep[i].strip()
        if en and en in G and tp_parts[i].strip() != G[en]:
            lead = tp_parts[i][: len(tp_parts[i]) - len(tp_parts[i].lstrip())]
            trail = tp_parts[i][len(tp_parts[i].rstrip()):]
            changes.append((tp_parts[i].strip(), G[en]))
            tp_parts[i] = lead + G[en] + trail
    if changes and apply:
        t["sidebar_html"] = "".join(tp_parts)
        json.dump(t, open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return True, changes


def main():
    apply = "--apply" in sys.argv
    docs = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not docs:
        docs = sorted(p[len(os.path.join(HERE, "translated")) + 1:-5]
                      for p in glob.glob(os.path.join(HERE, "translated", "**", "*.json"), recursive=True))
    skipped, changed, total = [], 0, 0
    pairs = Counter()
    for d in docs:
        ok, ch = normalize(d, apply)
        if ok is None:
            skipped.append(d)
            continue
        if ch:
            changed += 1
            total += len(ch)
            pairs.update(ch)
    print(f"docs={len(docs)} changed_docs={changed} replacements={total} skipped(structure mismatch)={len(skipped)} apply={apply}")
    for (a, b), n in pairs.most_common(25):
        print(f"  {n:5d}  {a!r} -> {b!r}")
    for s in skipped[:20]:
        print("  SKIP", s)


if __name__ == "__main__":
    main()
