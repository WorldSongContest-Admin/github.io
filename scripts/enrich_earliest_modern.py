#!/usr/bin/env python3
"""Import only fully cross-checked earliest Modern Era scores (excluding already imported Editions 5 and 6)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from import_published_early_edition import run
base="https://wscgenz.wordpress.com/previous-contests/wsc-genz01-genz10/"
for n in [1,2,3,4,7,8,9,10]:
    try:run(n,base+f"wsc-gen-z-edition-{n}/",True)
    except Exception as exc:
        print("NEEDS_REVIEW",n,type(exc).__name__,str(exc)[:450])
