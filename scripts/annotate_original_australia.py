#!/usr/bin/env python3
"""Mark user-confirmed Original Era Australia representative, editions 27-96.

The user's historical player display name is not yet known; do not invent one.
Keep all scoring/artist/rank fields and the Modern Era untouched.
"""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/"archive"/"data"/"editions"
found=[]
for number in range(27,97):
    path=root/f"{number:03d}.json"
    data=json.loads(path.read_text(encoding="utf-8"))
    if data["era"]!="original" or data["edition_number"]!=number:
        raise ValueError(f"Unexpected edition identity in {path}")
    australia=[item for item in data["entries"] if item["country"].strip().casefold()=="australia"]
    if len(australia)!=1:
        raise ValueError(f"Original Edition {number}: expected exactly one Australian entry, found {len(australia)}")
    item=australia[0]
    if "player" in item and item["player"] not in ("", None):
        raise ValueError(f"Existing player name needs review for edition {number}: {item['player']}")
    item["player_identity_id"]="original_australia_representative"
    item["player_attribution"]="User-confirmed: same Australian representative from Original Edition 27 through 96"
    data_text=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
    path.write_text(data_text,encoding="utf-8")
    found.append(number)
if found!=list(range(27,97)):raise ValueError("Unexpected edition coverage")
print(f"PASS: annotated {len(found)} Original Era Australian entries, all editions 27-96")
