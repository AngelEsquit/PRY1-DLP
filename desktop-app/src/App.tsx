import saveIcon from "../src-tauri/icons/svg/save.svg";
import {
  useEffect,
  useMemo,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import Editor, { type Monaco } from "@monaco-editor/react";
import {
  createDirectory,
  getWorkspaceRoot,
  listEntries,
  pickDirectory,
  readTextFile,
  runYalex,
  writeTextFile,
} from "./api";
import type { FileNode, OpenTab, YalexAction } from "./types";
import filePlusIcon from "../src-tauri/icons/svg/file-plus.svg";
import folderPlusIcon from "../src-tauri/icons/svg/folder-plus.svg";

type OutputItem = {
  ts: string;
  type: "info" | "ok" | "error";
  text: string;
};

const YAL_ACTIONS: Array<{ id: YalexAction; label: string }> = [
  { id: "spec", label: "Spec (JSON)" },
  { id: "ast", label: "AST" },
  { id: "nfa", label: "NFA" },
  { id: "combinedNfa", label: "Combined NFA" },
  { id: "dfa", label: "DFA" },
  { id: "tokenize", label: "Tokenize" },
  { id: "generate", label: "Generate Lexer" },
];

const ACTION_HELP: Record<YalexAction, string> = {
  spec: "Extrae la especificación parseada en JSON.",
  ast: "Construye y muestra el árbol sintáctico de regex.",
  nfa: "Genera el AFN por reglas tokenizadas.",
  combinedNfa: "Muestra el AFN combinado con prioridades.",
  dfa: "Construye y minimiza el AFD final.",
  tokenize: "Tokeniza una entrada por archivo o texto directo.",
  generate: "Genera un lexer Python autónomo.",
};

const PANEL_STORAGE_KEY = "yalex-studio.panel-sizes.v1";

type PanelSizes = {
  sidebarWidth: number;
  rightPanelWidth: number;
  resultPanelHeight: number;
  outputPanelHeight: number;
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function parseSavedSizes(raw: string | null): PanelSizes | null {
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<PanelSizes>;
    if (
      typeof parsed.sidebarWidth !== "number" ||
      typeof parsed.rightPanelWidth !== "number" ||
      typeof parsed.resultPanelHeight !== "number" ||
      typeof parsed.outputPanelHeight !== "number"
    ) {
      return null;
    }

    return {
      sidebarWidth: clamp(parsed.sidebarWidth, 220, 520),
      rightPanelWidth: clamp(parsed.rightPanelWidth, 260, 560),
      resultPanelHeight: clamp(parsed.resultPanelHeight, 160, 500),
      outputPanelHeight: clamp(parsed.outputPanelHeight, 120, 440),
    };
  } catch {
    return null;
  }
}

function nowTime(): string {
  return new Date().toLocaleTimeString();
}

function isTextFile(name: string): boolean {
  const lowered = name.toLowerCase();
  return (
    lowered.endsWith(".py") ||
    lowered.endsWith(".rs") ||
    lowered.endsWith(".toml") ||
    lowered.endsWith(".lock") ||
    lowered.endsWith(".md") ||
    lowered.endsWith(".txt") ||
    lowered.endsWith(".yal") ||
    lowered.endsWith(".yaml") ||
    lowered.endsWith(".yml") ||
    lowered.endsWith(".json") ||
    lowered.endsWith(".sh")
  );
}

function inferSeparator(path: string): "\\" | "/" {
  return path.includes("\\") ? "\\" : "/";
}

function trimTrailingSeparators(path: string): string {
  return path.replace(/[\\/]+$/, "");
}

function joinPath(base: string, ...segments: string[]): string {
  const sep = inferSeparator(base || "");
  const cleanedBase = trimTrailingSeparators(base);
  const cleanedSegments = segments.map((segment) => segment.replace(/^[\\/]+|[\\/]+$/g, ""));
  return [cleanedBase, ...cleanedSegments].filter(Boolean).join(sep);
}

function getPathBaseName(path: string): string {
  if (!path) {
    return "";
  }
  const normalized = path.replace(/[/\\]+$/, "");
  const parts = normalized.split(/[/\\]/);
  return parts[parts.length - 1] || normalized;
}

function getParentPath(path: string): string {
  if (!path) {
    return "";
  }
  const normalized = trimTrailingSeparators(path);
  const parts = normalized.split(/[\\/]/);
  if (parts.length <= 1) {
    return normalized;
  }
  const sep = inferSeparator(normalized);
  return parts.slice(0, -1).join(sep);
}

function languageFromFileName(name: string): string {
  const lowered = name.toLowerCase();
  if (lowered.endsWith(".py")) return "python";
  if (lowered.endsWith(".rs")) return "rust";
  if (lowered.endsWith(".md")) return "markdown";
  if (lowered.endsWith(".json")) return "json";
  if (lowered.endsWith(".yaml") || lowered.endsWith(".yml")) return "yaml";
  if (lowered.endsWith(".toml")) return "ini";
  if (lowered.endsWith(".sh")) return "shell";
  if (lowered.endsWith(".txt") || lowered.endsWith(".lock") || lowered.endsWith(".yal")) {
    return "plaintext";
  }
  return "plaintext";
}

function registerEditorTheme(monaco: Monaco) {
  monaco.editor.defineTheme("yalex-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "7CC7FF" },
      { token: "keyword.control", foreground: "7CC7FF" },
      { token: "type", foreground: "84E1BC" },
      { token: "string", foreground: "E6C07B" },
      { token: "number", foreground: "EFA8FF" },
      { token: "comment", foreground: "6F7D9A", fontStyle: "italic" },
      { token: "function", foreground: "5CE086" },
      { token: "delimiter", foreground: "A9C3FF" },
      { token: "operator", foreground: "36C3FF" },
    ],
    colors: {
      "editor.background": "#0F1521",
      "editor.foreground": "#DBE4FF",
      "editor.lineHighlightBackground": "#182238",
      "editorCursor.foreground": "#36C3FF",
      "editor.selectionBackground": "#2A3B63",
      "editor.inactiveSelectionBackground": "#223352",
      "editorLineNumber.foreground": "#607194",
      "editorLineNumber.activeForeground": "#A9C3FF",
      "editorIndentGuide.background1": "#1D2B46",
      "editorIndentGuide.activeBackground1": "#35507D",
      "editorWhitespace.foreground": "#24324E",
    },
  });
}

export function App() {
  const restoredSizes = useMemo(
    () =>
      parseSavedSizes(
        typeof window === "undefined" ? null : window.localStorage.getItem(PANEL_STORAGE_KEY)
      ),
    []
  );

  const [workspaceRoot, setWorkspaceRoot] = useState<string>("");
  const [treeMap, setTreeMap] = useState<Record<string, FileNode[]>>({});
  const [expandedDirs, setExpandedDirs] = useState<Record<string, boolean>>({});
  const [selectedPath, setSelectedPath] = useState<string>("");

  const [tabs, setTabs] = useState<OpenTab[]>([]);
  const [activeTabPath, setActiveTabPath] = useState<string>("");

  const [output, setOutput] = useState<OutputItem[]>([]);
  const [latestResult, setLatestResult] = useState<string>("Sin resultados todavía.");

  const [yalFilePath, setYalFilePath] = useState<string>("");
  const [inputFilePath, setInputFilePath] = useState<string>("");
  const [generateOutputPath, setGenerateOutputPath] = useState<string>("");
  const [tokenizeMode, setTokenizeMode] = useState<"path" | "text">("path");
  const [tokenizeText, setTokenizeText] = useState<string>("a a a\n");
  const [selectedAction, setSelectedAction] = useState<YalexAction>("spec");
  const [isRunningAction, setIsRunningAction] = useState<boolean>(false);
  const [sidebarWidth, setSidebarWidth] = useState<number>(restoredSizes?.sidebarWidth ?? 290);
  const [rightPanelWidth, setRightPanelWidth] = useState<number>(
    restoredSizes?.rightPanelWidth ?? 340
  );
  const [resultPanelHeight, setResultPanelHeight] = useState<number>(
    restoredSizes?.resultPanelHeight ?? 270
  );
  const [outputPanelHeight, setOutputPanelHeight] = useState<number>(
    restoredSizes?.outputPanelHeight ?? 180
  );
  const [resizeState, setResizeState] = useState<{
    target: "sidebar" | "rightPanel" | "resultPanel" | "outputPanel";
    startX: number;
    startY: number;
    startSidebarWidth: number;
    startRightPanelWidth: number;
    startResultPanelHeight: number;
    startOutputPanelHeight: number;
  } | null>(null);
  const [pendingCreate, setPendingCreate] = useState<{
    type: "file" | "folder";
    parentDir: string;
    draftName: string;
  } | null>(null);

  const activeTab = useMemo(
    () => tabs.find((tab) => tab.path === activeTabPath) ?? null,
    [tabs, activeTabPath]
  );

  function pushOutput(type: OutputItem["type"], text: string) {
    setOutput((prev) => [...prev, { ts: nowTime(), type, text }]);
  }

  async function loadDir(path: string) {
    try {
      const nodes = await listEntries(path);
      setTreeMap((prev) => ({ ...prev, [path]: nodes }));
      return nodes;
    } catch (error) {
      pushOutput("error", `No se pudo listar ${path}: ${String(error)}`);
      return null;
    }
  }

  async function openWorkspaceRoot(path: string) {
    const clean = path.trim();
    if (!clean) {
      pushOutput("error", "Ingrese una ruta de directorio.");
      return;
    }

    const nodes = await loadDir(clean);
    if (!nodes) {
      return;
    }

    setWorkspaceRoot(clean);
    setSelectedPath(clean);
    setTreeMap({ [clean]: nodes });
    setExpandedDirs({ [clean]: true });
    pushOutput("ok", `Directorio abierto: ${clean}`);
  }

  async function openWorkspaceRootFromDialog() {
    try {
      const selected = await pickDirectory();
      if (!selected) {
        return;
      }
      await openWorkspaceRoot(selected);
    } catch (error) {
      pushOutput("error", `No se pudo abrir selector de carpeta: ${String(error)}`);
    }
  }

  function isKnownDirectory(path: string): boolean {
    if (!path) {
      return false;
    }
    if (path === workspaceRoot) {
      return true;
    }
    for (const dirEntries of Object.values(treeMap)) {
      const match = dirEntries.find((entry) => entry.path === path);
      if (match?.isDir) {
        return true;
      }
    }
    return false;
  }

  function resolveCreationTargetDir(): string {
    if (!selectedPath) {
      return workspaceRoot;
    }
    if (isKnownDirectory(selectedPath)) {
      return selectedPath;
    }
    return getParentPath(selectedPath) || workspaceRoot;
  }

  async function startInlineCreate(type: "file" | "folder") {
    const targetDir = resolveCreationTargetDir();
    if (!targetDir) {
      pushOutput("error", "No se pudo determinar directorio destino.");
      return;
    }

    if (!treeMap[targetDir]) {
      await loadDir(targetDir);
    }

    setExpandedDirs((prev) => ({ ...prev, [targetDir]: true }));
    setPendingCreate({
      type,
      parentDir: targetDir,
      draftName: type === "file" ? "new_file.txt" : "new_folder",
    });
  }

  async function commitInlineCreate() {
    if (!pendingCreate) {
      return;
    }

    const itemName = pendingCreate.draftName.trim();
    if (!itemName) {
      pushOutput("error", "Ingrese un nombre válido.");
      return;
    }
    if (itemName.includes("\\") || itemName.includes("/")) {
      pushOutput("error", "Use solo el nombre, sin rutas.");
      return;
    }

    const fullPath = joinPath(pendingCreate.parentDir, itemName);

    try {
      if (pendingCreate.type === "folder") {
        await createDirectory(fullPath);
        pushOutput("ok", `Carpeta creada: ${fullPath}`);
      } else {
        await writeTextFile(fullPath, "");
        pushOutput("ok", `Archivo creado: ${fullPath}`);
      }
      await loadDir(pendingCreate.parentDir);
      if (pendingCreate.type === "file") {
        await openFile(fullPath);
      }
      setPendingCreate(null);
    } catch (error) {
      pushOutput("error", `No se pudo crear ${pendingCreate.type}: ${String(error)}`);
    }
  }

  async function refreshExplorerRoot(showMessage = true) {
    if (!workspaceRoot) {
      return;
    }
    await loadDir(workspaceRoot);
    if (showMessage) {
      pushOutput("info", "Explorer recargado.");
    }
  }

  async function toggleDir(path: string) {
    setSelectedPath(path);
    const isOpen = Boolean(expandedDirs[path]);
    if (isOpen) {
      setExpandedDirs((prev) => ({ ...prev, [path]: false }));
      return;
    }
    if (!treeMap[path]) {
      await loadDir(path);
    }
    setExpandedDirs((prev) => ({ ...prev, [path]: true }));
  }

  async function openFile(path: string) {
    if (tabs.some((tab) => tab.path === path)) {
      setActiveTabPath(path);
      return;
    }
    try {
      const content = await readTextFile(path);
      const name = path.split(/[/\\]/).pop() || path;
      const tab: OpenTab = { path, name, content, dirty: false };
      setTabs((prev) => [...prev, tab]);
      setActiveTabPath(path);
      if (name.endsWith(".yal")) {
        setYalFilePath(path);
      }
    } catch (error) {
      pushOutput("error", `No se pudo abrir archivo ${path}: ${String(error)}`);
    }
  }

  function closeTab(path: string) {
    setTabs((prev) => {
      const remaining = prev.filter((tab) => tab.path !== path);
      if (activeTabPath === path) {
        setActiveTabPath(remaining[remaining.length - 1]?.path ?? "");
      }
      return remaining;
    });
  }

  function updateActiveTabContent(next: string) {
    if (!activeTab) {
      return;
    }
    setTabs((prev) =>
      prev.map((tab) =>
        tab.path === activeTab.path
          ? {
              ...tab,
              content: next,
              dirty: true,
            }
          : tab
      )
    );
  }

  async function saveActiveTab() {
    if (!activeTab) {
      pushOutput("info", "No hay pestaña activa para guardar.");
      return;
    }
    try {
      await writeTextFile(activeTab.path, activeTab.content);
      setTabs((prev) =>
        prev.map((tab) => (tab.path === activeTab.path ? { ...tab, dirty: false } : tab))
      );
      pushOutput("ok", `Guardado: ${activeTab.path}`);
    } catch (error) {
      pushOutput("error", `Error al guardar ${activeTab.path}: ${String(error)}`);
    }
  }

  async function runAction(action: YalexAction) {
    if (!yalFilePath && !activeTab?.name.endsWith(".yal")) {
      pushOutput("error", "Seleccione o abra un archivo .yal antes de ejecutar acciones.");
      return;
    }

    const yalSource = activeTab?.name.endsWith(".yal") ? activeTab.content : undefined;
    const yalPath = yalSource ? undefined : yalFilePath;

    try {
      setIsRunningAction(true);
      pushOutput("info", `Ejecutando acción: ${action}`);
      const response = await runYalex({
        action,
        yalPath,
        yalSource,
        inputPath: action === "tokenize" && tokenizeMode === "path" ? inputFilePath : undefined,
        inputText: action === "tokenize" && tokenizeMode === "text" ? tokenizeText : undefined,
        outputPath: action === "generate" ? generateOutputPath : undefined,
        includeTrace: action === "tokenize",
        traceLimit: 200,
      });

      const parsed = response as { ok: boolean; result?: unknown; error?: string };
      if (!parsed.ok) {
        pushOutput("error", parsed.error || "Error desconocido en backend.");
        return;
      }
      const formatted = JSON.stringify(parsed.result, null, 2);
      setLatestResult(formatted);
      pushOutput("ok", `${action} finalizado correctamente.`);
    } catch (error) {
      pushOutput("error", `Fallo al ejecutar ${action}: ${String(error)}`);
    } finally {
      setIsRunningAction(false);
    }
  }

  function renderTree(path: string, depth: number) {
    const children = treeMap[path] || [];
    const rows: Array<JSX.Element> = [];

    if (pendingCreate?.parentDir === path) {
      rows.push(
        <div
          key={`pending-${path}`}
          className="entry entry-create"
          style={{ paddingLeft: `${10 + depth * 14}px` }}
        >
          <span className="entry-kind">{pendingCreate.type === "folder" ? "DIR" : "FILE"}</span>
          <input
            className="entry-create-input"
            value={pendingCreate.draftName}
            autoFocus
            onChange={(event) =>
              setPendingCreate((prev) =>
                prev
                  ? {
                      ...prev,
                      draftName: event.target.value,
                    }
                  : prev
              )
            }
            onKeyDown={(event: ReactKeyboardEvent<HTMLInputElement>) => {
              if (event.key === "Enter") {
                void commitInlineCreate();
              }
              if (event.key === "Escape") {
                setPendingCreate(null);
              }
            }}
            onBlur={() => setPendingCreate(null)}
          />
        </div>
      );
    }

    children.forEach((entry) => {
      const isOpen = Boolean(expandedDirs[entry.path]);
      const isSelected = selectedPath === entry.path;
      if (entry.isDir) {
        rows.push(
          <div key={entry.path}>
            <button
              className={`entry ${isSelected ? "selected" : ""}`}
              style={{ paddingLeft: `${10 + depth * 14}px` }}
              onClick={() => void toggleDir(entry.path)}
            >
              <span className="entry-kind">{isOpen ? "▾" : "▸"}</span>
              <span>{entry.name}</span>
            </button>
            {isOpen && <div>{renderTree(entry.path, depth + 1)}</div>}
          </div>
        );
        return;
      }

      rows.push(
        <button
          key={entry.path}
          className={`entry ${isSelected ? "selected" : ""}`}
          style={{ paddingLeft: `${10 + depth * 14}px` }}
          onClick={() => {
            setSelectedPath(entry.path);
            if (isTextFile(entry.name)) {
              void openFile(entry.path);
            }
          }}
        >
          <span className="entry-kind">•</span>
          <span>{entry.name}</span>
        </button>
      );
    });

    return rows;
  }

  useEffect(() => {
    async function bootstrap() {
      try {
        const root = await getWorkspaceRoot();
        setYalFilePath(joinPath(root, "examples", "simple.yal"));
        setInputFilePath(joinPath(root, "tests", "input", "low.txt"));
        setGenerateOutputPath(joinPath(root, "output", "lexer_generated_tauri.py"));
        await openWorkspaceRoot(root);
      } catch (error) {
        pushOutput("error", `No se pudo inicializar la app: ${String(error)}`);
      }
    }
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!resizeState) {
      return;
    }

    const activeResize = resizeState;

    function onMouseMove(event: globalThis.MouseEvent) {
      const dx = event.clientX - activeResize.startX;
      const dy = event.clientY - activeResize.startY;

      if (activeResize.target === "sidebar") {
        const nextWidth = Math.min(520, Math.max(220, activeResize.startSidebarWidth + dx));
        setSidebarWidth(nextWidth);
        return;
      }

      if (activeResize.target === "rightPanel") {
        const nextWidth = Math.min(560, Math.max(260, activeResize.startRightPanelWidth - dx));
        setRightPanelWidth(nextWidth);
        return;
      }

      if (activeResize.target === "resultPanel") {
        const nextHeight = Math.min(500, Math.max(160, activeResize.startResultPanelHeight - dy));
        setResultPanelHeight(nextHeight);
        return;
      }

      if (activeResize.target === "outputPanel") {
        const nextHeight = Math.min(440, Math.max(120, activeResize.startOutputPanelHeight - dy));
        setOutputPanelHeight(nextHeight);
      }
    }

    function onMouseUp() {
      setResizeState(null);
    }

    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;

    document.body.style.cursor =
      activeResize.target === "sidebar" || activeResize.target === "rightPanel"
        ? "col-resize"
        : "row-resize";
    document.body.style.userSelect = "none";

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    return () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [resizeState]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const payload: PanelSizes = {
      sidebarWidth,
      rightPanelWidth,
      resultPanelHeight,
      outputPanelHeight,
    };

    window.localStorage.setItem(PANEL_STORAGE_KEY, JSON.stringify(payload));
  }, [sidebarWidth, rightPanelWidth, resultPanelHeight, outputPanelHeight]);

  return (
    <div className="shell" style={{ gridTemplateRows: `44px 1fr 6px ${outputPanelHeight}px` }}>
      <header className="topbar">
        <h1>YALex Studio</h1>
        <div className="topbar-actions">
          <button className="topbar-action-btn" onClick={() => void saveActiveTab()}>
            <span
              className="panel-icon topbar-icon"
              style={{
                WebkitMaskImage: `url(${saveIcon})`,
                maskImage: `url(${saveIcon})`,
              }}
            />
            Guardar
          </button>
          <button onClick={() => void runAction(selectedAction)} disabled={isRunningAction}>
            {isRunningAction ? "Ejecutando..." : `Ejecutar ${selectedAction}`}
          </button>
        </div>
      </header>

      <main
        className="workspace"
        style={{ gridTemplateColumns: `${sidebarWidth}px 6px 1fr` }}
      >
        <aside className="sidebar">
          <div className="panel-title">
            <span>Explorer</span>
            <div className="panel-title-actions">
              <button
                title="Abrir carpeta"
                aria-label="Abrir carpeta"
                onClick={() => void openWorkspaceRootFromDialog()}
              >
                ≡
              </button>
              <button
                title="Refrescar"
                aria-label="Refrescar"
                onClick={() => void refreshExplorerRoot()}
              >
                ↻
              </button>
              <button
                title="Nuevo archivo"
                aria-label="Nuevo archivo"
                onClick={() => void startInlineCreate("file")}
              >
                <span
                  className="panel-icon"
                  style={{
                    WebkitMaskImage: `url(${filePlusIcon})`,
                    maskImage: `url(${filePlusIcon})`,
                  }}
                />
              </button>
              <button
                title="Nueva carpeta"
                aria-label="Nueva carpeta"
                onClick={() => void startInlineCreate("folder")}
              >
                <span
                  className="panel-icon"
                  style={{
                    WebkitMaskImage: `url(${folderPlusIcon})`,
                    maskImage: `url(${folderPlusIcon})`,
                  }}
                />
              </button>
            </div>
          </div>
          <div className="path-row" title={workspaceRoot}>
            <span className="path-row-name">{getPathBaseName(workspaceRoot)}</span>
            <span className="path-row-hint">{workspaceRoot || "Sin carpeta"}</span>
          </div>
          <div className="file-list">
            {workspaceRoot && renderTree(workspaceRoot, 0)}
          </div>
        </aside>

        <div
          className="splitter"
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize explorer"
          onMouseDown={(event) =>
            setResizeState({
              target: "sidebar",
              startX: event.clientX,
              startY: event.clientY,
              startSidebarWidth: sidebarWidth,
              startRightPanelWidth: rightPanelWidth,
              startResultPanelHeight: resultPanelHeight,
              startOutputPanelHeight: outputPanelHeight,
            })
          }
        />

        <section className="editor-area">
          <div className="tabs">
            {tabs.length === 0 ? (
              <span className="tabs-empty">Sin archivos abiertos</span>
            ) : (
              tabs.map((tab) => (
                <button
                  key={tab.path}
                  className={`tab ${tab.path === activeTabPath ? "active" : ""}`}
                  onClick={() => setActiveTabPath(tab.path)}
                >
                  {tab.name}
                  {tab.dirty ? " ●" : ""}
                  <span
                    className="tab-close"
                    onClick={(event) => {
                      event.stopPropagation();
                      closeTab(tab.path);
                    }}
                  >
                    ×
                  </span>
                </button>
              ))
            )}
          </div>

          <div
            className="workbench-split"
            style={{ gridTemplateColumns: `1fr 6px ${rightPanelWidth}px` }}
          >
            <div className="editor-shell">
              {activeTab ? (
                <Editor
                  beforeMount={registerEditorTheme}
                  language={languageFromFileName(activeTab.name)}
                  value={activeTab.content}
                  onChange={(value: string | undefined) => updateActiveTabContent(value ?? "")}
                  theme="yalex-dark"
                  options={{
                    fontSize: 14,
                    fontFamily: "Cascadia Code, Consolas, monospace",
                    minimap: { enabled: false },
                    automaticLayout: true,
                    tabSize: 2,
                    insertSpaces: true,
                    lineNumbers: "on",
                    wordWrap: "on",
                    smoothScrolling: true,
                    scrollBeyondLastLine: false,
                  }}
                />
              ) : (
                <div className="editor-empty">
                  <strong>Inicio rápido</strong>
                  <br />
                  1) Abre un archivo .yal desde el explorer.
                  <br />
                  2) Selecciona la acción en el panel lateral derecho.
                  <br />
                  3) Ejecuta y revisa el resultado.
                </div>
              )}
            </div>

            <div
              className="splitter splitter-inner-vertical"
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize pipeline"
              onMouseDown={(event) =>
                setResizeState({
                  target: "rightPanel",
                  startX: event.clientX,
                  startY: event.clientY,
                  startSidebarWidth: sidebarWidth,
                  startRightPanelWidth: rightPanelWidth,
                  startResultPanelHeight: resultPanelHeight,
                  startOutputPanelHeight: outputPanelHeight,
                })
              }
            />

            <aside className="command-panel">
              <div className="panel-title panel-title-tight">Pipeline</div>
              <label className="field">
                Acción
                <select
                  value={selectedAction}
                  onChange={(event) => setSelectedAction(event.target.value as YalexAction)}
                >
                  {YAL_ACTIONS.map((action) => (
                    <option key={action.id} value={action.id}>
                      {action.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                Archivo .yal
                <input
                  value={yalFilePath}
                  onChange={(event) => setYalFilePath(event.target.value)}
                  placeholder="Ruta al archivo .yal"
                />
              </label>

              {selectedAction === "tokenize" && (
                <>
                  <label className="field">
                    Modo tokenización
                    <select
                      value={tokenizeMode}
                      onChange={(event) =>
                        setTokenizeMode(event.target.value as "path" | "text")
                      }
                    >
                      <option value="path">Archivo</option>
                      <option value="text">Texto directo</option>
                    </select>
                  </label>

                  {tokenizeMode === "path" ? (
                    <label className="field">
                      Input (archivo)
                      <input
                        value={inputFilePath}
                        onChange={(event) => setInputFilePath(event.target.value)}
                        placeholder="Ruta del texto de entrada"
                      />
                    </label>
                  ) : (
                    <label className="field">
                      Input (texto)
                      <textarea
                        className="inline-textarea"
                        value={tokenizeText}
                        onChange={(event) => setTokenizeText(event.target.value)}
                        placeholder="Texto a tokenizar"
                      />
                    </label>
                  )}
                </>
              )}

              {selectedAction === "generate" && (
                <label className="field">
                  Output lexer
                  <input
                    value={generateOutputPath}
                    onChange={(event) => setGenerateOutputPath(event.target.value)}
                    placeholder="Ruta del lexer generado"
                  />
                </label>
              )}

              <button
                className="run-action-btn"
                onClick={() => void runAction(selectedAction)}
                disabled={isRunningAction}
              >
                {isRunningAction ? "Ejecutando..." : "Ejecutar acción"}
              </button>

              <p className="command-hint">{ACTION_HELP[selectedAction]}</p>
            </aside>
          </div>

          <div
            className="splitter splitter-horizontal"
            role="separator"
            aria-orientation="horizontal"
            aria-label="Resize result"
            onMouseDown={(event) =>
              setResizeState({
                target: "resultPanel",
                startX: event.clientX,
                startY: event.clientY,
                startSidebarWidth: sidebarWidth,
                startRightPanelWidth: rightPanelWidth,
                startResultPanelHeight: resultPanelHeight,
                startOutputPanelHeight: outputPanelHeight,
              })
            }
          />

          <section className="result-panel" style={{ height: `${resultPanelHeight}px` }}>
            <div className="panel-title panel-title-tight">Resultado JSON</div>
            <pre className="result-view">{latestResult}</pre>
          </section>
        </section>
      </main>

      <div
        className="splitter splitter-horizontal shell-horizontal-splitter"
        role="separator"
        aria-orientation="horizontal"
        aria-label="Resize output"
        onMouseDown={(event) =>
          setResizeState({
            target: "outputPanel",
            startX: event.clientX,
            startY: event.clientY,
            startSidebarWidth: sidebarWidth,
            startRightPanelWidth: rightPanelWidth,
            startResultPanelHeight: resultPanelHeight,
            startOutputPanelHeight: outputPanelHeight,
          })
        }
      />

      <section className="output-panel">
        <div className="panel-title">Output</div>
        <div className="output-log">
          {output.map((line, index) => (
            <div key={`${line.ts}-${index}`} className={`out-line ${line.type}`}>
              [{line.ts}] {line.text}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
