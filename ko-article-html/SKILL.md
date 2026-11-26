---
name: ko-article-html
description: Turn a web article into a complete Korean translation packaged as one self-contained HTML file for team sharing, keeping the original figures and animated demos inline. Use when the user asks to translate a URL or blog post fully into Korean and hand it over as HTML, e.g. "이 글 전체 번역해서 팀에 공유할 HTML로 만들어줘", "아티클 번역 HTML", "원문 그대로 그림까지 넣어서 한국어 문서로", "번역본 만들어서 파일로 줘".
compatibility: Python 3.9+, curl, ffmpeg/ffprobe for animated figures, rclone with article-translate remote (optional, for S3 sharing).
---

# 원문 아티클 → 한국어 단일 HTML

```text
PROCEDURE ko_article_html(URL):
    REQUIRE: Python 3.9+, curl, ffmpeg/ffprobe (움직이는 그림),
             rclone remote "article-translate" (선택, S3 공유)
    OUTPUT:  <slug>-ko.html
        # 이미지·영상·스타일 전부 내장, 오프라인 동작
        # 표지(제목·리드·필자·날짜·핵심 수치) → 목차 → 본문 → 각주 → 출처 푸터
        # Pretendard Variable(폴백: 시스템 한글 폰트), 다크 모드,
        # 글자 크기 3단계(가- / 가 / 가+), 모바일 접이식 목차,
        # 데스크톱 우측 sticky 목차, 라이트박스, 각주 팝오버, 인쇄, 읽기 진행률
        # 상단 "비공식 번역본" 안내 필수

    # ── 0. 준비 ─────────────────────────────────────────
    SKILL ← directory containing this SKILL.md
    TMP   ← python3 -c "import tempfile; print(tempfile.gettempdir())"
        # macOS/Linux: $TMPDIR 또는 /tmp, Windows: %TEMP%
    WORK  ← TMP/ko-article-html-<slug>
    mkdir -p WORK; cd WORK
        # 모든 중간 파일과 산출물은 WORK에만 만든다. 프로젝트 폴더에 work/를 만들지 않는다
    source.html ← curl -sL -A "Mozilla/5.0" "$URL"
        # why(inferred): 브라우저가 아닌 UA를 막는 사이트가 있다
    # 원문은 source.html, 조립 중인 템플릿은 page.html
        # why: 템플릿 복사가 원문을 덮어쓰면 6단계 og:image를 찾을 수 없다
    # 스크립트는 항상 $SKILL/scripts/... 로 호출
    # Windows에서는 python3 대신 py / python, 경로는 따옴표로 감싼다

    # ── 1. 원문과 그림 확보 ──────────────────────────────
    text ← fetch_content(URL, readable)
    figures ← python3 $SKILL/scripts/media.py list source.html
        # why: 읽기 모드 추출은 <video>와 <figure> 캡션을 자주 놓친다
        # 문서 순서대로 라벨·캡션·자산 URL, /_next/image 래퍼는 자동 해제
    IF figures is empty:                      # <figure> 없는 사이트
        MANUAL: source.html의 video|img 태그 직접 확인
        IF 상대 경로가 많음: rerun media.py list with --base "$URL"

    snippets ← python3 $SKILL/scripts/media.py fetch source.html
                   --out . --max-width 1080 --crf 26
        # 영상·움직이는 GIF → 무음 H.264 + poster_<key>.jpg
        # 3.6MB·22초 영상 → 약 0.3MB
        # why: 출력 스니펫을 그대로 쓰면 {{IMG:...}}, {{MEDIA:...}} 지시자가 맞는다
    IF total_media > 9MB:
        rerun media.py fetch with --crf 30 AND/OR --max-width 900
    WHILE total_media > 9MB:
        가장 큰 영상 → {{IMG:poster_<key>.jpg}} 정지 이미지
        캡션 끝에 "원문에서 영상 보기" 링크
        replaced ← replaced + figure          # 6단계에서 알림
    TARGET: final_html ≤ 12MB (가능하면 ≤ 4MB)
        # why: 12MB를 넘으면 메일·메신저에서 열리지 않는다

    # ── 2. 번역 ──────────────────────────────────────────
    READ $SKILL/references/translation.md      # 번역 원칙, 용어집 준수
    READ $SKILL/references/design.md           # 색·타이포·구성 요소 스니펫
    FOR EACH element IN 문단, 목록, 표, 각주, 그림 캡션, 인용, 링크 텍스트:
        translate fully                        # 요약 금지
        keep bold/italic at meaning-equivalent position
            # why(inferred): 어순이 달라 단어 위치를 그대로 옮기면 강조 대상이 바뀐다
        keep as-is: 고유명사, 제품명, 코드, 수식, 그림 속 영문 라벨
            # 그림 라벨은 캡션에서 한국어로 설명
        end with predicate; "—" → 쉼표 / 콜론 / 접속사
        keep every link; external → target="_blank" rel="noopener"

    # ── 3. 조립 ──────────────────────────────────────────
    cp $SKILL/assets/template.html page.html
    FILL fields IN page.html {
        {{TITLE}}         번역 제목 (<title>에도 같은 문자열)
        {{DESCRIPTION}}   한 문장 요약 (메타 설명)
        {{BRAND}}         원문 매체명
        {{TAG}}           "한국어 번역"
        {{EYEBROW}}       카테고리 (Research, Engineering 등)
        {{LEDE}}          원문 도입부, <p> 없이 문단 텍스트만, 링크 포함
        {{BYLINE}}        필자 (원문 표기)
        {{DATE}}          "2026년 10월 22일" 형식
        {{READ_TIME}}     본문 글자수 ÷ 700
        {{SOURCE_URL}}    원문 링크
        {{SOURCE_TITLE}}  원제
        {{SOURCE_META}}   "(매체, 날짜)"
        {{STATS}}         핵심 수치 카드 2~4개, 원문에 근거가 있는 숫자만
        {{TOC}}           toc_item 목록
        {{NOTICE}}        번역 안내 문구
        {{BODY}}          번역 본문 (그림 포함)
        {{FOOTNOTES}}     footnote_item 목록
        {{DISCLAIMER}}    비공식 번역·저작권 안내
    }
    toc_item      := <li><a href="#id">…</a></li>
    footnote_ref  := <sup class="fn"><a href="#fn-N" id="ref-N">N</a></sup>
    footnote_item := <li id="fn-N">… <a class="back" href="#ref-N">↩</a></li>
    figure        := <figure class="bleed"> (또는 <figure>)
                       … <figcaption><span class="fig-label">그림 N</span>…</figcaption>
    # 본문·그림 모두 720px 컨테이너 좌우 끝선 정렬, 정지 이미지는 클릭 시 라이트박스

    # ── 4. 빌드 ──────────────────────────────────────────
    LOOP:
        TRY python3 $SKILL/scripts/build.py page.html
                --out article-ko.html --root .
            # {{IMG}} → data URI, {{MEDIA}} → 포스터, {{PAYLOAD}} → 영상 base64
        ON FAIL (미해결 슬롯 / 없는 영상): fill missing; CONTINUE
        BREAK
    OPTIONAL: build.py … --preview         # 영상 제외, 레이아웃 동일, ≤ 512KB

    # ── 5. 검증 ──────────────────────────────────────────
    REPEAT python3 $SKILL/scripts/check.py article-ko.html; fix
    UNTIL errors == 0
        # 남은 슬롯, 네트워크 미디어, 깨진 내부 링크, 닫히지 않은 태그
    MANUAL: browser @ 390px AND desktop
        ASSERT no horizontal scroll
        ASSERT 본문·그림 좌우 끝선 일치
        ASSERT 라이트박스, 각주 팝오버, 글자 크기, 다크 모드 대비 정상
        ASSERT file:// 로 열어도 동작
            # why: 모든 자산이 내장되어 서버가 필요 없다
        IF video: ASSERT 재생바 드래그로 시킹
            # why: base64를 Blob URL로 바꾸는 처리가 들어 있다

    # ── 6. 전달 & S3 공유 ────────────────────────────────
    REPORT WORK/<slug>-ko.html (절대 경로), size, figure_count, replaced, "비공식 번역"
        # 임시 경로는 재부팅 등으로 지워질 수 있으니 보관하려면 옮기라고 알린다
        # 본문을 채팅에 다시 붙이지 않음
    reachable ← rclone lsf article-translate:public/article-translate/ (silent)
    IF NOT reachable:
        APPEND "💡 rclone에 `article-translate` 리모트를 설정해 두면 번역본을
                S3(`public/article-translate/`)에 올려 바로 공유할 수 있어요."
        RETURN                                 # 업로드 여부 묻지 않음
    ASK user "S3(article-translate:public/article-translate/)에 올릴까요?"
    IF NOT approved: RETURN

    FILE   ← <slug>-ko.html
    BASE   ← https://s3.preinpost.in/public/article-translate
    OG_IMG ← content of first <meta property="og:image"> IN source.html
    IF OG_IMG is relative: OG_IMG ← absolute URL against $URL
        # why: 메신저 미리보기는 og:image의 http(s) 절대 URL만 읽고 data URI는 무시한다
        # 원문 이미지가 내려가도 썸네일만 빠지고 문서는 영향 없음
    IF "og:title" NOT IN FILE:
        insert right after <head> (값은 html.escape(quote=True)):
            <meta property="og:type" content="article">
            <meta property="og:title" content="<번역 제목>">
            <meta property="og:description" content="<한 문장 요약>">
            <meta property="og:url" content="BASE/FILE">
        IF OG_IMG starts with "http":
            <meta property="og:image" content="OG_IMG">
            <meta name="twitter:card" content="summary_large_image">
    # HTML 한 파일만 올림, 썸네일 이미지는 따로 만들거나 올리지 않음

    DEST ← article-translate:public/article-translate/FILE
    IF rclone lsf DEST is non-empty:
        ASK user "덮어쓸까요?"
        IF NOT approved: RETURN
    rclone copyto FILE DEST
        --header-upload "Content-Type: text/html; charset=utf-8"
    ASSERT curl -sI BASE/FILE → HTTP 200 AND content-type text/html
    OUTPUT BASE/FILE + "버킷이 공개라 링크를 아는 누구나 볼 수 있음"

INVARIANTS:
    ✗ 요약본·발췌 번역을 "전체 번역"이라 부르기
    ✗ 원문 그림을 외부 URL로 참조한 채 두기
        # why: 링크가 죽으면 문서가 빈 채로 남는다
    ✗ 영상 무제한 삽입 (> 12MB)
        # why: 메일·메신저에서 열리지 않는다
    ✗ 각주 번호 수동 계산
        # why: check.py가 내부 링크를 검사해 어긋나면 바로 드러난다
    ✗ 원문에 없는 해설·평가를 본문에 섞기 (필요하면 상단 안내·푸터로 분리)
    ✗ 승인 없이 S3 업로드 / 확인 없이 기존 파일 덮어쓰기

FILES:
    references/design.md        색·타이포·구성 요소 스니펫
    references/translation.md   번역 원칙과 용어집
    assets/template.html        전체 CSS/JS가 들어 있는 셸
    scripts/media.py, scripts/build.py, scripts/check.py
```
