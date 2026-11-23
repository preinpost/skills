# Docs Site Translate (매뉴얼 사이트 번역 + 검수)

Pipeline for any static docs site (Sphinx, mdBook, MkDocs, Docusaurus, Hugo, …):
crawl → extract → glossary → translate (agents) → validate → build → global post-fix → triage → QA (agents) → post-QA normalize → publish → remote check.

Reference implementations live in `scripts/<generator>/` (currently `scripts/mdbook/` from Kubebuilder Book, 92 pages). They are **site-specific**: read and adapt them (content selector, sidebar source, title suffix, link rules, term rules). If no folder matches the generator, write new scripts following the same contracts (§1) and save them back as `scripts/<generator>/` at the end.
Earlier reference run: Linux kernel docs (Sphinx, 2,091 pages) — its lessons are kept below; its scripts are not bundled.

## 0. Setup decisions (ask the user once, recommend defaults)
- Source URL/version, target language, output dir (client's working dir; never the proxy/scratch of the harness), scope (exclude old versions, changelogs, generated API dumps, translation dirs).
- Title suffix (e.g. ` - <Product> 한국어 문서`), glossary seed terms, English-in-parentheses on first use (default yes).
- Sub-agent model/provider + max concurrency (default 5). Store the target in `_work/agent_target.json` and read it on every spawn so the user can switch models mid-run.
- Publishing target (GitHub Pages / object storage / …) — never publish without explicit confirmation.
- Size decides QA strategy: ≲300 pages → full QA directly; larger → triage + sample first (§5).

## 1. Identify the generator & contracts
First inspect one raw page + the site's assets:
- **Content root**: Sphinx `div[role=main]`/`.body`; mdBook `<main>`; MkDocs `article`/`.md-content`; Docusaurus `article`/`.markdown`; Hugo theme-dependent.
- **Sidebar source**: per-page HTML (Sphinx, MkDocs) vs shared file (mdBook `toc-*.js` + `toc.html`, Docusaurus JS bundle). Shared sidebars are translated once via `sidebar_glossary.json` (EN title → KO), not per doc.
- **Page list**: toctree / sidebar / `SUMMARY` / sitemap.xml.
- **Assets**: CSS/JS/fonts/images incl. `url()` inside CSS, search index, `toc.html`, 404 page. Note root-absolute paths (`/logos/x.svg`) and extensionless links (`href="faq"`).

Project layout (names are conventions; keep the contracts):
```
<project>/
  crawl_index.py    # page list → manifest.json [{docname,url,depth}], toc_order.json
  scrape_raw.py     # raw_html/<doc>.html (cached, polite delay, retries)
  fetch_assets.py   # static_assets/ (follow css url(); skip page links; extensionless page links are NOT assets)
  extract.py        # raw → extracted/<doc>.json; split content root at top-level element boundaries (~6KB); assert "".join(chunks)==body
  glossary.json     # {_rules:[...], terms:{en:ko}}  + sidebar_glossary.json
  validate_only.py  # structural diff extracted vs translated (see §3)
  build_site.py     # raw shell + translated body → out/ (see §6)
  verify.py         # every href/src in out/ resolves; + 0 body links to the original domain
  harness_batch.py  # `rebuild` = build + verify + validate translated docs
  triage.py         # per-doc risk signals
  link_title_sync.py# internal-link text that equals target's EN title → target's KO title (dry-run/--apply)
  term_normalize.py # bulk term fix on text nodes only (dry-run/--apply)
  _work/            # queues, results, inflight, hints, notes, agent_target.json, task templates
```
Schema rule: translated JSON keeps every key/metadata byte-identical to extracted (`docname, depth, static_prefix, body_bytes, chunk_count, chunk_id`, …); only text nodes (and `title`) change. Saved with `json.dump(..., ensure_ascii=False, indent=2)` + `"\n"`.

Python pitfall seen: `open(p,"w").write(f(open(p).read()))` truncates the file before reading → read into a variable first.

## 2. Glossary (before translation, then keep growing)
- Seed from a frequency scan of prose (strip `<pre>/<code>/<svg>`), unigram+bigram ≥15. Include rules: product/tool names untranslated, resource kinds/identifiers in English, commands/flags/paths/markers never translated.
- Distinguish near-synonyms explicitly (e.g. desired/actual/**observed** state; reconcile=조정 vs tweak/adjust ≠ 조정).
- **During translation**, every agent report lists terms it had to choose. Add them to glossary.json right away (later agents read it at start). Do the same for QA. This prevented most cross-doc drift; the remainder is fixed in §7.
- Before fixing a term globally, grep which form the corpus already uses.

## 3. Validation (`validate_only.py`)
Checks per chunk: tag/attr sequence identical; `<pre>/<code>/<svg>/<script>` verbatim **and in the same order**; counts of `&lt; &gt; &amp;`; no hanzi/kana (for Korean; adapt per language); meta keys; title suffix; JSON formatting.
Consequence to tell agents up front: tag/code order is fixed, so reorder the *surrounding words* to fit target-language order instead of moving tags.

## 4. Translation phase
- One doc per agent; biggest docs first; refill slots as they finish. Pop + delegate in one atomic step and append to `_work/tr_inflight.txt`.
- Tiny or pathological docs (e.g. a page that is one huge SVG + one sentence) → translate yourself.
- Task template (`scripts/*/tr_task_template.md`) must contain: paths, glossary-first rule, JSON rules, what not to translate (code, identifiers, URLs, license headers, product/Kind names, collapsible code labels inside `<pre>`), style, **known MT failure patterns**, forbidden actions, validate-until-0, report format (coverage 전체/일부, validate result, source oddities, terms chosen).
- Known MT failure patterns (generic for tag-chunked HTML):
  - identifier/link pushed after a colon at sentence end ("다음을 실행합니다: X");
  - `을(를)/은(는)` placeholders; sentences cut/duplicated at tag boundaries; line breaks copied from source wraps;
  - proper nouns/units/option values/**literal string values** translated as words (`clean`→깨끗한, `"alpha"`→알파, `kind` cluster→종류);
  - meaning inversions: "A instead of B", active/passive subject swap, negation, from/to, before/after, `only`, "can"→단정;
  - sentences split across `<summary>`/`<p>`, `<dt>`/`<dd>`, table cells → each fragment must still read naturally (don't leave a 1-word summary like "주어진");
  - source-site artifacts (`*` rendered as `<em>`, stray tags, typos in code): keep tags/code, fix only surrounding prose; list them in QA `extra_rules`.
- Forbid explicitly: external translation services, external LLM APIs, reading credential files, editing other docs/glossary/scripts/manifest.
- Spot-check the first 2–3 docs of any **new model** sentence-by-sentence before trusting it.

## 5. Global post-fix + triage
- Rebuild; CJK/kana/cyrillic scan = 0; placeholder particles = 0; grep known false friends (context-aware, review before bulk replace).
- **Title sync**: set each doc's `title` = sidebar KO title + suffix (sites normally use the same string). Then `link_title_sync.py` for internal links whose source text equals the target's EN title. Variants (paraphrased titles) need a grep pass after QA.
- Triage signals: `code_mut`, `ent_loss`, `eng_left`, `glue_eng`, `len_short/len_long`, `badword`. Exclude license text, identifier-only blocks, metric/flag names, tables of names. Korean is ~0.4× English length, so use a low short-ratio threshold.
- Triage does **not** predict meaning errors (reference runs: zero-score docs had inverted meaning; Linux run had C docs with score 0). Large sites: QA high-score first, then a fixed-seed random sample (~40) of the rest; if C ≳5% or meaning-B common → full QA. Small sites: full QA straight away, ordered by how likely readers follow instructions (getting started → tutorials → migration/guides → reference → plugin/hardware-specific).

## 6. Build rules (`build_site.py`) — link handling is where most bugs were
- Copy `static_assets/` → `out/`; translate shared sidebar files; set `<html lang>`; inject override CSS with `?v=<sha1[:8]>`; write `.nojekyll` and README.
- Rewrite every `href`/`src`:
  1. Decide "internal doc" by **manifest membership**, not by `os.path.exists(out/…)` (pages are written in order; later pages don't exist yet → links leaked to the original site, ~370 in one run). Strip `.html`, map `""`/`index` → landing doc, add `.html` to extensionless doc links.
  2. Absolute links to the original site (`https://<orig>/<doc>.html`) → relative internal.
  3. Root-absolute (`/logos/x.svg`) and double-slash (`..//logos`) asset paths → relative (works under any bucket prefix; breaks only when hosted under a sub-path, so it's invisible locally).
  4. Repo-relative source links (`../../../pkg/x.go`, `testdata/…`) → `https://github.com/<org>/<repo>/tree/<branch>/<path>`; generated `.html` of repo markdown (`designs/*.html`) → `.md`.
  5. Links broken on the source site itself → `LINK_FIX` map to the intended doc (verify with curl that the original 404s; tell the user these are guesses).
  6. Remaining non-existent targets → original site URL (+ "원문" badge for untranslated docs).
- Insert the "translated / 원문" notice **after** link rewriting (placeholder), otherwise its 원문 link gets rewritten to point at itself.
- `verify.py`: 0 broken internal links (except known stock pages like a theme 404), and **0 body links to the original domain** except the notice and print/edit buttons.
- Search index stays in the source language unless rebuilt; mention it.

## 7. QA phase
- Config in `_work/qa_config.json` (round, site, language, glossary paths, extra_rules); generic `next_queue.py` pops queue, records `<doc> <grade> <summary>`, prints `{doc, task, remaining}` with per-doc hints (from translation-phase notes in `_work/qa_notes.txt` + triage examples).
- Keep `_work/qa_notes.txt` during translation: every suspicious item an agent reports (awkward pun, split sentence, term drift, title mismatch) → one line `doc: note`. These become QA hints; GLOBAL/TERM lines become post-QA scripts.
- Review task: compare every block sentence-by-sentence; report coverage 전체/일부, self-grade, changes (meaning fixes as 원문/전/후), validate result. Glossary wins; never change toward non-glossary terms; don't touch title/meta/other docs.
- **Coverage**: partial review → keep grade but re-queue a full-coverage task. Docs > ~200 blocks: demand chunk-by-chunk reading and saving from the start; check the reported block counts.
- **Regrade** every report (agents err both ways): A = polish/terms only; B = any meaning fix, restored omission, inverted relation/subject, added content removed, lost identifier; C = multiple wrong core instructions, scrambled or large omissions (record C even if "fixed").
- **Agents introduce errors too** — spot-check reported diffs, especially: literal values translated, content added "for clarity", default/condition semantics changed, link text pointing to wrong titles. Revert immediately.
- **Don't bulk-edit a doc while it is in review** — the agent's save overwrites it. Either wait, or note `RECHECK:` and re-apply after it completes.
- Report to the user in batches (table: doc / grade / one-line fix; details only for meaning inversions and C).

### Concurrency, rate limits, resume
- Slot count lives in `_work/<round>_slots.txt`; refill only while inflight < slots. Workspace-wide limits are shared with other jobs and drop at peak hours.
- On 429/quota failure: validate the doc (partial edits must still pass), put it back at the **front** of the queue, don't refill; if failures repeat, cut slots and ask the user (wait / smaller slots / other model / mix).
- All state in files: queue, results, inflight. On resume reconcile: done vs queued vs inflight-but-lost; never record a doc twice; late completions from a previous model still count.

## 8. Post-QA normalization
- Grep leftover non-glossary forms (collected TERM lines) and fix with `term_normalize.py` (text nodes only, guards against `X(x)`→`X(X)`, dry-run, backup).
- Re-run `link_title_sync.py`; grep paraphrased link titles; unify UI strings that recur across docs (e.g. "show detailed argument help").
- Decide leftover open term choices explicitly and add them to glossary.
- Rebuild; validate all = 0; scans = 0; screenshots of a few pages (headless Chrome with `--virtual-time-budget=5000` so JS sidebars render).

## 9. Publish
- Rebuild immediately before publishing; README (source license + attribution + "machine translated, reviewed" + search-index note) generated by the build.
- Static hosting works anywhere because links are relative. Object storage via rclone: list the bucket first, upload under a **new prefix with `copy` (never `sync`)**; if the endpoint forbids HEAD (403 on metadata), use `--no-check-dest`. Compare local vs remote file counts.
- **Check the remote URL** with curl (status + content-type) and a headless screenshot — sub-path hosting exposed root-absolute asset paths that looked fine locally. Remind the user about browser cache (hard reload).
- GitHub push / Pages only after the user gives the repo and confirms.

### Known UI pitfalls
- Sphinx/Alabaster: badge chips in sidebar `li` inherit `text-indent:-1em` → `.kr-orig-badge{text-indent:0;white-space:nowrap}`.
- Korean text: `word-break: keep-all` for prose, `normal` for code.

## Reporting style
User's language, concise: what was done/fixed (grouped), grades, validate result, counts (완료/진행 중/대기, A/B/C), anything needing a decision. Batch multiple completions into one report.
