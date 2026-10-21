#!/usr/bin/env python3
"""Validate and install an original-era historical archive package.

Usage:
  python scripts/install_historical_archive.py path/to/wsc_historical_browser_all_column_filters.zip --check
  python scripts/install_historical_archive.py path/to/wsc_historical_browser_all_column_filters.zip

--check checks the package without changing files.
Without --check, the script writes archive/data/ and preserves archive/index.html.
"""
import argparse
import json
import shutil
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "archive" / "data"

def validate(dataset):
    manifest_path = dataset / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Missing manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    editions = manifest.get("editions", [])
    if manifest.get("era") != "original" or manifest.get("competition") != "World Song Contest":
        raise ValueError("Incorrect competition or era")
    if len(editions) != manifest.get("edition_count"):
        raise ValueError("Edition count mismatch")
    if len(set(e["edition_key"] for e in editions)) != len(editions):
        raise ValueError("Repeated edition keys")
    seen, total, statuses = set(), 0, Counter()
    for edition in editions:
        n = edition["edition_number"]
        path = edition["path"]
        if path != f"editions/{n:03}.json" or n < 1:
            raise ValueError(f"Unsafe or unexpected edition path: {path}")
        file = dataset / path
        if not file.is_file():
            raise ValueError(f"Missing edition: {path}")
        payload = json.loads(file.read_text(encoding="utf-8"))
        if payload.get("edition_key") != f"original:{n}" or payload.get("era") != "original":
            raise ValueError(f"Incorrect edition metadata in {path}")
        rows = payload.get("entries", [])
        if len(rows) != edition["entries"]:
            raise ValueError(f"Row count mismatch in {path}")
        if len(rows) != edition["finalists"] + edition["non_qualifiers"]:
            raise ValueError(f"Finalist/NQ count mismatch in {path}")
        for row in rows:
            key = row["entry_id"]
            if key in seen:
                raise ValueError(f"Duplicate entry identifier: {key}")
            seen.add(key)
            if row["edition_key"] != f"original:{n}" or row["edition_number"] != n:
                raise ValueError(f"Wrong edition in {path}: {key}")
            if row["result_status"] not in ("finalist", "non_qualifier"):
                raise ValueError(f"Unknown result status: {key}")
            if not row.get("artist_credit") or not row.get("song_title") or not row.get("country"):
                raise ValueError(f"Missing display values: {key}")
            if not row.get("source_url", "").startswith("https://web.archive.org/web/"):
                raise ValueError(f"Missing preserved original source URL: {key}")
            statuses[row["result_status"]] += 1
            total += 1
        if sum(row["result_status"] == "finalist" for row in rows) != edition["finalists"]:
            raise ValueError(f"Finalist count mismatch in {path}")
    if total != manifest["entry_count"]:
        raise ValueError("Total entry count mismatch")
    print(f"PASS: {len(editions)} original editions; {total} entries; {dict(statuses)}")
    return manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--check", action="store_true", help="Validate without installing")
    args = parser.parse_args()
    if not args.package.is_file():
        parser.error("Package not found")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        with zipfile.ZipFile(args.package) as archive:
            for info in archive.infolist():
                name = Path(info.filename)
                if info.filename.startswith("/") or ".." in name.parts:
                    raise ValueError("Invalid ZIP path")
                if info.is_dir():
                    continue
                if not (info.filename.endswith(".json") and "data" in name.parts):
                    continue
                pos = name.parts.index("data")
                relative = Path(*name.parts[pos + 1:])
                if not relative.parts:
                    continue
                out = root / relative
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(archive.read(info))
        manifest = validate(root)
        if args.check:
            return
        DEST.mkdir(parents=True, exist_ok=True)
        for item in manifest["editions"]:
            source = root / item["path"]
            target = DEST / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        shutil.copyfile(root / "manifest.json", DEST / "manifest.json")
        print(f"Installed historical archive at {DEST}")

if __name__ == "__main__":
    main()
