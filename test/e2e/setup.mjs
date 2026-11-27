import { docker, start, stop, VOLUME } from "./app.mjs";

export default function setup() {
  stop();
  docker("volume", "rm", "--force", VOLUME); // a fresh database every run
  start("--build");
}
