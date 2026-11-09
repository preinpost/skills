# skills

개인용 에이전트 스킬 모음. Pi(`~/.pi/agent/skills`), Claude Code, Codex 등에서 같은 형식(`SKILL.md` + `references/` + `scripts/`)으로 쓸 수 있게 관리한다.

## 목록

| 스킬 | 하는 일 | 대표 요청 |
|---|---|---|
| [`ko-article-html`](./ko-article-html) | 웹 아티클을 빠짐없이 한국어로 번역하고, 원문 그림·애니메이션까지 담은 단일 HTML로 패키징한다 | "이 글 전체 번역해서 팀에 공유할 HTML로 만들어줘" |
| [`orchestrator`](./orchestrator) | 메인 에이전트는 사용자 의도 파악과 계획만 맡고, 구현·조사·테스트·리뷰는 반드시 서브에이전트에 위임한다. 스폰 전에 모델과 thinking effort를 묻는다 | "오케스트레이터로 진행해줘" |

## 설치

Node 18+만 있으면 된다. 별도 npm 배포 없이 GitHub에서 바로 실행한다.

```bash
# TUI로 스킬 · 범위(프로젝트/전역) · 위치(claude/agents/pi) 선택
npx github:preinpost/skills

# 묻지 않고 모든 스킬을 ./.claude/skills, ./.agents/skills 에 설치
npx github:preinpost/skills -y

# 홈(~/.claude/skills, ~/.agents/skills)에 전역 설치
npx github:preinpost/skills -g

# 특정 스킬만 / 특정 에이전트만 (claude, agents, pi, all)
npx github:preinpost/skills orchestrator -a claude -g
npx github:preinpost/skills -a pi -g          # ~/.pi/agent/skills

# 목록 보기, 덮어쓰기
npx github:preinpost/skills --list
npx github:preinpost/skills -g --force
```

[vercel-labs/skills](https://github.com/vercel-labs/skills) CLI로도 설치할 수 있다: `npx skills add preinpost/skills`

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
