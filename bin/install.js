#!/usr/bin/env node
// Zero-dependency skill installer: npx github:preinpost/skills [skill...] [options]
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const { spawnSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const PRIVATE_REPO = process.env.SKILLS_PRIVATE_REPO || "preinpost/skills-private";
const TARGETS = {
  claude: ".claude/skills",
  agents: ".agents/skills",
  pi: ".pi/agent/skills",
};

const HELP = `Usage: npx github:preinpost/skills [skill...] [options]

Options:
  -g, --global         홈 디렉터리(~)에 설치 (기본: 현재 디렉터리)
  -a, --agent <name>   설치 대상: ${Object.keys(TARGETS).join(", ")}, all (반복 가능, 기본: claude,agents)
  -l, --list           설치 가능한 스킬 목록
  -f, --force          이미 있는 스킬 덮어쓰기
  -y, --yes            TUI 없이 기본값으로 설치
      --no-private     비공개 레포(${PRIVATE_REPO})를 받지 않음
  -h, --help           도움말

Examples:
  npx github:preinpost/skills                     # TUI로 스킬·위치 선택
  npx github:preinpost/skills -y                  # 모든 스킬을 ./.claude/skills, ./.agents/skills 에
  npx github:preinpost/skills orchestrator -g     # ~/.claude/skills, ~/.agents/skills 에
  npx github:preinpost/skills -a pi -g            # ~/.pi/agent/skills 에`;

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

function label(name, skill) {
  return skill.private ? `🔒 ${name}` : name;
}

function describe(skill) {
  const text = fs.readFileSync(path.join(skill.dir, "SKILL.md"), "utf8");
  const m = text.match(/^description:\s*['"]?(.*?)['"]?\s*$/m);
  return m ? m[1] : "";
}

function parseArgs(argv) {
  const opts = { skills: [], agents: [], global: false, force: false, list: false, help: false, yes: false, private: true };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-g" || a === "--global") opts.global = true;
    else if (a === "-f" || a === "--force") opts.force = true;
    else if (a === "-l" || a === "--list") opts.list = true;
    else if (a === "-y" || a === "--yes") opts.yes = true;
    else if (a === "-h" || a === "--help") opts.help = true;
    else if (a === "--no-private") opts.private = false;
    else if (a === "-a" || a === "--agent") opts.agents.push(...String(argv[++i] || "").split(","));
    else if (a.startsWith("-")) throw new Error(`알 수 없는 옵션: ${a}`);
    else opts.skills.push(a);
  }
  opts.interactive = argv.length === 0 && process.stdin.isTTY && process.stdout.isTTY;
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
    const [ow] = await select("이미 설치된 스킬이 있습니다", [{ label: "덮어쓰기" }, { label: "건너뛰기" }]);
    opts.force = ow === 0;
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

  if (opts.interactive && !opts.yes) await prompt(opts, available);

  const skills = opts.skills.length ? opts.skills : [...available.keys()];
  const missing = skills.filter((s) => !available.has(s));
  if (missing.length) throw new Error(`없는 스킬: ${missing.join(", ")} (목록: ${[...available.keys()].join(", ")})`);

  const base = opts.global ? os.homedir() : process.cwd();
  for (const agent of opts.agents) {
    const dir = path.join(base, TARGETS[agent]);
    fs.mkdirSync(dir, { recursive: true });
    for (const skill of skills) {
      const dest = path.join(dir, skill);
      if (fs.existsSync(dest)) {
        if (!opts.force) {
          console.log(`- skip  ${dest} (이미 있음, --force로 덮어쓰기)`);
          continue;
        }
        fs.rmSync(dest, { recursive: true, force: true });
      }
      fs.cpSync(available.get(skill).dir, dest, {
        recursive: true,
        filter: (src) => !/(__pycache__|\.pyc$|\.DS_Store$)/.test(src),
      });
      console.log(`✓ ${dest}${available.get(skill).private ? " 🔒" : ""}`);
    }
  }
}

main().catch((e) => {
  console.error(`error: ${e.message}\n\n${HELP}`);
  process.exit(1);
});
