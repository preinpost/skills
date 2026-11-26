# 디자인 시스템

원문 아티클을 "읽는 문서"로 만드는 규칙이다. 화려함보다 지면의 리듬과 한국어 가독성을 우선한다.

## 지면

| 항목 | 값 | 이유 |
|---|---|---|
| 본문·그림 폭 | 720px (`.layout` 그리드 첫 칸) | 한글 30~36자. 본문과 그림의 좌우 끝선을 맞춘다 |
| 데스크톱 목차 | 오른쪽 260px sticky, 1040px 이하에서 숨김 | 넓은 화면에서는 항상 위치를 보여 준다 |
| 모바일 목차 | `details.mtoc` 접이식, 1040px 이하에서만 표시 | |
| 본문 | `--fs` 18px(16/18/20 세 단계) / 행간 1.8 | 상단 `가- / 가 / 가+` 버튼이 `--fs`를 바꾼다 |
| 제목 | 2.3em, 600px 이하 1.75em | |

`body`에 `word-break: keep-all`을 반드시 둔다. 없으면 "형식 / 검증"처럼 단어 중간에서 줄이 끊긴다.

## 색

라이트는 따뜻한 미색 종이, 다크는 먹색. 강조색은 테라코타 하나만 쓴다.

```css
:root{--bg:#faf9f5;--fg:#191919;--muted:#5f5d57;--line:#e4e1d8;--card:#f0eee6;--accent:#c96442;--accent-soft:#f6e6dd;--code:#efede5}
[data-theme=dark]{--bg:#1a1917;--fg:#ecebe6;--muted:#a8a59c;--line:#34322e;--card:#252420;--accent:#e08a68;--accent-soft:#33261f;--code:#2a2925}
```

- 테마를 저장하지 않았으면 OS 설정(`prefers-color-scheme`)을 따른다.
- 안내 박스(`.notice`)와 수치 카드(`.stat`)는 `--card` 배경, 안내 박스만 왼쪽 강조선.
- 표는 헤더만 `--card`, 나머지는 1px `--line` 구분선. 넓은 표는 가로 스크롤.

## 구성 요소

### 표지

템플릿에 이미 들어 있다. 채우는 슬롯은 `{{EYEBROW}}`, `{{TITLE}}`, `{{LEDE}}`(`<p class="lede">` 안에 들어가므로 `<p>` 없이), `{{BYLINE}}`, `{{DATE}}`, `{{READ_TIME}}`, `{{SOURCE_URL}}`다.

### 핵심 수치

원문이 숫자를 전면에 내세울 때만 쓴다. 2~4개, 각 카드에 한 줄 설명.

```html
<div class="stats">
  <div class="stat"><b>약 70%↓</b><span>요청당 CPU 사용량</span></div>
  <div class="stat"><b>4096B</b><span>게스트 메모리 크기</span></div>
</div>
```

### 목차

`{{TOC}}`는 데스크톱 사이드 목차와 모바일 접이식 목차 두 곳에 같은 내용으로 들어간다. `h2`는 `<li>`, `h3`는 `<li class="sub">`.

```html
<li><a href="#why">01 왜 옮겼나</a></li><li class="sub"><a href="#tests">테스트</a></li>
```

본문의 `h2`/`h3`에 같은 `id`를 달아야 스크롤 위치에 따라 목차가 강조된다.

### 그림

```html
<figure class="bleed">
  <div class="media">                     <!-- .light: 밝은 배경 이미지 -->
    <span class="pill"><i></i>애니메이션</span>   <!-- 움직이는 자산에만 -->
    <video data-key="m1" poster="{{MEDIA:m1}}" muted loop playsinline controls preload="metadata" aria-label="…"></video>
  </div>
  <figcaption><span class="fig-label">그림 1</span><strong>한 문장 요약.</strong> 이어지는 설명.</figcaption>
</figure>
```

- 캡션은 원문 캡션을 그대로 번역한다. 굵은 리드 문장이 있으면 살린다.
- 영상은 `muted loop playsinline controls`가 기본이다. 소리가 있는 영상이면 `muted`를 빼고 각주로 안내한다.
- 정지 이미지는 `loading="lazy"`, `alt`에 그림이 보여 주는 내용을 적는다.
- 그림이 본문 흐름의 일부(작은 도표)라면 `.bleed`를 빼고 본문 폭에 둔다.

### 신뢰·전제 목록

```html
<div class="trust"><ul><li>항목</li><li>항목</li></ul></div>
```

체크 표시는 CSS로 그린다. 원문에 "이 세 가지만 신뢰하면 된다" 같은 열거가 있을 때만.

### 각주

```html
<!-- 본문 -->
<sup class="fn"><a href="#fn-1" id="ref-1">1</a></sup>

<!-- 각주 목록 -->
<li id="fn-1">각주 내용 <a class="back" href="#ref-1" aria-label="본문으로 돌아가기">↩</a></li>
```

번호는 CSS 카운터가 매기므로 `li` 순서만 맞추면 된다. `<sup>`의 숫자와 `id`만 일치시키면 된다.

### CTA

원문이 부록·PDF·저장소를 안내하면 본문 끝에 하나만 둔다.

```html
<div class="cta">
  <div><b>전체 부록 읽기</b><span>추가 실험과 세부 내용은 원문 부록에서 확인할 수 있습니다.</span></div>
  <a class="btn" href="…" target="_blank" rel="noopener">부록 PDF 열기 <svg …/></a>
</div>
```

## 동작

- **테마**: `localStorage`(`ko-art-theme`)에 저장, 없으면 OS 설정을 따른다.
- **글자 크기**: `가- / 가 / 가+`로 16/18/20px, `localStorage`(`ko-art-fs`)에 저장.
- **진행률**: 3px 상단 바. 사이드 목차는 현재 섹션을 강조한다.
- **라이트박스**: `main figure img` 클릭 시 확대, 배경 클릭이나 Esc로 닫는다. 영상은 대상이 아니다.
- **각주**: 본문 각주 번호를 누르면 내용이 팝오버로 뜬다. "각주로 이동"을 누르면 목록으로 이동해 1.4초 강조한다. 각주가 없으면 각주 절이 숨겨진다.
- **영상**: base64를 Blob URL로 바꿔 넣는다. data URI를 그대로 `src`에 넣으면 시킹이 어긋나는 브라우저가 있다. 처음 보일 때 한 번만 재생하고, 화면을 벗어나면 멈춘다.
- **폰트**: Pretendard Variable을 CDN으로 불러오고, 오프라인이면 시스템 한글 폰트로 대체된다.
- **모션 최소화**: `prefers-reduced-motion`에서 부드러운 스크롤·전환을 끈다.
- **인쇄**: 상단 바·목차·라이트박스를 숨기고, 본문 외부 링크는 URL을 괄호로 덧붙인다.

## 흔한 실수

- 그림을 외부 URL로 두는 것 → 링크가 죽으면 문서가 빈 채로 남는다.
- 본문 폭을 720px보다 넓히는 것 → 한글 가독성이 급격히 떨어진다.
- 강조색을 두 개 이상 쓰는 것 → 수치·라벨·링크가 서로 경쟁한다.
- 캡션을 요약하는 것 → 원문 캡션은 정보량이 많다. 줄이지 말고 번역한다.
- 영상에 `controls`를 빼는 것 → 팀원이 멈추거나 되감을 수 없어야 할 이유가 없다.
