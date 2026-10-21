# Original-era data (pending upload)

This folder is intentionally **not complete on GitHub yet**. The historical browser expects:

- `archive/data/manifest.json`
- `archive/data/editions/001.json` through `096.json`

The verified local upload package `wsc_github_archive_upload_ready.zip` contains all 97 JSON files at the exact expected repository paths. It contains **4,580 provisional entries** across 96 editions.

## Upload without changing the live site

1. Download and extract `wsc_github_archive_upload_ready.zip` from the ChatGPT conversation.
2. In GitHub, switch to **`feature/wsc-historical-archive-planning`** (not `main`).
3. Open `archive/data/`, click **Add file → Upload files**, and select `manifest.json` plus the `editions` directory contents, preserving the `editions/` subfolder. GitHub's browser upload may require dragging the entire folder rather than individually choosing files.
4. Commit these files directly to the **feature branch**, not `main`.
5. Check the **Verify WSC Historical Archive** GitHub Action. It should validate the manifest, all 96 edition files, and the 4,580 records.
6. The draft browser's source is at `archive/index.html`. Preview only after the data checks pass, then review integration with the main site.

The dataset retains published errors, uncertainty and provenance flags rather than silently correcting the original source. **Do not merge this draft PR until the browser and main application have both been tested.**
