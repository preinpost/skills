#!/usr/bin/env python3
"""Step 2: Extract Sphinx sidebar and body from local raw_html/ and split large
documents into balanced HTML chunks ready for translation.

Reads only from raw_html/ (zero network calls) and writes structured JSON to
extracted/{docname}.json.
"""

import argparse
import json
import os
import re
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(HERE, "manifest.json")
RAW_DIR = os.path.join(HERE, "raw_html")
EXTRACTED_DIR = os.path.join(HERE, "extracted")

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class TopBlockSplitter(HTMLParser):
    """Splits an HTML fragment into top-level balanced element/text blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.depth = 0
        self.blocks: list[str] = []
        self.buf: list[str] = []

    def _flush(self) -> None:
        chunk = "".join(self.buf).strip()
        if chunk:
            self.blocks.append(chunk)
        self.buf.clear()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raw = self.get_starttag_text()
        self.buf.append(raw)
        if tag.lower() not in VOID_TAGS:
            self.depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.buf.append(self.get_starttag_text())
        if self.depth == 0:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        self.buf.append(f"</{tag}>")
        if tag.lower() not in VOID_TAGS and self.depth > 0:
            self.depth -= 1
            if self.depth == 0:
                self._flush()

    def handle_data(self, data: str) -> None:
        self.buf.append(data)

    def handle_entityref(self, name: str) -> None:
        self.buf.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.buf.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self.buf.append(f"<!--{data}-->")

    def finish(self) -> list[str]:
        self._flush()
        return self.blocks


def split_top_blocks(html_fragment: str) -> list[str]:
    p = TopBlockSplitter()
    p.feed(html_fragment)
    p.close()
    return p.finish()


def extract_div_by_marker(raw_html: str, start_marker: str) -> str:
    idx = raw_html.find(start_marker)
    if idx == -1:
        return ""
    # Scan balanced <div> ... </div> from idx
    pos = idx
    depth = 0
    tag_re = re.compile(r"<(/?)div\b[^>]*>", re.I)
    for m in tag_re.finditer(raw_html, pos):
        if m.group(1) == "":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return raw_html[idx:m.end()]
    return raw_html[idx:]


def unwrap_outer_div(div_html: str) -> str:
    m_start = re.match(r"^<div\b[^>]*>", div_html, re.I)
    m_end = re.search(r"</div>\s*$", div_html, re.I)
    if m_start and m_end:
        return div_html[m_start.end():m_end.start()].strip()
    return div_html


def chunk_html_blocks(blocks: list[str], max_bytes: int) -> list[dict]:
    """Group balanced HTML blocks into chunks <= max_bytes.
    If a single <section> block exceeds max_bytes, recursively unpack that
    <section> wrapper and chunk its children (recording wrapper open/close tags).
    """
    chunks: list[dict] = []
    cur_parts: list[str] = []
    cur_bytes = 0

    def flush() -> None:
        nonlocal cur_parts, cur_bytes
        if cur_parts:
            chunks.append({
                "chunk_id": len(chunks),
                "wrapper_open": "",
                "wrapper_close": "",
                "html": "\n".join(cur_parts),
            })
            cur_parts = []
            cur_bytes = 0

    for blk in blocks:
        blk_bytes = len(blk.encode("utf-8"))
        if blk_bytes > max_bytes:
            m_open = re.match(r"^(<(?:section|dl|div)\b[^>]*>)(.*)(</(?:section|dl|div)>)\s*$", blk, re.S | re.I)
            if m_open:
                flush()
                sec_open, sec_inner, sec_close = m_open.group(1), m_open.group(2), m_open.group(3)
                sub_blocks = split_top_blocks(sec_inner)
                if len(sub_blocks) > 1 or (
                    len(sub_blocks) == 1 and re.match(r"^<(?:section|dl|div)\b", sub_blocks[0], re.I)
                ):
                    sub_chunks = chunk_html_blocks(sub_blocks, max_bytes)
                    for sc in sub_chunks:
                        sc["wrapper_open"] = sec_open + sc["wrapper_open"]
                        sc["wrapper_close"] = sc["wrapper_close"] + sec_close
                        sc["chunk_id"] = len(chunks)
                        chunks.append(sc)
                    continue

        if cur_parts and cur_bytes + blk_bytes > max_bytes:
            flush()

        cur_parts.append(blk)
        cur_bytes += blk_bytes

    flush()
    return chunks


def extract_one(docname: str, raw_path: str, max_chunk_bytes: int) -> dict:
    raw = open(raw_path, "r", encoding="utf-8", errors="replace").read()

    m_title = re.search(r"<title>(.*?)</title>", raw, re.S | re.I)
    title_html = m_title.group(1).strip() if m_title else docname

    sidebar_div = extract_div_by_marker(raw, '<div class="sphinxsidebar"')
    # Remove Sphinx JS quick searchbox block since static site uses prebuilt search or pure links
    sidebar_div = re.sub(
        r'<div id="searchbox"[^>]*>.*?</div>\s*<script>.*?</script>',
        "",
        sidebar_div,
        flags=re.S | re.I,
    )

    body_div = extract_div_by_marker(raw, '<div class="body" role="main">')
    body_inner = unwrap_outer_div(body_div)

    body_bytes = len(body_inner.encode("utf-8"))
    if body_bytes <= max_chunk_bytes:
        chunks = [{"chunk_id": 0, "wrapper_open": "", "wrapper_close": "", "html": body_inner}]
    else:
        top_blocks = split_top_blocks(body_inner)
        chunks = chunk_html_blocks(top_blocks, max_chunk_bytes)

    depth = docname.count("/")
    static_prefix = "../" * depth + "_static/"

    return {
        "docname": docname,
        "depth": depth,
        "static_prefix": static_prefix,
        "title": title_html,
        "sidebar_html": sidebar_div,
        "body_bytes": body_bytes,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Sphinx sidebar/body & chunk large docs locally")
    parser.add_argument("--prefix", help="Filter by docname prefix")
    parser.add_argument("--doc", action="append", help="Specific docname to extract")
    parser.add_argument("--max-chunk-bytes", type=int, default=24000, help="Max UTF-8 bytes per translation chunk")
    args = parser.parse_args()

    manifest = json.loads(open(MANIFEST_PATH, encoding="utf-8").read())
    exact_docs = set(args.doc or [])
    count = 0
    multi_chunk = 0

    for d in manifest["documents"]:
        if d["excluded"]:
            continue
        if exact_docs and d["docname"] not in exact_docs:
            continue
        if args.prefix and not d["docname"].startswith(args.prefix):
            continue
        raw_path = os.path.join(RAW_DIR, d["output_path"])
        if not os.path.exists(raw_path):
            continue

        extracted = extract_one(d["docname"], raw_path, args.max_chunk_bytes)
        out_path = os.path.join(EXTRACTED_DIR, f"{d['docname']}.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(extracted, f, ensure_ascii=False, indent=2)

        count += 1
        if extracted["chunk_count"] > 1:
            multi_chunk += 1
            print(f"  [chunked x{extracted['chunk_count']}] {d['docname']} ({extracted['body_bytes']:,} bytes)")

    print(f"Extracted {count} document(s) into {EXTRACTED_DIR} ({multi_chunk} split into multiple chunks).")


if __name__ == "__main__":
    main()
