#!/usr/bin/env python3
"""Score early Modern Era editions from public results, no inferred scores."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from import_published_early_edition import run

BASE="https://wscgenz.wordpress.com/previous-contests/wsc-genz11-genz20/"
PATHS={
12:"wsc-gen-z-edition-12-final/",
13:"wsc-gen-z-edition-13-final/",
14:"wsc-genz-edition-14/",
15:"wsc-genz-edition-15-final/",
16:"wsc-genz-edition-16/",
17:"wsc-genz-edition-17/",
18:"wsc-genz-edition-18-final/",
19:"wsc-genz-edition-19/",
}
for n,slug in PATHS.items():
    try:
        run(n,BASE+slug,True)
    except Exception as exc:
        print("NEEDS_REVIEW",n,type(exc).__name__,str(exc)[:400])
