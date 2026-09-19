import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  HATHOR_OPERATIONS,
  OPERATION_MAP,
  buildMinimalEnv,
  isHathorOperation,
  tryParseCliResponse,
} from "./index.js";

describe("operations", () => {
  it("exposes four frozen operations with json output", () => {
    assert.equal(HATHOR_OPERATIONS.length, 4);
    assert.ok(Object.isFrozen(OPERATION_MAP));
    for (const op of HATHOR_OPERATIONS) {
      assert.ok(Object.isFrozen(OPERATION_MAP[op]));
      assert.equal(OPERATION_MAP[op][0], "--output");
      assert.ok(OPERATION_MAP[op].includes("json"));
    }
    assert.equal(isHathorOperation("version"), true);
    assert.equal(isHathorOperation("rm -rf"), false);
  });
});

describe("buildMinimalEnv", () => {
  it("allowlists only approved keys", () => {
    const env = buildMinimalEnv({
      PATH: "/usr/bin",
      HOME: "/tmp",
      HATH0R_GROUP_ROOT: "/g",
      SECRET: "nope",
    });
    assert.deepEqual(env, {
      PATH: "/usr/bin",
      HOME: "/tmp",
      HATH0R_GROUP_ROOT: "/g",
    });
  });
});

describe("tryParseCliResponse", () => {
  it("accepts hath0r.cli.response/1", () => {
    const body = JSON.stringify({
      schema: "hath0r.cli.response/1",
      command: "version",
      generated_at: "2026-09-18T00:00:00Z",
      state: "ok",
      data: { version: "0.2.0" },
      diagnostics: [],
      meta: { cli_version: "0.2.0", duration_ms: 1 },
    });
    const parsed = tryParseCliResponse(body);
    assert.ok(parsed);
    assert.equal(parsed?.state, "ok");
  });

  it("rejects wrong schema", () => {
    const body = JSON.stringify({
      schema: "hath0r.cli.response/2",
      command: "version",
      state: "ok",
    });
    assert.equal(tryParseCliResponse(body), null);
  });
});
