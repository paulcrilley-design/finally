// The app under test: its own container, volume and port, so your data is never touched.
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new globalThis.URL("../../", import.meta.url));
const PORT = process.env.E2E_PORT || "8765";

export const CONTAINER = "finally-e2e";
export const VOLUME = "finally-e2e-data";
export const URL = `http://localhost:${PORT}`;

const env = {
  ...process.env,
  FINALLY_CONTAINER: CONTAINER,
  FINALLY_VOLUME: VOLUME,
  FINALLY_PORT: PORT,
  FINALLY_ENV_FILE: "", // no keys: the models are mocked and the simulator is used
  LLM_MOCK: "true",
};

const run = (command, args) => execFileSync(command, args, { cwd: ROOT, env, stdio: "inherit" });

export const start = (...args) => run("scripts/start_mac.sh", args);
export const stop = () => run("scripts/stop_mac.sh", []);
export const docker = (...args) => run("docker", args);
