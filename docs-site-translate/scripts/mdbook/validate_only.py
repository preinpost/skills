#!/usr/bin/env python3
"""extracted/<doc>.json vs translated/<doc>.json 구조 검증. usage: validate_only.py [doc ...]  (없으면 전체)"""
import json, re, sys, os, glob
from html.parser import HTMLParser
SUFFIX = " - Kubebuilder 한국어 문서"
META = ["docname","depth","static_prefix","body_bytes","chunk_count"]
VERBATIM = re.compile(r'<(pre|code|svg|script|style)\b[^>]*>.*?</\1>', re.S)
CJK = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]')
class Tags(HTMLParser):
    def __init__(s): super().__init__(convert_charrefs=False); s.t=[]
    def handle_starttag(s,t,a): s.t.append(("<",t,tuple(a)))
    def handle_startendtag(s,t,a): s.t.append(("<",t,tuple(a)))
    def handle_endtag(s,t): s.t.append(("/",t))
def tags(h): p=Tags(); p.feed(h); p.close(); return p.t
def ents(h):
    out={}
    for e in re.findall(r'&[#\w]+;', VERBATIM.sub('',h)): out[e]=out.get(e,0)+1
    return out
def check(doc):
    errs=[]
    src=json.load(open(f"extracted/{doc}.json",encoding="utf-8"))
    tp=f"translated/{doc}.json"
    if not os.path.exists(tp): return ["missing translated file"]
    raw=open(tp,encoding="utf-8").read()
    try: tr=json.loads(raw)
    except Exception as e: return [f"json error {e}"]
    if json.dumps(tr,ensure_ascii=False,indent=2)+"\n"!=raw: errs.append("format: must be ensure_ascii=False, indent=2, trailing newline")
    if set(tr)!=set(src): errs.append(f"top keys differ {set(tr)^set(src)}")
    for k in META:
        if tr.get(k)!=src.get(k): errs.append(f"meta {k} changed")
    t=tr.get("title","")
    if not t.endswith(SUFFIX): errs.append(f"title must end with '{SUFFIX}': {t!r}")
    if CJK.search(t): errs.append("CJK in title")
    sc,tc=src["chunks"],tr.get("chunks",[])
    if len(sc)!=len(tc): return errs+["chunk count differ"]
    for a,b in zip(sc,tc):
        i=a["chunk_id"]
        if set(b)!={"chunk_id","html"} or b.get("chunk_id")!=i: errs.append(f"[{i}] chunk keys/id changed"); continue
        A,B=a["html"],b["html"]
        ta,tb=tags(A),tags(B)
        if ta!=tb:
            for n,(x,y) in enumerate(zip(ta,tb)):
                if x!=y: errs.append(f"[{i}] tag/attr mismatch at #{n}: {x} vs {y}"); break
            else: errs.append(f"[{i}] tag count {len(ta)} vs {len(tb)}")
        va,vb=VERBATIM.findall(A),VERBATIM.findall(B)
        ma=[m.group(0) for m in VERBATIM.finditer(A)]; mb=[m.group(0) for m in VERBATIM.finditer(B)]
        if ma!=mb:
            for n,(x,y) in enumerate(zip(ma,mb)):
                if x!=y: errs.append(f"[{i}] pre/code/svg changed #{n}: {x[:80]!r} -> {y[:80]!r}"); break
            else: errs.append(f"[{i}] pre/code count {len(ma)} vs {len(mb)}")
        ea,eb=ents(A),ents(B)
        for e in ("&lt;","&gt;","&amp;"):
            if ea.get(e,0)!=eb.get(e,0): errs.append(f"[{i}] entity {e} {ea.get(e,0)} -> {eb.get(e,0)}")
        if CJK.search(VERBATIM.sub('',B)): errs.append(f"[{i}] hanzi/kana leakage: {CJK.findall(VERBATIM.sub('',B))[:5]}")
    return errs
if __name__=="__main__":
    docs=sys.argv[1:] or [json.load(open("manifest.json"))[i]["docname"] for i in range(len(json.load(open("manifest.json"))))]
    total=0
    for d in docs:
        e=check(d); total+=len(e)
        if e or len(docs)==1:
            print(f"{d}: {len(e)} errors"); [print("  ",x) for x in e[:30]]
    print("TOTAL errors:",total, "docs:",len(docs))
    sys.exit(1 if total else 0)
