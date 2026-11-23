#!/usr/bin/env python3
"""Harness batch coordinator for translating extracted/*.json -> translated/*.json
using subscription-harness subagents, validating outputs, updating manifest.json,
and rebuilding out/.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(HERE, "manifest.json")
EXTRACTED_DIR = os.path.join(HERE, "extracted")
TRANSLATED_DIR = os.path.join(HERE, "translated")

HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def load_manifest() -> dict:
    return json.loads(open(MANIFEST_PATH, encoding="utf-8").read())


def save_manifest(m: dict) -> None:
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)


def cmd_status(args: argparse.Namespace) -> None:
    m = load_manifest()
    docs = m["documents"]
    status_cnt = Counter(d["status"] for d in docs)
    prio_cnt = {}
    for d in docs:
        if d["excluded"]:
            continue
        p = d["priority"] or "P3_guides_other"
        prio_cnt.setdefault(p, Counter())[d["status"]] += 1

    print("=== Overall Status ===")
    for k, v in sorted(status_cnt.items()):
        print(f"  {k:12s}: {v:,}")
    print("\n=== By Priority (Included Only) ===")
    for p in sorted(prio_cnt):
        c = prio_cnt[p]
        total = sum(c.values())
        done = c.get("translated", 0)
        print(f"  {p:22s}: {done:,} / {total:,} translated (scraped={c.get('scraped', 0):,})")


def cmd_next(args: argparse.Namespace) -> None:
    m = load_manifest()
    picked = []
    for d in m["documents"]:
        if d["excluded"]:
            continue
        t_path = os.path.join(TRANSLATED_DIR, f"{d['docname']}.json")
        if os.path.exists(t_path):
            continue
        if args.priority and d["priority"] != args.priority:
            continue
        if args.prefix and not d["docname"].startswith(args.prefix):
            continue
        e_path = os.path.join(EXTRACTED_DIR, f"{d['docname']}.json")
        if not os.path.exists(e_path):
            continue
        ext = json.loads(open(e_path, encoding="utf-8").read())
        picked.append((d["priority"], ext["chunk_count"], ext["body_bytes"], d["docname"]))

    if args.sort_small:
        picked.sort(key=lambda x: (x[1], x[2], x[3]))

    for prio, chunks, bbytes, name in picked[: args.limit]:
        print(f"{name:50s} chunks={chunks:<3d} bytes={bbytes:,} [{prio}]")
    print(f"\nTotal remaining matching filter: {len(picked)}")


def validate_one(docname: str) -> list[str]:
    e_path = os.path.join(EXTRACTED_DIR, f"{docname}.json")
    t_path = os.path.join(TRANSLATED_DIR, f"{docname}.json")
    errs = []
    if not os.path.exists(e_path):
        return [f"Missing extracted JSON: {e_path}"]
    if not os.path.exists(t_path):
        return [f"Missing translated JSON: {t_path}"]

    ext = json.loads(open(e_path, encoding="utf-8").read())
    try:
        trn = json.loads(open(t_path, encoding="utf-8").read())
    except Exception as exc:
        return [f"Invalid JSON in {t_path}: {exc}"]

    for req_key in ("docname", "depth", "static_prefix", "title", "sidebar_html", "chunks"):
        if req_key not in trn:
            errs.append(f"Missing key '{req_key}' in {docname}")

    if trn.get("docname") != docname:
        errs.append(f"docname mismatch: {trn.get('docname')} != {docname}")

    e_chunks = ext.get("chunks", [])
    t_chunks = trn.get("chunks", [])
    if len(e_chunks) != len(t_chunks):
        errs.append(f"chunk count mismatch in {docname}: expected {len(e_chunks)}, got {len(t_chunks)}")
        return errs

    for ec, tc in zip(e_chunks, t_chunks):
        cid = ec["chunk_id"]
        if tc.get("chunk_id") != cid:
            errs.append(f"{docname}#chunk{cid}: chunk_id mismatch")
        if tc.get("wrapper_open", "") != ec.get("wrapper_open", ""):
            errs.append(f"{docname}#chunk{cid}: wrapper_open modified")
        if tc.get("wrapper_close", "") != ec.get("wrapper_close", ""):
            errs.append(f"{docname}#chunk{cid}: wrapper_close modified")
        th = tc.get("html", "")
        eh = ec.get("html", "")
        if not th.strip():
            errs.append(f"{docname}#chunk{cid}: empty translated html")
        if th.count("<pre") != eh.count("<pre") or th.count("</pre>") != eh.count("</pre>"):
            errs.append(f"{docname}#chunk{cid}: <pre> tag count mismatch")
        # Require Korean characters if source prose had substantial alphabetic words
        if len(re.sub(r"<[^>]+>", "", eh).strip()) > 80 and not HANGUL_RE.search(th):
            errs.append(f"{docname}#chunk{cid}: no Hangul found (untranslated?)")

    return errs


def cmd_validate(args: argparse.Namespace) -> int:
    m = load_manifest()
    docs_by_name = {d["docname"]: d for d in m["documents"]}
    target_docs = args.doc or []

    if not target_docs:
        for root, _, files in os.walk(TRANSLATED_DIR):
            for fn in files:
                if fn.endswith(".json"):
                    rel = os.path.relpath(os.path.join(root, fn), TRANSLATED_DIR)
                    target_docs.append(rel[:-5].replace(os.sep, "/"))

    total_errors = []
    validated = 0
    for docname in sorted(target_docs):
        errs = validate_one(docname)
        if errs:
            total_errors.extend(errs)
        else:
            validated += 1
            if docname in docs_by_name:
                docs_by_name[docname]["status"] = "translated"
                docs_by_name[docname]["translated_at"] = datetime.now(timezone.utc).isoformat()

    save_manifest(m)
    print(f"Validated {validated} translated doc(s). Errors: {len(total_errors)}")
    for e in total_errors[:30]:
        print(" -", e)
    return 1 if total_errors else 0


def cmd_rebuild(args: argparse.Namespace) -> None:
    rc = cmd_validate(args)
    if rc != 0:
        sys.exit(rc)
    subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "verify.py")], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Subscription-harness batch helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_stat = sub.add_parser("status", help="Show translation progress")
    p_stat.set_defaults(func=cmd_status)

    p_next = sub.add_parser("next", help="List next untranslated docs")
    p_next.add_argument("--priority")
    p_next.add_argument("--prefix")
    p_next.add_argument("--limit", type=int, default=20)
    p_next.add_argument("--sort-small", action="store_true")
    p_next.set_defaults(func=cmd_next)

    p_val = sub.add_parser("validate", help="Validate translated/*.json and update manifest.json")
    p_val.add_argument("--doc", action="append")
    p_val.set_defaults(func=lambda a: sys.exit(cmd_validate(a)))

    p_reb = sub.add_parser("rebuild", help="Validate translations, rebuild out/, and verify links")
    p_reb.add_argument("--doc", action="append")
    p_reb.set_defaults(func=cmd_rebuild)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
