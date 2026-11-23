#!/usr/bin/env python3
"""raw_html/<doc>.html -> extracted/<doc>.json
schema: {docname, depth, static_prefix, title, body_bytes, chunk_count, chunks:[{chunk_id, html}]}
본문(<main>)을 최상위 요소 경계에서 ~6KB 단위 chunk로 자름. 번역은 html 안의 텍스트 노드만."""
import json, os, re, sys
from html.parser import HTMLParser
VOID = {"br","img","hr","input","meta","link","source","wbr","col","area","embed","param","track"}
LIMIT = 6000
class Top(HTMLParser):
    def __init__(s): super().__init__(convert_charrefs=False); s.d=0; s.cuts=[]
    def handle_starttag(s,t,a):
        if t not in VOID: s.d+=1
    def handle_endtag(s,t):
        if t not in VOID: s.d-=1
        if s.d==0: s.cuts.append(s.off())
    def off(s):
        ln,col=s.getpos(); return s.lines[ln-1]+col+len(s.get_endtag_text() if hasattr(s,'x') else '')
def split_top(body):
    # 최상위 요소 끝 위치 목록
    p=Top(); p.lines=[0]
    for l in body.splitlines(keepends=True): p.lines.append(p.lines[-1]+len(l))
    ends=[]
    orig=p.handle_endtag
    def he(t):
        orig_d=p.d
        if t not in VOID: p.d-=1
        if p.d==0 and orig_d==1:
            ln,col=p.getpos(); s=p.lines[ln-1]+col
            e=body.index(">",s)+1; ends.append(e)
    p.handle_endtag=he; p.feed(body); p.close()
    return ends
def chunks_of(body):
    ends=split_top(body); out=[]; start=0; last=0
    for e in ends:
        if e-start>LIMIT and last>start:
            out.append(body[start:last]); start=last
        last=e
    out.append(body[start:])
    return [c for c in out if c] or [body]
def main(docs):
    man={d["docname"]:d for d in json.load(open("manifest.json"))}
    for doc in docs or man:
        h=open(f"raw_html/{doc}.html",encoding="utf-8").read()
        m=re.search(r'<main>(.*)</main>',h,re.S)
        body=m.group(1)
        title=re.search(r'<title>(.*?)</title>',h,re.S).group(1)
        cs=chunks_of(body)
        assert "".join(cs)==body
        j={"docname":doc,"depth":man[doc]["depth"],"static_prefix":"../"*man[doc]["depth"],
           "title":title,"body_bytes":len(body.encode()),"chunk_count":len(cs),
           "chunks":[{"chunk_id":i,"html":c} for i,c in enumerate(cs)]}
        p=f"extracted/{doc}.json"; os.makedirs(os.path.dirname(p),exist_ok=True)
        with open(p,"w",encoding="utf-8") as f: json.dump(j,f,ensure_ascii=False,indent=2); f.write("\n")
    print("ok", len(docs or man))
if __name__=="__main__": main(sys.argv[1:])
