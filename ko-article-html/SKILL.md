---
name: ko-article-html
description: Turn a web article into a complete Korean translation packaged as one self-contained HTML file for team sharing, keeping the original figures and animated demos inline. Use when the user asks to translate a URL or blog post fully into Korean and hand it over as HTML, e.g. "이 글 전체 번역해서 팀에 공유할 HTML로 만들어줘", "아티클 번역 HTML", "원문 그대로 그림까지 넣어서 한국어 문서로", "번역본 만들어서 파일로 줘".
compatibility: Python 3.9+, curl, ffmpeg/ffprobe for animated figures.
---

# 원문 아티클 → 한국어 단일 HTML

원문 한 편을 **빠짐없이 번역**하고, 원문의 그림과 애니메이션을 그대로 담아, 파일 하나만 보내면 끝나는 공유용 HTML로 만든다.

## 산출물

- `<slug>-ko.html` 파일 하나. 이미지·영상·스타일이 전부 내장되어 오프라인에서도 열린다.
- 표지(제목·리드·필자·날짜·핵심 수치) → 목차 → 본문 → 각주 → 출처 푸터.
- 다크 모드, 모바일, 인쇄, 각주 상호 이동, 읽기 진행률이 동작한다.
- 상단에 "비공식 번역본" 안내를 반드시 넣는다.

## 준비

```bash
SKILL=~/.pi/agent/skills/ko-article-html
mkdir -p work && cd work
curl -sL -A "Mozilla/5.0" "$URL" -o page.html
```

스크립트는 항상 `$SKILL/scripts/...`로 부르고, 산출물은 작업 폴더에 만든다.

## 작업 순서

### 1. 원문과 그림 확보

```bash
python3 "$SKILL/scripts/media.py" list page.html
```

- 본문 텍스트는 `fetch_content`(readable)로 먼저 읽는다. 읽기 모드 추출은 `<video>`와 `<figure>` 캡션을 놓치는 경우가 많으므로, 그림 정보는 저장한 `page.html`에서 뽑는다.
- `list`는 문서 순서대로 그림 라벨, 캡션, 실제 자산 URL을 보여준다. Next.js의 `/_next/image?url=...` 래퍼는 자동으로 벗겨 원본 파일을 가리킨다.
- 그림이 안 잡히면 `<figure>`가 없는 사이트다. `page.html`의 `video|img` 태그를 직접 보고, 상대 경로가 많으면 `--base "$URL"`을 넘긴다.

```bash
python3 "$SKILL/scripts/media.py" fetch page.html --out . --max-width 1080 --crf 26
```

- 영상과 움직이는 GIF는 무음 H.264로 다시 인코딩하고 `poster_<key>.jpg`를 만든다. 3.6MB·22초 영상이 0.3MB 수준이 된다.
- 출력된 스니펫을 그대로 쓰면 `{{IMG:...}}`, `{{MEDIA:...}}` 지시자가 맞춰진다.
- 전체 미디어가 9MB를 넘으면 `--crf 30` 또는 `--max-width 900`으로 다시 뽑는다. 목표는 최종 HTML 12MB 이하, 가능하면 4MB 이하.

### 2. 번역

`references/translation.md`를 먼저 읽고 용어집을 지킨 뒤, `references/design.md`의 구성 요소로 문서를 조립한다.

- **요약하지 않는다.** 문단, 목록, 표, 각주, 그림 캡션, 인용, 링크 텍스트까지 전부 옮긴다.
- 원문의 굵게·기울임 강조는 의미가 유지되는 위치에 살린다.
- 고유명사, 제품명, 코드, 수식은 원문 표기를 유지한다. 그림 안의 영문 라벨도 원본 그대로 두고 캡션에서 한국어로 설명한다.
- 문장은 서술어로 끝맺고, 엠대시(—) 대신 쉼표·콜론·접속사로 잇는다.
- 링크는 전부 살린다. 외부 링크는 `target="_blank" rel="noopener"`.

### 3. 조립

```bash
cp "$SKILL/assets/template.html" page.html
```

`page.html`의 슬롯을 채운다. 슬롯은 전부 `{{...}}` 형태다.

| 슬롯 | 내용 |
|---|---|
| `{{TITLE}}` | 번역 제목. `<title>`에도 같은 문자열을 쓴다 |
| `{{DESCRIPTION}}` | 한 문장 요약 (메타 설명) |
| `{{BRAND}}` / `{{TAG}}` | 원문 매체명 / "한국어 번역" |
| `{{EYEBROW}}` | 카테고리 (Research, Engineering 등) |
| `{{LEDE}}` | 원문 도입부. `<p>` 없이 문단 텍스트만, 링크 포함 |
| `{{BYLINE}}` | 필자 (원문 표기) |
| `{{DATE}}` / `{{READ_TIME}}` | `2026년 10월 22일` / 본문 글자수 ÷ 700 |
| `{{SOURCE_URL}}` / `{{SOURCE_TITLE}}` / `{{SOURCE_META}}` | 원문 링크, 원제, `(매체, 날짜)` |
| `{{STATS}}` | 핵심 수치 카드 3~4개. 원문에 근거가 있는 숫자만 |
| `{{TOC}}` | `<li><a href="#id">…</a></li>` 목록 |
| `{{NOTICE}}` | 번역 안내 문구 |
| `{{BODY}}` | 번역 본문 (그림 포함) |
| `{{FOOTNOTES}}` | `<li id="fn-1">… <a class="back" href="#ref-1">↩</a></li>` |
| `{{DISCLAIMER}}` | 비공식 번역·저작권 안내 |

본문 각주는 `<sup class="fn"><a href="#fn-1" id="ref-1">1</a></sup>`로 쓰고 목록의 `id`와 짝을 맞춘다.
그림은 `<figure class="bleed">` 안에 넣고 `<figcaption><span class="fig-label">그림 1</span>…</figcaption>`로 캡션을 단다. 지면(760px)보다 넓게 퍼지는 것이 이 디자인의 핵심이다.

### 4. 빌드

```bash
python3 "$SKILL/scripts/build.py" page.html --out article-ko.html --root .
```

- `{{IMG:...}}` → data URI, `{{MEDIA:...}}` → 포스터, `{{PAYLOAD}}` → 영상 base64.
- 미해결 슬롯이나 없는 영상이 있으면 빌드가 실패한다. 빠진 것을 채우고 다시 돌린다.
- 인라인 프리뷰가 필요하면 `--preview`를 붙인다. 영상만 빠지고 레이아웃은 같으며 512KB 제한을 넘지 않는다.

### 5. 검증

```bash
python3 "$SKILL/scripts/check.py" article-ko.html
```

- ERROR는 0으로 만든다. 남은 슬롯, 네트워크를 가리키는 미디어, 깨진 내부 링크, 닫히지 않은 태그를 잡는다.
- 브라우저로 390px 폭과 데스크톱을 확인한다. 가로 스크롤이 없어야 하고, 그림이 화면에 들어올 때 한 번 재생되며, 다크 모드에서 캡션 대비가 유지되어야 한다.
- `file://`로 직접 열어도 동작하는지 확인한다. 모든 자산이 내장되어 있으므로 서버가 필요 없다.
- 영상 시킹이 되는지 확인한다. base64를 Blob URL로 바꾸는 처리가 들어 있으니, 재생바를 끌어 위치를 옮겨 본다.

### 6. 전달

파일 경로, 크기, 포함한 그림 수를 한두 줄로 알린다. 본문 내용을 채팅에 다시 붙이지 않는다. "비공식 번역"임을 한 번 더 밝힌다.

## 하지 말 것

- 요약본이나 발췌 번역을 "전체 번역"이라고 부르지 않는다.
- 원문 그림을 외부 URL로 참조한 채 두지 않는다. 링크가 죽으면 문서가 빈 채로 남는다.
- 영상 여러 개를 무제한으로 넣지 않는다. 12MB를 넘으면 메일·메신저에서 열리지 않는다.
- 각주 번호를 손으로 세지 않는다. `check.py`가 내부 링크를 검사하므로 어긋나면 바로 드러난다.
- 원문에 없는 해설이나 평가를 본문에 섞지 않는다. 해설이 필요하면 상단 안내나 푸터에 분리해 적는다.

## 참고 파일

- `references/design.md` — 색·타이포·구성 요소 스니펫
- `references/translation.md` — 번역 원칙과 용어집
- `assets/template.html` — 전체 CSS/JS가 들어 있는 셸
- `scripts/media.py`, `scripts/build.py`, `scripts/check.py`
