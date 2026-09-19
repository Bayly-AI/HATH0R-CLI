# Golden CLI contract fixtures

Canonical `hath0r.cli.response/1` success and error fixtures for machine consumers
(especially the HATHOR POC adapter).

| File | Command | State | Notes |
|------|---------|-------|-------|
| `version-ok.json` | `version` | ok | SemVer payload |
| `doctor-ok.json` | `doctor` | ok | All checks pass |
| `doctor-degraded.json` | `doctor` | degraded | Exit class 6 |
| `kb-path-ok.json` | `kb.path` | ok | Mock path only |
| `kb-path-missing.json` | `kb.path` | unavailable | `KNOWLEDGEBASE_NOT_FOUND` |
| `kb-products-ok.json` | `kb.products` | ok | Three suite products |
| `kb-products-missing.json` | `kb.products` | unavailable | `PRODUCT_CATALOG_NOT_FOUND` |
| `kb-products-invalid.json` | `kb.products` | error | `PRODUCT_CATALOG_INVALID` |

Rules:

- No real home paths or secrets
- Fixed `generated_at` and `meta.cli_version` (`0.2.0`)
- Validated in CI/tests against Framework schemas under `hath0r/lib/schemas/`
