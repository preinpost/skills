#!/usr/bin/env python3
"""QA 큐 드라이버. <project>/_work/ 에 두고 사용.
  python3 _work/next_queue.py                 # 다음 문서 pop → {doc, task, remaining}
  python3 _work/next_queue.py <doc> <A|B|C>   # 결과 기록 후 다음 문서 pop
설정: _work/qa_config.json (없으면 기본값). 예:
{
  "round": "qa4",                       # _work/<round>_queue.txt / _results.txt / _hints.json
  "site_name": "Linux 커널 문서",
  "target_lang": "한국어",
  "title_suffix": "&#8212; Linux 커널 문서",
  "glossary": "glossary.json",
  "forbidden_paths": ["~/.pi/agent/auth.json", "_work/b3_*"],
  "extra_rules": ["원문 kernel-doc의 깨진 xref(<code>struct is</code> 등)는 <code> 안은 그대로 두고 주변 문장만 자연스럽게"]
}
"""
import json, os, sys

W = os.path.dirname(os.path.abspath(__file__))
P = os.path.dirname(W)
cfg = {
    "round": "qa1", "site_name": "문서", "target_lang": "한국어", "title_suffix": "",
    "glossary": "glossary.json", "forbidden_paths": [], "extra_rules": [],
}
cp = os.path.join(W, "qa_config.json")
if os.path.exists(cp):
    cfg.update(json.load(open(cp, encoding="utf-8")))
R = cfg["round"]
f_queue, f_res, f_hint = (os.path.join(W, f"{R}_{x}") for x in ("queue.txt", "results.txt", "hints.json"))

if len(sys.argv) >= 3:
    with open(f_res, "a") as f:
        f.write(f"{sys.argv[1]} {sys.argv[2]}\n")
q = open(f_queue).read().split() if os.path.exists(f_queue) else []
if not q:
    print(json.dumps({"doc": None, "remaining": 0}))
    sys.exit()
doc, rest = q[0], q[1:]
open(f_queue, "w").write("".join(d + "\n" for d in rest))
hints = json.load(open(f_hint)) if os.path.exists(f_hint) else {}
hint = json.dumps(hints.get(doc, {}), ensure_ascii=False)
title_rule = f'- title 접미사 "{cfg["title_suffix"]}"\n' if cfg["title_suffix"] else ""
forbid = ", ".join(cfg["forbidden_paths"])
extra = "".join(f"- {r}\n" for r in cfg["extra_rules"])

task = f"""{cfg["site_name"]} {cfg["target_lang"]} 번역 품질 검증 및 수정. 작업 디렉터리: {P}
대상 문서 하나: {doc}
자동 분석(triage.py) 신호: {hint}. 점수가 낮아도 자동 분석이 못 잡는 오역·뜻 반전·누락·기계 번역체가 있을 수 있으니 원문과 문장 단위로 꼼꼼히 대조하라.
(code_mut=<code> 안 텍스트가 원문과 다름, ent_loss=&lt;/&gt;/&amp; 엔티티 손실, eng_left=번역 안 된 원문 문단, glue_eng=번역문에 원문 단어 섞임, len_short/len_long=길이 이상(누락/환각), badword=알려진 오역 단어. badword/glue_eng 는 단순 매칭이라 문맥상 정확한 번역이나 고유명사·인용문이면 그대로 둘 것. 신호를 없애려고 부자연스럽게 바꾸지 말 것)
원문 extracted/{doc}.json 과 번역 translated/{doc}.json 을 비교하고 문제가 있으면 translated/{doc}.json 을 직접 수정한다. python3 triage.py {doc} 로 신호를 확인할 수 있다.
검토 항목:
- 오역, 누락, 어색한 기계 번역체, 문맥에 안 맞는 용어, 원문에 없는 내용
- 자주 나오는 기계 번역 패턴: 식별자/링크를 콜론 뒤 문장 끝으로 빼낸 문장("다음 …합니다: X"), 조사 자리표시자("을(를)"), 태그/링크 경계에서 끊기거나 중복된 문장, 원문 줄바꿈대로 잘린 문장, 고유명사·단위·옵션 값을 일반 단어로 번역한 것
{extra}- <code>/식별자/명령어/경로/설정값은 원문 그대로. HTML 엔티티(&lt; &gt; &amp;)도 원문 그대로.
- 용어는 {cfg["glossary"]}가 기준이다. 문서 안 다수 표기가 glossary와 달라도 glossary 쪽으로 맞출 것(반대 방향 금지). sidebar_html 용어는 건드리지 말 것(태그 구조 오류만 수정).
- 긴 문서도 모든 chunk의 모든 문단을 끝까지 대조할 것(출력 잘림 주의: chunk별로 나눠 읽기). 표본·앞부분만 보는 것 금지.
- 다른 문자 체계 혼입 금지(예: 한국어 번역에 한자/가나)
{title_rule}- 구조: HTML 태그/속성/순서, <pre> 내용, 모든 메타 키(docname, depth, static_prefix, body_bytes, chunk_count, chunk_id, wrapper_open, wrapper_close) 원문과 동일.
금지: 외부 번역 서비스, 외부 LLM API 호출, 인증 키 파일 읽기{(", " + forbid) if forbid else ""}. 번역은 네가 직접.
수정 후 python3 validate_only.py {doc} 오류 0까지 수정. JSON은 기존 형식 유지(ensure_ascii=False, indent=2, 끝 줄바꿈 유무 동일).
manifest.json 및 다른 문서 수정 금지.
보고: 품질 등급(A 양호/B 일부 수정/C 대폭 수정), 실제로 대조한 범위(전체/일부 명시), 주요 문제와 수정 내용 요약(짧게), 최종 validate 결과."""
print(json.dumps({"doc": doc, "task": task, "remaining": len(rest)}, ensure_ascii=False))
