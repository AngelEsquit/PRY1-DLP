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

const child = process.platform === "win32"
  ? spawn("cmd.exe", ["/d", "/s", "/c", "npm run dev"], {
      stdio: "inherit",
      shell: false,
      cwd: process.cwd(),
      env: { ...process.env },
      windowsHide: false,
    })
  : spawn("npm", ["run", "dev"], {
      stdio: "inherit",
      shell: false,
      cwd: process.cwd(),
      env: { ...process.env },
    });

child.on("error", (error) => {
  console.error(`[tauri] No se pudo iniciar Vite: ${error.message}`);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
