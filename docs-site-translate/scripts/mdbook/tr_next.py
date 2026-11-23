#!/usr/bin/env python3
"""usage: tr_next.py [done_doc status]  -> 결과 기록 후 다음 문서 pop, JSON {doc, task, remaining} 출력"""
import sys, json, os
P="<PROJECT>"; os.chdir(P)
if len(sys.argv)>=3: open("_work/tr_results.txt","a").write(f"{sys.argv[1]} {sys.argv[2]}\n")
q=[l for l in open("_work/tr_queue.txt").read().split("\n") if l]
if not q: print(json.dumps({"doc":None,"remaining":0})); sys.exit()
doc=q.pop(0); open("_work/tr_queue.txt","w").write("\n".join(q)+("\n" if q else ""))
task=open("_work/tr_task_template.md",encoding="utf-8").read().replace("{DOC}",doc).replace("{P}",P)
print(json.dumps({"doc":doc,"task":task,"remaining":len(q)},ensure_ascii=False))
