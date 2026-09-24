# Runbook: HATH0R CLI

> Canonical operations runbook for **HATH0R CLI**.  
> Satisfies Hath0r initialization gate **CR-HATH0R-INIT-001**.  
> Tech family: Python CLI / control tower. Peer reference: `/Users/raybayly/Development/OpenSource/hathor-cli/docs/hathor-guide-047-install-and-release-20260918.md`.

---

## 1. Overview

Product workspace initialized on the HATHOR Universal Project Layout (`layout: hathor-upl`).

---

## 2. Prerequisites

- Operator CLI: `hath0r` on PATH (pin 0.2.0)
- Framework checkout: `/Users/raybayly/Development/OpenSource/hath0r`
- Secrets: `/Users/raybayly/Development/.credentials/<service>/.env` (never commit)

---

## 3. Install / bootstrap

```bash
cd /Users/raybayly/Development/OpenSource/hathor-cli
./bin/hath0r-bootstrap.sh
```

---

## 4. Develop / quality / test / build

```bash
pip install -e '.[dev]'
hath0r --version
hath0r doctor
make test || pytest
```

---

## 5. Hath0r doctor

```bash
# standalone (default)
./bin/hath0r-bootstrap.sh

# optional suite doctor
export HATH0R_GROUP_ROOT=/Users/raybayly/Development/OpenSource   # or product group root
hath0r doctor
```

---

## 6. Deploy / rollback

Document host-specific deploy/rollback here as the product matures. Prefer sibling peer runbooks when available.

---

## 7. Promotion path (CR-BAI-001)

```text
local → development → testing → staging → master (Production)
```

- Issue first; branch from `development` using `feature|bugfix|.../<issue>-slug`
- Feature PRs target `development` only

---

## 8. Related

| Doc | Role |
|-----|------|
| Setup playbook | `/Users/raybayly/Development/OpenSource/hath0r/docs/developers/hathor-playbook-001-repo-init-setup-20260919.md` |
| `AGENTS.md` | Product identity + agent rules |
| Peer runbook | `/Users/raybayly/Development/OpenSource/hathor-cli/docs/hathor-guide-047-install-and-release-20260918.md` |
