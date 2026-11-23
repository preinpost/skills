#!/usr/bin/env python3
"""Step 1: Crawl docs.kernel.org searchindex.js + index.html, apply exclusion rules,
and generate manifest.json & report.md without performing any translation.
"""

import html
import json
import os
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(HERE, "exclude_rules.json")
MANIFEST_PATH = os.path.join(HERE, "manifest.json")
REPORT_PATH = os.path.join(HERE, "report.md")


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "kernel-docs-kr-indexer/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def main() -> None:
    rules = json.loads(open(RULES_PATH, encoding="utf-8").read())
    base_url = rules["base_url"].rstrip("/") + "/"

    prev_by_doc: dict[str, dict] = {}
    if os.path.exists(MANIFEST_PATH):
        prev_manifest = json.loads(open(MANIFEST_PATH, encoding="utf-8").read())
        prev_by_doc = {d["docname"]: d for d in prev_manifest.get("documents", [])}

    print(f"Fetching {base_url}index.html ...")
    index_html = fetch_text(base_url + "index.html")
    ver_match = re.search(r'<p class="blurb">\s*([^<\n]+)\s*</p>', index_html)
    if not ver_match:
        ver_match = re.search(r"The Linux Kernel</a>\s*([0-9]+\.[0-9]+[^\s<]*)", index_html)
    kernel_version = ver_match.group(1).strip() if ver_match else "unknown"

    print(f"Fetching {base_url}searchindex.js ...")
    raw_idx = fetch_text(base_url + "searchindex.js")
    m = re.search(r"Search\.setIndex\((\{.*\})\)\s*$", raw_idx, re.S)
    if not m:
        raise RuntimeError("Failed to parse Search.setIndex(...) from searchindex.js")
    idx_data = json.loads(m.group(1))

    docnames = idx_data["docnames"]
    filenames = idx_data.get("filenames", [])
    titles = idx_data.get("titles", [])

    tier1_prefixes = rules["tier1_always_exclude_prefixes"]
    tier1_exact = set(rules["tier1_always_exclude_exact"])
    tier2_prefixes = rules["tier2_recommended_exclude_prefixes"]
    priority_groups = rules["priority_groups"]

    docs = []
    tier_counts = Counter()
    reason_counts = Counter()
    priority_counts = Counter()
    included_section_counts = Counter()
    excluded_section_counts = Counter()

    for i, docname in enumerate(docnames):
        title = strip_tags(titles[i]) if i < len(titles) else docname
        source_rst = filenames[i] if i < len(filenames) else f"{docname}.rst"
        top_section = docname.split("/")[0] if "/" in docname else "(root)"

        exclusion_tier = None
        exclude_reason = None

        if docname in tier1_exact:
            exclusion_tier = "tier1_always"
            exclude_reason = f"exact:{docname}"
        else:
            for pfx in tier1_prefixes:
                if docname.startswith(pfx):
                    exclusion_tier = "tier1_always"
                    exclude_reason = f"prefix:{pfx}"
                    break

        if exclusion_tier is None:
            for pfx in tier2_prefixes:
                if docname.startswith(pfx):
                    exclusion_tier = "tier2_recommended"
                    exclude_reason = f"prefix:{pfx}"
                    break

        excluded = exclusion_tier is not None
        priority = None
        if not excluded:
            for p_name, p_prefixes in priority_groups.items():
                if any(docname == pp or docname.startswith(pp) for pp in p_prefixes):
                    priority = p_name
                    break
            if priority is None:
                priority = "P3_guides_other"

            tier_counts["included"] += 1
            priority_counts[priority] += 1
            included_section_counts[top_section] += 1
        else:
            tier_counts[exclusion_tier] += 1
            reason_counts[exclude_reason] += 1
            excluded_section_counts[top_section] += 1

        prev = prev_by_doc.get(docname, {})
        prev_status = prev.get("status")
        if excluded:
            status = "excluded"
        elif prev_status in ("scraped", "translated"):
            status = prev_status
        else:
            status = "pending"

        entry = {
            "docname": docname,
            "top_section": top_section,
            "title": title,
            "url": f"{base_url}{docname}.html",
            "output_path": f"{docname}.html",
            "source_rst": source_rst,
            "excluded": excluded,
            "exclusion_tier": exclusion_tier,
            "exclude_reason": exclude_reason,
            "priority": priority,
            "status": status,
            "content_sha256": prev.get("content_sha256"),
            "body_bytes": prev.get("body_bytes"),
        }
        for opt_key in ("raw_bytes", "etag", "last_modified", "scraped_at", "translated_at"):
            if opt_key in prev:
                entry[opt_key] = prev[opt_key]
        docs.append(entry)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "kernel_version": kernel_version,
        "summary": {
            "total_docs_in_index": len(docs),
            "tier1_excluded": tier_counts["tier1_always"],
            "tier2_excluded": tier_counts["tier2_recommended"],
            "total_excluded": tier_counts["tier1_always"] + tier_counts["tier2_recommended"],
            "target_included": tier_counts["included"],
            "priority_breakdown": dict(priority_counts),
        },
        "documents": docs,
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Build human-readable report.md
    lines = [
        f"# docs.kernel.org Step 1 크롤링 & 필터링 리포트",
        "",
        f"- **원본 기준**: `{base_url}` (감지된 버전: `{kernel_version}`)",
        f"- **생성 시각**: `{manifest['generated_at']}`",
        f"- **전체 인덱스 문서 수**: **{len(docs):,}개**",
        f"- **제외된 문서 수**: **{manifest['summary']['total_excluded']:,}개** (Tier 1 무조건 제외: {tier_counts['tier1_always']:,}개, Tier 2 권장 제외: {tier_counts['tier2_recommended']:,}개)",
        f"- **최종 번역 대상**: **{tier_counts['included']:,}개**",
        "",
        "## 번역 대상 우선순위 분포",
        "",
        "| 우선순위 | 문서 수 | 설명 |",
        "|---|---:|---|",
        f"| `P1_core_virt_driver` | {priority_counts['P1_core_virt_driver']:,} | 루트, core-api, driver-model/vfio, virt, PCI, mm, locking, scheduler, RCU |",
        f"| `P2_subsystems_dev` | {priority_counts['P2_subsystems_dev']:,} | 나머지 driver-api, filesystems, networking, bpf, trace, gpu, arch 등 |",
        f"| `P3_guides_other` | {priority_counts['P3_guides_other']:,} | admin-guide, userspace-api, tools, kbuild, firmware-guide 등 |",
        "",
        "## 번역 대상 섹션별 분포 (포함된 문서)",
        "",
        "| 섹션 | 포함 문서 수 |",
        "|---|---:|",
    ]
    for sec, cnt in included_section_counts.most_common():
        lines.append(f"| `{sec}` | {cnt:,} |")

    lines.extend([
        "",
        "## 제외 규칙별 분포 (제외된 문서)",
        "",
        "| 제외 사유 (`exclude_rules.json`) | 제외 문서 수 |",
        "|---|---:|",
    ])
    for reason, cnt in reason_counts.most_common():
        lines.append(f"| `{reason}` | {cnt:,} |")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps(manifest["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote {MANIFEST_PATH} and {REPORT_PATH}")


if __name__ == "__main__":
    main()
