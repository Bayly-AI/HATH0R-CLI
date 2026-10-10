# Runbook — verified biography portraits

HTTP 404/410 means missing. HTTP 403/429 and network failures are unverified, never evidence of absence. Respect Retry-After: a 429/503 is retried up to 4 times with Retry-After or exponential backoff, and every worker on that host slows down. The host circuit opens on the first 403, or once the host's throttle score (incremented per 429/503, decremented per success) reaches 12; after that the host is not requested again in this run. Retry unavailable hosts in a later run; do not bypass their controls. Every profile receives a terminal outcome, and the report exposes source errors. Rollback uses old_photo_url from the immutable run report. Do not overwrite concurrent edits.

