# skills

개인용 에이전트 스킬 모음. Pi(`~/.pi/agent/skills`), Claude Code, Codex 등에서 같은 형식(`SKILL.md` + `references/` + `scripts/`)으로 쓸 수 있게 관리한다.

## 목록

| 스킬 | 하는 일 | 대표 요청 |
|---|---|---|
| [`ko-article-html`](./ko-article-html) | 웹 아티클을 빠짐없이 한국어로 번역하고, 원문 그림·애니메이션까지 담은 단일 HTML로 패키징한다 | "이 글 전체 번역해서 팀에 공유할 HTML로 만들어줘" |

## 설치

각 스킬 디렉터리를 스킬 검색 경로에 두면 된다.

```bash
# Pi
ln -s ~/dev/skills/ko-article-html ~/.pi/agent/skills/ko-article-html

# 또는 복사
cp -R ko-article-html ~/.pi/agent/skills/
```

Pi에서 스킬을 수정한 뒤에는 `/reload`로 다시 읽는다.

## 새 스킬 추가

1. `<name>/SKILL.md`에 frontmatter를 쓴다. `name`은 디렉터리명과 같게, `description`에는 "무엇을 하는지"와 "언제 쓰는지"를 함께 적는다.
2. 긴 참고 자료는 `references/`, 실행 코드는 `scripts/`, 템플릿은 `assets/`에 둔다.
3. `SKILL.md`에서 경로는 스킬 디렉터리 기준 상대 경로로 적는다.
4. 스크립트는 표준 라이브러리만으로 돌아가게 하고, 외부 의존성은 `compatibility`에 밝힌다.

## 저장소

```bash
git clone git@github.com:preinpost/skills.git
```
