import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { ExtensionHath0rClient } from "../dist/client.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

test("Hath0r VSCode Extension Manifest & Structure Verification", () => {
  const pkgPath = resolve(__dirname, "../package.json");
  assert.ok(existsSync(pkgPath), "package.json must exist");

  const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));
  assert.equal(pkg.name, "hath0r-vscode");
  assert.equal(pkg.publisher, "BaylyAI");
  assert.equal(pkg.engines?.vscode, "^1.80.0");
  assert.ok(pkg.contributes?.commands?.length >= 5, "Must declare core commands");
  assert.ok(pkg.contributes?.views?.["hath0r-explorer"]?.length >= 4, "Must contribute 4 control plane views");
  assert.ok(existsSync(resolve(__dirname, "../media/hath0r.svg")), "SVG icon must exist");
  assert.ok(existsSync(resolve(__dirname, "../media/hath0r.png")), "PNG icon must exist");
});

test("Hath0r Extension Client CLI Bridge Test", async () => {
  const root = resolve(__dirname, "../../..");
  const client = new ExtensionHath0rClient(root);

  const doctor = await client.runDoctor();
  assert.equal(typeof doctor.status, "string");
  assert.ok(doctor.checks_passed >= 0);

  const finops = await client.runFinOps();
  assert.ok(finops.script_families_audited >= 10, "FinOps must audit script families");
});
