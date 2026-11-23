#!/usr/bin/env python3
"""raw_html이 참조하는 로컬 정적 파일(css/js/폰트/이미지) -> static_assets/"""
import re, os, glob, json, posixpath, urllib.request, urllib.parse
BASE="https://book.kubebuilder.io/"
need=set()
for d in json.load(open("manifest.json")):
    h=open(f"raw_html/{d['docname']}.html",encoding="utf-8").read()
    dirn=posixpath.dirname(d["docname"])
    for u in re.findall(r'(?:src|href)="([^"#?]+)', h):
        if re.match(r'^[a-z]+:|^//|^mailto', u) or u.endswith(".html") or u.endswith("/"): continue
        need.add(posixpath.normpath(posixpath.join(dirn,u)))
todo=list(need); done=set()
while todo:
    p=todo.pop()
    if p in done or p.startswith(".."): continue
    done.add(p); out=f"static_assets/{p}"
    if not os.path.exists(out):
        try: data=urllib.request.urlopen(BASE+urllib.parse.quote(p),timeout=30).read()
        except Exception as e: print("FAIL",p,e); continue
        os.makedirs(os.path.dirname(out) or ".",exist_ok=True); open(out,"wb").write(data)
    if p.endswith(".css"):
        for u in re.findall(r'url\(["\']?([^)"\'?#]+)', open(out,encoding="utf-8",errors="ignore").read()):
            if not re.match(r'^[a-z]+:',u): todo.append(posixpath.normpath(posixpath.join(posixpath.dirname(p),u)))
print(len(done),"assets")
