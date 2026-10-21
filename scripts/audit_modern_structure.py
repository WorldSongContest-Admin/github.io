#!/usr/bin/env python3
"""Read-only structural reconnaissance of the published WSC application.
Prints counts and redacted field surroundings, no entrant/song/vote values.
"""
from pathlib import Path
import re
from collections import Counter
s=Path("index.html").read_text(encoding="utf-8")
print("FILE",len(s),"characters",len(s.splitlines()),"lines")
for tag in ["html","head","body","script","style","table","tr","td","section","div"]:
    print("TAG",tag,len(re.findall(r"<"+tag+r"\\b",s,re.I)))
for term in ["pts","votes","total","rank","position","result","points","score","edition","results","final","semifinal","country","artist","song","entries","data","json","fetch(","localStorage","firebase","<script","<html"]:
    occur=list(re.finditer(re.escape(term),s,re.I))
    print("TERM",repr(term),"COUNT",len(occur))
print("FILE_START_CHARACTER_CLASSES",''.join('A' if c.isalpha() else 'N' if c.isdigit() else c if c in '<>/=;:{}[]' else '.' for c in s[:100]))
print("LINE_LENGTH_TOP5",sorted((len(x) for x in s.splitlines()),reverse=True)[:5])
print("EXTENSIONS",dict(Counter(re.findall(r"\\b(?:[\\w/-]+)\\.(?:json|js|csv|html|php)\\b",s,re.I)).most_common(15)))
for term in ["points","score","edition","results","artist"]:
    m=re.search(r"(?i)"+term,s)
    if m:
        fragment=s[max(0,m.start()-80):m.end()+80]
        print("STRUCTURAL_CONTEXT",term,repr(''.join('A' if c.isalpha() else 'N' if c.isdigit() else c if c in '<>=:/;{}[],.()_' else ' ' for c in fragment)))
