#!/usr/bin/env python3
"""Step 1.5: Polite raw HTML scraper for docs.kernel.org.

Downloads target HTML documents from manifest.json into local raw_html/ BEFORE
any parsing or translation happens.

Scraping policy:
- Sequential single-connection fetch by default (no burst concurrency)
- Configurable base delay + random jitter (default: 0.40s + 0.05~0.20s)
- gzip compression enabled to minimize bandwidth
- Local file cache skip (idempotent resume) + optional ETag / Last-Modified
  conditional refresh (--refresh)
- Exponential backoff honoring Retry-After on HTTP 429 / 503 / 5xx
- Circuit breaker: aborts cleanly after consecutive network/HTTP errors
"""

import argparse
import gzip
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(HERE, "manifest.json")
RAW_DIR = os.path.join(HERE, "raw_html")

USER_AGENT = "kernel-docs-kr-research/1.0 (+polite-sequential-cache)"


def decode_body(raw_bytes: bytes, content_encoding: str) -> bytes:
    if content_encoding and "gzip" in content_encoding.lower():
        return gzip.decompress(raw_bytes)
    return raw_bytes


def fetch_with_backoff(
    url: str,
    etag: str | None = None,
    last_modified: str | None = None,
    max_retries: int = 4,
) -> tuple[str, bytes | None, str | None, str | None]:
    """Returns (status_tag, body_bytes_or_none, new_etag, new_last_modified).
    status_tag is 'ok', 'not_modified', or raises on permanent failure.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "gzip",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    backoff = 5.0
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = decode_body(resp.read(), resp.headers.get("Content-Encoding", ""))
                return (
                    "ok",
                    raw,
                    resp.headers.get("ETag"),
                    resp.headers.get("Last-Modified"),
                )
        except urllib.error.HTTPError as e:
            if e.code == 304:
                return ("not_modified", None, etag, last_modified)
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                retry_after = e.headers.get("Retry-After")
                wait_s = float(retry_after) if (retry_after and retry_after.isdigit()) else backoff
                print(f"  [HTTP {e.code}] backing off {wait_s:.1f}s for {url}")
                time.sleep(wait_s)
                backoff = min(backoff * 2.5, 120.0)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < max_retries:
                print(f"  [NET ERR: {e}] retrying in {backoff:.1f}s for {url}")
                time.sleep(backoff)
                backoff = min(backoff * 2.5, 120.0)
                continue
            raise
    raise RuntimeError(f"Exhausted retries for {url}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Politely scrape raw HTML pages from manifest.json")
    parser.add_argument("--priority", help="Filter by priority (e.g. P1_core_virt_driver)")
    parser.add_argument("--prefix", help="Filter by docname prefix (e.g. driver-api/driver-model/)")
    parser.add_argument("--doc", action="append", help="Specific docname to fetch (repeatable)")
    parser.add_argument("--limit", type=int, default=0, help="Max number of network fetches in this run (0 = unlimited)")
    parser.add_argument("--delay", type=float, default=0.40, help="Base delay in seconds between requests (default: 0.40)")
    parser.add_argument("--jitter", type=float, default=0.15, help="Max random extra jitter in seconds (default: 0.15)")
    parser.add_argument("--refresh", action="store_true", help="Re-check cached files using ETag/Last-Modified")
    parser.add_argument("--max-consecutive-errors", type=int, default=5, help="Circuit breaker threshold")
    args = parser.parse_args()

    manifest = json.loads(open(MANIFEST_PATH, encoding="utf-8").read())
    docs = manifest["documents"]

    targets = []
    exact_docs = set(args.doc or [])
    for d in docs:
        if d["excluded"]:
            continue
        if exact_docs and d["docname"] not in exact_docs:
            continue
        if args.priority and d["priority"] != args.priority:
            continue
        if args.prefix and not d["docname"].startswith(args.prefix):
            continue
        targets.append(d)

    print(f"Matched {len(targets)} included document(s). Local cache dir: {RAW_DIR}")
    os.makedirs(RAW_DIR, exist_ok=True)

    fetched = 0
    skipped_cached = 0
    not_modified = 0
    errors = 0
    consecutive_errors = 0

    for idx, d in enumerate(targets, 1):
        out_file = os.path.join(RAW_DIR, d["output_path"])
        os.makedirs(os.path.dirname(out_file), exist_ok=True)

        exists = os.path.exists(out_file) and os.path.getsize(out_file) > 0
        if exists and not args.refresh:
            if d["status"] == "pending":
                raw_bytes = open(out_file, "rb").read()
                d["raw_bytes"] = len(raw_bytes)
                d["content_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
                d["status"] = "scraped"
            skipped_cached += 1
            continue

        if args.limit and fetched >= args.limit:
            print(f"Reached --limit={args.limit}; stopping cleanly.")
            break

        try:
            tag, body, new_etag, new_lm = fetch_with_backoff(
                d["url"],
                etag=d.get("etag") if args.refresh else None,
                last_modified=d.get("last_modified") if args.refresh else None,
            )
            consecutive_errors = 0
            if tag == "not_modified":
                not_modified += 1
            else:
                assert body is not None
                with open(out_file, "wb") as f:
                    f.write(body)
                d["raw_bytes"] = len(body)
                d["content_sha256"] = hashlib.sha256(body).hexdigest()
                d["etag"] = new_etag
                d["last_modified"] = new_lm
                d["scraped_at"] = datetime.now(timezone.utc).isoformat()
                if d["status"] == "pending":
                    d["status"] = "scraped"
                fetched += 1
                print(f"[{idx}/{len(targets)}] fetched {d['docname']} ({len(body):,} bytes)")
        except Exception as exc:
            errors += 1
            consecutive_errors += 1
            d["last_error"] = str(exc)
            print(f"[{idx}/{len(targets)}] ERROR {d['docname']}: {exc}")
            if consecutive_errors >= args.max_consecutive_errors:
                print(f"Circuit breaker tripped ({consecutive_errors} consecutive errors). Saving progress and exiting.")
                break

        # Periodic manifest checkpoint every 25 downloads
        if fetched > 0 and fetched % 25 == 0:
            with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

        sleep_for = max(0.1, args.delay + random.uniform(0, args.jitter))
        time.sleep(sleep_for)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(
        f"Done. fetched={fetched}, skipped_cached={skipped_cached}, "
        f"not_modified={not_modified}, errors={errors}"
    )


if __name__ == "__main__":
    main()
