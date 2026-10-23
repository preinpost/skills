#!/usr/bin/env python3
"""Inline a filled-in template into one self-contained HTML file.

Usage:
    python3 build.py page.html --out article-ko.html [--root DIR]
    python3 build.py page.html --out preview.html --preview

Template directives resolved by this script:

    {{IMG:relative/path.png}}   -> data: URI (mime from extension)
    {{MEDIA:m1}}                -> data: URI of poster_m1.jpg, or empty
    {{PAYLOAD}}                 -> JSON map of video key -> base64 MP4

Video keys come from `data-key="..."` attributes in the template; each needs
a matching <root>/media/<key>.mp4. Everything else ({{TITLE}}, {{BODY}}, ...)
is plain text substitution the author performs before calling this script.

--preview skips the MP4 payload so the page is small enough for an inline
browser preview; posters and images are still embedded.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys

MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".avif": "image/avif",
}


def read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def data_uri(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    mime = MIME.get(ext) or mimetypes.guess_type(path)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(read(path)).decode("ascii")


def find(root: str, *candidates: str) -> str | None:
    for rel in candidates:
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            return path
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("--out", required=True)
    ap.add_argument("--root", default=".", help="directory holding media/ and assets/")
    ap.add_argument("--preview", action="store_true", help="omit video payload")
    ap.add_argument("--budget", type=float, default=12.0, help="MB warning threshold")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    doc = open(args.template, encoding="utf-8").read()

    # 1) Images referenced by relative path.
    missing: list[str] = []

    def img(match: re.Match) -> str:
        path = os.path.join(root, match.group(1))
        if not os.path.isfile(path):
            missing.append(match.group(1))
            return match.group(0)
        return data_uri(path)

    doc = re.sub(r"\{\{IMG:([^}]+)\}\}", img, doc)

    # 2) Video poster frames.
    def poster(match: re.Match) -> str:
        key = match.group(1)
        path = find(root, f"poster_{key}.jpg", f"media/poster_{key}.jpg", f"assets/poster_{key}.jpg")
        return data_uri(path) if path else ""

    doc = re.sub(r"\{\{MEDIA:([A-Za-z0-9_-]+)\}\}", poster, doc)

    # 3) Video payload, limited to the keys the template actually uses.
    keys = sorted(set(re.findall(r'data-key="([A-Za-z0-9_-]+)"', doc)))
    payload: dict[str, str] = {}
    if not args.preview:
        for key in keys:
            path = find(root, f"media/{key}.mp4", f"{key}.mp4", f"assets/{key}.mp4")
            if not path:
                sys.exit(f"Missing video for data-key=\"{key}\" under {root}/media/")
            payload[key] = base64.b64encode(read(path)).decode("ascii")

    doc = doc.replace("{{PAYLOAD}}", json.dumps(payload))

    left = sorted(set(re.findall(r"\{\{[^}]*\}\}", doc)))
    if left:
        print("Unresolved placeholders:", ", ".join(left), file=sys.stderr)
        sys.exit(1)
    if missing:
        print("Missing images:", ", ".join(missing), file=sys.stderr)
        sys.exit(1)

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(doc)

    mb = os.path.getsize(args.out) / 1024 / 1024
    videos = f", {len(keys)} video(s)" if keys else ""
    print(f"{args.out}  {mb:.2f} MB{videos}")
    if mb > args.budget:
        print(
            f"Warning: {mb:.1f}MB is heavy for chat or email. "
            "Re-run media.py with --crf 30 or --max-width 900.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
