#!/usr/bin/env python3
"""out/ 내부 링크(상대 경로) 존재 확인"""
import re, os, glob, posixpath
bad=0; n=0
for p in glob.glob("out/**/*.html",recursive=True):
    rel=os.path.relpath(p,"out"); d=posixpath.dirname(rel)
    for u in re.findall(r'(?:src|href)="([^"#?]+)',open(p,encoding="utf-8").read()):
        if re.match(r'^[a-z]+:|^//',u) or u.startswith("{{"): continue
        n+=1; t=posixpath.normpath(posixpath.join(d,u))
        if not os.path.exists(f"out/{t}"):
            bad+=1; print("BROKEN",rel,"->",u)
print(f"links checked {n}, broken {bad}")
