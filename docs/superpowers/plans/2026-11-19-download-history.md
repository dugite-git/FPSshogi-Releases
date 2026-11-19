# Download History Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans and verification-before-completion. The user authorized implementation and specified three daily runs; routine implementation decisions do not require another approval.

**Goal:** Persist release download history three times daily and make the trend readable from GitHub.

**Architecture:** A Python standard-library collector records complete validated observations. A separate renderer derives a dedicated Japanese trends page, daily CSV, and SVG charts. The root README only links to that page, as requested. One serialized Actions workflow runs tests, collects data, renders reports, and commits only generated files to main.

**Tech Stack:** Python >=3.11, unittest, GitHub REST API, GitHub Actions, CSV/JSON/SVG.

**Spec:** `docs/superpowers/specs/2026-11-19-download-history-design.md`

## Global Constraints

- Repository: `dugite-git/FPSshogi-Releases`; default branch: `main`.
- Asset: `FPSshogi-Windows.zip`; schedule: UTC `17 0,8,16 * * *` (JST 01:17, 09:17, 17:17).
- No runtime third-party Python dependencies; no fabricated historical observations.
- Preserve deleted assets' last known counts; reject malformed or decreasing counters.
- Never commit a failed or incomplete fetch. Never force-push.

## Review Focus

- Pagination and API failures: complete fetch or no observation.
- New/deleted/replaced assets: totals remain explainable; first delta is unknown.
- Same run rerun: no duplicated observations; timestamps are strictly increasing for distinct runs.
- Japan date boundary: interval deltas grouped by observation date and clearly labeled.
- Concurrent main edits: normal push/rebase preserves other changes, without re-counting a sample.

## Task 1: Collector

Files: `scripts/collect_download_stats.py`, `tests/test_collect_download_stats.py`.

Interface: CLI `--repository OWNER/REPO --data-dir PATH [--input-json PATH] [--observed-at ISO8601] [--run-key KEY]`. `input-json` accepts the normal releases API array for fixture and bootstrap validation. `GH_TOKEN` is optional for public API reads.

Output: `state.json` with `schema_version`, `repository`, and `assets` keyed by ID. Each asset has `release_id`, `tag`, `name`, `download_count`, `active`, `first_seen_at`, `last_seen_at`. History columns: `observed_at_utc,observed_at_jst,run_key,active_downloads,total_downloads,new_downloads,release_count,asset_count,archived_asset_count`. Per-asset observation columns: `observed_at_utc,asset_id,release_id,tag,name,download_count,active`.

- [x] Write behavioral tests for first observation, later increment, pagination, new/deleted asset, malformed/failing fetch, decreasing counter and duplicate run; verify expected failures.
- [x] Implement collector and atomic file replacements after all validation.
- [x] Run `python3 -m unittest discover -s tests -v`; confirm all collector tests pass.

## Task 2: Report and Workflow

Files: `scripts/render_download_stats.py`, `tests/test_render_download_stats.py`, `.github/workflows/download-stats.yml`, `README.md`, `.gitignore`.

Interface: renderer CLI `--data-dir PATH`; reads Task 1 outputs and writes `trends.md`, `daily.csv`, `cumulative.svg`, `daily.svg`. Daily columns: `date_jst,new_downloads,observations,baseline_only`.

- [x] Test first-day baseline exclusion and Japan date grouping using literal observations; verify expected failures.
- [x] Implement reports with explicit units, sparse-data handling, and honest observation-interval semantics.
- [x] Add three-times-daily schedule, manual and path-filtered push trigger, pinned checkout, tests, authenticated API read, generated-path-only normal push with bounded rebase retry.
- [x] Run the full tests, process one live fetched API response, inspect generated charts, and review the final diff.

## Task 3: Publish and Verify

- [x] Fresh independent code review of collector, reporting, and workflow.
- [x] Publish the verified files to main through the authorized GitHub connector, preserving the latest branch head.
- [x] Observe an actual successful Actions run and the resulting history commit; confirm schedule, CSV rows, and report links.
- [x] Report schedule and direct links; distinguish a configured workflow from a verified successful run if blocked.

## Verification record

- Local full suite: 20 tests passed; staged diff whitespace check passed.
- Fresh independent review: no critical or important findings.
- Real API baseline: 31 Windows ZIP assets, 121 cumulative downloads at 2026-11-19 17:24:23 JST.
- Hosted workflow run [44488150347](https://github.com/dugite-git/FPSshogi-Releases/actions/runs/44488150347) completed successfully at 2026-11-19 17:30:41 JST. Tests, live collection, report generation and authenticated Git push all succeeded.
- Saved CSV confirmed a second observation at 17:30:35 JST, total 121, interval increase 0.
- Root README links to the separate stats/downloads/trends.md page; charts are not embedded in the root README.
