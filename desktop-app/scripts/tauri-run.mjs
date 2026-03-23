import { existsSync } from "node:fs";
import { delimiter } from "node:path";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import os from "node:os";

const isWin = process.platform === "win32";
const cargoBin = isWin ? `${os.homedir()}\\.cargo\\bin` : `${os.homedir()}/.cargo/bin`;
const cargoExe = isWin ? `${cargoBin}\\cargo.exe` : `${cargoBin}/cargo`;
const require = createRequire(import.meta.url);

function hasCargoAvailable(environment) {
  const probe = spawnSync("cargo", ["--version"], {
    stdio: "ignore",
    env: environment,
    shell: false,
  });
  return probe.status === 0;
}

const env = { ...process.env };
const currentPath = String(env.PATH || env.Path || "");
if (existsSync(cargoBin) && !currentPath.includes(cargoBin)) {
  const mergedPath = `${cargoBin}${delimiter}${currentPath}`;
  env.PATH = mergedPath;
  env.Path = mergedPath;
} else {
  env.PATH = currentPath;
  env.Path = currentPath;
}

if (!existsSync(cargoExe) && !hasCargoAvailable(env)) {
  console.error("No se encontro cargo (ni en ~/.cargo/bin ni en PATH).");
  console.error("Instala Rust con rustup o agrega cargo al PATH: https://rustup.rs/");
  process.exit(1);
}

const args = process.argv.slice(2);
const tauriCliEntrypoint = require.resolve("@tauri-apps/cli/tauri.js");
const result = spawnSync(process.execPath, [tauriCliEntrypoint, ...args], {
  stdio: "inherit",
  env,
  shell: false,
});

if (typeof result.status === "number") {
  process.exit(result.status);
}

process.exit(1);
