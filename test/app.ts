// Runs the built `finally` image in a throwaway container and volume owned by these tests.
// The user's `finally` container and `finally-data` volume are never touched, and no .env is read.
import { execFileSync } from "node:child_process";

const IMAGE = "finally";
const CONTAINER = "finally-e2e";
const VOLUME = "finally-e2e-data";
const PORT = process.env.E2E_PORT ?? "8010";

export const BASE_URL = `http://127.0.0.1:${PORT}`;

function docker(...args: string[]): string {
  return execFileSync("docker", args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
}

async function waitForHealth(): Promise<void> {
  for (let attempt = 0; attempt < 120; attempt++) {
    try {
      const response = await fetch(`${BASE_URL}/api/health`, { signal: AbortSignal.timeout(2000) });
      if (response.ok) return;
    } catch {
      // Not listening yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`The app at ${BASE_URL} did not become healthy. See: docker logs ${CONTAINER}`);
}

export function removeApp(): void {
  if (docker("ps", "-aq", "--filter", `name=^${CONTAINER}$`)) docker("rm", "-f", CONTAINER);
  if (docker("volume", "ls", "-q", "--filter", `name=^${VOLUME}$`)) docker("volume", "rm", VOLUME);
}

/** A new container on an empty volume: the app seeds a fresh database. */
export async function freshApp(): Promise<void> {
  removeApp();
  docker(
    "run", "-d", "--name", CONTAINER, "-p", `127.0.0.1:${PORT}:8000`, "-v", `${VOLUME}:/app/db`,
    "-e", "LLM_MOCK=true", IMAGE,
  );
  await waitForHealth();
}

export function stopApp(): void {
  docker("stop", CONTAINER);
}

export async function startApp(): Promise<void> {
  docker("start", CONTAINER);
  await waitForHealth();
}
