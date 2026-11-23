#!/usr/bin/env python3
"""본문 내부 링크 중 원문 링크 텍스트가 대상 문서 제목(사이드바 영어)과 같은 경우 → 번역본 링크 텍스트를 사이드바 한국어 제목으로 통일.
usage: link_title_sync.py [--apply]"""
import json,re,html,sys,posixpath
side=json.load(open("sidebar_glossary.json"))
js=open("toc_source.js").read()
href2en={h[:-5]:html.unescape(t) for h,t in re.findall(r'<a href="([^"]+)">(?:<strong aria-hidden="true">[^<]*</strong> )?([^<]*)</a>',js)}
en2ko={html.unescape(k):html.unescape(v) for k,v in side.items()}
A=re.compile(r'(<a href="([^"#]*?)(?:\.html)?(#[^"]*)?"[^>]*>)([^<]*)</a>')
apply="--apply" in sys.argv; n=0
for d in json.load(open("manifest.json")):
    doc=d["docname"]; s=json.load(open(f"extracted/{doc}.json")); p=f"translated/{doc}.json"; t=json.load(open(p)); ch=False
    for a,b in zip(s["chunks"],t["chunks"]):
        la=list(A.finditer(a["html"])); lb=list(A.finditer(b["html"]))
        if len(la)!=len(lb): continue
        out=b["html"]
        for x,y in reversed(list(zip(la,lb))):
            href=x.group(2); txt=re.sub(r'\s+',' ',html.unescape(x.group(4))).strip()
            if not href or re.match(r'^[a-z]+:',href): continue
            tgt=href.strip("/") if href.startswith("/") else posixpath.normpath(posixpath.join(posixpath.dirname(doc),href))
            if tgt not in href2en or txt.lower()!=href2en[tgt].lower(): continue
            ko=en2ko.get(href2en[tgt]); 
            if not ko or y.group(4).strip()==ko: continue
            print(f"{doc}: [{y.group(4).strip()}] -> [{ko}]"); n+=1
            out=out[:y.start(4)]+html.escape(ko,quote=False)+out[y.end(4):]
        if out!=b["html"]: b["html"]=out; ch=True
    if ch and apply:
        with open(p,"w") as f: json.dump(t,f,ensure_ascii=False,indent=2); f.write("\n")
print("changes",n,"applied" if apply else "(dry-run)")
