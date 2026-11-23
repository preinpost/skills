#!/usr/bin/env python3
"""book.kubebuilder.io (mdBook) TOC -> manifest.json, toc_order.json"""
import json, re, urllib.request
BASE = "https://book.kubebuilder.io/"
idx = urllib.request.urlopen(BASE).read().decode()
toc_js = re.search(r'src="(toc-[0-9a-f]+\.js)"', idx).group(1)
js = urllib.request.urlopen(BASE + toc_js).read().decode()
order, seen = [], set()
for m in re.finditer(r'href=\\?"([^"\\#]+\.html)', js):
    h = m.group(1)
    if h.startswith("http") or h in seen: continue
    seen.add(h); order.append(h)
manifest = [{"docname": h[:-5], "url": BASE + h, "depth": h.count("/")} for h in order]
json.dump(order, open("toc_order.json", "w"), ensure_ascii=False, indent=2)
json.dump(manifest, open("manifest.json", "w"), ensure_ascii=False, indent=2)
open("toc_source.js", "w").write(js)
print(len(manifest), "pages")
