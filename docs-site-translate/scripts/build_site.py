#!/usr/bin/env python3
"""Step 4: Assemble 1:1 static HTML pages using the exact Sphinx Alabaster
layout and rewrite internal links with remote fallback to docs.kernel.org
for excluded or not-yet-translated pages.
"""

import argparse
import json
import os
import posixpath
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(HERE, "manifest.json")
EXTRACTED_DIR = os.path.join(HERE, "extracted")
TRANSLATED_DIR = os.path.join(HERE, "translated")
STATIC_SRC_DIR = os.path.join(HERE, "static_assets", "_static")
OUT_DIR = os.path.join(HERE, "out")


def _static_versions() -> dict:
    """CSS 내용 해시를 ?v= 로 붙여 CDN/브라우저 캐시를 자동 무효화."""
    import hashlib
    vers = {}
    for name in ("pygments.css", "alabaster.css", "custom.css", "kr-override.css"):
        path = os.path.join(STATIC_SRC_DIR, name)
        with open(path, "rb") as f:
            vers[name] = hashlib.sha1(f.read()).hexdigest()[:8]
    return vers


STATIC_VER = _static_versions()


def resolve_doc_href(current_docname: str, href: str) -> tuple[str, str, bool] | None:
    """Resolve a relative href inside current_docname.html.
    Returns (resolved_path, fragment, is_html_doc) or None for external/same-page links.
    """
    if not href or href.startswith(("http://", "https://", "ftp://", "file:", "mailto:", "javascript:", "#")):
        return None
    if href.startswith("https:/") or href.startswith("http:/"):
        return None

    path_part, _, frag = href.partition("#")
    cur_dir = posixpath.dirname(current_docname)
    resolved = posixpath.normpath(posixpath.join(cur_dir, path_part))
    while resolved.startswith("../"):
        resolved = resolved[3:]
    fragment = f"#{frag}" if frag else ""
    if path_part.endswith(".html"):
        return (resolved[:-5], fragment, True)
    if resolved.startswith("_static/") or "/_static/" in resolved:
        return None
    if resolved.startswith("_images/") or "/_images/" in resolved:
        return None
    return (resolved, fragment, False)


def rewrite_links(html_fragment: str, current_docname: str, built_docs: set[str], base_url: str) -> str:
    anchor_re = re.compile(r'(<a\b[^>]*href=")([^"]+)("[^>]*>)(.*?)(</a>)', re.S | re.I)

    def repl(m: re.Match) -> str:
        prefix, href, mid, inner, close_tag = m.groups()
        if href.startswith("https:/") and not href.startswith("https://"):
            return f'{prefix}https://{href[7:]}{mid}{inner}{close_tag}'
        if href.startswith("http:/") and not href.startswith("http://"):
            return f'{prefix}http://{href[6:]}{mid}{inner}{close_tag}'
        resolved = resolve_doc_href(current_docname, href)
        if resolved is None:
            return m.group(0)
        target_path, fragment, is_html_doc = resolved
        if is_html_doc:
            if target_path in built_docs:
                return m.group(0)
            remote_url = f"{base_url}{target_path}.html{fragment}"
            if "kr-orig-badge" in inner:
                return f'{prefix}{remote_url}" target="_blank" rel="noopener noreferrer" title="원문(docs.kernel.org)으로 이동">{inner}{close_tag}'
            return (
                f'{prefix}{remote_url}" target="_blank" rel="noopener noreferrer" '
                f'title="미번역/제외 페이지 — docs.kernel.org 원문으로 이동">{inner}{close_tag}'
                f'<span class="kr-orig-badge">원문</span>'
            )
        remote_url = f"{base_url}{target_path}{fragment}"
        return f'{prefix}{remote_url}" target="_blank" rel="noopener noreferrer">{inner}{close_tag}'

    return anchor_re.sub(repl, html_fragment)


def rewrite_images(html_fragment: str, current_docname: str, base_url: str) -> str:
    cur_dir = posixpath.dirname(current_docname)
    img_re = re.compile(r'\b(src|href)="((?:\.\./)*_images/[^"]+)"', re.I)

    def repl(m: re.Match) -> str:
        attr, target = m.groups()
        resolved = posixpath.normpath(posixpath.join(cur_dir, target))
        if resolved.startswith("../"):
            resolved = resolved.lstrip("./")
        return f'{attr}="{base_url}{resolved}"'

    return img_re.sub(repl, html_fragment)


def assemble_page(doc: dict, base_url: str, built_docs: set[str], is_translated: bool) -> str:
    docname = doc["docname"]
    static_prefix = doc["static_prefix"]
    root_prefix = "../" * doc["depth"]

    sidebar_html = rewrite_links(doc["sidebar_html"], docname, built_docs, base_url)
    sidebar_html = rewrite_images(sidebar_html, docname, base_url)
    # Normalize _static references in sidebar (e.g. logo.svg)
    sidebar_html = re.sub(r'(src=["\'])(?:\.\./)*_static/', rf"\1{static_prefix}", sidebar_html)

    body_parts = []
    for ch in doc["chunks"]:
        part = f"{ch.get('wrapper_open', '')}{ch['html']}{ch.get('wrapper_close', '')}"
        body_parts.append(part)
    body_html = "\n".join(body_parts)
    body_html = rewrite_links(body_html, docname, built_docs, base_url)
    body_html = rewrite_images(body_html, docname, base_url)
    body_html = re.sub(r'(src=["\'])(?:\.\./)*_static/', rf"\1{static_prefix}", body_html)

    status_label = "한국어 번역본" if is_translated else "원문 미러 (번역 대기 중)"
    banner = (
        f'<div class="kr-lang-banner">'
        f'<strong>[{status_label}]</strong> '
        f'<a href="{root_prefix}index.html">한국어 목차</a> · '
        f'<a href="{base_url}{docname}.html" target="_blank" rel="noopener noreferrer">'
        f'docs.kernel.org 원문 보기 ↗</a>'
        f"</div>"
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{doc['title']}</title>
  <link rel="stylesheet" type="text/css" href="{static_prefix}pygments.css?v={STATIC_VER['pygments.css']}" />
  <link rel="stylesheet" type="text/css" href="{static_prefix}alabaster.css?v={STATIC_VER['alabaster.css']}" />
  <link rel="stylesheet" type="text/css" href="{static_prefix}custom.css?v={STATIC_VER['custom.css']}" />
  <link rel="stylesheet" type="text/css" href="{static_prefix}kr-override.css?v={STATIC_VER['kr-override.css']}" />
</head>
<body>
  <div class="document">
    {sidebar_html}
    <div class="documentwrapper">
      <div class="bodywrapper">
        <div class="body" role="main">
          {banner}
          {body_html}
        </div>
      </div>
    </div>
    <div class="clearer"></div>
  </div>
  <div class="footer">
    &copy; The kernel development community. · 원문: <a href="{base_url}{docname}.html" target="_blank" rel="noopener noreferrer">docs.kernel.org</a>
  </div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 1:1 static HTML site from translated (or extracted) docs")
    parser.add_argument(
        "--include-untranslated",
        action="store_true",
        help="Also emit extracted-but-untranslated pages as fallback test build",
    )
    args = parser.parse_args()

    manifest = json.loads(open(MANIFEST_PATH, encoding="utf-8").read())
    base_url = manifest["base_url"].rstrip("/") + "/"

    # Copy _static assets
    out_static = os.path.join(OUT_DIR, "_static")
    if os.path.exists(out_static):
        shutil.rmtree(out_static)
    shutil.copytree(STATIC_SRC_DIR, out_static)

    # Determine which docs exist in translated/ vs extracted/
    to_build: list[tuple[dict, bool]] = []
    built_docs: set[str] = set()

    for d in manifest["documents"]:
        if d["excluded"]:
            continue
        t_path = os.path.join(TRANSLATED_DIR, f"{d['docname']}.json")
        e_path = os.path.join(EXTRACTED_DIR, f"{d['docname']}.json")
        if os.path.exists(t_path):
            to_build.append((json.loads(open(t_path, encoding="utf-8").read()), True))
            built_docs.add(d["docname"])
        elif args.include_untranslated and os.path.exists(e_path):
            to_build.append((json.loads(open(e_path, encoding="utf-8").read()), False))
            built_docs.add(d["docname"])

    for doc_data, is_translated in to_build:
        out_path = os.path.join(OUT_DIR, f"{doc_data['docname']}.html")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        html_out = assemble_page(doc_data, base_url, built_docs, is_translated)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_out)

    print(f"Built {len(to_build)} HTML page(s) in {OUT_DIR}")


if __name__ == "__main__":
    main()
