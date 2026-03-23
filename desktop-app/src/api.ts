import { invoke } from "@tauri-apps/api/core";
import type { FileNode, YalexAction } from "./types";

const TAURI_INVOKE_TIMEOUT_MS = 15000;

// Check if window is defined (not in SSR context)
function isWindowDefined(): boolean {
  return typeof window !== "undefined";
}

// Detect if we're running inside Tauri
// This will be true if @tauri-apps/api succeeded to import and inject
export function isTauriRuntime(): boolean {
  if (!isWindowDefined()) {
    return false;
  }

  const runtime = window as unknown as {
    __TAURI__?: unknown;
    __TAURI_INTERNALS__?: { invoke?: unknown };
  };

  return Boolean(runtime.__TAURI__) || typeof runtime.__TAURI_INTERNALS__?.invoke === "function";
}

async function invokeTauri<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  if (!isWindowDefined()) {
    throw new Error("Not in browser environment - cannot call Tauri commands");
  }

  if (!isTauriRuntime()) {
    throw new Error(
      "Runtime Tauri no disponible. Inicie la app con `npm run tauri -- dev` dentro de `desktop-app`."
    );
  }

  let timeoutHandle: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timeoutHandle = setTimeout(() => {
      reject(new Error(`Timeout ejecutando '${command}' (${TAURI_INVOKE_TIMEOUT_MS} ms)`));
    }, TAURI_INVOKE_TIMEOUT_MS);
  });

  try {
    console.debug(`[Tauri] Invoking: ${command}`, args);
    const result = await Promise.race([invoke<T>(command, args), timeoutPromise]);
    console.debug(`[Tauri] Command '${command}' succeeded`);
    return result;
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error(`[Tauri] Command '${command}' failed: ${errorMsg}`, { error, args });
    throw new Error(`Failed to execute command '${command}': ${errorMsg}`);
  } finally {
    if (timeoutHandle) {
      clearTimeout(timeoutHandle);
    }
  }
}

export async function ping(): Promise<string> {
  console.log("[API] ping called");
  try {
    const result = await invokeTauri<string>("ping");
    console.log("[API] ping returned:", result);
    return result;
  } catch (error) {
    console.error("[API] ping failed:", error);
    throw error;
  }
}

export async function getWorkspaceRoot(): Promise<string> {
  console.log("[API] getWorkspaceRoot called");
  try {
    const result = await invokeTauri<string>("get_workspace_root");
    console.log("[API] getWorkspaceRoot returned:", result);
    return result;
  } catch (error) {
    console.error("[API] getWorkspaceRoot failed:", error);
    throw error;
  }
}

export async function listEntries(path: string): Promise<FileNode[]> {
  console.log("[API] listEntries called with path:", path);
  try {
    const result = await invokeTauri<FileNode[]>("list_entries", { path });
    console.log("[API] listEntries returned", result.length, "entries");
    return result;
  } catch (error) {
    console.error("[API] listEntries failed:", { error, path });
    throw error;
  }
}

export async function readTextFile(path: string): Promise<string> {
  console.log("[API] readTextFile called with path:", path);
  try {
    const result = await invokeTauri<string>("read_text_file", { path });
    console.log("[API] readTextFile success, got", result.length, "characters");
    return result;
  } catch (error) {
    console.error("[API] readTextFile failed:", {error, path});
    throw error;
  }
}

export async function writeTextFile(path: string, content: string): Promise<void> {
  await invokeTauri("write_text_file", { path, content });
}

export async function createDirectory(path: string): Promise<void> {
  await invokeTauri("create_directory", { path });
}

export async function pickDirectory(): Promise<string | null> {
  return invokeTauri("pick_directory");
}

export async function copyFile(src: string, dest: string): Promise<void> {
  await invokeTauri("copy_file", { src, dest });
}

export async function moveFile(src: string, dest: string): Promise<void> {
  await invokeTauri("move_file", { src, dest });
}

export async function deleteFile(path: string): Promise<void> {
  await invokeTauri("delete_file", { path });
}

export async function runYalex(payload: {
  action: YalexAction;
  yalPath?: string;
  yalSource?: string;
  inputPath?: string;
  inputText?: string;
  includeTrace?: boolean;
  traceLimit?: number;
  outputPath?: string;
}): Promise<unknown> {
  const raw = await invokeTauri<string>("run_yalex_bridge", { payloadJson: JSON.stringify(payload) });
  return JSON.parse(raw);
}
