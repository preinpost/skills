#!/usr/bin/env python3
"""Extract and localize the media of a web article.

Two subcommands:

  list  README.html
      Print every figure in document order with its caption and source URL.
      Use this to decide which figures to keep and in what order.

  fetch README.html --out media_dir
      Download images, transcode videos (and animated GIFs) to compact MP4,
      extract poster frames, and print the HTML/payload mapping to paste
      into the template.

Design notes:
  * Next.js image wrappers (/ _next/image?url=...) are unwrapped so the
    original CDN file is fetched instead of a resized variant.
  * Relative URLs resolve against the page URL found in og:url / canonical,
    or against --base.
  * Videos keep their native resolution up to --max-width, are muted, and
    become faststart H.264 so they start playing before they finish loading.
  * Everything is downloaded sequentially with a browser user agent; that is
    enough for public articles and keeps the script dependency free.
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def strip_tags(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = htmllib.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def page_url(doc: str, fallback: str | None) -> str:
    for pattern in (
        r'<meta[^>]+property="og:url"[^>]+content="([^"]+)"',
        r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"',
    ):
        m = re.search(pattern, doc)
        if m:
            return htmllib.unescape(m.group(1))
    return fallback or ""


def unwrap_src(src: str, base: str) -> str:
    """Resolve relative URLs and unwrap Next.js image proxies."""
    src = htmllib.unescape(src.strip())
    if src.startswith("data:"):
        return src
    if "url=" in src and ("/_next/image" in src or "/image?" in src):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(src).query)
        if query.get("url"):
            src = query["url"][0]
    return urllib.parse.urljoin(base, src)


def media_items(doc: str, base: str) -> list[dict]:
    items: list[dict] = []

    def push(kind: str, src: str, caption: str, label: str, poster: str = "") -> None:
        url = unwrap_src(src, base)
        if not url or url.startswith("data:"):
            return
        items.append(
            {
                "kind": kind,
                "src": url,
                "poster": unwrap_src(poster, base) if poster else "",
                "label": label,
                "caption": caption,
                "index": len(items) + 1,
            }
        )

    # Preferred shape: <figure> blocks, which carry their own captions.
    figures = list(re.finditer(r"<figure\b.*?</figure>", doc, re.S))
    for fig in figures:
        block = fig.group(0)
        label_m = re.search(r"--figure-label:\s*&quot;([^&]+)&quot;", block) or re.search(
            r"--figure-label:\s*\"([^\"]+)\"", block
        )
        label = htmllib.unescape(label_m.group(1)) if label_m else ""
        cap_m = re.search(r"<figcaption\b.*?</figcaption>", block, re.S)
        caption = strip_tags(cap_m.group(0)) if cap_m else ""
        video_m = re.search(r"<video\b[^>]*\bsrc=\"([^\"]+)\"", block) or re.search(
            r"<source\b[^>]*\bsrc=\"([^\"]+)\"", block
        )
        if video_m:
            poster_m = re.search(r"<video\b[^>]*\bposter=\"([^\"]+)\"", block)
            push("video", video_m.group(1), caption, label, poster_m.group(1) if poster_m else "")
            continue
        img_m = re.search(r"<img\b[^>]*\bsrc=\"([^\"]+)\"", block)
        if img_m:
            push("image", img_m.group(1), caption, label)

    # Fallback for articles without <figure>: scan the article body only.
    if not items:
        body_m = re.search(r"<article\b.*?</article>", doc, re.S)
        body = body_m.group(0) if body_m else doc
        for tag in re.finditer(r"<(video|img)\b[^>]*>", body, re.S):
            attrs = tag.group(0)
            src_m = re.search(r"\bsrc=\"([^\"]+)\"", attrs)
            if not src_m:
                continue
            poster_m = re.search(r"\bposter=\"([^\"]+)\"", attrs)
            push(
                "video" if tag.group(1) == "video" else "image",
                src_m.group(1),
                "",
                "",
                poster_m.group(1) if poster_m else "",
            )

    return items


def download(url: str, dest: str, referer: str = "") -> int:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if referer:
        req.add_header("Referer", referer)
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        out.write(resp.read())
    return os.path.getsize(dest)


def ffprobe_duration(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return float(out or 0)
    except Exception:
        return 0.0


def transcode(src: str, dest: str, max_width: int, crf: int) -> None:
    # -2 keeps the height even, which H.264 requires. No audio track: the
    # source figures are silent, and a stray audio stream only adds weight.
    vf = f"scale='min({max_width},iw)':-2"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", src, "-an",
         "-vf", vf, "-c:v", "libx264", "-profile:v", "high",
         "-pix_fmt", "yuv420p", "-crf", str(crf), "-preset", "slow",
         "-movflags", "+faststart", "-loop", "0", dest],
        check=True,
    )


def poster_frame(src: str, dest: str, duration: float) -> None:
    at = min(3.0, max(0.5, duration / 3)) if duration else 1.0
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", src,
         "-frames:v", "1", "-q:v", "4", dest],
        check=True,
    )


def load(path: str) -> tuple[str, str]:
    doc = open(path, encoding="utf-8", errors="replace").read()
    return doc, page_url(doc, None)


def cmd_list(args: argparse.Namespace) -> None:
    doc, base = load(args.file)
    items = media_items(doc, args.base or base)
    if args.json:
        open(args.json, "w", encoding="utf-8").write(
            json.dumps(items, ensure_ascii=False, indent=2)
        )
    if not items:
        print("No figures found. Fall back to reading the page by hand.")
        return
    print(f"{len(items)} figure(s) in document order\n")
    for it in items:
        label = it["label"] or f"#{it['index']}"
        cap = (it["caption"][:110] + "…") if len(it["caption"]) > 110 else it["caption"]
        print(f"[{it['index']}] {label} ({it['kind']})")
        print(f"    src   {it['src']}")
        if it["poster"]:
            print(f"    poster {it['poster']}")
        if cap:
            print(f"    cap   {cap}")
        print()


def cmd_fetch(args: argparse.Namespace) -> None:
    doc, base = load(args.file)
    items = media_items(doc, args.base or base)
    if not items:
        sys.exit("No figures found; nothing to download.")

    videos_dir = os.path.join(args.out, "media")
    images_dir = os.path.join(args.out, "assets")
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)

    report = []
    for it in items:
        n = it["index"]
        ext = os.path.splitext(urllib.parse.urlparse(it["src"]).path)[1].lower()
        animated_gif = ext == ".gif"
        is_video = it["kind"] == "video" or animated_gif

        if is_video:
            key = f"m{n}"
            raw = os.path.join(videos_dir, f"{key}.source{ext or '.mp4'}")
            size = download(it["src"], raw, base)
            out = os.path.join(videos_dir, f"{key}.mp4")
            transcode(raw, out, args.max_width, args.crf)
            os.remove(raw)
            poster = os.path.join(args.out, f"poster_{key}.jpg")
            poster_frame(out, poster, ffprobe_duration(out))
            it.update(key=key, out=out, poster_file=poster)
            report.append((n, key, "video", os.path.getsize(out), size))
        else:
            name = f"fig{n}{ext or '.png'}"
            out = os.path.join(images_dir, name)
            size = download(it["src"], out, base)
            it.update(out=out, key=f"fig{n}")
            report.append((n, f"fig{n}", "image", size, size))

    print("Downloaded:\n")
    for n, key, kind, final, original in report:
        delta = f" ({original/1024/1024:.1f}MB → {final/1024/1024:.2f}MB)" if kind == "video" else ""
        print(f"  [{n}] {kind:5} {key}{delta}")
        print(f"      {it_path(items, n)}")

    print("\nTemplate snippets:\n")
    for it in items:
        label = it["label"] or f"그림 {it['index']}"
        if it["kind"] == "video" or it["src"].lower().endswith(".gif"):
            print(
                f'<figure class="bleed">\n'
                f'  <div class="media">\n'
                f'    <span class="pill"><i></i>애니메이션</span>\n'
                f'    <video data-key="{it["key"]}" poster="{{{{MEDIA:{it["key"]}}}}}" muted loop playsinline controls preload="metadata" aria-label="..."></video>\n'
                f'  </div>\n'
                f'  <figcaption><span class="fig-label">{label}</span>...</figcaption>\n'
                f'</figure>\n'
            )
        else:
            rel = os.path.relpath(it["out"], args.out)
            print(
                f'<figure class="bleed">\n'
                f'  <div class="media light">\n'
                f'    <img src="{{{{IMG:{rel}}}}}" alt="..." loading="lazy">\n'
                f'  </div>\n'
                f'  <figcaption><span class="fig-label">{label}</span>...</figcaption>\n'
                f'</figure>\n'
            )

    total = sum(os.path.getsize(it["out"]) for it in items)
    print(f"Total media on disk: {total/1024/1024:.2f} MB")
    if total > 9 * 1024 * 1024:
        print("Warning: over ~9MB before base64. Lower --crf/--max-width or drop a figure.")


def it_path(items: list[dict], n: int) -> str:
    for it in items:
        if it["index"] == n:
            return os.path.relpath(it["out"])
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="print figures with captions")
    p_list.add_argument("file")
    p_list.add_argument("--base", default="", help="base URL when the page has no og:url")
    p_list.add_argument("--json", default="", help="also write the figure list as JSON")
    p_list.set_defaults(func=cmd_list)

    p_fetch = sub.add_parser("fetch", help="download, transcode, extract posters")
    p_fetch.add_argument("file")
    p_fetch.add_argument("--base", default="")
    p_fetch.add_argument("--out", default=".", help="working directory (default: .)")
    p_fetch.add_argument("--max-width", type=int, default=1080)
    p_fetch.add_argument("--crf", type=int, default=26)
    p_fetch.set_defaults(func=cmd_fetch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
