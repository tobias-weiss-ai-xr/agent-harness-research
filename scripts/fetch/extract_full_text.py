#!/usr/bin/env python3
"""Download arXiv HTML and extract plain text for each paper in papers.yaml."""
import argparse
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

import requests
import yaml

REPO = Path(__file__).resolve().parent.parent.parent
OUT = REPO / "data" / "full_text"

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out = []
        self.skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "header", "footer"):
            self.skip = True
    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "header", "footer"):
            self.skip = False
    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)

def arxiv_id(url):
    m = re.search(r"arxiv\.org/abs/((?:[a-z\-]+/)?\d{4}\.\d{4,5})", url)
    return m.group(1) if m else None

def fetch_html(aid):
    for suffix in ("", "v1"):
        url = f"https://arxiv.org/html/{aid}{suffix}"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200 and "<html" in r.text.lower():
                return r.text
        except Exception:
            pass
        time.sleep(0.5)
    return None

def extract(text):
    p = TextExtractor()
    p.feed(text)
    out = " ".join(p.out)
    out = re.sub(r"\s+", " ", out).strip()
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max papers to process (0=all)")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    with open(REPO / "papers.yaml", encoding="utf-8") as f:
        papers = yaml.safe_load(f).get("papers", [])

    OUT.mkdir(parents=True, exist_ok=True)
    done = 0
    skipped = 0
    failed = 0
    for i, p in enumerate(papers):
        if args.limit and done >= args.limit:
            break
        aid = arxiv_id(p.get("url", ""))
        if not aid:
            failed += 1
            continue
        safe = aid.replace("/", "_")
        outpath = OUT / f"{safe}.txt"
        if outpath.exists() and outpath.stat().st_size > 200:
            skipped += 1
            continue
        html = fetch_html(aid)
        if not html:
            failed += 1
            print(f"[{i+1}/{len(papers)}] FAIL {aid}", flush=True)
            continue
        text = extract(html)
        if len(text) < 500:
            failed += 1
            print(f"[{i+1}/{len(papers)}] SHORT {aid} ({len(text)})", flush=True)
            continue
        outpath.write_text(text, encoding="utf-8")
        done += 1
        print(f"[{i+1}/{len(papers)}] OK {aid} ({len(text)} chars)", flush=True)
        time.sleep(args.delay)

    print(f"\nDone: {done} new, {skipped} skipped, {failed} failed", flush=True)

if __name__ == "__main__":
    main()
