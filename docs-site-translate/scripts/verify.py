#!/usr/bin/env python3
"""Step 5: Verify generated 1:1 static HTML pages in out/ for broken local links,
missing _static assets, empty content, and unbalanced <pre> tags.
"""

import os
import posixpath
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out")


def main() -> None:
    if not os.path.isdir(OUT_DIR):
        print(f"OUT_DIR not found: {OUT_DIR}")
        sys.exit(1)

    html_files = []
    for root, _, files in os.walk(OUT_DIR):
        for fn in files:
            if fn.endswith(".html"):
                html_files.append(os.path.relpath(os.path.join(root, fn), OUT_DIR))

    errors = []
    for rel in sorted(html_files):
        full = os.path.join(OUT_DIR, rel)
        txt = open(full, encoding="utf-8", errors="replace").read()
        if len(txt) < 200:
            errors.append(f"TOO SMALL: {rel}")

        if txt.count("<pre") != txt.count("</pre>"):
            errors.append(f"UNBALANCED <pre> in {rel}")

        cur_dir = posixpath.dirname(rel.replace(os.sep, "/"))
        for attr, target in re.findall(r'(href|src)="([^"]+)"', txt):
            if target.startswith(("http://", "https://", "ftp://", "file:", "mailto:", "javascript:", "#")):
                continue
            path_part = target.split("#")[0].split("?")[0]
            if not path_part:
                continue
            resolved = posixpath.normpath(posixpath.join(cur_dir, path_part))
            disk_path = os.path.join(OUT_DIR, resolved)
            if not os.path.exists(disk_path):
                errors.append(f"BROKEN {attr} in {rel}: {target} -> {resolved}")

    print(f"Verified {len(html_files)} HTML file(s) in {OUT_DIR}. Errors: {len(errors)}")
    for e in errors[:30]:
        print(" -", e)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
