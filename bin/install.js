#!/usr/bin/env node
// Zero-dependency skill installer: npx github:preinpost/skills [skill...] [options]
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const crypto = require("crypto");
const { spawnSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const PUBLIC_REPO = "preinpost/skills";
const PRIVATE_REPO = process.env.SKILLS_PRIVATE_REPO || "preinpost/skills-private";
const LEGACY_META = ".skill-meta.json";
const SOURCE_FILE = ".ms-skills-source.json";
const IGNORE = /(__pycache__|\.pyc$|\.DS_Store$)/;
// 프로젝트(로컬)와 전역(~) 경로가 다른 에이전트는 { local, global } 객체로 적는다.
const TARGETS = {
  claude: ".claude/skills",
  agents: ".agents/skills",
  pi: ".pi/agent/skills",
  antigravity: { local: ".agents/skills", global: ".gemini/config/skills" },
};

function targetRel(agent, global) {
  const t = TARGETS[agent];
  return typeof t === "string" ? t : global ? t.global : t.local;
}

function allTargetRels() {
  return [...new Set(Object.values(TARGETS).flatMap((t) => (typeof t === "string" ? [t] : [t.local, t.global])))];
}

function targetDirs(base, global, agents) {
  return [...new Set(agents.map((a) => path.resolve(base, targetRel(a, global))))];
}

// update/sync/remove/list가 찾는 (base, global) 쌍. 같은 곳을 두 번 보지 않게 realpath로 중복만 거른다.
function scopes(opts) {
  const real = (p) => fs.realpathSync(p);
  if (opts.global) return [{ base: os.homedir(), global: true }];
  if (opts.explicitAgents) return [{ base: process.cwd(), global: false }];
  if (real(process.cwd()) === real(os.homedir())) return [{ base: os.homedir(), global: true }];
  return [
    { base: process.cwd(), global: false },
    { base: os.homedir(), global: true },
  ];
}

const HELP = `Usage: npx github:preinpost/skills [skill...] [options]
       npx github:preinpost/skills update [skill...] [options]
       npx github:preinpost/skills sync [skill...] [options]
       npx github:preinpost/skills remove <skill|path...> [options]
       npx github:preinpost/skills list [skill...] [options]

Commands:
  update               설치된 스킬 중 내용(hash)이 바뀐 것만 업데이트
                       (-g/-a를 안 주면 현재 디렉터리와 ~ 의 ${Object.keys(TARGETS).join("/")} 를 모두 찾음)
  sync                 설치본을 직접 고친 스킬을 원본 레포에 커밋·푸시하고
                       같은 스킬의 다른 설치 사본에도 반영 (찾는 범위는 update와 같음)
  remove               로컬 스킬 디렉터리를 지우고 레지스트리 항목도 뺌 (원본 레포는 건드리지 않음)
                       (이름이면 update와 같은 범위에서 찾고, 사본이 여럿이면 TUI로 고름.
                        경로를 주면 그 사본만 바로 지움)
  list                 이 설치기로 설치한 스킬과 위치를 표시 (찾는 범위는 update와 같음)

Options:
  -g, --global         홈 디렉터리(~)에 설치 (기본: 현재 디렉터리)
  -a, --agent <name>   설치 대상: ${Object.keys(TARGETS).join(", ")}, all (반복 가능, 기본: claude,agents)
  -l, --list           설치 가능한 스킬 목록 (설치된 목록은 list 명령)
  -f, --force          이미 있는 스킬 무조건 덮어쓰기 (로컬 수정 포함), remove에서는 로컬 수정본도 삭제
  -c, --check          update/sync/remove에서 바꾸지 않고 상태만 표시
  -m, --message <msg>  sync 커밋 메시지 (기본: "sync: <스킬들> (<호스트명>)")
  -v, --verbose        update에서 최신인 스킬도 사본별로 펼쳐 표시
  -y, --yes            TUI 없이 기본값으로 설치 (remove는 찾은 사본을 고르지 않고 모두 삭제)
      --no-private     비공개 레포(${PRIVATE_REPO})를 받지 않음
  -h, --help           도움말

설치·업데이트는 이 설치기가 관리하는 스킬의 hash·출처·설치·갱신 시각을
<base>/.ms-skills-source.json 한 파일에 기록한다(base는 전역이면 ~, 아니면 현재 디렉터리).
항목의 installedAt 은 최초 설치 시각, updatedAt 은 마지막으로 내용을 덮어쓴 시각이다.
스킬 폴더에는 메타 파일을 만들지 않으며, 예전 .skill-meta.json 은 로컬 수정 판별용으로만 읽는다.
다른 도구로 설치한 스킬은 이 파일에 나오지 않는다.

Examples:
  npx github:preinpost/skills                     # TUI로 스킬·위치 선택
  npx github:preinpost/skills -y                  # 모든 스킬을 ./.claude/skills, ./.agents/skills 에
  npx github:preinpost/skills orchestrator -g     # ~/.claude/skills, ~/.agents/skills 에
  npx github:preinpost/skills -a pi -g            # ~/.pi/agent/skills 에
  npx github:preinpost/skills -a antigravity -g   # ~/.gemini/config/skills 에 (프로젝트는 ./.agents/skills)
  npx github:preinpost/skills update              # 바뀐 스킬만 업데이트
  npx github:preinpost/skills update --check      # 업데이트할 것만 확인
  npx github:preinpost/skills sync                # 로컬에서 고친 스킬을 git에 커밋·푸시
  npx github:preinpost/skills sync --check        # 푸시할 것만 확인
  npx github:preinpost/skills remove ko-article-html            # 사본이 여럿이면 골라서 삭제
  npx github:preinpost/skills remove ~/.pi/agent/skills/ko-article-html  # 그 사본만 삭제
  npx github:preinpost/skills remove ko-article-html --check    # 지울 대상만 확인
  npx github:preinpost/skills list                # 설치된 스킬 목록`;

// Shallow-clone the private repo into a temp dir. Returns null without prompting if there is no access.
function fetchPrivate() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "skills-private-"));
  process.on("exit", () => fs.rmSync(dir, { recursive: true, force: true }));
  const env = { ...process.env, GIT_TERMINAL_PROMPT: "0", GCM_INTERACTIVE: "never", GIT_SSH_COMMAND: "ssh -o BatchMode=yes" };
  for (const url of [`https://github.com/${PRIVATE_REPO}.git`, `git@github.com:${PRIVATE_REPO}.git`]) {
    const r = spawnSync("git", ["clone", "-q", "--depth", "1", url, dir], { env, stdio: "ignore", timeout: 30000 });
    if (r.status === 0) return dir;
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir);
  }
  return null;
}

// name -> { dir, private }. Private skills win on name clashes.
function listSkills(roots) {
  const skills = new Map();
  for (const { root, private: priv } of roots) {
    for (const d of fs.readdirSync(root, { withFileTypes: true })) {
      if (d.isDirectory() && fs.existsSync(path.join(root, d.name, "SKILL.md"))) {
        skills.set(d.name, { dir: path.join(root, d.name), private: priv });
      }
    }
  }
  return new Map([...skills].sort(([a, x], [b, y]) => x.private - y.private || a.localeCompare(b)));
}

// Content hash of a skill dir: sorted relative paths + file bytes, ignoring build junk and our meta file.
function hashDir(dir) {
  const h = crypto.createHash("sha256");
  const walk = (d) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true }).sort((a, b) => (a.name < b.name ? -1 : 1))) {
      const p = path.join(d, e.name);
      if (IGNORE.test(p) || (d === dir && e.name === LEGACY_META)) continue;
      if (e.isDirectory()) walk(p);
      else if (e.isFile()) h.update(`${path.relative(dir, p).split(path.sep).join("/")}\0`).update(fs.readFileSync(p)).update("\0");
    }
  };
  walk(dir);
  return h.digest("hex").slice(0, 12);
}

// 구버전 설치기가 스킬 폴더에 남긴 메타. 새 버전은 읽기만 하고 다시 쓰지 않는다.
function readLegacyMeta(dest) {
  try {
    return JSON.parse(fs.readFileSync(path.join(dest, LEGACY_META), "utf8"));
  } catch {
    return null;
  }
}

function gitUrl(repo) {
  return `git@github.com:${repo}.git`;
}

// 스킬 폴더에는 메타 파일을 쓰지 않는다. 레지스트리 갱신은 호출 측(installSkill)이 맡는다.
function copySkill(skill, dest) {
  fs.rmSync(dest, { recursive: true, force: true });
  fs.cpSync(skill.dir, dest, { recursive: true, filter: (src) => !IGNORE.test(src) });
}

// 홈 아래 경로를 ~로 축약한다. 레지스트리의 dir 표기에 쓴다.
function tilde(p) {
  const home = os.homedir();
  return p === home ? "~" : p.startsWith(home + path.sep) ? `~${p.slice(home.length)}` : p;
}

// 레지스트리에 적힌 ~ 경로를 현재 홈 기준 절대 경로로 되돌린다.
function expandTilde(p) {
  const home = os.homedir();
  if (p === "~") return home;
  if (p.startsWith("~/") || p.startsWith(`~${path.sep}`)) return path.join(home, p.slice(2));
  return p;
}

// <base>/.ms-skills-source.json 한 파일이 그 base 아래 모든 위치의 스킬을 담는다.
// base는 전역이면 홈, 프로젝트 설치면 현재 디렉터리다. `ms-` 접두사는 사용자 본인이 관리하는 파일임을 표시한다.
function loadRegistry(base) {
  const file = path.join(base, SOURCE_FILE);
  const skills = new Map();
  try {
    const data = JSON.parse(fs.readFileSync(file, "utf8"));
    for (const entry of Array.isArray(data.skills) ? data.skills : []) {
      if (typeof entry?.dir !== "string" || typeof entry.hash !== "string") continue;
      const dir = path.resolve(expandTilde(entry.dir));
      skills.set(dir, {
        name: entry.name,
        dir,
        hash: entry.hash,
        source: entry.source,
        sourceUrl: entry.sourceUrl,
        installedAt: entry.installedAt,
        updatedAt: entry.updatedAt ?? entry.installedAt,
      });
    }
  } catch {
    // 파일이 없거나 깨졌으면 빈 레지스트리로 시작한다.
  }
  return { file, skills };
}

function putEntry(registry, name, dest, hash, skill, installedAt, updatedAt) {
  const dir = path.resolve(dest);
  const source = skill.private ? PRIVATE_REPO : PUBLIC_REPO;
  const stamp = new Date().toISOString();
  const first = installedAt || stamp;
  registry.skills.set(dir, {
    name,
    dir,
    hash,
    source,
    sourceUrl: gitUrl(source),
    installedAt: first,
    updatedAt: updatedAt || first,
  });
}

// 실행 중 메모리에서 갱신한 레지스트리를 한 번만 쓴다. --check 호출부는 이 함수를 부르지 않는다.
function saveRegistry(registry) {
  const skills = [...registry.skills.values()]
    .filter((s) => fs.existsSync(s.dir))
    .map((s) => ({
      name: s.name,
      dir: tilde(s.dir),
      hash: s.hash,
      source: s.source,
      sourceUrl: s.sourceUrl,
      installedAt: s.installedAt,
      updatedAt: s.updatedAt || s.installedAt,
    }))
    .sort((a, b) => a.dir.localeCompare(b.dir));
  // 기록할 것도 없고 기존 파일도 없으면 빈 디렉터리만 만들지 않는다.
  if (!skills.length && !fs.existsSync(registry.file)) return;
  const data = { updatedAt: new Date().toISOString() };
  // 실제 체크아웃에서 실행할 때만 repoPath를 남긴다. npx는 임시 클론이라 의미가 없다.
  if (fs.existsSync(path.join(ROOT, ".git"))) data.repoPath = ROOT;
  data.skills = skills;
  fs.mkdirSync(path.dirname(registry.file), { recursive: true });
  fs.writeFileSync(registry.file, JSON.stringify(data, null, 2) + "\n");
}

// mode: "update" (바뀐 것만, 로컬 수정은 보호) | "force" | "skip". check=true면 상태만 보고.
// 기존 hash는 레지스트리에서 읽고, 항목이 없으면 구버전 .skill-meta.json을 fallback으로 쓴다.
// 원본과 같으면 최신, 저장된 hash와 현재 hash가 다르면 로컬 수정으로 보고 건너뛴다. 그 외에는 덮어쓴다.
function installSkill(name, skill, dest, { mode, check = false, registry }) {
  const src = hashDir(skill.dir);
  const entry = registry.skills.get(path.resolve(dest));
  const legacy = entry ? null : readLegacyMeta(dest);
  const savedHash = entry?.hash ?? legacy?.hash;
  const installedAt = entry?.installedAt ?? legacy?.installedAt;
  const updatedAt = entry?.updatedAt ?? legacy?.updatedAt ?? legacy?.installedAt;
  const res = (state, extra = {}) => ({ name, skill, dest, src, state, ...extra });
  // copied=true는 내용을 실제로 복사한 경우다. 그때만 updatedAt을 now로 올린다.
  const record = (hash, copied = false) => {
    if (check) return;
    const stamp = copied ? new Date().toISOString() : null;
    putEntry(registry, name, dest, hash, skill, installedAt || stamp, stamp || updatedAt);
  };
  if (!fs.existsSync(dest)) {
    if (check) return res("missing");
    copySkill(skill, dest);
    record(src, true);
    return res("installed");
  }
  if (mode === "skip") return res("skipped");
  const cur = hashDir(dest);
  if (mode !== "force") {
    if (cur === src) {
      if (entry || legacy) record(src); // hash만 갱신하거나 구버전 meta를 레지스트리로 옮긴다
      return res("latest");
    }
    if (savedHash && savedHash !== cur) return res("modified", { cur });
  }
  const from = savedHash || cur;
  if (check) return res("outdated", { from });
  copySkill(skill, dest);
  record(src, true);
  return res("updated", { from });
}

// 설치 위치(dest)의 하네스 이름. .agents/skills 처럼 여럿이 공유하는 경로는 먼저 나온 이름을 쓴다.
function agentOf(dest) {
  const parent = path.dirname(dest);
  for (const [agent, t] of Object.entries(TARGETS)) {
    for (const rel of typeof t === "string" ? [t] : [t.local, t.global]) {
      if (parent.endsWith(path.sep + path.normalize(rel))) return agent;
    }
  }
  return "?";
}

// 표시용 경로: 현재 디렉터리 아래면 ./, 홈 아래면 ~
function shortPath(p) {
  const cwd = process.cwd();
  if (cwd !== os.homedir() && p.startsWith(cwd + path.sep)) return `.${p.slice(cwd.length)}`;
  return tilde(p);
}

// 상태별 기호·심각도·설명. 스킬 전체 상태는 사본 중 가장 심각한 것으로 정한다.
const STATES = {
  latest: { mark: "=", rank: 0 },
  skipped: { mark: "-", rank: 1, note: "이미 있음, 건너뜀" },
  installed: { mark: "✓", rank: 2, note: "설치함" },
  updated: { mark: "↑", rank: 3, note: (r) => `${r.from} → ${r.src}` },
  outdated: { mark: "↑", rank: 4, note: (r) => `${r.from} → ${r.src}, 업데이트 가능` },
  missing: { mark: "+", rank: 5, note: "미설치" },
  modified: { mark: "!", rank: 6, note: "로컬에서 수정됨" },
};

// installSkill 결과를 스킬별로 묶어 출력한다. 모든 사본이 최신이면 한 줄로 접는다(verbose면 펼침).
function report(results, { verbose = false } = {}) {
  const byName = new Map();
  for (const r of results) {
    if (!byName.has(r.name)) byName.set(r.name, []);
    byName.get(r.name).push(r);
  }
  const width = Math.max(0, ...[...byName.keys()].map((n) => n.length));
  const agentWidth = Math.max(0, ...results.map((r) => agentOf(r.dest).length));
  const hints = new Set();
  for (const [name, list] of byName) {
    const worst = list.reduce((a, b) => (STATES[b.state].rank > STATES[a.state].rank ? b : a));
    const lock = list[0].skill.private ? " 🔒" : "";
    const where = list.map((r) => agentOf(r.dest)).join(", ");
    const head = `${STATES[worst.state].mark} ${name.padEnd(width)}  ${list[0].src}  (${where})${lock}`;
    console.log(head);
    const uniform = list.every((r) => r.state === worst.state);
    if (uniform && worst.state === "latest" && !verbose) continue;
    for (const r of list) {
      const st = STATES[r.state];
      const note = typeof st.note === "function" ? st.note(r) : st.note;
      console.log(`    ${st.mark} ${agentOf(r.dest).padEnd(agentWidth)}  ${shortPath(r.dest)}${note ? `  ${note}` : ""}`);
    }
    if (list.some((r) => r.state === "modified")) hints.add(`${name}: 로컬 수정 있음 → \`sync\`로 올려 다른 사본에도 전파, 또는 \`update --force\`로 덮어쓰기`);
    if (list.some((r) => r.state === "outdated")) hints.add(`${name}: 원본이 바뀜 → \`update\``);
  }
  if (hints.size) {
    console.log();
    for (const h of hints) console.log(`→ ${h}`);
  }
}

function label(name, skill) {
  return skill.private ? `🔒 ${name}` : name;
}

function describe(skill) {
  const text = fs.readFileSync(path.join(skill.dir, "SKILL.md"), "utf8");
  const m = text.match(/^description:\s*['"]?(.*?)['"]?\s*$/m);
  return m ? m[1] : "";
}

function parseArgs(argv) {
  const opts = { skills: [], agents: [], global: false, force: false, list: false, help: false, yes: false, private: true, check: false };
  if (["update", "sync", "remove", "list"].includes(argv[0])) opts.command = argv.shift();
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-g" || a === "--global") opts.global = true;
    else if (a === "-f" || a === "--force") opts.force = true;
    else if (a === "-l" || a === "--list") opts.list = true;
    else if (a === "-c" || a === "--check") opts.check = true;
    else if (a === "-y" || a === "--yes") opts.yes = true;
    else if (a === "-v" || a === "--verbose") opts.verbose = true;
    else if (a === "-h" || a === "--help") opts.help = true;
    else if (a === "--no-private") opts.private = false;
    else if (a === "-m" || a === "--message") opts.message = argv[++i];
    else if (a === "-a" || a === "--agent") opts.agents.push(...String(argv[++i] || "").split(","));
    else if (a.startsWith("-")) throw new Error(`알 수 없는 옵션: ${a}`);
    else opts.skills.push(a);
  }
  opts.interactive = !opts.command && argv.length === 0 && process.stdin.isTTY && process.stdout.isTTY;
  opts.explicitAgents = opts.agents.length > 0;
  if (opts.agents.includes("all")) opts.agents = Object.keys(TARGETS);
  if (opts.agents.length === 0) opts.agents = ["claude", "agents"];
  for (const a of opts.agents) if (!TARGETS[a]) throw new Error(`알 수 없는 agent: ${a}`);
  return opts;
}

// Minimal arrow-key picker. multi: space toggles, enter confirms. Resolves to selected indices.
// pickCursor: multi에서 아무것도 체크하지 않고 enter를 누르면 커서가 있는 항목 하나를 고른다.
function select(question, items, { multi = false, checked = [], allowEmpty = false, pickCursor = false } = {}) {
  return new Promise((resolve) => {
    const out = process.stdout;
    const on = new Set(checked);
    let cur = 0;
    let lines = 0;
    let error = "";
    const hint = multi ? "↑↓ 이동 · space 선택 · a 전체 · enter 확인" : "↑↓ 이동 · enter 확인";
    const render = () => {
      if (lines) out.write(`\x1b[${lines}A\x1b[0J`);
      const rows = [`\x1b[1m? ${question}\x1b[0m \x1b[2m(${hint})\x1b[0m`];
      items.forEach((it, i) => {
        const pointer = i === cur ? "\x1b[36m❯\x1b[0m" : " ";
        const box = multi ? (on.has(i) ? "\x1b[32m◉\x1b[0m " : "◯ ") : "";
        const label = i === cur ? `\x1b[36m${it.label}\x1b[0m` : it.label;
        rows.push(`${pointer} ${box}${label}${it.hint ? ` \x1b[2m${it.hint}\x1b[0m` : ""}`);
      });
      if (error) rows.push(`\x1b[31m${error}\x1b[0m`);
      out.write(rows.join("\n") + "\n");
      lines = rows.length;
    };
    const done = (result) => {
      process.stdin.off("keypress", onKey);
      process.stdin.setRawMode(false);
      process.stdin.pause();
      out.write(`\x1b[${lines}A\x1b[0J`);
      const shown = result.map((i) => items[i].label).join(", ") || "없음";
      out.write(`\x1b[32m✔\x1b[0m \x1b[1m${question}\x1b[0m \x1b[36m${shown}\x1b[0m\n`);
      resolve(result);
    };
    const onKey = (_, key = {}) => {
      error = "";
      if (key.ctrl && key.name === "c") {
        process.stdin.setRawMode(false);
        out.write("\n");
        process.exit(130);
      }
      if (key.name === "up" || key.name === "k") cur = (cur - 1 + items.length) % items.length;
      else if (key.name === "down" || key.name === "j") cur = (cur + 1) % items.length;
      else if (multi && key.name === "space") on.has(cur) ? on.delete(cur) : on.add(cur);
      else if (multi && key.name === "a") {
        if (on.size === items.length) on.clear();
        else items.forEach((_, i) => on.add(i));
      } else if (key.name === "return") {
        if (!multi) return done([cur]);
        if (!on.size && pickCursor) return done([cur]);
        if (on.size || allowEmpty) return done([...on].sort((a, b) => a - b));
        error = "하나 이상 선택하세요";
      }
      render();
    };
    readline.emitKeypressEvents(process.stdin);
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.on("keypress", onKey);
    render();
  });
}

async function prompt(opts, available) {
  // Public and private skills are picked in separate steps; either step may be left empty.
  opts.skills = [];
  for (const priv of [false, true]) {
    const names = [...available].filter(([, s]) => s.private === priv).map(([n]) => n);
    if (!names.length) continue;
    const idx = await select(
      priv ? "설치할 비공개 스킬" : "설치할 공개 스킬",
      names.map((n) => ({ label: label(n, available.get(n)) })),
      { multi: true, allowEmpty: true },
    );
    opts.skills.push(...idx.map((i) => names[i]));
  }
  if (!opts.skills.length) {
    console.log("선택한 스킬이 없습니다.");
    process.exit(0);
  }

  const [scope] = await select("설치 범위", [
    { label: "프로젝트", hint: process.cwd() },
    { label: "전역", hint: os.homedir() },
  ]);
  opts.global = scope === 1;

  const base = opts.global ? "~" : ".";
  const agents = Object.keys(TARGETS);
  const agentIdx = await select(
    "설치 위치",
    agents.map((n) => ({ label: n, hint: `${base}/${targetRel(n, opts.global)}` })),
    { multi: true },
  );
  opts.agents = agentIdx.map((i) => agents[i]);

  const exists = targetDirs(opts.global ? os.homedir() : process.cwd(), opts.global, opts.agents).some((dir) =>
    opts.skills.some((s) => fs.existsSync(path.join(dir, s))),
  );
  if (exists) {
    const [ow] = await select("이미 설치된 스킬이 있습니다", [
      { label: "바뀐 것만 업데이트", hint: "hash 비교, 로컬 수정은 보호" },
      { label: "덮어쓰기" },
      { label: "건너뛰기" },
    ]);
    opts.mode = ["update", "force", "skip"][ow];
  }
  console.log();
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) return console.log(HELP);
  // remove는 원본 레포가 필요 없다. 레포에서 빠진 스킬도 지울 수 있게 비공개 레포도 받지 않는다.
  if (opts.command === "remove") return remove(opts);
  if (opts.command === "list") return listInstalled(opts);
  const roots = [{ root: ROOT, private: false }];
  const privateRoot = opts.private && fetchPrivate();
  if (privateRoot) roots.push({ root: privateRoot, private: true });
  const available = listSkills(roots);
  if (opts.list) {
    for (const [n, s] of available) console.log(`${label(n, s)}\n  ${describe(s).slice(0, 120)}`);
    return;
  }

  if (opts.command === "update") return update(opts, available);
  if (opts.command === "sync") return sync(opts, available);
  if (opts.interactive && !opts.yes) await prompt(opts, available);
  const mode = opts.mode || (opts.force ? "force" : "update");

  const skills = opts.skills.length ? opts.skills : [...available.keys()];
  const missing = skills.filter((s) => !available.has(s));
  if (missing.length) throw new Error(`없는 스킬: ${missing.join(", ")} (목록: ${[...available.keys()].join(", ")})`);

  const base = opts.global ? os.homedir() : process.cwd();
  const registry = loadRegistry(base);
  const results = [];
  for (const dir of targetDirs(base, opts.global, opts.agents)) {
    fs.mkdirSync(dir, { recursive: true });
    for (const skill of skills) {
      results.push(installSkill(skill, available.get(skill), path.join(dir, skill), { mode, registry }));
    }
  }
  if (!opts.check) saveRegistry(registry);
  // 설치 결과는 접지 않고 모두 펼쳐서 보여준다.
  report(results, { verbose: true });
}

// Find installed copies of known skills and refresh the ones whose hash differs from the source.
function update(opts, available) {
  const agents = opts.explicitAgents ? opts.agents : Object.keys(TARGETS);
  const missing = opts.skills.filter((s) => !available.has(s));
  if (missing.length) throw new Error(`없는 스킬: ${missing.join(", ")}`);
  const results = [];
  for (const { base, global } of scopes(opts)) {
    const registry = loadRegistry(base);
    for (const dir of targetDirs(base, global, agents)) {
      if (!fs.existsSync(dir)) continue;
      for (const name of fs.readdirSync(dir).sort()) {
        if (!available.has(name) || (opts.skills.length && !opts.skills.includes(name))) continue;
        results.push(installSkill(name, available.get(name), path.join(dir, name), {
          mode: opts.force ? "force" : "update",
          check: opts.check,
          registry,
        }));
      }
    }
    if (!opts.check) saveRegistry(registry);
  }
  if (!results.length) return console.log("업데이트할 설치된 스킬이 없습니다.");
  report(results, { verbose: opts.verbose });
}

function git(cwd, args, opts = {}) {
  const r = spawnSync("git", args, { cwd, encoding: "utf8", ...opts });
  if (r.status !== 0) throw new Error(`git ${args.join(" ")} 실패\n${(r.stderr || r.stdout || "").trim()}`);
  return (r.stdout || "").trim();
}

// 푸시할 수 있게 원본 레포를 임시 디렉터리에 클론한다. SSH를 먼저, 안 되면 HTTPS(gh 자격 증명)를 쓴다.
function cloneForPush(repo) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "skills-sync-"));
  process.on("exit", () => fs.rmSync(dir, { recursive: true, force: true }));
  const env = { ...process.env, GIT_TERMINAL_PROMPT: "0", GIT_SSH_COMMAND: "ssh -o BatchMode=yes" };
  for (const url of [gitUrl(repo), `https://github.com/${repo}.git`]) {
    const r = spawnSync("git", ["clone", "-q", "--depth", "1", url, dir], { env, stdio: "ignore", timeout: 60000 });
    if (r.status === 0) return dir;
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir);
  }
  throw new Error(`${repo} 를 클론할 수 없습니다 (SSH 키 또는 gh auth login 확인)`);
}

// 설치본 중 레지스트리 hash와 현재 내용이 다른(=로컬에서 고친) 스킬을 원본 레포에 커밋·푸시한다.
// 원본도 설치 이후 바뀌었으면 양쪽 수정이므로 --force 없이는 건너뛴다.
// 푸시 후에는 같은 스킬의 다른 설치 사본도 새 내용으로 맞추고 레지스트리 hash를 갱신한다.
function sync(opts, available) {
  const agents = opts.explicitAgents ? opts.agents : Object.keys(TARGETS);
  const missing = opts.skills.filter((s) => !available.has(s));
  if (missing.length) throw new Error(`없는 스킬: ${missing.join(", ")}`);

  // name -> [{ dest, registry, saved, cur }]
  const copies = new Map();
  const registries = [];
  for (const { base, global } of scopes(opts)) {
    const registry = loadRegistry(base);
    registries.push(registry);
    for (const dir of targetDirs(base, global, agents)) {
      if (!fs.existsSync(dir)) continue;
      for (const name of fs.readdirSync(dir).sort()) {
        if (!available.has(name) || (opts.skills.length && !opts.skills.includes(name))) continue;
        const dest = path.join(dir, name);
        const entry = registry.skills.get(path.resolve(dest));
        const saved = entry?.hash ?? readLegacyMeta(dest)?.hash;
        if (!copies.has(name)) copies.set(name, []);
        copies.get(name).push({ dest, registry, entry, saved, cur: hashDir(dest) });
      }
    }
  }

  // 레포별로 반영할 스킬을 모은다: repo -> [{ name, skill, from, list }]
  const plans = new Map();
  for (const [name, list] of copies) {
    const skill = available.get(name);
    const src = hashDir(skill.dir);
    const edited = list.filter((c) => c.saved && c.cur !== c.saved && c.cur !== src);
    if (!edited.length) continue;
    const variants = new Set(edited.map((c) => c.cur));
    if (variants.size > 1) {
      console.log(`! ${name}: 사본들이 서로 다르게 수정됨, 건너뜀`);
      for (const c of edited) console.log(`    ${agentOf(c.dest)}  ${shortPath(c.dest)}  (${c.cur})`);
      continue;
    }
    const from = edited[0];
    if (from.saved !== src && !opts.force) {
      console.log(`! ${name}: 원본도 설치 이후 바뀜 (${from.saved} → ${src}), --force로 로컬 내용으로 덮어쓰기`);
      continue;
    }
    const repo = skill.private ? PRIVATE_REPO : PUBLIC_REPO;
    console.log(`↑ ${name}${skill.private ? " 🔒" : ""}  ${src} → ${from.cur}`);
    const others = list.filter((c) => c.cur !== from.cur);
    const w = Math.max(...[from, ...others].map((c) => agentOf(c.dest).length));
    console.log(`    출처  ${agentOf(from.dest).padEnd(w)}  ${shortPath(from.dest)}`);
    others.forEach((c, i) => console.log(`    ${i ? "    " : "전파"}  ${agentOf(c.dest).padEnd(w)}  ${shortPath(c.dest)}`));
    if (!plans.has(repo)) plans.set(repo, []);
    plans.get(repo).push({ name, skill, from, list });
  }
  if (!plans.size) return console.log("커밋할 로컬 수정이 없습니다.");
  if (opts.check) return;

  for (const [repo, items] of plans) {
    const dir = cloneForPush(repo);
    for (const { name, from } of items) copySkill({ dir: from.dest }, path.join(dir, name));
    git(dir, ["add", "-A", ...items.map((i) => i.name)]);
    if (!git(dir, ["status", "--porcelain"])) {
      console.log(`= ${repo}: 원격과 같아 커밋할 것이 없음`);
    } else {
      const msg = opts.message || `sync: ${items.map((i) => i.name).join(", ")} (${os.hostname()})`;
      git(dir, ["commit", "-q", "-m", msg]);
      git(dir, ["push", "-q", "origin", "HEAD"], { stdio: ["ignore", "pipe", "pipe"] });
      console.log(`✓ ${repo}: ${git(dir, ["log", "-1", "--format=%h %s"])}`);
    }
    // 푸시한 내용을 기준으로 다른 사본을 맞추고 hash를 기록한다.
    for (const { name, list } of items) {
      const pushed = { dir: path.join(dir, name), private: available.get(name).private };
      const hash = hashDir(pushed.dir);
      for (const c of list) {
        let copied = false;
        if (c.cur !== hash) {
          copySkill(pushed, c.dest);
          copied = true;
          console.log(`  → ${agentOf(c.dest)}  ${shortPath(c.dest)}`);
        }
        const stamp = new Date().toISOString();
        putEntry(c.registry, name, c.dest, hash, pushed, c.entry?.installedAt || stamp, copied ? stamp : c.entry?.updatedAt);
      }
    }
  }
  for (const registry of registries) saveRegistry(registry);
}

// 레지스트리(또는 구버전 meta)에 기록된 사본만 지운다. 다른 도구로 설치한 폴더는 건드리지 않는다.
// 로컬에서 수정된 사본은 sync 안 한 변경이 날아갈 수 있어 --force 없이는 건너뛴다.
async function remove(opts) {
  if (!opts.skills.length) throw new Error("지울 스킬 이름을 지정하세요 (예: remove ko-article-html)");
  const scopeList = scopes(opts);
  const agents = opts.explicitAgents ? opts.agents : Object.keys(TARGETS);

  // 경로 인자(/ 포함)는 그 사본 하나, 이름 인자는 찾는 범위의 모든 위치가 후보다.
  // 경로 사본의 레지스트리는 <base>/<target>/<name> 에서 base를 거꾸로 구한다.
  const candidates = [];
  const registries = new Map();
  const registryOf = (base) => registries.get(base) || registries.set(base, loadRegistry(base)).get(base);
  const rels = allTargetRels();
  for (const arg of opts.skills) {
    if (arg.includes("/") || arg.includes(path.sep)) {
      const dest = path.resolve(expandTilde(arg));
      const target = rels.find((t) => path.dirname(dest).endsWith(path.sep + path.normalize(t)));
      if (!target) throw new Error(`스킬 설치 위치가 아닙니다: ${arg} (${rels.join(", ")} 아래 경로)`);
      if (!fs.existsSync(dest)) throw new Error(`없는 경로: ${arg}`);
      candidates.push({ name: path.basename(dest), dest, registry: registryOf(path.dirname(dest).slice(0, -path.normalize(target).length - 1)) });
      continue;
    }
    for (const { base, global } of scopeList) for (const dir of targetDirs(base, global, agents)) {
      const dest = path.join(dir, arg);
      if (fs.existsSync(dest)) candidates.push({ name: arg, dest, registry: registryOf(base) });
    }
  }

  const targets = [];
  for (const { name, dest, registry } of candidates) {
    const entry = registry.skills.get(path.resolve(dest));
    const saved = entry?.hash ?? readLegacyMeta(dest)?.hash;
    if (!saved) {
      console.log(`- ${dest} (이 설치기로 설치한 기록 없음, 건너뜀)`);
      continue;
    }
    if (hashDir(dest) !== saved && !opts.force) {
      console.log(`! ${dest} (로컬에서 수정됨, sync하거나 --force로 삭제)`);
      continue;
    }
    targets.push({ name, dest, registry });
  }
  if (!targets.length) return console.log("지울 설치된 스킬이 없습니다.");
  if (opts.check) {
    for (const t of targets) console.log(`- ${t.dest} (삭제 예정)`);
    return;
  }

  // 사본이 하나면 묻지 않고 지운다. 여럿일 때만 고르게 한다.
  let picked = targets;
  if (!opts.yes && targets.length > 1) {
    if (!(process.stdin.isTTY && process.stdout.isTTY)) {
      for (const t of targets) console.log(`- ${t.dest}`);
      throw new Error("사본이 여럿입니다. 경로로 하나를 지정하거나, 모두 지우려면 -y를 붙이세요");
    }
    const idx = await select(
      "삭제할 사본",
      targets.map((t) => ({ label: tilde(t.dest) })),
      { multi: true, pickCursor: true },
    );
    picked = idx.map((i) => targets[i]);
  }

  for (const t of picked) {
    fs.rmSync(t.dest, { recursive: true, force: true });
    t.registry.skills.delete(path.resolve(t.dest));
    console.log(`✗ ${t.dest}`);
  }
  for (const registry of registries.values()) saveRegistry(registry);
}

// 레지스트리에 기록된 사본을 스킬 이름별로 묶어 보여준다. 원본 레포는 받지 않으므로
// 업데이트 여부는 알 수 없고, 기록된 hash와 비교한 로컬 수정·폴더 누락만 표시한다.
function listInstalled(opts) {
  const scopeList = scopes(opts);
  const agents = opts.explicitAgents ? opts.agents : Object.keys(TARGETS);
  const dirs = new Set(scopeList.flatMap(({ base, global }) => targetDirs(base, global, agents)));
  const byName = new Map();
  for (const { base } of scopeList) {
    for (const e of loadRegistry(base).skills.values()) {
      if (!dirs.has(path.dirname(e.dir)) || (opts.skills.length && !opts.skills.includes(e.name))) continue;
      if (!byName.has(e.name)) byName.set(e.name, []);
      byName.get(e.name).push(e);
    }
  }
  if (!byName.size) return console.log("설치된 스킬이 없습니다.");
  // 설치 TUI와 같이 공개 → 비공개 순, 그 안에서는 이름순.
  const isPrivate = (name) => byName.get(name)[0].source === PRIVATE_REPO;
  const names = [...byName.keys()].sort((a, b) => isPrivate(a) - isPrivate(b) || a.localeCompare(b));
  for (const [i, name] of names.entries()) {
    const list = byName.get(name);
    console.log(`${i + 1}. ${isPrivate(name) ? "🔒 " : ""}${name}`);
    for (const e of list.sort((a, b) => a.dir.localeCompare(b.dir))) {
      const state = !fs.existsSync(e.dir) ? "폴더 없음" : hashDir(e.dir) !== e.hash ? "로컬 수정됨" : e.hash;
      console.log(`   ${tilde(e.dir)}  (${state}, ${(e.updatedAt || "").slice(0, 10)})`);
    }
  }
}

main().catch((e) => {
  console.error(`error: ${e.message}\n\n${HELP}`);
  process.exit(1);
});
