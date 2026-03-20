import { invoke } from "@tauri-apps/api/core";
import type { FileNode, YalexAction } from "./types";

export async function getWorkspaceRoot(): Promise<string> {
  return invoke("get_workspace_root");
}

export async function listEntries(path: string): Promise<FileNode[]> {
  return invoke("list_entries", { path });
}

export async function readTextFile(path: string): Promise<string> {
  return invoke("read_text_file", { path });
}

export async function writeTextFile(path: string, content: string): Promise<void> {
  await invoke("write_text_file", { path, content });
}

export async function createDirectory(path: string): Promise<void> {
  await invoke("create_directory", { path });
}

export async function pickDirectory(): Promise<string | null> {
  return invoke("pick_directory");
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
  const raw = await invoke<string>("run_yalex_bridge", { payloadJson: JSON.stringify(payload) });
  return JSON.parse(raw);
}
