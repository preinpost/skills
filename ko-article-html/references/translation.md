# 번역 원칙

기술 아티클을 한국어로 옮길 때의 규칙이다. 문장 품질은 `fluent-korean` 지침을 따르고, 여기서는 이 산출물에 특유한 판단만 적는다.

## 기본

- **전부 옮긴다.** 문단, 목록, 표, 각주, 캡션, 인용, 이미지 alt, 링크 텍스트까지 대상이다.
- **요약하지 않는다.** 압축이 필요하면 문서 끝이나 상단에 별도 "요약" 블록을 두고, 본문은 원문 구조를 유지한다. 원문의 소제목 순서와 개수를 바꾸지 않는다.
- **문장은 서술어로 끝맺는다.** 소제목·목록 항목·캡션은 명사구로 끝나도 된다.
- **엠대시(—)를 쓰지 않는다.** 콜론, 쉼표, 접속사로 대체한다.
- **번역투를 피한다.** "~에 의해", "~되어진다", "그것은 ~이다"를 걷어내고 주어와 서술어를 살린다.
- **원문의 강조를 보존한다.** `<strong>`은 주장의 핵심, `<em>`은 용어 정의에 주로 대응한다.

## 숫자와 단위

| 원문 | 표기 |
|---|---|
| 180 million lines | 1억 8천만 줄 |
| 64 MB | 64MB (숫자와 단위 붙여 씀) |
| 123 libraries | 123개 라이브러리 |
| 1,000+ vulnerabilities | 1,000건이 넘는 취약점 |
| two person-years | 2인년 |
| 99.95% | 99.95% |
| under 64 MB | 64MB 미만 |

통계 카드처럼 좁은 자리에서만 `1.8억` 같은 축약을 허용하고, 본문에서는 `1억 8천만`으로 풀어 쓴다.

## 용어집

| English | 한국어 | 비고 |
|---|---|---|
| formal verification | 형식 검증 | "정형 검증" 아님 |
| formally verified | 형식 검증된 | |
| specification / spec | 명세 | |
| proof | 증명 | |
| proof checker | 증명 검사기 | |
| theorem statement | 정리 서술 | |
| fuzzing / fuzzer | 퍼징 / 퍼저 | |
| fuzz test | 퍼즈 테스트 | |
| entry point | 진입점 | |
| crash | 크래시 | "충돌"보다 정확 |
| memory safety | 메모리 안전성 | |
| out-of-bounds read/write | 경계 밖 읽기/쓰기 | |
| assertion | 단언 | 첫 등장 시 `단언(assertion)` |
| counter underflow | 카운터 언더플로 | |
| stack overflow | 스택 오버플로 | |
| use-after-free | use-after-free | 관용 표기 유지 |
| semantics | 시맨틱스 | |
| instruction set (ISA) | 명령어 집합(ISA) | |
| assembly code | 어셈블리 코드 | |
| binary / executable | 바이너리 / 실행 파일 | |
| static binary | 정적 바이너리 | |
| specification gap | 명세의 틈 | |
| trusted component | 신뢰 구성 요소 | |
| reward hacking | 보상 해킹 | |
| power law | 멱법칙 | |
| roundtrip | 왕복 | |
| idempotence | 멱등성 | |
| differential testing | 차분 테스트 | |
| rebalancing | 재균형 | |
| decompressor | 압축 해제기 | |
| corner case | 코너 케이스 | 관용 |
| end-to-end | 종단 간 | |

고유명사는 원문 표기를 유지한다: Claude, Theorem, Rocq, RISC-V, Linux(본문은 "리눅스" 허용), OSS-Fuzz, AddressSanitizer(ASan), seL4, Mathlib, libc++, musl, glibc, cpp-httplib, libexpat, Verus, Lean, Rust, Python(본문은 "파이썬" 허용), CPython, zlib, Nix, cURL, OpenSSL.

## 캡션

원문 캡션은 대개 "굵은 한 문장 + 부연" 구조다. 그대로 살린다.

```html
<figcaption><span class="fig-label">그림 2</span><strong>퍼징은 입력을 한 진입점에 대량으로 흘려보내 크래시를 찾습니다.</strong> 입력은 무한히 많으므로 탐색은 끝나지 않습니다.</figcaption>
```

- 그림 안의 영문 라벨(Source code, Trusted, Proven 등)은 번역하지 않는다. 캡션에서 필요하면 괄호로 설명을 붙인다.
- 도표의 축 이름이나 범례를 캡션에서 다시 설명하지 않는다. 원문이 설명한 만큼만 옮긴다.

## 각주

- 각주는 문장 단위로 완역한다. 괄호 안 정의도 생략하지 않는다.
- 본문의 각주 번호 위치를 원문과 같게 유지한다. 문장을 재배열했다면 가장 가까운 절 끝으로 옮긴다.
- 각주 안의 링크도 살린다.

## 링크

- 링크 텍스트를 번역하되, 고유명사만으로 된 링크는 그대로 둔다.
- 원문자가 다른 사이트로 거는 링크는 전부 유지한다. "자세한 내용은 원문 참고"로 대체하지 않는다.
- PDF·저장소·논문 링크는 푸터나 CTA에도 한 번 더 모아 둔다.

## 확인이 필요한 순간

- 원문에 오탈자나 사실 오류로 보이는 부분이 있으면 고치지 말고 그대로 옮긴 뒤, 푸터에 "원문 표기 유지" 한 줄을 남긴다.
- 문장이 모호해 두 가지 해석이 가능하면 원문에 가까운 쪽을 택하고, 필요하면 각주에 원문 문장을 병기한다.
- 인용문은 따옴표 안에서도 완역하되, 원문 인용임을 밝힌다.

## 마지막 점검

1. 소제목 개수와 순서가 원문과 같은가.
2. 각주 번호가 본문과 목록에서 일치하는가.
3. 숫자·단위가 원문과 같은가. (특히 억/만 단위 변환)
4. 고유명사 표기가 문서 전체에서 일관적인가.
5. 번역하지 않은 문장이 남아 있지 않은가. (그림 내부 라벨 제외)
6. 모든 외부 링크가 살아 있는 형태로 남아 있는가.
