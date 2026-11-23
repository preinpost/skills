#!/usr/bin/env python3
"""translated/(없으면 extracted/) + raw_html 껍데기 -> out/"""
import json, os, re, shutil, hashlib, html
SUFFIX_EN=" - The Kubebuilder Book"; ORIG="https://book.kubebuilder.io/"
side=json.load(open("sidebar_glossary.json",encoding="utf-8"))
def tr_toc(s):
    def f(m):
        t=m.group(2); return m.group(1)+side.get(t,t)+"</a>"
    return re.sub(r'(<a href="[^"]+">(?:<strong aria-hidden="true">[^<]*</strong> )?)([^<]*)</a>',f,s)
import posixpath
# 원문 사이트 자체가 깨진 링크 -> 의도한 대상으로 보정
LINK_FIX={
 "plugins/creating-plugins":"plugins/extending",
 "reference/rescaffold":"reference/commands/alpha_generate",
 "multiversion-tutorial/api-design":"cronjob-tutorial/api-design",
}
GH="https://github.com/kubernetes-sigs/kubebuilder/blob/master/"
def fix_links(h,doc,docs):
    """내부 링크 정리: 확장자 없는 문서 링크 -> .html, out/에 없는 대상 -> 원문 사이트 절대 URL(+문서면 원문 배지)"""
    d=posixpath.dirname(doc)
    def f(m):
        attr,u,frag=m.group(1),m.group(2),m.group(3) or ""
        if not u: return m.group(0)
        am=re.match(r'^https?://book\.kubebuilder\.io/(.*)$',u)
        if am: u="/"+am.group(1)   # 원문 사이트 절대 링크도 내부 문서면 상대 링크로
        elif re.match(r'^[a-z]+:|^//',u): return m.group(0)
        if u.startswith("/"): t=u.strip("/")
        else: t=posixpath.normpath(posixpath.join(d,u))
        if t.endswith("/"): t=t[:-1]
        if t.endswith(".html") and t[:-5] in LINK_FIX: t=LINK_FIX[t[:-5]]
        if t.startswith("multiversion-tutorial/multiversion-tutorial/testdata/"):
            return f'{attr}="{GH}docs/book/src/{t.split("/",1)[1]}{frag}"'
        if t.endswith(".html") and t[:-5] in docs: t=t[:-5]
        if t=="" or t=="index": t="introduction"
        if t in docs:
            return f'{attr}="{posixpath.relpath(t+".html",d or ".")}{frag}"'
        if not t.startswith("..") and os.path.exists(f"out/{t}") and os.path.isfile(f"out/{t}"):
            if u.startswith("/") or "//" in u: return f'{attr}="{posixpath.relpath(t,d or ".")}{frag}"'
            return m.group(0)
        if ".." in u and not am:
            src=posixpath.normpath(posixpath.join("docs/book/src",d,u))
            if not src.startswith("..") and not src.startswith("docs/book/src/"):
                if src.startswith("designs/") and src.endswith(".html"): src=src[:-5]+".md"
                return f'{attr}="https://github.com/kubernetes-sigs/kubebuilder/tree/master/{src}{frag}"'
        tgt=t if not t.startswith("..") else u
        return f'{attr}="{ORIG}{tgt}{frag}"'
    return re.sub(r'(href|src)="([^"#?]*)([#?][^"]*)?"',f,h)
def main():
    if os.path.exists("out"): shutil.rmtree("out")
    shutil.copytree("static_assets","out")
    # 사이드바: toc js / toc.html 번역
    toc_js=[f for f in os.listdir("out") if re.match(r'toc-[0-9a-f]+\.js$',f)][0]
    for f in (toc_js,"toc.html"):
        p=f"out/{f}"; src=open(p,encoding="utf-8").read(); open(p,"w",encoding="utf-8").write(tr_toc(src).replace('lang="en"','lang="ko"'))
    css="_static/kr-override.css"; ver=hashlib.sha1(open(f"out/{css}","rb").read()).hexdigest()[:8]
    man=json.load(open("manifest.json")); ntr=0
    docs={d["docname"] for d in man}
    for d in man:
        doc=d["docname"]; tp=f"translated/{doc}.json"
        is_tr=os.path.exists(tp); ntr+=is_tr
        j=json.load(open(tp if is_tr else f"extracted/{doc}.json",encoding="utf-8"))
        h=open(f"raw_html/{doc}.html",encoding="utf-8").read()
        body="".join(c["html"] for c in j["chunks"])
        notice=(f'<p class="kr-notice">이 문서는 <a href="{ORIG}{doc}.html">원문</a>을 기계 번역 후 검수 중인 한국어 번역본입니다.</p>' if is_tr
                else f'<p class="kr-notice">아직 번역되지 않은 문서입니다. <a href="{ORIG}{doc}.html">원문</a></p>')
        h=re.sub(r'<main>.*</main>',lambda m:"<main>@@KR_NOTICE@@"+body+"</main>",h,count=1,flags=re.S)
        title=j["title"] if is_tr else j["title"]
        h=re.sub(r'<title>.*?</title>',lambda m:f"<title>{title}</title>",h,count=1,flags=re.S)
        h=h.replace('<html lang="en"','<html lang="ko"',1)
        h=h.replace("</head>",f'    <link rel="stylesheet" href="{j["static_prefix"]}{css}?v={ver}">\n    </head>',1)
        h=fix_links(h,doc,docs).replace("@@KR_NOTICE@@",notice,1)
        p=f"out/{doc}.html"; os.makedirs(os.path.dirname(p),exist_ok=True)
        open(p,"w",encoding="utf-8").write(h)
    if not os.path.exists("out/index.html"): shutil.copy("out/introduction.html","out/index.html")
    open("out/.nojekyll","w").close()
    shutil.copy("README.md","out/README.md")
    print(f"built {len(man)} pages ({ntr} translated)")
if __name__=="__main__": main()
