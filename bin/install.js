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
const TARGETS = {
  claude: ".claude/skills",
  agents: ".agents/skills",
  pi: ".pi/agent/skills",
};

const HELP = `Usage: npx github:preinpost/skills [skill...] [options]
       npx github:preinpost/skills update [skill...] [options]

Commands:
  update               설치된 스킬 중 내용(hash)이 바뀐 것만 업데이트
                       (-g/-a를 안 주면 현재 디렉터리와 ~ 의 claude/agents/pi 를 모두 찾음)

Options:
  -g, --global         홈 디렉터리(~)에 설치 (기본: 현재 디렉터리)
  -a, --agent <name>   설치 대상: ${Object.keys(TARGETS).join(", ")}, all (반복 가능, 기본: claude,agents)
  -l, --list           설치 가능한 스킬 목록
  -f, --force          이미 있는 스킬 무조건 덮어쓰기 (로컬 수정 포함)
  -c, --check          update에서 바꾸지 않고 상태만 표시
  -y, --yes            TUI 없이 기본값으로 설치
      --no-private     비공개 레포(${PRIVATE_REPO})를 받지 않음
  -h, --help           도움말

설치·업데이트는 이 설치기가 관리하는 스킬의 hash·출처·설치 시각을
<base>/.ms-skills-source.json 한 파일에 기록한다(base는 전역이면 ~, 아니면 현재 디렉터리).
스킬 폴더에는 메타 파일을 만들지 않으며, 예전 .skill-meta.json 은 로컬 수정 판별용으로만 읽는다.
다른 도구로 설치한 스킬은 이 파일에 나오지 않는다.

Examples:
  npx github:preinpost/skills                     # TUI로 스킬·위치 선택
  npx github:preinpost/skills -y                  # 모든 스킬을 ./.claude/skills, ./.agents/skills 에
  npx github:preinpost/skills orchestrator -g     # ~/.claude/skills, ~/.agents/skills 에
  npx github:preinpost/skills -a pi -g            # ~/.pi/agent/skills 에
  npx github:preinpost/skills update              # 바뀐 스킬만 업데이트
  npx github:preinpost/skills update --check      # 업데이트할 것만 확인`;

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

// <base>/.ms-skills-source.json 한 파일이 그 base 아래 세 위치의 스킬을 모두 담는다.
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
      });
    }
  } catch {
    // 파일이 없거나 깨졌으면 빈 레지스트리로 시작한다.
  }
  return { file, skills };
}

function putEntry(registry, name, dest, hash, skill, installedAt) {
  const dir = path.resolve(dest);
  const source = skill.private ? PRIVATE_REPO : PUBLIC_REPO;
  registry.skills.set(dir, { name, dir, hash, source, sourceUrl: gitUrl(source), installedAt: installedAt || new Date().toISOString() });
}

// 실행 중 메모리에서 갱신한 레지스트리를 한 번만 쓴다. --check 호출부는 이 함수를 부르지 않는다.
function saveRegistry(registry) {
  const skills = [...registry.skills.values()]
    .filter((s) => fs.existsSync(s.dir))
    .map((s) => ({ name: s.name, dir: tilde(s.dir), hash: s.hash, source: s.source, sourceUrl: s.sourceUrl, installedAt: s.installedAt }))
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
  const lock = skill.private ? " 🔒" : "";
  const src = hashDir(skill.dir);
  const entry = registry.skills.get(path.resolve(dest));
  const legacy = entry ? null : readLegacyMeta(dest);
  const savedHash = entry?.hash ?? legacy?.hash;
  const installedAt = entry?.installedAt ?? legacy?.installedAt;
  const record = (hash) => {
    if (!check) putEntry(registry, name, dest, hash, skill, installedAt);
  };
  if (!fs.existsSync(dest)) {
    if (check) return console.log(`+ ${dest} (미설치)`);
    copySkill(skill, dest);
    record(src);
    return console.log(`✓ ${dest}${lock}`);
  }
  if (mode === "skip") return console.log(`- skip  ${dest} (이미 있음)`);
  const cur = hashDir(dest);
  if (mode !== "force") {
    if (cur === src) {
      if (entry || legacy) record(src); // hash만 갱신하거나 구버전 meta를 레지스트리로 옮긴다
      return console.log(`= ${dest} (최신 ${src})`);
    }
    if (savedHash && savedHash !== cur) {
      return console.log(`! ${dest} (로컬에서 수정됨, --force로 덮어쓰기)`);
    }
  }
  const from = savedHash || cur;
  if (check) return console.log(`↑ ${dest} (${from} → ${src}, 업데이트 가능)`);
  copySkill(skill, dest);
  record(src);
  console.log(`↑ ${dest}${lock} (${from} → ${src})`);
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
  if (argv[0] === "update") opts.command = argv.shift();
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-g" || a === "--global") opts.global = true;
    else if (a === "-f" || a === "--force") opts.force = true;
    else if (a === "-l" || a === "--list") opts.list = true;
    else if (a === "-c" || a === "--check") opts.check = true;
    else if (a === "-y" || a === "--yes") opts.yes = true;
    else if (a === "-h" || a === "--help") opts.help = true;
    else if (a === "--no-private") opts.private = false;
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
function select(question, items, { multi = false, checked = [], allowEmpty = false } = {}) {
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
      { multi: true, checked: names.map((_, i) => i), allowEmpty: true },
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
    agents.map((n) => ({ label: n, hint: `${base}/${TARGETS[n]}` })),
    { multi: true },
  );
  opts.agents = agentIdx.map((i) => agents[i]);

  const exists = opts.agents.some((a) =>
    opts.skills.some((s) => fs.existsSync(path.join(opts.global ? os.homedir() : process.cwd(), TARGETS[a], s))),
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
  const roots = [{ root: ROOT, private: false }];
  const privateRoot = opts.private && fetchPrivate();
  if (privateRoot) roots.push({ root: privateRoot, private: true });
  const available = listSkills(roots);
  if (opts.list) {
    for (const [n, s] of available) console.log(`${label(n, s)}\n  ${describe(s).slice(0, 120)}`);
    return;
  }

  if (opts.command === "update") return update(opts, available);
  if (opts.interactive && !opts.yes) await prompt(opts, available);
  const mode = opts.mode || (opts.force ? "force" : "update");

  const skills = opts.skills.length ? opts.skills : [...available.keys()];
  const missing = skills.filter((s) => !available.has(s));
  if (missing.length) throw new Error(`없는 스킬: ${missing.join(", ")} (목록: ${[...available.keys()].join(", ")})`);

  const base = opts.global ? os.homedir() : process.cwd();
  const registry = loadRegistry(base);
  for (const agent of opts.agents) {
    const dir = path.join(base, TARGETS[agent]);
    fs.mkdirSync(dir, { recursive: true });
    for (const skill of skills) {
      installSkill(skill, available.get(skill), path.join(dir, skill), { mode, registry });
    }
  }
  if (!opts.check) saveRegistry(registry);
}

// Find installed copies of known skills and refresh the ones whose hash differs from the source.
function update(opts, available) {
  const bases = opts.global ? [os.homedir()] : opts.explicitAgents ? [process.cwd()] : [...new Set([process.cwd(), os.homedir()])];
  const agents = opts.explicitAgents ? opts.agents : Object.keys(TARGETS);
  const missing = opts.skills.filter((s) => !available.has(s));
  if (missing.length) throw new Error(`없는 스킬: ${missing.join(", ")}`);
  let found = 0;
  for (const base of bases) {
    const registry = loadRegistry(base);
    for (const agent of agents) {
      const dir = path.join(base, TARGETS[agent]);
      if (!fs.existsSync(dir)) continue;
      for (const name of fs.readdirSync(dir).sort()) {
        if (!available.has(name) || (opts.skills.length && !opts.skills.includes(name))) continue;
        found++;
        installSkill(name, available.get(name), path.join(dir, name), {
          mode: opts.force ? "force" : "update",
          check: opts.check,
          registry,
        });
      }
    }
    if (!opts.check) saveRegistry(registry);
  }
  if (!found) console.log("업데이트할 설치된 스킬이 없습니다.");
}

main().catch((e) => {
  console.error(`error: ${e.message}\n\n${HELP}`);
  process.exit(1);
});
