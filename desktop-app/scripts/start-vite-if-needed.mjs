import net from "node:net";
import { spawn } from "node:child_process";

const HOST = "127.0.0.1";
const PORT = 1420;

function isPortOpen(host, port, timeoutMs = 700) {
  return new Promise((resolve) => {
    const socket = new net.Socket();

    const finish = (result) => {
      socket.removeAllListeners();
      socket.destroy();
      resolve(result);
    };

    socket.setTimeout(timeoutMs);
    socket.once("connect", () => finish(true));
    socket.once("timeout", () => finish(false));
    socket.once("error", () => finish(false));

    socket.connect(port, host);
  });
}

const alreadyRunning = await isPortOpen(HOST, PORT);

if (alreadyRunning) {
  console.log(`[tauri] Reutilizando servidor Vite existente en http://${HOST}:${PORT}`);
  process.exit(0);
}

const cmd = process.platform === "win32" ? "npm.cmd" : "npm";
const child = spawn(cmd, ["run", "dev"], {
  stdio: "inherit",
  shell: false,
  env: process.env,
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
