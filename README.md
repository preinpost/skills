# skills

개인용 에이전트 스킬 모음. Pi(`~/.pi/agent/skills`), Claude Code, Codex 등에서 같은 형식(`SKILL.md` + `references/` + `scripts/`)으로 쓸 수 있게 관리한다.

## 목록

| 스킬 | 하는 일 | 대표 요청 |
|---|---|---|
| [`english-tutor-ko`](./english-tutor-ko) | 화상영어 준비·복습용 코치. 한국어 문장을 영어로 옮기고, 내 영어 문장을 첨삭해 반복되는 오류 패턴과 스스로 고치는 팁, 관련 어휘·연어·문장 틀까지 알려준다. 한국 고유 음식·장소·문화도 원어민에게 설명할 수 있게 풀어준다 | "이거 영어로 뭐라고 해?", "이 문장 맞아? 첨삭해줘" |
| [`ko-article-html`](./ko-article-html) | 웹 아티클을 빠짐없이 한국어로 번역하고, 원문 그림·애니메이션까지 담은 단일 HTML로 패키징한다 | "이 글 전체 번역해서 팀에 공유할 HTML로 만들어줘" |
| [`orchestrator`](./orchestrator) | 메인 에이전트는 사용자 의도 파악과 계획만 맡고, 구현·조사·테스트·리뷰는 반드시 서브에이전트에 위임한다. 스폰 전에 모델과 thinking effort를 묻는다 | "오케스트레이터로 진행해줘" |

## 설치

Node 18+만 있으면 된다. 별도 npm 배포 없이 GitHub에서 바로 실행한다.

```bash
# TUI로 스킬 · 범위(프로젝트/전역) · 위치(claude/agents/pi, 직접 체크) 선택
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

### 업데이트

설치·업데이트할 때 스킬 디렉터리 내용의 sha256 hash를 `<base>/.ms-skills-source.json`에 기록해 둔다. `base`는 전역 설치면 홈(`~`), 프로젝트 설치는 현재 디렉터리다. `update`는 이 hash와 레포의 현재 hash를 비교해서 바뀐 스킬만 다시 설치한다.

```bash
npx github:preinpost/skills update            # ./ 와 ~ 의 claude/agents/pi 전부 확인 후 바뀐 것만 업데이트
npx github:preinpost/skills update --check    # 확인만 (바꾸지 않음)
npx github:preinpost/skills update orchestrator -g
```

- `=` 최신 · `↑` 업데이트됨 · `!` 설치본을 로컬에서 직접 고쳐서 건너뜀 (`--force`로 덮어쓰기)
- 일반 설치도 기본 동작은 똑같다. 이미 있으면 바뀐 경우에만 덮어쓴다.

### 설치본에서 고친 스킬을 git에 반영 (sync)

설치된 스킬(`~/.claude/skills/...` 등)을 직접 고친 뒤 원본 레포에 바로 커밋·푸시한다. 다른 PC에서는 `update`로 받으면 된다.

```bash
npx github:preinpost/skills sync --check      # 푸시할 것만 확인
npx github:preinpost/skills sync              # 커밋·푸시 (🔒 스킬은 비공개 레포로)
npx github:preinpost/skills sync orchestrator -m "orchestrator: 규칙 추가"
```

- 레지스트리 hash와 현재 내용이 다른 스킬만 올린다. 푸시 후 같은 스킬의 다른 사본(claude/agents/pi)도 맞추고 hash를 갱신한다.
- 원본도 설치 이후 바뀌었으면(양쪽 수정) 건너뛴다. 먼저 `update`로 받거나 `--force`로 로컬 내용을 올린다.
- 같은 스킬의 사본들이 서로 다르게 수정됐으면 건너뛴다.
- 푸시 권한은 SSH 키 또는 `gh auth login`을 쓴다.

### 원본 저장소 안내

설치한 스킬의 hash·출처(`source`)·클론 URL(`sourceUrl`)·설치 시각(`installedAt`, `updatedAt`)은 `<base>/.ms-skills-source.json` 한 파일에 모아 기록한다. 이 파일 하나가 그 base 아래 세 위치(`.claude/skills`, `.agents/skills`, `.pi/agent/skills`)의 스킬을 모두 담는다. 실제 체크아웃에서 실행하면 `repoPath`도 함께 남는다. 스킬 폴더 안에는 메타 파일을 만들지 않으므로 원본 파일만 남는다.
항목의 `installedAt`은 최초 설치 시각, `updatedAt`은 마지막으로 내용을 덮어쓴 시각이며, 복사 없이 hash만 갱신할 때는 둘 다 바뀌지 않는다.
예전 버전이 스킬 폴더에 남긴 `<스킬>/.skill-meta.json`은 따로 지우지 않고, 레지스트리에 항목이 없을 때 로컬 수정 판별용 fallback으로만 읽는다. 이 설치기가 설치·갱신한 스킬만 기록하며, 다른 도구(예: `npx skills`)로 설치한 스킬은 이 파일에 나오지 않는다. 이 설치기는 `AGENTS.md`, `CLAUDE.md` 같은 사용자 소유 지침 파일은 쓰지 않는다. 스킬을 고칠 때는 레지스트리의 정보로 원본 저장소를 찾아 수정하고 커밋한 뒤 사본에 반영한다.

### 비공개 스킬

비공개 레포 [`preinpost/skills-private`](https://github.com/preinpost/skills-private)에 접근 권한이 있으면(`gh auth login` 또는 SSH 키) 같은 명령으로 그 레포의 스킬도 `🔒`로 함께 표시·설치된다. 권한이 없으면 묻지 않고 건너뛴다. 다른 레포를 쓰려면 `SKILLS_PRIVATE_REPO=owner/repo`, 끄려면 `--no-private`.

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
