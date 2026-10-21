#!/usr/bin/env python3
"""Inspect the main WSC HTML without modifying it or exposing private results.

Usage: python scripts/inspect_main_app.py [index.html] [--json]
Prints likely embedded data blocks and external asset references. It does NOT
guess schema or interpret arbitrary JavaScript as trusted data.
"""
import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path

class Inspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.current = None
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.current = {"type": attrs.get("type", ""), "id": attrs.get("id", ""),
                            "src": attrs.get("src", ""), "data": ""}
        elif tag == "link" and attrs.get("href"):
            self.links.append(attrs["href"])
    def handle_data(self, data):
        if self.current is not None:
            self.current["data"] += data
    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append(self.current)
            self.current = None

def inspect(path):
    html = path.read_text(encoding="utf-8")
    parser = Inspector()
    parser.feed(html)
    scripts = []
    for s in parser.scripts:
        data = s["data"]
        candidates = sorted(set(re.findall(
            r"(?i)(?:edition|voting|score|points|country|result|entries|archive|final)",
            data
        )))
        scripts.append({
            "id": s["id"], "type": s["type"], "src": s["src"],
            "inline_bytes": len(data.encode("utf-8")),
            "candidate_result_keywords": candidates,
            "potential_json_data": s["type"] in ("application/json", "application/ld+json"),
        })
    return {
        "file": str(path), "size_bytes": path.stat().st_size,
        "script_count": len(scripts), "scripts": scripts,
        "asset_links": parser.links[:100],
        "note": "Inventory only; do not assume a match proves a modern results table."
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("html", nargs="?", type=Path, default=Path("index.html"))
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    report = inspect(args.html)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("Application size:", report["size_bytes"], "bytes")
        for i, script in enumerate(report["scripts"], 1):
            print(f"Script {i}: source={script['src'] or '[embedded]'}",
                  f"size={script['inline_bytes']}",
                  f"keywords={','.join(script['candidate_result_keywords']) or '-'}")
        print("This inventory is for planning an audited modern-results export.")
