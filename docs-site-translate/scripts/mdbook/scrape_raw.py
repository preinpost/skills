#!/usr/bin/env python3
"""manifest.json -> raw_html/<doc>.html (cached, polite)"""
import json, os, time, urllib.request
for d in json.load(open("manifest.json")):
    p = f"raw_html/{d['docname']}.html"
    if os.path.exists(p) and os.path.getsize(p) > 0: continue
    os.makedirs(os.path.dirname(p), exist_ok=True)
    for i in range(3):
        try:
            data = urllib.request.urlopen(d["url"], timeout=30).read(); break
        except Exception as e:
            print("retry", d["url"], e); time.sleep(2)
    else: print("FAIL", d["url"]); continue
    open(p, "wb").write(data); time.sleep(0.3)
print("done")
