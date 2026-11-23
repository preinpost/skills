Kubebuilder Book(https://book.kubebuilder.io) 한국어 번역 작업입니다. 문서 하나를 직접 번역하세요.

프로젝트 경로: {P}
대상 문서: {DOC}
- 원본: {P}/extracted/{DOC}.json
- 출력: {P}/translated/{DOC}.json (새로 만들기, 디렉터리 없으면 생성)
- 용어집: {P}/glossary.json — 먼저 읽고 반드시 따르세요. 용어집이 문서 안의 다른 표현보다 우선합니다.

## JSON 규칙
- 원본 JSON과 같은 구조. `docname, depth, static_prefix, body_bytes, chunk_count`와 각 chunk의 `chunk_id`는 그대로 둡니다.
- `title`: "영어 제목 - The Kubebuilder Book" → "한국어 제목 - Kubebuilder 한국어 문서"
- 각 chunk의 `html`에서 **텍스트 노드만** 번역합니다. 태그, 속성(href, id, class 포함), 태그 개수와 순서는 바이트 단위로 동일해야 합니다.
- 저장은 Python으로: `json.dump(obj, f, ensure_ascii=False, indent=2)` 후 `f.write("\n")`.
- chunk가 크면 chunk별로 나눠 작업하고 중간 저장해도 됩니다. 문서 전체의 모든 문단을 빠짐없이 번역하세요(일부만 번역하고 끝내지 말 것).

## 번역하지 않는 것
- `<pre>`, `<code>`, `<svg>`, `<script>` 내부는 한 글자도 바꾸지 않습니다.
- 명령어, 플래그, 파일 경로, 필드명, 마커(`+kubebuilder:...`), 식별자, 설정값, URL.
- 제품/도구 이름(Kubebuilder, controller-runtime, Kustomize, Helm, kind 등)과 Kubernetes Kind 이름(Pod, Deployment ...).
- 엔티티 `&lt; &gt; &amp;`는 그대로 유지(개수 동일). `&#39;` `&quot;` 같은 다른 엔티티는 텍스트로 바꿔도 됩니다.
- 라이선스 헤더(Apache License 본문, Copyright 줄)는 영어 원문 그대로 둡니다.

## 문체
- 기술 문서체 "~합니다/~하세요". 자연스러운 한국어로 의역하되 의미를 빠뜨리거나 더하지 마세요.
- 원문의 줄바꿈 위치를 따라 문장을 끊지 마세요. 문단 내 줄바꿈 문자는 없애도 됩니다(<pre> 밖에서만).
- 한자/가나 사용 금지.

## 흔한 기계번역 실패 패턴 (반드시 피할 것)
1. 태그(`<code>`, `<a>`, `<em>`)로 문장이 쪼개져 있어도 문장 전체를 이해하고 번역하세요. "다음을 실행합니다: <code>X</code>"처럼 식별자를 문장 끝 콜론 뒤로 밀어내지 말고, 자연스러운 위치에 두세요(태그 순서는 유지해야 하므로 어순을 조정해 맞추세요).
2. `을(를)`, `은(는)` 같은 자리표시 조사 금지. 앞 단어의 받침에 맞게 조사를 고르세요.
3. 태그 경계에서 문장이 잘리거나 중복되지 않게 하세요.
4. 고유명사/단위/옵션값을 일반 단어로 번역하지 마세요(예: `kind` 클러스터를 "종류"로, `clean`을 "깨끗한"으로 바꾸는 것 금지).
5. 의미 반전 주의: "A instead of B", 능동/수동 주어, 부정문, 조건문, 방향(before/after, up/down)을 정확히.

## 금지 사항
- Google 번역 등 외부 번역 서비스, 외부 LLM API(OpenRouter 등) 사용 금지. 직접 번역하세요.
- 자격 증명 파일(~/.pi/agent/auth.json 등) 읽기 금지.
- 다른 문서의 translated 파일, manifest.json, glossary.json, 스크립트 수정 금지.

## 검증
작업 후 `cd {P} && python3 validate_only.py {DOC}`를 실행해 0 errors가 될 때까지 고치세요.

## 보고
마지막에 짧게: 번역한 범위(전체/일부), validate 결과, 원문 자체의 이상한 점이나 애매했던 용어(있으면).
