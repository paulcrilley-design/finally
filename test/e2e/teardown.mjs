import { docker, stop, VOLUME } from "./app.mjs";

export default function teardown() {
  stop();
  docker("volume", "rm", "--force", VOLUME);
}
