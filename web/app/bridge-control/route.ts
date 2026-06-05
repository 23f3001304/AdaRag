// Local-dev convenience: start/check the host CLI bridge from the UI. This runs in the Next server
// (on your machine), so it can spawn the host process the Docker api forwards LLM/vision work to.
// Not for production: anyone who can reach this dev server could start the process.

import { spawn } from "child_process";
import path from "path";

import { NextResponse } from "next/server";

export const runtime = "nodejs";

const BRIDGE = process.env.BRIDGE_URL ?? "http://localhost:8088";

async function isUp(): Promise<boolean> {
  try {
    const r = await fetch(`${BRIDGE}/health`, { signal: AbortSignal.timeout(2000), cache: "no-store" });
    return r.ok;
  } catch {
    return false;
  }
}

export async function GET() {
  return NextResponse.json({ running: await isUp() });
}

export async function POST() {
  if (await isUp()) return NextResponse.json({ running: true, started: false });

  // The repo root is the parent of the Next app's cwd (web/); override with env vars if needed.
  const cwd = process.env.BRIDGE_CWD ?? path.resolve(process.cwd(), "..");
  const py = process.env.BRIDGE_PYTHON ?? path.join(cwd, ".venv", "Scripts", "python.exe");
  try {
    const child = spawn(
      py,
      ["-m", "uvicorn", "scripts.cli_bridge:app", "--host", "0.0.0.0", "--port", "8088"],
      { cwd, detached: true, stdio: "ignore", windowsHide: true },
    );
    child.unref();
  } catch (e) {
    return NextResponse.json({ running: false, started: false, error: String(e) }, { status: 500 });
  }

  // Give uvicorn a moment to bind before reporting back.
  await new Promise((r) => setTimeout(r, 2500));
  return NextResponse.json({ running: await isUp(), started: true });
}
