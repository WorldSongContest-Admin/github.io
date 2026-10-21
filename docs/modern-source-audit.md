# Modern Era results: source audit (21 October 2026)

## Findings

The repository's existing root `index.html` is a static browseable results archive, not a JavaScript-backed results database.

- Approximately 1.21 MB, 42 source lines.
- 290 HTML result tables, 5,921 `<tr>` elements.
- Table headers: 243 occurrences of `Edition | Country | Artist | Song | Player | Result` and 47 occurrences of `Country | Artist | Song | Player | Result`.
- **No points column** appears in those tables, so final scores cannot be derived reliably from this file alone.
- No JavaScript scripts or network fetch calls were identified.
- This audit counts HTML structure only; table rows are not yet normalised or matched to modern editions.

## Verified alternative sources in the organiser's connected private storage

Separate completed-edition **final result workbooks** contain jury, televote, combined scores and final placing. In particular the Edition 47 final results workbook has explicit `TELEVOTE`, `JURY`, `COMBINED` and `PLACE` columns. This is a usable primary source for modern points.

Other private files include country/song statistics and an Original Era points history; do not confuse the latter with Modern Era final scores.

**Do not publish the private spreadsheet itself**, individual unpublished votes, or currently ongoing Edition 48 results. Any public import should contain only confirmed published final country-level points and placements, alongside publicly known entry identities.

## Next implementation

1. Read an already completed modern final workbook, infer its result table and validate combined points = jury + televote.
2. Cross-check each country's finalist identity against published edition entries from the static HTML archive.
3. Import only confirmed published rows using the existing `scripts/import_modern_results.py` adapter. Preserve true zeroes and null unknowns.
4. Add clear provenance to public entries without exposing private Drive file URLs or nonpublic ballots.
5. Review the imported edition on a draft branch before public deployment.
