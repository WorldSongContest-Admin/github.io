# Importing verified Modern Era results

The original-era records (96 editions, 4,580 provisional entries) already live at `archive/data/`.
The combined browser can show Modern Era records once we provide a verified modern dataset.
No scores have been imported or fabricated.

## 1. Identify the source

The existing WSC application's `index.html` is approximately 1.2 MB and contains much of the application logic. Before importing modern results:

```bash
python scripts/inspect_main_app.py index.html --json > modern_app_inventory.json
```

Review the inventory to identify where the app stores **published results**. Submissions, running totals,
semifinal votes and unrevealed ballots are not substitutes for final edition results.
Do not include private voting data or unpublished current-edition results in a public archive.

## 2. Prepare an audited CSV

Create a UTF-8 CSV using exactly these required headers:

```csv
edition,country,artist,song,rank,points,status,source_url,verification_status
```

One row per entry. Use `finalist` or `non_qualifier` for status. Leave unknown final rank or points
**blank**, never `0`. Points `0` is a genuine zero-point result and must not represent an unknown.
Retain original numeric scores as published; do not normalise historical scores.

**Every row must have a real source URL and the appropriate verification status.** Do not use example
or invented scores, artist names, or sources in the actual import.

## 3. Convert and validate locally

```bash
python scripts/import_modern_results.py --input modern_verified_results.csv --output archive/data/modern
```

This creates `archive/data/modern/manifest.json` and an edition file per imported modern edition.
The combined browser uses the composite keys `original:1` and `modern:1`; identical edition
numbers will not collide. The Original Era browser continues to work without the Modern Era data.

## 4. Review before publishing

- Match imported totals, placements and points against the official published result source.
- Check country/artist/song identities and Unicode characters.
- Keep unreleased edition results private.
- Test filters for both eras, range filters for points and rank, and linked source pages.
- Review the draft pull request before merging. **Do not alter the live voting system.**

## Still required

We have not extracted the modern competition's full original source data because the GitHub
connector cannot return the entire large app file. The new inspection script lets us analyse
a local checkout of that file, without assuming a schema or guessing any results.
