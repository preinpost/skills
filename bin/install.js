#!/usr/bin/env node
// Zero-dependency skill installer: npx github:preinpost/skills [skill...] [options]
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");

const ROOT = path.resolve(__dirname, "..");
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
  -h, --help           도움말

Examples:
  npx github:preinpost/skills                     # TUI로 스킬·위치 선택
  npx github:preinpost/skills -y                  # 모든 스킬을 ./.claude/skills, ./.agents/skills 에
  npx github:preinpost/skills orchestrator -g     # ~/.claude/skills, ~/.agents/skills 에
  npx github:preinpost/skills -a pi -g            # ~/.pi/agent/skills 에`;

function listSkills() {
  return fs
    .readdirSync(ROOT, { withFileTypes: true })
    .filter((d) => d.isDirectory() && fs.existsSync(path.join(ROOT, d.name, "SKILL.md")))
    .map((d) => d.name)
    .sort();
}

function describe(name) {
  const text = fs.readFileSync(path.join(ROOT, name, "SKILL.md"), "utf8");
  const m = text.match(/^description:\s*['"]?(.*?)['"]?\s*$/m);
  return m ? m[1] : "";
}

function parseArgs(argv) {
  const opts = { skills: [], agents: [], global: false, force: false, list: false, help: false, yes: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-g" || a === "--global") opts.global = true;
    else if (a === "-f" || a === "--force") opts.force = true;
    else if (a === "-l" || a === "--list") opts.list = true;
    else if (a === "-y" || a === "--yes") opts.yes = true;
    else if (a === "-h" || a === "--help") opts.help = true;
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
function select(question, items, { multi = false, checked = [] } = {}) {
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
      const shown = result.map((i) => items[i].label).join(", ");
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
        if (on.size) return done([...on].sort((a, b) => a - b));
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
  const skillIdx = await select(
    "설치할 스킬",
    available.map((s) => ({ label: s })),
    { multi: true, checked: available.map((_, i) => i) },
  );
  opts.skills = skillIdx.map((i) => available[i]);

  const [scope] = await select("설치 범위", [
    { label: "프로젝트", hint: process.cwd() },
    { label: "전역", hint: os.homedir() },
  ]);
  opts.global = scope === 1;

  const base = opts.global ? "~" : ".";
  const names = Object.keys(TARGETS);
  const agentIdx = await select(
    "설치 위치",
    names.map((n) => ({ label: n, hint: `${base}/${TARGETS[n]}` })),
    { multi: true },
  );
  opts.agents = agentIdx.map((i) => names[i]);

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
  const available = listSkills();
  if (opts.help) return console.log(HELP);
  if (opts.list) {
    for (const s of available) console.log(`${s}\n  ${describe(s).slice(0, 120)}`);
    return;
  }

  if (opts.interactive && !opts.yes) await prompt(opts, available);

  const skills = opts.skills.length ? opts.skills : available;
  const missing = skills.filter((s) => !available.includes(s));
  if (missing.length) throw new Error(`없는 스킬: ${missing.join(", ")} (목록: ${available.join(", ")})`);

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
      fs.cpSync(path.join(ROOT, skill), dest, {
        recursive: true,
        filter: (src) => !/(__pycache__|\.pyc$|\.DS_Store$)/.test(src),
      });
      console.log(`✓ ${dest}`);
    }
  }
}

main().catch((e) => {
  console.error(`error: ${e.message}\n\n${HELP}`);
  process.exit(1);
});
