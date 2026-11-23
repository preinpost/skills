---
name: docs-site-translate
description: Translate an entire documentation/manual website (Sphinx, MkDocs, Docusaurus, etc.) into another language (default Korean) as a static mirror site, then quality-review it with parallel sub-agents. Use when the user asks to "translate the docs site", "make a Korean version of <manual>", "번역해서 정적 사이트로", "매뉴얼 번역", or to QA/re-review an existing machine translation of many documents.
---

# Docs Site Translate (매뉴얼 사이트 번역 + 검수)

Large-scale pipeline: crawl → extract → translate (agents) → validate → build static site → triage → agent QA → sample-based decision → full QA → publish.
Reference implementation (Linux kernel docs, 2,091 pages) is in `scripts/`. Scripts are **site-specific**: read and adapt them (selectors, sidebar structure, title suffix, paths, term RULES) rather than running blindly.

## 0. Setup decisions (ask the user once)
- Source URL, target language, output dir, scope (exclude rules: changelogs, generated API dumps, translations dirs).
- Title suffix (e.g. `&#8212; Linux 커널 문서`), glossary seed terms, whether to keep English in parentheses on first use.
- Sub-agent model/provider and max concurrency (default 5; 10 worked fine for QA). Publishing target (GitHub Pages / object storage / …) — never push without explicit confirmation.
- Glossary must exist **before** translation and cover recurring domain terms (userspace, discrete GPU, aperture, lease …). Missing entries caused cross-doc drift that later needed bulk fixes.

## 1. Pipeline layout
```
<project>/
  crawl_index.py   # discover pages from toctree/sidebar → manifest.json, toc_order.json
  scrape_raw.py    # fetch raw_html/ (polite, cached)
  extract.py       # raw_html → extracted/<doc>.json  {title, body chunks, sidebar_html, meta keys}
  glossary.json    # term → translation (+ sidebar_glossary.json for nav terms)
  translated/<doc>.json   # same schema as extracted, text translated
  validate_only.py # structural diff extracted vs translated (tags/attrs, <pre>, <code>, entities, keys, CJK leakage, title suffix)
  build_site.py    # translated → out/ (copy static_assets, rewrite links)
  verify.py        # check out/ html + links
  harness_batch.py # batch drive + `rebuild` = build+verify+validate all
  triage.py        # per-doc risk signals → score
  term_normalize.py   # bulk glossary term fix on text nodes only (dry-run / --apply)
  sidebar_sync.py     # align sidebar TOC link text to body headings (dry-run / --apply)
  static_assets/_static/kr-override.css  # font + "원문" badge styles (reference: scripts/kr-override.css)
  _work/           # queues, results, hints, logs; next_queue.py + qa_reconcile.py live here
```
Key schema rule: chunked JSON whose keys/metadata (`docname, depth, static_prefix, body_bytes, chunk_count, chunk_id, wrapper_open, wrapper_close`) must be byte-identical to extracted; only text nodes change.

## 2. Translation phase
- One doc (or one chunk set) per sub-agent; refill a slot as soon as one finishes.
- Agent task must include: file paths, glossary, "translate yourself" rule, structure rules, and "run validate_only.py <doc> until 0 errors".
- **Forbid explicitly**: external translation services (Google Translate), external LLM APIs (OpenRouter etc.), reading credential files (`~/.pi/agent/auth.json`), reusing other batches' caches. Agents have been caught doing this — if discovered, re-translate that batch.
- Preserve: HTML tags/attrs, `<pre>` verbatim, `<code>`/identifiers/paths/config values, entities `&lt; &gt; &amp;`, no hanzi/kana leakage for Korean.
- Put the known MT failure patterns into the translate prompt up front (they dominated QA fixes). Examples below are from the reference run (Linux kernel → Korean); patterns 1–3 are generic for any tag-chunked docs site, adapt wording to the target language:
  - "다음 …합니다: X" — identifier/link pushed after a colon at sentence end (Sphinx splits sentences at `<code>`/`<a>`; MT translates fragments).
  - `을(를)/은(는)` placeholders; sentences cut/duplicated at tag boundaries; lines broken at the English line wraps.
  - Proper nouns/units/option values translated as words (Clang→"땡땡이", `us`→"우리", arm→"팔", `clean`→"깨끗한", `M=$PWD`→`남=$PWD`).
  - Generator artifacts in the source itself (e.g. broken kernel-doc xrefs `<code>struct is</code>`): keep the code, fix only the surrounding sentence. List such site-specific artifacts in `qa_config.json` → `extra_rules`.
- JSON format must be stable: `ensure_ascii=False, indent=2`, same trailing-newline as before. Tell agents explicitly (they rewrote with indent=1 etc.).

## 3. Global post-fixes (scripted, after all translated)
- CJK/kana scan → 0. Title normalization. Sidebar normalization against sidebar_glossary (skip docs whose structure mismatches).
- Grep known bad words/false friends and fix context-aware (e.g. sleep→"슬립" not "수면", "origin"→"출처" not "원산지"). Review before bulk replace; revert overreach.
- `harness_batch.py rebuild` → build/verify/validate all 0 errors.

## 4. QA phase
### Triage signals (triage.py)
`code_mut` (code text changed), `ent_loss`, `eng_left` (untranslated paragraph), `glue_eng` (English words glued into sentence), `len_short`/`len_long` (omission/hallucination by length ratio), `badword`, `misaligned`. badword/glue_eng are naive — tell agents NOT to distort correct translations to clear them.

### Lessons (important)
- Triage score does **not** predict meaning errors. Low/zero-score docs still had inverted meaning ("A 대신 B" swapped, passive/active subject swapped, `analogous to`→"되돌린다", `moved forward` direction flipped, swapped adjacent `<code>` spans).
- So: QA high-score docs first, then run a **random sample (~40, fixed seed)** of the low-score pool. If C-rate ≳5% or B with meaning errors is common → full review of the rest, prioritized by how likely readers follow instructions (admin/user guides, process, userspace API, core API, driver API … hardware-specific last).

- Triage-0 docs can be catastrophically bad (whole-doc MT garbage). Reference run: 1,403 reviewed → A 57% / B 40% / C 3%, several C's had triage score 0 — i.e. full review was worth it.

### Coverage rule (big docs)
- Agents silently review only part of long docs (first N chars per chunk, 1/6 sample, "risky paragraphs only") and still report A/B. Require **"대조한 범위(전체/일부)"** in every report; if partial → record grade but add to a re-review list and later delegate a *full-coverage* task ("모든 chunk의 모든 문단, chunk별로 나눠 읽고 chunk마다 저장"). In the reference run every partially reviewed doc had hidden problems (one had ~150 MT-pattern fixes and a stray Russian word).
- For docs > ~200 paragraphs, assign full coverage from the start.

### Glossary authority
- Agents "fix" toward the doc-local majority even when it contradicts glossary (reference run: 유저 공간→사용자 공간). Prompt: *glossary wins; never change toward non-glossary terms.* Orchestrator: scan each report for term changes and revert violations immediately.
- Collect inconsistent terms during QA in a list; after QA run `scripts/term_normalize.py` (text nodes only, skips `<pre>/<code>/<cite>`/attributes/sidebar, dry-run first, backup to /tmp, guards like `(?<!\()aperture` so `애퍼처(aperture)` doesn't become `애퍼처(애퍼처)`), then add the terms to glossary.json. Before choosing the target term, grep which form the body already uses (reference run: lease → "리스" was already used ~15×, so the proposed "임대" would have been wrong).

### Sidebar
- Agents are told not to touch `sidebar_html` terms, so body heading fixes leave the sidebar stale. After QA: `scripts/sidebar_sync.py` (aligns sidebar `href="#id"` link text to the body heading of that section; dry-run then `--apply`) + term_normalize on sidebar strings, then rebuild.

### Review agent task template
See `scripts/next_queue.py` — generic; per-project values (round name, site name, target language, title suffix, glossary path, forbidden cache paths, extra site-specific rules) go in `_work/qa_config.json`, not in the script (pops `_work/qaN_queue.txt`, appends grade to `_work/qaN_results.txt`, prints `{doc, task, remaining}` with per-doc triage hint). Task includes: compare sentence-by-sentence with original, fix in place, keep structure, glossary consistency, forbidden actions, validate to 0 errors, don't touch manifest/other docs, report grade A/B/C + short summary.

### Grading rule (orchestrator re-grades agent self-reports)
- A: only trivial wording/particles/terminology polish.
- B: any meaning fix, restored omission, inverted clause, lost identifier/entity — even if agent said A.
- C: multiple inverted/wrong core instructions, scrambled sentences, large omissions. If agent says "C→A after fixes" record C.

### Orchestration loop
```
on completion(doc, agentReport):
  grade = regrade(agentReport)
  r = python3 _work/next_queue.py <doc> <grade>   # records + pops next
  if r.doc: delegate_task(task=r.task, title="검수: "+r.doc, role="review")
  report to user: short per-doc summary (detail only for C / meaning inversions) + counts
```
Periodically: `awk '{print $2}' _work/qaN_results.txt | sort | uniq -c` and `harness_batch.py rebuild`.
- Batch several completions into one tool call when many arrive together; report to the user per batch (table: doc / grade / one-line fix), not per doc.
- Popping a doc and delegating it must be one atomic step (pop → delegate in the same script). A provider quota stop between them left 4 docs popped but never run.

### Resume / handoff (model switch, quota, context reset)
- All state lives in files: `_work/qaN_queue.txt`, `qaN_results.txt`, `qaN_hints.json`. On resume run `scripts/qa_reconcile.py qaN` (copy into `_work/`): shows done/queued/**inflight_or_lost**/dups/grades. Lost in-flight docs = popped but no result; wait for late completions first, re-delegate if none arrive, and never record a doc twice.
- Completion notifications from the previous model's children may still arrive after the switch — record them normally.

## 5. Publish
- **Rebuild `out/` right before publishing** (`build_site.py`); out/ goes stale after QA edits.
- `out/.nojekyll`, README with license of source (e.g. GPL-2.0) and attribution + "machine translated, under review" notice if QA incomplete.
- Local preview: `cd out && python3 -m http.server 8000`. Visual check with headless Chrome: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --window-size=1400,2200 --screenshot=/tmp/s.png file://$PWD/out/index.html`.
- GitHub push / Pages enable only after user gives repo and confirms.
- All internal links are relative `.html`, so any static host/prefix works (S3, R2, Pages, …). Untranslated targets link to the original site with an "원문" badge.
- `build_site.py` appends `?v=<sha1[:8]>` of each CSS to its `<link>` so CDN/browser caches pick up CSS changes after a rebuild — keep it.

### Known UI pitfall (Sphinx/Alabaster theme)
- Badge chips inside sidebar `li` inherit `text-indent:-1em` from the theme → text spills out of the chip. `.kr-orig-badge { text-indent:0; white-space:nowrap }` (already in kr-override.css of the reference).

## Reporting style
User-facing reports in the user's language, concise: what was fixed (grouped), grade, validate result, progress counts (완료/진행 중/대기, A/B/C).
