# Bot specification — verified biography portraits

PortraitSyncBot accepts a declarative config, supports bounded concurrency, dry run, resume, per-host pacing and circuit breakers. The adapter uses read-only Docker/psql export and parameter-safe COPY staging for updates; image retrieval is limited to public government and Wikimedia hosts with redirect validation. Exit status distinguishes infrastructure errors from fully processed but unresolved profiles. It never reports 100% picture coverage unless every profile is verified.

