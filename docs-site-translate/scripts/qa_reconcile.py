#!/usr/bin/env python3
"""QA 상태 대조: 대상(hints) vs 결과(results) vs 대기열(queue).
세션/모델 전환·할당량 중단 뒤 '큐에서 빠졌지만 결과가 없는(유실된 in-flight)' 문서를 찾는다.
usage: qa_reconcile.py <qaN>   (예: qa1 → _work/qa1_hints.json, qa1_results.txt, qa1_queue.txt)
"""
import json, os, sys
from collections import Counter

W = os.path.dirname(os.path.abspath(__file__))  # place this file in <project>/_work/ (like next_queue.py)
n = sys.argv[1] if len(sys.argv) > 1 else "qa1"
hints = json.load(open(os.path.join(W, f"{n}_hints.json")))
res = [l.split() for l in open(os.path.join(W, f"{n}_results.txt")) if l.strip()]
queue = open(os.path.join(W, f"{n}_queue.txt")).read().split() if os.path.exists(os.path.join(W, f"{n}_queue.txt")) else []
done = Counter(r[0] for r in res)
inflight = [d for d in hints if d not in done and d not in queue]
print(json.dumps({
    "total": len(hints), "done": len(done), "queued": len(queue),
    "inflight_or_lost": inflight,
    "dup_results": [d for d, c in done.items() if c > 1],
    "no_grade": [r[0] for r in res if len(r) < 2],
    "grades": Counter(r[1] for r in res if len(r) > 1),
}, ensure_ascii=False, indent=1))
