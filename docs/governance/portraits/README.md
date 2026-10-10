# Verified biography portraits

Issue: Bayly-AI/HATH0R-CLI#384; consumer: Bayly-AI/1-Nation-ATC#133.

## Strategy
Resolve all current and historical identities using Bioguide IDs and curated executive mappings. Prefer government biography portraits; only fall back to the identity-linked Wikipedia biography when government candidates are unavailable. A populated URL is not verification.

## Procedure
Read profiles without changing identity data. Resolve government candidates, fetch image bytes with bounded requests, decode raster data and reject small/non-image payloads. Resolve Wikipedia only via a stored or crosswalk-linked title, never fuzzy name search. Record source page, final URL, SHA-256, dimensions, check time and failures. Apply only verified results with optimistic old-URL checks. Preserve prior data and record unresolved cases.

## Playbook
Run `hath0r portraits sync --config cfg/portraits.yaml` to mine and checkpoint without database writes. Review the JSONL report. Add `--apply` to write verified results; add `--resume` to reuse a completed checkpoint in the same run directory. Dry-run factory execution performs no requests or writes. Revalidate in a fresh run directory on later syncs.

## Runbook
HTTP 404/410 means missing. HTTP 403/429 and network failures are unverified, never evidence of absence. Respect Retry-After: a 429/503 is retried up to 4 times with Retry-After or exponential backoff, and every worker on that host slows down. The host circuit opens on the first 403, or once the host's throttle score (incremented per 429/503, decremented per success) reaches 12; after that the host is not requested again in this run. Retry unavailable hosts in a later run; do not bypass their controls. Every profile receives a terminal outcome, and the report exposes source errors. Rollback uses old_photo_url from the immutable run report. Do not overwrite concurrent edits.

## Workflow
Sync-Sources -> portrait bot -> government candidates -> identity-linked Wikipedia fallback -> decode -> provenance report -> verified-only database update -> edge API and browser checks.

## Bot specification
PortraitSyncBot accepts a declarative config, supports bounded concurrency, dry run, resume, per-host pacing and circuit breakers. The adapter uses read-only Docker/psql export and parameter-safe COPY staging for updates; image retrieval is limited to public government and Wikimedia hosts with redirect validation. Exit status distinguishes infrastructure errors from fully processed but unresolved profiles. It never reports 100% picture coverage unless every profile is verified.
