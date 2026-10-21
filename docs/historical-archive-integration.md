# World Song Contest

Official World Song Contest application and historical archive project.

## Historical archive integration (planning)

The existing application and its modern-edition data must remain intact. Historical material from the original World Song Contest will be integrated into the same browsing experience, while preserving edition numbering and provenance.

### Data model principles
- `era`: `original` or `modern`, independent of edition number. The distinction is useful for disambiguation, not a separate competition identity.
- `edition_number`: integer from the corresponding original numbering sequence.
- `edition_key`: composite stable identifier, e.g. `original:54` or `modern:54`, to prevent collisions.
- `entry_id`: stable identifier within a particular edition and source row.
- `country`, `artist_credit`, `song_title`, `rank`, `points`, `result_status`: preserve values and uncertainty from historical evidence.
- `source_url`, `source_type`, `verification_status`, `verification_notes`: maintain an auditable trail back to original material.

### Safe roll-out
1. Review the structure of the existing large single-file application and its live data before touching it.
2. Add historical records as separate source-controlled data files, not as modifications to modern results.
3. Validate edition keys, entry counts, duplicates, rankings, source links and encoding.
4. Build a unified read-only search/browser that filters by era, edition, country and artist.
5. Verify modern results and qualifier-reveal functionality remain unchanged before deploying.
6. Preserve the original labels only when quoting or identifying an original historical source.

### Current recovery scope
- 96 recovered original-era editions, with 4,580 **provisional** result entries, including 15 newly recovered tied non-qualifiers.
- WSC 97–102: incomplete and not yet appropriate to import as fully verified editions.
- Artist name normalization and country histories are provisional; conflicts must be retained, not silently resolved.

The full historical archive data and quality-check CSVs are held separately from this repository pending import validation. This branch documents the integration without publishing incomplete or unverified records.
