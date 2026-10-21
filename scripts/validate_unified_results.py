#!/usr/bin/env python3
"""Validate both eras' published manifests and results without changing files."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "archive" / "data"

def verify(era, required):
    folder = ROOT if era == "original" else ROOT / "modern"
    manifest_file = folder / "manifest.json"
    if not manifest_file.exists():
        if not required:
            print("Modern era not yet imported; historical records remain available.")
            return 0, 0
        raise ValueError(f"Missing {manifest_file}")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("era") != era or manifest.get("competition") != "World Song Contest":
        raise ValueError(f"{era}: incorrect manifest identity")
    editions = manifest.get("editions", [])
    if len(editions) != manifest.get("edition_count"):
        raise ValueError(f"{era}: edition-count mismatch")
    edition_keys = set()
    entry_ids = set()
    total = 0
    for item in editions:
        n = item["edition_number"]
        key = f"{era}:{n}"
        if not isinstance(n,int) or n < 1 or item["edition_key"] != key or key in edition_keys:
            raise ValueError(f"{era}: invalid/duplicate edition key")
        edition_keys.add(key)
        relative = f"editions/{n:03}.json"
        if item["path"] != relative:
            raise ValueError(f"{era}: unexpected path for edition {n}")
        path = folder / relative
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("era") != era or payload.get("edition_key") != key:
            raise ValueError(f"{era}: bad edition metadata for {n}")
        rows = payload.get("entries", [])
        if len(rows) != item["entries"]:
            raise ValueError(f"{era}: edition {n} entry count mismatch")
        if era == "original":
            finalists = sum(x.get("result_status") == "finalist" for x in rows)
            nq = sum(x.get("result_status") == "non_qualifier" for x in rows)
            if (finalists,nq) != (item["finalists"],item["non_qualifiers"]):
                raise ValueError(f"{era}: edition {n} status totals mismatch")
        for x in rows:
            entry_id=x.get("entry_id")
            if not isinstance(entry_id,str) or not entry_id.startswith(key+":") or entry_id in entry_ids:
                raise ValueError(f"{era}: bad or duplicate entry ID in {n}")
            entry_ids.add(entry_id)
            if x.get("era") != era or x.get("edition_key") != key or x.get("edition_number") != n:
                raise ValueError(f"{era}: wrong edition identity for {entry_id}")
            if not all(isinstance(x.get(t),str) and x[t].strip() for t in ("country","artist_credit","song_title","verification_status")):
                raise ValueError(f"{era}: required metadata missing for {entry_id}")
            if x.get("result_status") not in {"finalist","non_qualifier"}:
                raise ValueError(f"{era}: invalid status for {entry_id}")
            for col,minv in (("rank",1),("points",0)):
                val = x.get(col)
                if val is not None and (type(val) is not int or val < minv):
                    raise ValueError(f"{era}: invalid {col} for {entry_id}")
            url=x.get("source_url")
            if not isinstance(url,str) or not url.startswith(("https://","http://")):
                raise ValueError(f"{era}: missing source link for {entry_id}")
            if era=="original" and not url.startswith("https://web.archive.org/web/"):
                raise ValueError(f"{era}: original source must be Wayback URL for {entry_id}")
            total += 1
    if total != manifest.get("entry_count"):
        raise ValueError(f"{era}: total entries mismatch")
    print(f"PASS {era}: {len(editions)} editions, {total} entries")
    return len(editions),total

if __name__=="__main__":
    verify("original",True)
    verify("modern",False)
