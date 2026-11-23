#!/usr/bin/env python3
"""용어 일괄 정리(사이트·언어별로 RULES를 바꿔 쓸 것; 아래 RULES는 Linux 커널 문서 한국어 번역 때의 예시). 본문 텍스트 노드만 치환(태그 속성, <pre>/<code>/<cite>/<kbd>/<samp>/<tt> 내부, sidebar_html 제외).
usage: qa5_terms.py [--apply]   (기본은 dry-run)
"""
import json, os, re, sys, glob, shutil

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLY = "--apply" in sys.argv
BACKUP = "/tmp/qa5_terms_backup"

RULES = [
    (re.compile(r"사용자 공간"), "유저 공간"),
    (re.compile(r"이산\(discrete\) GPU"), "외장(discrete) GPU"),
    (re.compile(r"이산형? GPU"), "외장 GPU"),
    (re.compile(r"어퍼처"), "애퍼처"),
    (re.compile(r"(?<![A-Za-z0-9_./(-])aperture(?![A-Za-z0-9_./)-])"), "애퍼처"),
    (re.compile(r"(?<![A-Za-z0-9_./(-])apertures(?![A-Za-z0-9_./)-])"), "애퍼처"),
]
SKIP_TAGS = {"pre", "code", "cite", "kbd", "samp", "tt", "script", "style"}
TOK = re.compile(r"(<[^>]*>)")
TAGNAME = re.compile(r"<\s*(/)?\s*([a-zA-Z0-9]+)")
SPAN_PRE = re.compile(r'<span[^>]*class="[^"]*\bpre\b')


def fix_html(s, stats, samples, doc):
    out, stack = [], []  # stack of skip markers
    for part in TOK.split(s):
        if part.startswith("<") and part.endswith(">"):
            m = TAGNAME.match(part)
            if m:
                closing, name = m.group(1), m.group(2).lower()
                if not part.endswith("/>"):
                    if closing:
                        if stack and stack[-1] == name:
                            stack.pop()
                    elif name in SKIP_TAGS or (name == "span" and SPAN_PRE.match(part)):
                        stack.append(name)
                    elif stack and name == stack[-1]:
                        stack.append(name)  # nested same tag inside skip
            out.append(part)
            continue
        if stack or not part:
            out.append(part)
            continue
        new = part
        for i, (rx, rep) in enumerate(RULES):
            def r(m, i=i, rep=rep):
                stats[i] = stats.get(i, 0) + 1
                if len(samples.setdefault(i, [])) < 6:
                    a, b = m.start(), m.end()
                    samples[i].append(f"{doc}: …{new[max(0,a-20):b+20]}…".replace("\n", " "))
                return rep
            new = rx.sub(r, new)
        out.append(new)
    return "".join(out)


def walk(o, f):
    if isinstance(o, dict):
        return {k: (v if k == "sidebar_html" else walk(v, f)) for k, v in o.items()}
    if isinstance(o, list):
        return [walk(x, f) for x in o]
    if isinstance(o, str):
        return f(o)
    return o


def main():
    stats, samples, changed = {}, {}, []
    for path in sorted(glob.glob(os.path.join(P, "translated", "**", "*.json"), recursive=True)):
        raw = open(path, encoding="utf-8").read()
        d = json.loads(raw)
        doc = os.path.relpath(path, os.path.join(P, "translated"))[:-5]
        nd = walk(d, lambda s: fix_html(s, stats, samples, doc))
        if nd != d:
            changed.append(doc)
            if APPLY:
                bp = os.path.join(BACKUP, doc + ".json")
                os.makedirs(os.path.dirname(bp), exist_ok=True)
                if not os.path.exists(bp):
                    shutil.copy2(path, bp)
                indent = 2 if raw.startswith("{\n  \"") else (1 if raw.startswith("{\n \"") else None)
                txt = json.dumps(nd, ensure_ascii=False, indent=indent)
                if raw.endswith("\n"):
                    txt += "\n"
                open(path, "w", encoding="utf-8").write(txt)
    for i, (rx, rep) in enumerate(RULES):
        print(f"[{stats.get(i,0):5d}] {rx.pattern} -> {rep}")
        for s in samples.get(i, []):
            print("        ", s)
    print("changed docs:", len(changed), "(applied)" if APPLY else "(dry-run)")
    open("/tmp/qa5_terms_changed.txt", "w").write("\n".join(changed) + "\n")


main()
