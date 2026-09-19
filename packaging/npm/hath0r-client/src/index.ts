/**
 * @bayly-ai/hath0r — thin client for the hath0r operator CLI.
 *
 * Trust boundary: callers select a named operation only.
 * Never pass browser/HTTP-supplied argv into spawn.
 */

import { spawn } from "node:child_process";
import { accessSync, constants as fsConstants } from "node:fs";
import path from "node:path";

export const HATHOR_OPERATIONS = ["version", "doctor", "kb.path", "kb.products"] as const;
export type HathorOperation = (typeof HATHOR_OPERATIONS)[number];

/** Server/client-owned argv map — not configurable via untrusted input. */
export const OPERATION_MAP: Readonly<Record<HathorOperation, readonly string[]>> = Object.freeze({
  version: Object.freeze(["--output", "json", "--version"]),
  doctor: Object.freeze(["--output", "json", "doctor"]),
  "kb.path": Object.freeze(["--output", "json", "--quiet", "kb", "path"]),
  "kb.products": Object.freeze(["--output", "json", "kb", "products"]),
});

export const CLI_RESPONSE_SCHEMA = "hath0r.cli.response/1" as const;

export type CliState = "ok" | "degraded" | "unavailable" | "error";

export interface CliResponse {
  schema: typeof CLI_RESPONSE_SCHEMA;
  command: string;
  generated_at: string;
  state: CliState;
  data: Record<string, unknown> | null;
  diagnostics: unknown[];
  meta: { cli_version: string; duration_ms: number; [key: string]: unknown };
}

export interface RunnerResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
  signal: NodeJS.Signals | null;
  timedOut: boolean;
  truncated: boolean;
  durationMs: number;
}

export interface RunOptions {
  executable?: string;
  timeoutMs?: number;
  maxOutputBytes?: number;
  cwd?: string;
  env?: NodeJS.ProcessEnv;
}

const DEFAULT_TIMEOUT_MS = 10_000;
const DEFAULT_MAX_OUTPUT_BYTES = 64 * 1024;
const ALLOWED_ENV = ["PATH", "HOME", "HATH0R_GROUP_ROOT", "HATH0R_KB_PATH"] as const;

export class HathorClientError extends Error {
  constructor(
    message: string,
    readonly cause?: unknown,
  ) {
    super(message);
    this.name = "HathorClientError";
  }
}

export function isHathorOperation(value: string): value is HathorOperation {
  return (HATHOR_OPERATIONS as readonly string[]).includes(value);
}

export function buildMinimalEnv(source: NodeJS.ProcessEnv = process.env): Record<string, string> {
  const out: Record<string, string> = {};
  for (const key of ALLOWED_ENV) {
    const value = source[key];
    if (typeof value === "string" && value.length > 0) out[key] = value;
  }
  if (!out.PATH && typeof source.PATH === "string") out.PATH = source.PATH;
  return out;
}

export function resolveExecutable(override?: string, pathEnv: string = process.env.PATH ?? ""): string {
  if (override) {
    accessSync(override, fsConstants.X_OK);
    return override;
  }
  for (const dir of pathEnv.split(path.delimiter).filter(Boolean)) {
    for (const name of ["hath0r", "hath0r.exe"]) {
      const full = path.join(dir, name);
      try {
        accessSync(full, fsConstants.X_OK);
        return full;
      } catch {
        // continue
      }
    }
  }
  throw new HathorClientError("hath0r executable not found on PATH");
}

export function tryParseCliResponse(stdout: string): CliResponse | null {
  const trimmed = stdout.trim();
  if (!trimmed.startsWith("{")) return null;
  try {
    const parsed = JSON.parse(trimmed) as Partial<CliResponse>;
    if (parsed.schema !== CLI_RESPONSE_SCHEMA) return null;
    if (typeof parsed.command !== "string" || typeof parsed.state !== "string") return null;
    return parsed as CliResponse;
  } catch {
    return null;
  }
}

export async function runOperation(
  operation: HathorOperation,
  options: RunOptions = {},
): Promise<RunnerResult> {
  if (!isHathorOperation(operation)) {
    throw new HathorClientError(`unsupported operation: ${String(operation)}`);
  }
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const maxOutputBytes = options.maxOutputBytes ?? DEFAULT_MAX_OUTPUT_BYTES;
  const executable = resolveExecutable(options.executable, options.env?.PATH ?? process.env.PATH);
  const args = [...OPERATION_MAP[operation]];
  const env = buildMinimalEnv(options.env ?? process.env);
  const cwd = options.cwd ?? process.cwd();
  const started = Date.now();

  return await new Promise<RunnerResult>((resolve, reject) => {
    let child;
    try {
      child = spawn(executable, args, {
        shell: false,
        cwd,
        env,
        stdio: ["ignore", "pipe", "pipe"],
      });
    } catch (err) {
      reject(new HathorClientError(`Failed to spawn hath0r: ${String(err)}`, err));
      return;
    }

    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];
    let stdoutBytes = 0;
    let stderrBytes = 0;
    let truncated = false;
    let timedOut = false;
    let settled = false;

    const timer = setTimeout(() => {
      timedOut = true;
      try {
        child.kill("SIGKILL");
      } catch {
        // ignore
      }
    }, timeoutMs);

    const onChunk = (stream: "stdout" | "stderr", chunk: Buffer) => {
      const list = stream === "stdout" ? stdoutChunks : stderrChunks;
      let used = stream === "stdout" ? stdoutBytes : stderrBytes;
      if (used >= maxOutputBytes) {
        truncated = true;
        return;
      }
      const remaining = maxOutputBytes - used;
      if (chunk.length > remaining) {
        list.push(chunk.subarray(0, remaining));
        used = maxOutputBytes;
        truncated = true;
        try {
          child.kill("SIGKILL");
        } catch {
          // ignore
        }
      } else {
        list.push(chunk);
        used += chunk.length;
      }
      if (stream === "stdout") stdoutBytes = used;
      else stderrBytes = used;
    };

    child.stdout?.on("data", (c: Buffer) => onChunk("stdout", c));
    child.stderr?.on("data", (c: Buffer) => onChunk("stderr", c));
    child.on("error", (err) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(new HathorClientError(`hath0r spawn error: ${err.message}`, err));
    });
    child.on("close", (code, signal) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({
        exitCode: code,
        stdout: Buffer.concat(stdoutChunks).toString("utf8"),
        stderr: Buffer.concat(stderrChunks).toString("utf8"),
        signal,
        timedOut,
        truncated,
        durationMs: Math.max(0, Date.now() - started),
      });
    });
  });
}

export async function runOperationJson(
  operation: HathorOperation,
  options: RunOptions = {},
): Promise<{ result: RunnerResult; response: CliResponse | null }> {
  const result = await runOperation(operation, options);
  return { result, response: tryParseCliResponse(result.stdout) };
}
