#!/usr/bin/env python3
"""Import VERIFIED modern-era results without modifying historic records.

Input UTF-8 CSV fields:
 edition, country, artist, song, rank, points, status, source_url
 Optional: verification_status

Use --input results.csv --output archive/data/modern.
No scores are invented: blank ranks or points become null.
No publication is performed by this script.
"""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

FIELDS = {"edition", "country", "artist", "song", "rank", "points", "status", "source_url"}
STATUSES = {"finalist", "non_qualifier"}

def whole_number(value, field, line, allow_empty=False):
    value = (value or "").strip()
    if not value and allow_empty:
        return None
    if not value.isascii() or not value.isdecimal():
        raise ValueError(f"Row {line}: invalid {field}: {value!r}")
    number = int(value)
    if number < (0 if field == "points" else 1):
        raise ValueError(f"Row {line}: invalid {field}: {value!r}")
    return number

def convert(source, dest):
    records = defaultdict(list)
    seen = set()
    with source.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = FIELDS.difference(reader.fieldnames or ())
        if missing:
            raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
        for line, row in enumerate(reader, 2):
            number = whole_number(row["edition"], "edition", line)
            rank = whole_number(row["rank"], "rank", line, True)
            points = whole_number(row["points"], "points", line, True)
            country = row["country"].strip()
            artist = row["artist"].strip()
            song = row["song"].strip()
            status = row["status"].strip()
            url = row["source_url"].strip()
            if not all((country, artist, song)):
                raise ValueError(f"Row {line}: missing artist/song/country")
            if status not in STATUSES:
                raise ValueError(f"Row {line}: status must be finalist or non_qualifier")
            if not (url.startswith("https://") or url.startswith("http://")):
                raise ValueError(f"Row {line}: a source link is required")
            signature = "\x1f".join((str(number), country, artist, song))
            key = f"modern:{number}:" + hashlib.sha256(signature.encode()).hexdigest()[:16]
            if key in seen:
                raise ValueError(f"Row {line}: duplicate entry {key}")
            seen.add(key)
            records[number].append({
                "entry_id": key, "edition_key": f"modern:{number}",
                "era": "modern", "edition_number": number,
                "rank": rank, "country": country, "artist_credit": artist,
                "song_title": song, "points": points, "result_status": status,
                "source_url": url,
                "verification_status": (row.get("verification_status") or "source_needs_review").strip(),
            })
    if not records:
        raise ValueError("No verified modern records found")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "editions").mkdir(exist_ok=True)
    summary = []
    for n, entries in sorted(records.items()):
        filename = f"editions/{n:03}.json"
        (dest / filename).write_text(
            json.dumps({"schema_version": 1, "era": "modern",
                        "edition_key": f"modern:{n}", "edition_number": n,
                        "entries": entries}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
        )
        summary.append({"edition_key":f"modern:{n}", "edition_number":n,
                        "entries":len(entries), "path":filename})
    (dest / "manifest.json").write_text(json.dumps({
        "schema_version":1, "competition":"World Song Contest", "era":"modern",
        "edition_count":len(summary), "entry_count":len(seen), "editions":summary,
    }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Prepared {len(seen)} modern entries in {len(summary)} editions. No live data changed.")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", type=Path, default=Path("archive/data/modern"))
    args = p.parse_args()
    convert(args.input, args.output)
