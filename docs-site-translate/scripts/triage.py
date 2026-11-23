#!/usr/bin/env python3
"""Automatic quality triage for translated/*.json.

Signals per doc (body chunks only; sidebar handled separately):
  code_mut   : text inside <code>/<tt>/<kbd>/<span class="pre"> differs from source (position-aligned)
  ent_loss   : &lt; / &gt; / &amp; count dropped vs source
  eng_left   : prose text nodes (outside code/pre) that still look like English sentences
  glue_eng   : Korean text nodes containing stray English function words (and/the/of/to/is...)
  len_short  : prose nodes much shorter than source (possible omission)
  len_long   : prose nodes much longer than source (possible hallucination)
  badword    : known mistranslation words found in QA
Usage: triage.py [--fix-code] [--top N] [docname ...]
  --fix-code  deterministically restore code-span text from source (tag structure must match)
"""
import glob, json, os, re, sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
HANGUL = re.compile(r"[\uac00-\ud7a3]")
ENGWORD = re.compile(r"[A-Za-z]{2,}")
GLUE = re.compile(r"(?<![A-Za-z_./-])(and|the|of|to|is|are|with|for|that|this|or|be|by|not|should|must|will)(?![A-Za-z_./-])")
BADWORDS = ["운전자", "운전기사", "수영장", "주지사", "총재", "가치를 ", "가치가 ", "장애인", "원산지", "약력",
            "히트작", "배낭", "아바타 상어", "건반", "후기입", "죄송", "천당", "스마트폰", "통화 ",
            "루트 복소수", "주문 컨트롤러", "원단", "독서", "배송", "교육 정보",
            "심장박동", "잘못된 긍정", "손잡이", "돼지", "나뭇잎", "후방교회", "삼투", "바보",
            "스핑크스", "특급", "정오표", "방언", "사서함"]
CODE_TAGS = {"code", "tt", "kbd", "samp"}
ENT = re.compile(r"&(lt|gt|amp);")


class Walker(HTMLParser):
    """Yields text nodes with context flags; keeps raw source for rebuilding."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.nodes = []  # (kind, text) kind: 'tag' | 'code' | 'pre' | 'prose' | 'other'
        self.stack = []

    def _ctx(self):
        if any(t == "pre" for t, _ in self.stack):
            return "pre"
        if any(t in CODE_TAGS or (t == "span" and "pre" in (c or "").split()) for t, c in self.stack):
            return "code"
        if any(t in ("script", "style") for t, _ in self.stack):
            return "other"
        return "prose"

    def handle_starttag(self, tag, attrs):
        self.nodes.append(("tag", self.get_starttag_text()))
        if tag not in ("br", "img", "input", "hr", "meta", "link", "wbr"):
            self.stack.append((tag, dict(attrs).get("class")))

    def handle_startendtag(self, tag, attrs):
        self.nodes.append(("tag", self.get_starttag_text()))

    def handle_endtag(self, tag):
        self.nodes.append(("tag", f"</{tag}>"))
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def _text(self, raw):
        self.nodes.append((self._ctx(), raw))

    def handle_data(self, d):
        self._text(d)

    def handle_entityref(self, n):
        self._text(f"&{n};")

    def handle_charref(self, n):
        self._text(f"&#{n};")

    def handle_comment(self, d):
        self.nodes.append(("tag", f"<!--{d}-->"))


def walk(html):
    w = Walker()
    w.feed(html)
    w.close()
    # merge adjacent text nodes of same kind
    out = []
    for k, t in w.nodes:
        if out and k != "tag" and out[-1][0] == k:
            out[-1] = (k, out[-1][1] + t)
        else:
            out.append((k, t))
    return out


def analyze(doc, fix=False):
    e = json.load(open(os.path.join(HERE, "extracted", doc + ".json"), encoding="utf-8"))
    tpath = os.path.join(HERE, "translated", doc + ".json")
    t = json.load(open(tpath, encoding="utf-8"))
    s = dict(code_mut=0, ent_loss=0, eng_left=0, glue_eng=0, len_short=0, len_long=0, badword=0, prose=0, misaligned=0)
    ex = []
    changed = False
    for ec, tc in zip(e["chunks"], t["chunks"]):
        en, tn = walk(ec["html"]), walk(tc["html"])
        for m in ("lt", "gt", "amp"):
            d = len(re.findall(f"&{m};", ec["html"])) - len(re.findall(f"&{m};", tc["html"]))
            if d > 0:
                s["ent_loss"] += d
        etags = [x for x in en if x[0] == "tag"]
        ttags = [x for x in tn if x[0] == "tag"]
        if [re.sub(r"\s+", " ", x[1]) for x in etags] != [re.sub(r"\s+", " ", x[1]) for x in ttags]:
            s["misaligned"] += 1
            continue
        # align text segments between tags
        def segs(nodes):
            res, cur = [], []
            for k, x in nodes:
                if k == "tag":
                    res.append(cur)
                    cur = []
                else:
                    cur.append((k, x))
            res.append(cur)
            return res
        es_, ts_ = segs(en), segs(tn)
        src_codes = {"".join(x for _, x in sg).strip() for sg in es_ if sg and sg[0][0] == "code"}
        new_t = []
        ti = 0
        for i, (eseg, tseg) in enumerate(zip(es_, ts_)):
            ekind = eseg[0][0] if eseg else None
            etext = "".join(x for _, x in eseg)
            ttext = "".join(x for _, x in tseg)
            if ekind in ("code",) and etext.strip() != ttext.strip() and ttext.strip() not in src_codes:
                s["code_mut"] += 1
                if len(ex) < 6:
                    ex.append(f"code: {etext.strip()[:40]!r} -> {ttext.strip()[:40]!r}")
                if fix:
                    tseg[:] = [("code", etext)]
                    changed = True
            if ekind == "prose":
                ep = etext.strip()
                tp = ttext.strip()
                words = ENGWORD.findall(ep)
                if len(words) >= 4:
                    s["prose"] += 1
                    if not HANGUL.search(tp) and len(GLUE.findall(tp)) >= 2 and len(re.findall(r"\b[a-z]{3,}\b", tp)) >= 5 and tp == ep:
                        s["eng_left"] += 1
                        if len(ex) < 6:
                            ex.append(f"eng: {tp[:60]!r}")
                    elif HANGUL.search(tp):
                        g = GLUE.findall(tp)
                        if g:
                            s["glue_eng"] += 1
                            if len(ex) < 6:
                                ex.append(f"glue: {tp[:60]!r}")
                        if len(tp) < 0.25 * len(ep) and len(ep) > 60:
                            s["len_short"] += 1
                        if len(tp) > 2.2 * len(ep) and len(tp) > 80:
                            s["len_long"] += 1
                if HANGUL.search(tp):
                    for b in BADWORDS:
                        if b in tp:
                            s["badword"] += 1
                            if len(ex) < 6:
                                ex.append(f"bad[{b}]: {tp[:50]!r}")
        if fix and changed:
            out = []
            for i, seg in enumerate(ts_):
                out.append("".join(x for _, x in seg))
                if i < len(ttags):
                    out.append(ttags[i][1])
            tc["html"] = "".join(out)
    if fix and changed:
        json.dump(t, open(tpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    score = (s["code_mut"] * 2 + s["ent_loss"] * 2 + s["eng_left"] * 3 + s["glue_eng"] * 2
             + s["len_short"] * 0.5 + s["len_long"] * 2 + s["badword"] * 3)
    norm = score / max(1, s["prose"]) * 10
    return s, score, norm, ex


def main():
    fix = "--fix-code" in sys.argv
    top = 40
    if "--top" in sys.argv:
        top = int(sys.argv[sys.argv.index("--top") + 1])
    docs = [a for a in sys.argv[1:] if not a.startswith("--") and not a.isdigit()]
    if not docs:
        docs = sorted(p[len(os.path.join(HERE, "translated")) + 1:-5]
                      for p in glob.glob(os.path.join(HERE, "translated", "**", "*.json"), recursive=True))
    rows = []
    for d in docs:
        try:
            rows.append((d,) + analyze(d, fix))
        except Exception as exc:
            print("ERR", d, exc)
    rows.sort(key=lambda r: -r[2])
    tot = {k: sum(r[1][k] for r in rows) for k in rows[0][1]}
    print(f"docs={len(rows)} fix={fix} totals={tot}")
    flagged = [r for r in rows if r[2] > 0]
    print(f"docs with any signal: {len(flagged)}")
    for b in (5, 10, 20, 40):
        print(f"  score>={b}: {sum(1 for r in rows if r[2] >= b)}")
    json.dump([{"doc": r[0], "score": r[2], "norm": round(r[3], 2), **r[1], "examples": r[4]} for r in rows],
              open(os.path.join(HERE, "_work", "triage.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for r in rows[:top]:
        print(f"{r[2]:5.0f} {r[0]:55s} {dict((k, v) for k, v in r[1].items() if v and k != 'prose')}")
        for x in r[4][:2]:
            print("        ", x)


if __name__ == "__main__":
    main()
