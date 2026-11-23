#!/usr/bin/env python3
"""문서별 위험 신호 점수 -> _work/triage.json, 표 출력
신호: eng_left(번역 안 된 문단), len_short/len_long(길이 비율), glue_eng(한국어 문장 속 영어 단어 덩어리), badword, title_mismatch"""
import json, re, glob
V=re.compile(r'<(pre|code|svg|script|style)\b[^>]*>.*?</\1>',re.S)
BLOCK=re.compile(r'<(p|li|h[1-6]|td|th|dd|summary)\b[^>]*>(.*?)</\1>',re.S)
HANGUL=re.compile(r'[가-힣]')
LICENSE=re.compile(r'(Copyright|Licensed under|Unless required|You may obtain|limitations under|http://www.apache)')
BAD=re.compile(r'[을은이가]\([를는가이]\)|땡땡이|원산지')
def text(h): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',V.sub(' ',h))).strip()
def blocks(h): return [text(m.group(2)) for m in BLOCK.finditer(V.sub('<code></code>',h))]
out={}
for p in sorted(glob.glob("translated/**/*.json",recursive=True)):
    doc=p[11:-5]; t=json.load(open(p)); s=json.load(open(f"extracted/{doc}.json"))
    sig={"eng_left":0,"len_short":0,"len_long":0,"glue_eng":0,"badword":0}
    ex=[]
    for a,b in zip(s["chunks"],t["chunks"]):
        for x,y in zip(blocks(a["html"]),blocks(b["html"])):
            words=re.findall(r'[A-Za-z]{3,}',x)
            if len(words)<4 or LICENSE.match(x) or " " not in x.strip() or re.fullmatch(r"[\w\s,./:()\-{}=“”$\[\]]+",x) and not re.search(r"\b(the|is|are|to|of|and|you)\b",x): continue
            if not HANGUL.search(y) and y==x: sig["eng_left"]+=1; ex.append(("eng_left",x[:80])); continue
            r=len(y)/max(1,len(x))
            if r<0.22: sig["len_short"]+=1; ex.append(("len_short",f"{r:.2f} {x[:60]} => {y[:60]}"))
            if r>1.6: sig["len_long"]+=1; ex.append(("len_long",f"{r:.2f} {x[:60]} => {y[:60]}"))
            if re.search(r'(?:\b[a-z]{3,}\b[ ,]+){4,}',y) and HANGUL.search(y): sig["glue_eng"]+=1; ex.append(("glue_eng",y[:80]))
        sig["badword"]+=len(BAD.findall(text(b["html"])))
    score=sig["eng_left"]*3+sig["len_short"]*3+sig["len_long"]*2+sig["glue_eng"]+sig["badword"]*2
    out[doc]={"score":score,**sig,"examples":ex[:8],"size":sum(len(c["html"]) for c in s["chunks"])}
json.dump(out,open("_work/triage.json","w"),ensure_ascii=False,indent=2)
for d,v in sorted(out.items(),key=lambda x:-x[1]["score"])[:25]:
    print(f'{v["score"]:3d} {d:60s} el{v["eng_left"]} sh{v["len_short"]} lo{v["len_long"]} gl{v["glue_eng"]} bw{v["badword"]}')
print("zero-score docs:",sum(1 for v in out.values() if v["score"]==0),"/",len(out))
