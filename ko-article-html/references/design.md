# 디자인 시스템

원문 아티클을 "읽는 문서"로 만드는 규칙이다. 화려함보다 지면의 리듬과 한국어 가독성을 우선한다.

## 지면

| 항목 | 값 | 이유 |
|---|---|---|
| 본문 폭 | 760px | 한글 30~38자. 그보다 넓으면 눈이 줄을 놓친다 |
| 그림 폭 | `min(960px, 100vw - 2.2rem)` | 본문보다 넓게 빼서 시각적 숨통을 만든다 |
| 본문 | 18px / 행간 1.85 | 한글은 라틴 문자보다 행간이 넓어야 한다 |
| 모바일 | 17px / 1.82 | 390px에서 한 줄 20자 안팎 |
| 제목 | `clamp(30px, 4.7vw, 47px)` / 1.33 | 두 줄로 떨어져도 균형이 유지된다 |
| 단락 간격 | 1.15em | 문단 사이가 행간보다 살짝 넓어야 경계가 보인다 |

`body`에 `word-break: keep-all`을 반드시 둔다. 없으면 "형식 / 검증"처럼 단어 중간에서 줄이 끊긴다.

## 색

라이트는 따뜻한 종이, 다크는 잉크. 강조색은 테라코타 하나만 쓴다.

```css
--paper:#FBFAF6; --paper-2:#F4F1EA; --ink:#1A1917; --ink-soft:#3B3833;
--muted:#6D675D; --line:#E3DED2; --card:#FFFFFF;
--accent:#B8562F; --accent-2:#8A3F22; --accent-soft:#F6E9E1;

html[data-theme="dark"]{
  --paper:#121110; --paper-2:#191816; --ink:#EDE8DE; --ink-soft:#D3CDC2;
  --muted:#9B9488; --line:#2C2A25; --card:#181715;
  --accent:#E08A61; --accent-2:#F0A886; --accent-soft:#2A211C;
}
```

- 링크는 강조색 + 32% 투명 밑줄. hover에서 밑줄만 진해진다.
- 인용·요약 박스는 `--accent-soft` 배경, 테두리 없음.
- 표(table)는 헤더만 `--paper-2`, 나머지는 1px `--line` 구분선.

## 구성 요소

### 표지

```html
<p class="eyebrow">Research</p>
<h1>번역 제목</h1>
<div class="lede">도입부. 링크 포함 가능.</div>
<p class="byline">필자, 필자, 필자</p>
<div class="meta-row">
  <span>2026년 10월 22일</span><span class="sep"></span>
  <span>약 14분</span><span class="sep"></span>
  <a href="원문" target="_blank" rel="noopener">원문 보기 ↗</a>
</div>
```

### 핵심 수치

원문이 숫자를 전면에 내세울 때만 쓴다. 3~4개, 각 카드에 단위와 한 줄 설명.

```html
<div class="stats" role="list" aria-label="핵심 수치">
  <div class="stat" role="listitem"><b><span>123</span>개</b><small>증명을 완료한 라이브러리</small></div>
  <div class="stat" role="listitem"><b><span>64</span>MB</b><small>증명이 포괄하는 입력 상한</small></div>
</div>
```

숫자만 `<span>`으로 강조하고 단위는 잉크색으로 둔다. 카드마다 강조 위치가 달라지면 산만해진다.

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

- **테마**: `localStorage`에 저장, 없으면 OS 설정을 따른다. 버튼 `aria-label`은 현재 상태에 맞춰 바뀐다.
- **진행률**: `scrollHeight` 기준, 3px 상단 바. 읽기 방해 금지.
- **영상**: base64를 Blob URL로 바꿔 넣는다. data URI를 그대로 `src`에 넣으면 시킹이 어긋나는 브라우저가 있다. `IntersectionObserver`로 처음 보일 때 한 번만 재생하고, 화면을 벗어나면 멈춘다.
- **각주**: 이동 후 1.4초 하이라이트.
- **모션 최소화**: `prefers-reduced-motion`에서 스크롤·전환을 끈다.
- **인쇄**: 헤더·목차·CTA를 숨기고, 외부 링크는 URL을 괄호로 덧붙인다.

## 흔한 실수

- 그림을 외부 URL로 두는 것 → 링크가 죽으면 문서가 빈 채로 남는다.
- 본문 폭을 900px 이상으로 넓히는 것 → 한글 가독성이 급격히 떨어진다.
- 강조색을 두 개 이상 쓰는 것 → 수치·라벨·링크가 서로 경쟁한다.
- 캡션을 요약하는 것 → 원문 캡션은 정보량이 많다. 줄이지 말고 번역한다.
- 영상에 `controls`를 빼는 것 → 팀원이 멈추거나 되감을 수 없어야 할 이유가 없다.
