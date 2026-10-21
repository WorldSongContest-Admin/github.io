#!/usr/bin/env python3
"""Convert recovered original-era WSC CSV into validated, provenance-rich JSON.
Usage:
  python scripts/build_historical_archive.py path/to/master.csv --out-dir data/historical
This script never modifies the existing application or modern results.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED = {
    "edition", "rank", "country_as_published", "artist_as_published",
    "song_as_published", "points", "qualification_status",
    "source_url", "verification_status",
}
VALID_STATUSES = {"final", "NQ"}

def numeric(value, field, row_num, errors):
    if not value.strip():
        return None
    try:
        v = Decimal(value)
        if not v.is_finite() or v != v.to_integral_value() or v < 0:
            raise InvalidOperation
        return int(v)
    except (InvalidOperation, ValueError):
        errors.append(f"CSV row {row_num}: invalid {field} {value!r}")
        return None

def transform(source):
    errors, warnings, rows = [], [], []
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED.difference(reader.fieldnames or ())
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
        for line, raw in enumerate(reader, 2):
            edition = numeric(raw["edition"], "edition", line, errors)
            rank = numeric(raw["rank"], "rank", line, errors)
            if edition is None or edition < 1 or rank is None or rank < 1:
                errors.append(f"CSV row {line}: edition and rank must be positive integers")
                continue
            status = raw["qualification_status"].strip()
            if status not in VALID_STATUSES:
                errors.append(f"CSV row {line}: unknown qualification status {status!r}")
            points = numeric(raw["points"], "points", line, errors)
            if status == "NQ" and points is not None:
                warnings.append(f"CSV row {line}: NQ has points; retained without correction")
            if status == "final" and points is None:
                warnings.append(f"CSV row {line}: finalist has no points")
            country = raw["country_as_published"].strip()
            artist = raw["artist_as_published"].strip()
            song = raw["song_as_published"].strip()
            if not all((country, artist, song)):
                errors.append(f"CSV row {line}: empty country, artist or song")
            source_url = raw["source_url"].strip()
            if not source_url.startswith("https://web.archive.org/web/"):
                warnings.append(f"CSV row {line}: non-Wayback source URL")
            identity = "\x1f".join((str(edition), country, artist, song))
            suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
            rows.append({
                "entry_id": f"original:{edition}:{suffix}",
                "edition_key": f"original:{edition}",
                "era": "original",
                "edition_number": edition,
                "rank": rank,
                "country": country,
                "artist_credit": artist,
                "song_title": song,
                "points": points,
                "result_status": "non_qualifier" if status == "NQ" else "finalist",
                "source_url": source_url,
                "verification_status": raw["verification_status"].strip() or "unverified",
            })
    ids = Counter(row["entry_id"] for row in rows)
    for key, count in ids.items():
        if count > 1:
            errors.append(f"Duplicate entry identity: {key} ({count} rows)")
    return rows, errors, warnings

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("data/historical"))
    args = parser.parse_args()
    entries, errors, warnings = transform(args.source)
    if errors:
        for item in errors: print("ERROR:", item)
        raise SystemExit(f"Import aborted: {len(errors)} error(s)")
    grouped = defaultdict(list)
    for entry in entries:
        grouped[entry["edition_number"]].append(entry)
    output = args.out_dir
    editions_dir = output / "editions"
    editions_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for number in sorted(grouped):
        edition_entries = grouped[number]
        payload = {
            "schema_version": 1,
            "edition_key": f"original:{number}",
            "era": "original",
            "edition_number": number,
            "entries": edition_entries,
        }
        (editions_dir / f"{number:03}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        summary.append({
            "edition_key": f"original:{number}",
            "edition_number": number,
            "entries": len(edition_entries),
            "finalists": sum(e["result_status"] == "finalist" for e in edition_entries),
            "non_qualifiers": sum(e["result_status"] == "non_qualifier" for e in edition_entries),
            "path": f"editions/{number:03}.json",
        })
    manifest = {
        "schema_version": 1, "competition": "World Song Contest",
        "era": "original", "verification": "provisional",
        "edition_count": len(grouped), "entry_count": len(entries), "editions": summary,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "import_warnings.json").write_text(
        json.dumps(warnings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {len(grouped)} editions, {len(entries)} records, {len(warnings)} warnings at {output}")

if __name__ == "__main__":
    main()
