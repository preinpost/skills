#!/usr/bin/env python3
"""usage: next_queue.py [done_doc grade [summary...]] -> 결과 기록 후 다음 문서 pop, JSON {doc, task, remaining}"""
import sys, json, os
here=os.path.dirname(os.path.abspath(__file__)); cfg=json.load(open(f"{here}/qa_config.json"))
P=cfg["project"]; R=cfg["round"]; os.chdir(P)
qf=f"_work/{R}_queue.txt"; rf=f"_work/{R}_results.txt"
if len(sys.argv)>=3:
    open(rf,"a").write(f"{sys.argv[1]} {sys.argv[2]} {' '.join(sys.argv[3:])}\n".rstrip()+"\n")
q=[l for l in open(qf).read().split("\n") if l]
if not q: print(json.dumps({"doc":None,"remaining":0})); sys.exit()
doc=q.pop(0); open(qf,"w").write("\n".join(q)+("\n" if q else ""))
hints=json.load(open(f"_work/{R}_hints.json")).get(doc,[])
rules="\n".join(f"- {r}" for r in cfg["extra_rules"])
hint="\n".join(f"- {h}" for h in hints) or "- (없음)"
task=f"""{cfg['site']} {cfg['language']} 번역본 검수 작업입니다. 문서 하나를 원문과 문장 단위로 대조해 직접 고치세요.

프로젝트: {P}
대상 문서: {doc}
- 원문: {P}/extracted/{doc}.json
- 번역본(수정 대상): {P}/translated/{doc}.json
- 용어집: {cfg['glossary']} (용어집이 문서 내 다수 표현보다 우선)
- 사이드바 제목: {cfg['sidebar_glossary']}

## 할 일
1. 모든 chunk의 모든 문단·목록·제목·표 셀·summary를 원문과 한 문장씩 대조합니다. 일부만 보고 끝내지 마세요. chunk가 크면 chunk별로 나눠 읽고 chunk마다 저장하세요.
2. 다음을 찾아 고칩니다:
   - 의미 반전/왜곡: 부정문, "A instead of B", 능동/수동 주어, 조건, 방향(before/after, from/to), 수량
   - 누락·추가된 내용, 문장이 태그 경계에서 잘리거나 중복된 곳
   - 식별자를 문장 끝 콜론 뒤로 밀어낸 어색한 어순, `을(를)` 같은 조사 자리표시
   - 고유명사/옵션값/명령을 일반 단어로 번역한 곳
   - 용어집과 다른 표기, 부자연스러운 직역
3. 텍스트 노드만 수정합니다. 태그·속성·<pre>/<code>/<svg> 내부·엔티티(&lt; &gt; &amp;)는 그대로. JSON 메타와 title은 건드리지 마세요.
4. 저장: Python json.dump(obj, f, ensure_ascii=False, indent=2) 후 f.write("\\n").
5. `cd {P} && python3 validate_only.py {doc}` 가 0 errors가 될 때까지 확인.

## 사이트별 규칙
{rules}

## 이 문서에 대한 사전 메모(번역 단계에서 나온 지적, 참고용. 오탐일 수 있음)
{hint}

## 금지
- 외부 번역 서비스·외부 LLM API 사용, 자격 증명 파일({', '.join(cfg['forbidden_paths'])}) 읽기.
- 다른 문서, manifest.json, glossary.json, sidebar_glossary.json, 스크립트 수정.
- 정상 번역을 신호(영어 잔존, 길이 비율 등)를 없애려고 왜곡하는 것.

## 보고 (짧게)
- 대조한 범위: 전체/일부 (일부면 어디까지)
- 자체 등급: A(사소한 다듬기만) / B(의미 수정·누락 복원 1건 이상) / C(핵심 지시가 여러 곳 틀림·대량 누락)
- 고친 내용 요약(의미 수정은 원문/수정 전/수정 후 각 1줄), validate 결과
"""
print(json.dumps({"doc":doc,"task":task,"remaining":len(q)},ensure_ascii=False))
