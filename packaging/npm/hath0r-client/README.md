# `@bayly-ai/hath0r`

Thin Node/TypeScript client for the **hath0r** operator CLI.

## Install

```sh
npm install @bayly-ai/hath0r
# engine must be installed separately:
#   pipx install hath0r-cli
#   or GitHub Release binary on PATH
```

## Usage

```ts
import { runOperation, runOperationJson } from "@bayly-ai/hath0r";

const result = await runOperation("version");
const { response } = await runOperationJson("doctor");
```

## Trust boundary

- Select operations by **name only** (`version | doctor | kb.path | kb.products`).
- Never forward HTTP/browser-supplied argv, paths, or env into `runOperation`.
- Spawn uses `shell: false`, timeouts, output caps, and a minimal env allowlist.

## Version matrix

Client major should track breaking changes to `hath0r.cli.response/1` / CLI major.
Current package version aligns with `hath0r-cli` **0.2.x**.
