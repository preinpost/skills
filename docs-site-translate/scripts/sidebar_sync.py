#!/usr/bin/env python3
"""(Sphinx/Alabaster 마크업 기준: <a class="reference internal" href="#id"> 와 <section id><hN> — 다른 생성기는 정규식 A/SEC를 조정)
사이드바의 현재 문서 목차 링크(href="#id") 문구와 본문 제목(id 섹션의 h1~h6) 문구 비교.
usage: qa5_sidebar_check.py [--apply]  -> 불일치 시 사이드바 문구를 본문 제목으로 맞춤
"""
import json, os, re, sys, glob, shutil, html
P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLY = "--apply" in sys.argv
BK = "/tmp/qa5_sidebar_backup"
A = re.compile(r'(<a class="reference internal" href="#([^"]+)">)([^<]*)(</a>)')
SEC = re.compile(r'<section id="([^"]+)">\s*<h[1-6][^>]*>(.*?)<a class="headerlink"', re.S)
TAG = re.compile(r"<[^>]+>")
n_docs = n_fix = 0
samples = []
for path in sorted(glob.glob(os.path.join(P, "translated", "**", "*.json"), recursive=True)):
    raw = open(path, encoding="utf-8").read()
    d = json.loads(raw)
    sb = d.get("sidebar_html")
    if not sb:
        continue
    body = json.dumps(d.get("chunks", ""), ensure_ascii=False)
    body = json.loads(json.dumps([c.get("html", "") for c in d.get("chunks", [])], ensure_ascii=False))
    heads = {}
    for h in body:
        for sid, t in SEC.findall(h):
            heads.setdefault(sid, TAG.sub("", t).strip())
    changed = 0
    def rep(m):
        global n_fix
        nonlocal_changed[0]
        sid, txt = m.group(2), m.group(3)
        h = heads.get(sid)
        if h is None or h == txt.strip():
            return m.group(0)
        if not re.search(r"[가-힣]", h):
            return m.group(0)
        nonlocal_changed[0] += 1
        if len(samples) < 40:
            samples.append(f"{os.path.relpath(path, P)} #{sid}: {txt!r} -> {h!r}")
        return m.group(1) + h + m.group(4)
    nonlocal_changed = [0]
    nsb = A.sub(rep, sb)
    if nonlocal_changed[0]:
        n_docs += 1
        n_fix += nonlocal_changed[0]
        if APPLY:
            bp = os.path.join(BK, os.path.relpath(path, os.path.join(P, "translated")))
            os.makedirs(os.path.dirname(bp), exist_ok=True)
            if not os.path.exists(bp):
                shutil.copy2(path, bp)
            d["sidebar_html"] = nsb
            txt = json.dumps(d, ensure_ascii=False, indent=2)
            if raw.endswith("\n"):
                txt += "\n"
            open(path, "w", encoding="utf-8").write(txt)
for s in samples:
    print(s)
print("docs", n_docs, "links", n_fix, "(applied)" if APPLY else "(dry-run)")
