# Checklist — OpenTelemetry adherence (#60)

- [ ] `cfg/observability/otel.json` present (or inherits control tower)
- [ ] Resource attrs: service.name, namespace/group, deployment.environment
- [ ] OTLP endpoint via env; headers secret via env only
- [ ] No tokens in git
- [ ] HTTP/MCP path creates spans when service is long-running
- [ ] Docs link from AGENTS or product README
