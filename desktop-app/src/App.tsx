import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import Editor, { loader, type Monaco } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import {
  createDirectory,
  getWorkspaceRoot,
  isTauriRuntime,
  listEntries,
  pickDirectory,
  readTextFile,
  runYalex,
  writeTextFile,
} from "./api";
import type { FileNode, OpenTab, YalexAction } from "./types";

loader.config({ monaco });

const saveIcon = "/icons/save.svg";
const filePlusIcon = "/icons/file-plus.svg";
const folderPlusIcon = "/icons/folder-plus.svg";

type OutputItem = {
  ts: string;
  type: "info" | "ok" | "error";
  text: string;
};

const YAL_ACTIONS: Array<{ id: YalexAction; label: string }> = [
  { id: "spec", label: "Spec (JSON)" },
  { id: "ast", label: "AST" },
  { id: "combinedNfa", label: "Construcción Directa" },
  { id: "dfa", label: "DFA" },
  { id: "tokenize", label: "Tokenizar" },
  { id: "generate", label: "Generar Lexer" },
];

const FULL_PIPELINE_ACTIONS: YalexAction[] = YAL_ACTIONS.map((action) => action.id);

function getActionLabel(action: YalexAction): string {
  return YAL_ACTIONS.find((item) => item.id === action)?.label ?? action;
}

const PANEL_STORAGE_KEY = "yalex-studio.panel-sizes.v1";

type PanelSizes = {
  sidebarWidth: number;
  rightPanelWidth: number;
  resultPanelHeight: number;
  outputPanelHeight: number;
};

type GraphNode = {
  id: string;
  label: string;
  isStart?: boolean;
  isAccept?: boolean;
};

type GraphEdge = {
  from: string;
  to: string;
  label: string;
};

type GraphPanel = {
  title: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
};

type ValidationCheck = {
  id: YalexAction;
  label: string;
  ok: boolean;
  detail: string;
};

type DfaEdgeLabelMode = "ranges" | "aliases";
type DfaLabelDensity = "compact" | "detailed";

function asObject(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function formatCharLabel(raw: string): string {
  if (raw === "\n") return "\\n";
  if (raw === "\r") return "\\r";
  if (raw === "\t") return "\\t";
  if (raw === " ") return "space";
  if (raw === "\\") return "\\\\";

  if (raw.length === 1) {
    const code = raw.charCodeAt(0);
    if (code < 32 || code === 127) {
      return `\\x${code.toString(16).toUpperCase().padStart(2, "0")}`;
    }
  }

  return raw;
}

function transitionLabel(transition: Record<string, unknown>): string {
  const char = asString(transition.char);
  if (char !== null) {
    return formatCharLabel(char);
  }

  const kind = asString(transition.kind) ?? "?";
  const payload = asObject(transition.payload);
  if (kind === "epsilon") return "ε";
  if (kind === "char") return payload?.value ? formatCharLabel(String(payload.value)) : "char";
  if (kind === "wildcard") return "wildcard";
  if (kind === "charset") return "charset";
  if (kind === "charset_difference") return "set-diff";
  return kind;
}

function escapeCharForSetLiteral(ch: string): string {
  if (ch === "\\") return "\\\\";
  if (ch === "'") return "\\'";
  if (ch === "\n") return "\\n";
  if (ch === "\r") return "\\r";
  if (ch === "\t") return "\\t";

  if (ch.length === 1) {
    const code = ch.charCodeAt(0);
    if (code < 32 || code === 127) {
      return `\\x${code.toString(16).toUpperCase().padStart(2, "0")}`;
    }
  }

  return ch;
}

function buildCanonicalCodeSet(codes: number[]): string {
  return codes.join(",");
}

function getKnownAliasDefinitions(): Array<{ name: string; codes: number[] }> {
  const lower = Array.from({ length: 26 }, (_, i) => 97 + i);
  const upper = Array.from({ length: 26 }, (_, i) => 65 + i);
  const digits = Array.from({ length: 10 }, (_, i) => 48 + i);
  const vowels = [65, 69, 73, 79, 85, 97, 101, 105, 111, 117].sort((a, b) => a - b);
  const letter = [...upper, ...lower].sort((a, b) => a - b);
  const vowelSet = new Set(vowels);
  const consonant = letter.filter((code) => !vowelSet.has(code));
  const ws = [9, 10, 13, 32];

  return [
    { name: "consonant", codes: consonant },
    { name: "vowel", codes: vowels },
    { name: "letter", codes: letter },
    { name: "lower", codes: lower },
    { name: "upper", codes: upper },
    { name: "digit", codes: digits },
    { name: "ws", codes: ws },
  ];
}

function getAliasForCharCodes(codes: number[]): string | null {
  const unique = Array.from(new Set(codes)).sort((a, b) => a - b);
  const key = buildCanonicalCodeSet(unique);

  const aliasMap = new Map<string, string>(
    getKnownAliasDefinitions().map((entry) => [buildCanonicalCodeSet(entry.codes), entry.name])
  );

  return aliasMap.get(key) ?? null;
}

function factorAliasesFromCodes(codes: number[]): { aliases: string[]; remaining: number[] } {
  const remaining = new Set(codes);
  const aliases: string[] = [];

  const definitions = getKnownAliasDefinitions().sort((a, b) => b.codes.length - a.codes.length);
  for (const definition of definitions) {
    const allPresent = definition.codes.every((code) => remaining.has(code));
    if (!allPresent) {
      continue;
    }

    aliases.push(definition.name);
    for (const code of definition.codes) {
      remaining.delete(code);
    }
  }

  return {
    aliases,
    remaining: Array.from(remaining).sort((a, b) => a - b),
  };
}

function formatCharSetLabel(chars: string[], mode: DfaEdgeLabelMode = "ranges"): string {
  if (chars.length === 0) {
    return "";
  }

  const sortedCodes = Array.from(new Set(chars.map((ch) => ch.charCodeAt(0)))).sort((a, b) => a - b);

  const alias = getAliasForCharCodes(sortedCodes);
  if (mode === "aliases" && alias) {
    return alias;
  }

  if (mode === "aliases") {
    const factored = factorAliasesFromCodes(sortedCodes);
    if (factored.aliases.length > 0) {
      const parts: string[] = [factored.aliases.join(" ")];
      if (factored.remaining.length > 0) {
        parts.push(formatCharSetLabel(factored.remaining.map((code) => String.fromCharCode(code)), "ranges"));
      }
      return parts.join("\n");
    }
  }

  const ranges: Array<{ start: number; end: number }> = [];
  let start = sortedCodes[0];
  let end = sortedCodes[0];

  for (let i = 1; i < sortedCodes.length; i++) {
    const next = sortedCodes[i];
    if (next === end + 1) {
      end = next;
      continue;
    }
    ranges.push({ start, end });
    start = next;
    end = next;
  }
  ranges.push({ start, end });

  const labels = ranges.map((range) => {
    const startLit = escapeCharForSetLiteral(String.fromCharCode(range.start));
    const endLit = escapeCharForSetLiteral(String.fromCharCode(range.end));
    if (range.start === range.end) {
      return `['${startLit}']`;
    }
    return `['${startLit}'-'${endLit}']`;
  });

  const groupsPerLine = 4;
  const lines: string[] = [];
  for (let i = 0; i < labels.length; i += groupsPerLine) {
    lines.push(labels.slice(i, i + groupsPerLine).join(" "));
  }

  return lines.join("\n");
}

function renderEdgeLabel(
  label: string,
  x: number,
  y: number,
  className: string,
  textAnchor: "start" | "middle" | "end" = "middle"
): JSX.Element {
  const lines = label.split("\n");
  const maxChars = Math.max(...lines.map((line) => line.length), 1);
  const lineHeight = 14;
  const boxWidth = Math.min(300, Math.max(44, maxChars * 7 + 14));
  const boxHeight = lines.length * lineHeight + 8;
  const boxX = x - boxWidth / 2;
  const boxY = y - boxHeight / 2;
  const textStartY = boxY + 14;

  return (
    <g className="graph-edge-label-group">
      <rect x={boxX} y={boxY} width={boxWidth} height={boxHeight} rx={4} className="graph-edge-label-box" />
      <text x={x} y={textStartY} className={className} textAnchor={textAnchor}>
        {lines.map((line, index) => (
          <tspan key={`${line}-${index}`} x={x} dy={index === 0 ? "0" : `${lineHeight}px`}>
            {line}
          </tspan>
        ))}
      </text>
    </g>
  );
}

function buildSingleAutomatonPanel(
  source: Record<string, unknown>,
  title: string,
  includeDfaAcceptMetadata = false,
  dfaEdgeLabelMode: DfaEdgeLabelMode = "ranges"
): GraphPanel | null {
  const stateSet = new Set<string>();
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  const startState = asNumber(source.start_state);
  const acceptSingle = asNumber(source.accept_state);
  const acceptStatesMulti = new Set<number>();

  for (const acceptItem of asArray(source.accept_states)) {
    const acceptObj = asObject(acceptItem);
    if (!acceptObj) continue;
    const state = asNumber(acceptObj.state);
    if (state !== null) {
      acceptStatesMulti.add(state);
    }
  }

  for (const stateItem of asArray(source.states)) {
    const stateObj = asObject(stateItem);
    if (stateObj && includeDfaAcceptMetadata) {
      const sid = asNumber(stateObj.id);
      if (sid === null) continue;
      const isAccept = Boolean(stateObj.is_accept);
      const labelRaw = asString(stateObj.accept_label);
      const label = labelRaw ? `q${sid} (${labelRaw})` : `q${sid}`;
      stateSet.add(String(sid));
      nodes.push({
        id: String(sid),
        label,
        isStart: startState === sid,
        isAccept,
      });
      continue;
    }

    const sid = asNumber(stateItem);
    if (sid === null) continue;
    stateSet.add(String(sid));
    nodes.push({
      id: String(sid),
      label: `q${sid}`,
      isStart: startState === sid,
      isAccept: acceptSingle === sid || acceptStatesMulti.has(sid),
    });
  }

  const edgeBuckets = new Map<
    string,
    {
      from: string;
      to: string;
      chars: string[];
      misc: string[];
    }
  >();

  for (const transitionItem of asArray(source.transitions)) {
    const transitionObj = asObject(transitionItem);
    if (!transitionObj) continue;

    const from = asNumber(transitionObj.from);
    const to = asNumber(transitionObj.to);
    if (from === null || to === null) continue;

    const fromId = String(from);
    const toId = String(to);
    stateSet.add(fromId);
    stateSet.add(toId);

    const key = `${fromId}->${toId}`;
    const bucket = edgeBuckets.get(key) ?? { from: fromId, to: toId, chars: [], misc: [] };
    const asChar = asString(transitionObj.char);
    if (asChar && asChar.length === 1) {
      bucket.chars.push(asChar);
    } else {
      bucket.misc.push(transitionLabel(transitionObj));
    }
    edgeBuckets.set(key, bucket);
  }

  for (const bucket of edgeBuckets.values()) {
    const parts: string[] = [];
    if (bucket.chars.length > 0) {
      parts.push(formatCharSetLabel(bucket.chars, dfaEdgeLabelMode));
    }
    if (bucket.misc.length > 0) {
      parts.push(Array.from(new Set(bucket.misc)).join(", "));
    }
    edges.push({
      from: bucket.from,
      to: bucket.to,
      label: parts.join(" "),
    });
  }

  for (const sid of stateSet) {
    if (nodes.some((node) => node.id === sid)) {
      continue;
    }
    const numeric = Number(sid);
    nodes.push({
      id: sid,
      label: `q${sid}`,
      isStart: startState === numeric,
      isAccept: acceptSingle === numeric || acceptStatesMulti.has(numeric),
    });
  }

  nodes.sort((a, b) => Number(a.id) - Number(b.id));
  edges.sort((a, b) => {
    const fromDiff = Number(a.from) - Number(b.from);
    if (fromDiff !== 0) return fromDiff;
    return Number(a.to) - Number(b.to);
  });
  if (nodes.length === 0) {
    return null;
  }

  return { title, nodes, edges };
}

function buildAutomatonPanels(
  action: YalexAction,
  payload: unknown,
  dfaEdgeLabelMode: DfaEdgeLabelMode
): GraphPanel[] {
  const root = asObject(payload);
  if (!root) return [];

  if (action === "dfa") {
    const dfa = asObject(root.dfa);
    const panel = dfa ? buildSingleAutomatonPanel(dfa, "DFA", true, dfaEdgeLabelMode) : null;
    return panel ? [panel] : [];
  }

  return [];
}

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
  const workbenchSplitRef = useRef<HTMLDivElement | null>(null);
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
  const [actionResults, setActionResults] = useState<Partial<Record<YalexAction, string>>>({});
  const [actionResultObjects, setActionResultObjects] = useState<
    Partial<Record<YalexAction, unknown>>
  >({});
  const [activeResultAction, setActiveResultAction] = useState<YalexAction | null>(null);
  const [resultViewMode, setResultViewMode] = useState<"json" | "graph" | "code">("graph");
  const [generatedPythonCode, setGeneratedPythonCode] = useState<string>("");
  const [isLoadingGeneratedCode, setIsLoadingGeneratedCode] = useState<boolean>(false);
  const [dfaEdgeLabelMode, setDfaEdgeLabelMode] = useState<DfaEdgeLabelMode>("ranges");
  const [dfaLabelDensity, setDfaLabelDensity] = useState<DfaLabelDensity>("compact");
  const [hoveredEdgeKey, setHoveredEdgeKey] = useState<string | null>(null);
  const [validationChecks, setValidationChecks] = useState<ValidationCheck[]>([]);
  const [validationRunAt, setValidationRunAt] = useState<string>("");

  const [yalFilePath, setYalFilePath] = useState<string>("");
  const [inputFilePath, setInputFilePath] = useState<string>("");
  const [generateOutputPath, setGenerateOutputPath] = useState<string>("");
  const [isRunningAction, setIsRunningAction] = useState<boolean>(false);
  const [isInitializing, setIsInitializing] = useState<boolean>(true); // Show loading state while Tauri initializes
  const [initError, setInitError] = useState<string>(""); // Track initialization errors
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

  const visibleResultActions = useMemo(
    () => FULL_PIPELINE_ACTIONS.filter((action) => Boolean(actionResults[action])),
    [actionResults]
  );

  const activeResultText =
    activeResultAction && actionResults[activeResultAction]
      ? actionResults[activeResultAction]
      : latestResult;

  const activeResultObject = activeResultAction ? actionResultObjects[activeResultAction] : null;

  const graphSupportedActions: YalexAction[] = ["ast", "dfa"];
  const canRenderGraph = Boolean(
    activeResultAction && graphSupportedActions.includes(activeResultAction) && activeResultObject
  );
  const generateRoot = activeResultAction === "generate" ? asObject(activeResultObject) : null;
  const generatedOutputPath = generateRoot ? asString(generateRoot.outputPath) : null;
  const generatedCodePathCandidates = useMemo(() => {
    if (activeResultAction !== "generate") {
      return [] as string[];
    }

    const candidates: string[] = [];
    if (generatedOutputPath?.trim()) {
      candidates.push(generatedOutputPath.trim());
    }
    if (generateOutputPath.trim()) {
      candidates.push(generateOutputPath.trim());
    }

    const sourcePath = generatedOutputPath?.trim() || generateOutputPath.trim();
    const baseName = sourcePath ? getPathBaseName(sourcePath) : "";
    if (workspaceRoot && baseName) {
      candidates.push(joinPath(workspaceRoot, "output", baseName));
      candidates.push(joinPath(workspaceRoot, baseName));
    }

    return Array.from(new Set(candidates.filter(Boolean)));
  }, [activeResultAction, generatedOutputPath, generateOutputPath, workspaceRoot]);
  const canRenderCode = generatedCodePathCandidates.length > 0;

  const passedChecks = validationChecks.filter((check) => check.ok).length;
  const totalChecks = validationChecks.length;

  useEffect(() => {
    if (resultViewMode !== "code") {
      return;
    }

    if (!canRenderCode) {
      setGeneratedPythonCode("");
      return;
    }

    let cancelled = false;
    setIsLoadingGeneratedCode(true);

    const loadGeneratedCode = async () => {
      let lastError: unknown = null;
      for (const candidatePath of generatedCodePathCandidates) {
        try {
          const content = await readTextFile(candidatePath);
          if (!cancelled) {
            setGeneratedPythonCode(content);
          }
          return;
        } catch (error) {
          lastError = error;
        }
      }

      if (!cancelled) {
        const attempted = generatedCodePathCandidates.join(" | ");
        setGeneratedPythonCode(
          `No se pudo leer el lexer generado. Rutas intentadas: ${attempted}. Error: ${String(lastError)}`
        );
      }
    };

    void loadGeneratedCode().finally(() => {
      if (!cancelled) {
        setIsLoadingGeneratedCode(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [resultViewMode, canRenderCode, generatedCodePathCandidates]);

  function buildValidationChecks(
    results: Partial<Record<YalexAction, unknown>>
  ): ValidationCheck[] {
    const tokenize = asObject(results.tokenize);
    const tokens = tokenize ? asArray(tokenize.tokens) : [];
    const errors = tokenize ? asArray(tokenize.errors) : [];
    const lexicalFailureDetected = errors.length > 0;

    return [
      {
        id: "tokenize",
        label: "Tokenización ejecutada",
        ok: Boolean(tokenize && Array.isArray(tokenize.tokens) && Array.isArray(tokenize.errors)),
        detail: tokenize
          ? `tokens=${tokens.length}, errors=${errors.length}`
          : "Ejecuta la etapa Tokenizar para validar el fallo léxico",
      },
      {
        id: "combinedNfa",
        label: "Fallo léxico real detectado",
        ok: lexicalFailureDetected,
        detail: lexicalFailureDetected
          ? "Sí: la lista errors contiene elementos"
          : "No: errors está vacío para la última tokenización",
      },
      {
        id: "generate",
        label: "Comportamiento esperado en lexer generado",
        ok: lexicalFailureDetected,
        detail: lexicalFailureDetected
          ? "Con esos errors, el lexer generado terminaría con código 1 en main"
          : "Si no hay errors, el lexer generado terminaría sin fallo léxico",
      },
    ];
  }

  function runValidationFromCurrentResults() {
    const checks = buildValidationChecks(actionResultObjects);
    setValidationChecks(checks);
    const passCount = checks.filter((check) => check.ok).length;
    setValidationRunAt(nowTime());
    if (passCount === checks.length) {
      pushOutput("ok", `Validación completa OK (${passCount}/${checks.length}).`);
    } else {
      pushOutput("error", `Validación con fallos (${passCount}/${checks.length}).`);
    }
  }

  async function runGeneratedLexerProgram() {
    if (!workspaceRoot) {
      pushOutput("error", "No hay workspace abierto.");
      return;
    }
    if (!generateOutputPath.trim()) {
      pushOutput("error", "Debe indicar la ruta del lexer generado (.py).");
      return;
    }
    if (!inputFilePath.trim()) {
      pushOutput("error", "Debe indicar la ruta del input (.txt).");
      return;
    }

    try {
      setIsRunningAction(true);
      pushOutput("info", "Ejecutando lexer generado...");

      const response = await runYalex({
        workspaceRoot,
        action: "executeGeneratedLexer",
        lexerPath: generateOutputPath,
        inputPath: inputFilePath,
      });

      const parsed = response as { ok: boolean; result?: unknown; error?: string };
      if (!parsed.ok) {
        pushOutput("error", parsed.error || "Error ejecutando lexer generado.");
        return;
      }

      const result = (parsed.result ?? {}) as Record<string, unknown>;
      const success = Boolean(result.success);
      const exitCode = Number(result.exitCode ?? -1);
      const tokenCount = Number(result.tokenCount ?? 0);
      const lexicalErrorCount = Number(result.lexicalErrorCount ?? 0);

      const formatted = JSON.stringify(parsed.result, null, 2);
      setLatestResult(formatted);
      setActionResults((prev) => ({ ...prev, executeGeneratedLexer: formatted }));
      setActionResultObjects((prev) => ({ ...prev, executeGeneratedLexer: parsed.result }));
      setActiveResultAction("executeGeneratedLexer");

      if (success) {
        pushOutput(
          "ok",
          `Lexer generado ejecutado correctamente (exit=${exitCode}, tokens=${tokenCount}, errors=${lexicalErrorCount}).`
        );
      } else {
        pushOutput(
          "error",
          `Lexer generado terminó con fallo (exit=${exitCode}, tokens=${tokenCount}, errors=${lexicalErrorCount}).`
        );
      }
    } catch (error) {
      pushOutput("error", `Fallo ejecutando lexer generado: ${String(error)}`);
    } finally {
      setIsRunningAction(false);
    }
  }

  function renderRegexNodeTree(node: unknown, keyPrefix: string): JSX.Element {
    const obj = asObject(node);
    if (!obj) {
      return <li key={keyPrefix}>Nodo inválido</li>;
    }

    const nodeType = asString(obj.type) ?? "node";
    const labelValue =
      asString(obj.value) ?? asString(obj.name) ?? asString(obj.operator) ?? nodeType;

    const children: ReactNode[] = [];
    if (obj.operand) {
      children.push(renderRegexNodeTree(obj.operand, `${keyPrefix}-operand`));
    }
    if (obj.left) {
      children.push(renderRegexNodeTree(obj.left, `${keyPrefix}-left`));
    }
    if (obj.right) {
      children.push(renderRegexNodeTree(obj.right, `${keyPrefix}-right`));
    }
    for (const [index, part] of asArray(obj.parts).entries()) {
      children.push(renderRegexNodeTree(part, `${keyPrefix}-part-${index}`));
    }

    return (
      <li key={keyPrefix}>
        <span className="ast-node-label">{`${nodeType}: ${labelValue}`}</span>
        {children.length > 0 && <ul className="ast-node-children">{children}</ul>}
      </li>
    );
  }

  function renderAstGraph(payload: unknown): JSX.Element {
    const root = asObject(payload);
    const regexAst = root ? asObject(root.regex_ast) : null;
    if (!regexAst) {
      return <div className="graph-empty">No hay estructura AST para renderizar.</div>;
    }

    const sections: JSX.Element[] = [];
    for (const letItem of asArray(regexAst.lets)) {
      const letObj = asObject(letItem);
      if (!letObj) continue;
      const name = asString(letObj.name) ?? "let";
      sections.push(
        <section key={`let-${name}`} className="graph-panel">
          <h4>{`AST let: ${name}`}</h4>
          <ul className="ast-tree">{renderRegexNodeTree(letObj.ast, `let-${name}`)}</ul>
        </section>
      );
    }

    for (const altItem of asArray(regexAst.rule_alternatives)) {
      const altObj = asObject(altItem);
      if (!altObj) continue;
      const index = asNumber(altObj.index);
      sections.push(
        <section key={`alt-${index ?? "?"}`} className="graph-panel">
          <h4>{`AST alternativa ${index ?? "?"}`}</h4>
          <ul className="ast-tree">{renderRegexNodeTree(altObj.ast, `alt-${index ?? "?"}`)}</ul>
        </section>
      );
    }

    return <div className="graph-panels">{sections.length > 0 ? sections : <div className="graph-empty">Sin nodos AST.</div>}</div>;
  }

  function renderAutomatonSvg(panel: GraphPanel): JSX.Element {
    const width = 820;
    const height = 340;
    const cx = width / 2;
    const cy = height / 2;
    const radius = Math.max(90, Math.min(130, 28 * panel.nodes.length));
    const nodeRadius = 20;
    const markerId = `arrow-${panel.title.replace(/[^a-zA-Z0-9_-]/g, "-")}`;

    const positions = new Map<string, { x: number; y: number }>();
    panel.nodes.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / panel.nodes.length - Math.PI / 2;
      positions.set(node.id, {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      });
    });

    const edgeKeySet = new Set(panel.edges.map((edge) => `${edge.from}->${edge.to}`));
    const edgeLabels: Array<{ key: string; x: number; y: number; label: string }> = [];

    return (
      <section key={panel.title} className="graph-panel">
        <h4>{panel.title}</h4>
        <div className="graph-canvas-wrap">
          <svg viewBox={`0 0 ${width} ${height}`} className="automaton-svg" aria-label={panel.title}>
            <defs>
              <marker id={markerId} markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" />
              </marker>
            </defs>

            {panel.edges.map((edge, index) => {
              const edgeKey = `${edge.from}-${edge.to}-${index}`;
              const from = positions.get(edge.from);
              const to = positions.get(edge.to);
              if (!from || !to) return null;

              if (edge.from === edge.to) {
                const loopRadius = nodeRadius + 14;
                const startX = from.x + nodeRadius * 0.7;
                const startY = from.y - nodeRadius * 0.7;
                const endX = from.x - nodeRadius * 0.7;
                const endY = from.y - nodeRadius * 0.7;
                const c1x = from.x + loopRadius;
                const c1y = from.y - loopRadius - 24;
                const c2x = from.x - loopRadius;
                const c2y = from.y - loopRadius - 24;
                const labelX = from.x;
                const labelY = from.y - loopRadius - 28;

                edgeLabels.push({ key: edgeKey, x: labelX, y: labelY, label: edge.label });

                return (
                  <g key={edgeKey} className="graph-edge-group">
                    <path
                      d={`M ${startX} ${startY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${endX} ${endY}`}
                      className={`graph-edge ${hoveredEdgeKey === edgeKey ? "is-hovered" : ""}`}
                      markerEnd={`url(#${markerId})`}
                      fill="none"
                      onMouseEnter={() => setHoveredEdgeKey(edgeKey)}
                      onMouseLeave={() =>
                        setHoveredEdgeKey((prev) => (prev === edgeKey ? null : prev))
                      }
                    />
                  </g>
                );
              }

              const dx = to.x - from.x;
              const dy = to.y - from.y;
              const distance = Math.hypot(dx, dy);
              if (distance < 0.001) {
                return null;
              }

              const ux = dx / distance;
              const uy = dy / distance;
              const edgePadding = 2;
              const startX = from.x + ux * (nodeRadius + edgePadding);
              const startY = from.y + uy * (nodeRadius + edgePadding);
              const endX = to.x - ux * (nodeRadius + edgePadding);
              const endY = to.y - uy * (nodeRadius + edgePadding);

              const reverseExists = edgeKeySet.has(`${edge.to}->${edge.from}`);
              const directionBias = Number(edge.from) <= Number(edge.to) ? 1 : -1;
              const curveOffset = reverseExists ? 18 * directionBias : 0;
              const nx = -uy;
              const ny = ux;
              const controlX = (startX + endX) / 2 + nx * curveOffset;
              const controlY = (startY + endY) / 2 + ny * curveOffset;

              const isCurved = curveOffset !== 0;
              const pathD = isCurved
                ? `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY}`
                : `M ${startX} ${startY} L ${endX} ${endY}`;

              const labelX = isCurved ? (startX + 2 * controlX + endX) / 4 : (startX + endX) / 2;
              const labelY = (isCurved ? (startY + 2 * controlY + endY) / 4 : (startY + endY) / 2) - 6;

              edgeLabels.push({ key: edgeKey, x: labelX, y: labelY, label: edge.label });

              return (
                <g key={edgeKey} className="graph-edge-group">
                  <path
                    d={pathD}
                    className={`graph-edge ${hoveredEdgeKey === edgeKey ? "is-hovered" : ""}`}
                    markerEnd={`url(#${markerId})`}
                    fill="none"
                    onMouseEnter={() => setHoveredEdgeKey(edgeKey)}
                    onMouseLeave={() =>
                      setHoveredEdgeKey((prev) => (prev === edgeKey ? null : prev))
                    }
                  />
                </g>
              );
            })}

            {panel.nodes.map((node) => {
              const pos = positions.get(node.id);
              if (!pos) return null;
              return (
                <g key={node.id}>
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={nodeRadius}
                    className={`graph-node ${node.isAccept ? "accept" : ""} ${node.isStart ? "start" : ""}`}
                  />
                  {node.isAccept && <circle cx={pos.x} cy={pos.y} r={nodeRadius - 5} className="graph-node-accept" />}
                  <text x={pos.x} y={pos.y + 4} className="graph-node-label" textAnchor="middle">
                    {node.label}
                  </text>
                </g>
              );
            })}

            {edgeLabels.map((edgeLabel) => {
              const visible =
                dfaLabelDensity === "detailed" ||
                (dfaLabelDensity === "compact" && hoveredEdgeKey === edgeLabel.key);
              if (!visible) {
                return null;
              }

              return (
                <g key={`label-${edgeLabel.key}`}>
                  {renderEdgeLabel(edgeLabel.label, edgeLabel.x, edgeLabel.y, "graph-edge-label", "middle")}
                </g>
              );
            })}
          </svg>
        </div>
      </section>
    );
  }

  function renderGraphView(): JSX.Element {
    if (!activeResultAction || !activeResultObject) {
      return <div className="graph-empty">Ejecuta una etapa para ver una visualización.</div>;
    }

    if (activeResultAction === "ast") {
      return renderAstGraph(activeResultObject);
    }

    if (activeResultAction === "dfa") {
      const panels = buildAutomatonPanels(activeResultAction, activeResultObject, dfaEdgeLabelMode);
      if (panels.length === 0) {
        return <div className="graph-empty">No hay estructura de autómata para renderizar.</div>;
      }
      return <div className="graph-panels">{panels.map((panel) => renderAutomatonSvg(panel))}</div>;
    }

    return <div className="graph-empty">Esta etapa no tiene visualización gráfica todavía.</div>;
  }

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
      console.log("[openFile] Opening file:", path);
      const content = await readTextFile(path);
      console.log("[openFile] File content loaded successfully,  length:", content.length);
      const name = path.split(/[/\\]/).pop() || path;
      const tab: OpenTab = { path, name, content, dirty: false };
      setTabs((prev) => [...prev, tab]);
      setActiveTabPath(path);
      if (name.endsWith(".yal")) {
        setYalFilePath(path);
      }
      if (name.endsWith(".txt")) {
        setInputFilePath(path);
      }
      pushOutput("ok", `Archivo abierto: ${name}`);
      setIsRunningAction(false);
    } catch (error) {
      console.error("[openFile] Error opening file:", error);
      const errorMsg = error instanceof Error ? error.message : String(error);
      pushOutput("error", `No se pudo abrir archivo ${path}: ${errorMsg}`);
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

  async function executeAction(
    action: YalexAction,
    yalPath: string | undefined,
    yalSource: string | undefined
  ): Promise<boolean> {
    const response = await runYalex({
      workspaceRoot,
      action,
      yalPath,
      yalSource,
      inputPath: action === "tokenize" ? inputFilePath : undefined,
      outputPath: action === "generate" ? generateOutputPath : undefined,
      includeTrace: action === "tokenize",
      traceLimit: 200,
    });

    const parsed = response as { ok: boolean; result?: unknown; error?: string };
    if (!parsed.ok) {
      pushOutput("error", parsed.error || "Error desconocido en backend.");
      return false;
    }

    const formatted = JSON.stringify(parsed.result, null, 2);
    setLatestResult(formatted);
    setActionResults((prev) => ({ ...prev, [action]: formatted }));
    setActionResultObjects((prev) => ({ ...prev, [action]: parsed.result }));
    setActiveResultAction(action);
    pushOutput("ok", `${getActionLabel(action)} finalizado correctamente.`);
    return true;
  }

  async function runFullPipeline(): Promise<boolean> {
    if (!workspaceRoot) {
      pushOutput("error", "No hay workspace abierto.");
      return false;
    }

    if (!yalFilePath.trim()) {
      pushOutput("error", "Debe ingresar la ruta del archivo .yal.");
      return false;
    }

    if (!inputFilePath.trim()) {
      pushOutput("error", "Debe ingresar la ruta del archivo .txt de entrada.");
      return false;
    }

    const yalSource = undefined;
    const yalPath = yalFilePath;

    try {
      setIsRunningAction(true);
      setValidationChecks([]);
      setValidationRunAt("");
      pushOutput("info", "Iniciando ejecución secuencial de todo el pipeline.");

      for (let index = 0; index < FULL_PIPELINE_ACTIONS.length; index++) {
        const nextAction = FULL_PIPELINE_ACTIONS[index];
        pushOutput(
          "info",
          `Paso ${index + 1}/${FULL_PIPELINE_ACTIONS.length}: ejecutando ${getActionLabel(nextAction)}`
        );

        const ok = await executeAction(nextAction, yalPath, yalSource);
        if (!ok) {
          pushOutput("error", `Pipeline detenido en '${getActionLabel(nextAction)}'.`);
          return false;
        }
      }

      pushOutput("ok", "Pipeline completo finalizado correctamente.");
      return true;
    } catch (error) {
      pushOutput("error", `Fallo al ejecutar pipeline completo: ${String(error)}`);
      return false;
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

  const didBootstrapRef = useRef<boolean>(false);

  useEffect(() => {
    if (didBootstrapRef.current) {
      return;
    }
    didBootstrapRef.current = true;

    async function bootstrap() {
      const safetyTimeout = setTimeout(() => {
        console.warn("[Bootstrap] Safety timeout reached — forcing isInitializing=false");
        setIsInitializing(false);
        setInitError("Timeout de inicialización: Tauri tardó demasiado en responder.");
      }, 20000);

      try {
        console.log("[Bootstrap] Starting initialization...");

        let tauriReady = false;
        for (let i = 0; i < 12; i++) {
          if (isTauriRuntime()) {
            tauriReady = true;
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 250));
        }

        if (!tauriReady) {
          throw new Error(
            "Tauri runtime no detectado después de 3s. Asegúrate de correr con `npm run tauri -- dev`."
          );
        }

        console.log("[Bootstrap] Tauri detected, calling getWorkspaceRoot...");

        const root = await getWorkspaceRoot();
        console.log("[Bootstrap] Got workspace root:", root);

        setYalFilePath("");
        setInputFilePath("");
        setGenerateOutputPath(joinPath(root, "output", "lexer_generated_tauri.py"));

        console.log("[Bootstrap] Opening workspace root...");
        await openWorkspaceRoot(root);
        console.log("[Bootstrap] Workspace root opened successfully");
        setInitError(""); // Clear any errors
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        console.error("[Bootstrap] Initialization failed:", error);
        setInitError(errorMsg);
        pushOutput("error", `No se pudo inicializar la app: ${errorMsg}`);
      } finally {
        clearTimeout(safetyTimeout);
        setIsInitializing(false);
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
        const hostWidth = workbenchSplitRef.current?.clientWidth ?? window.innerWidth;
        const minRightPanelWidth = 260;
        const minEditorWidth = 320;
        const splitterWidth = 6;
        const maxRightPanelWidth = Math.max(
          minRightPanelWidth,
          hostWidth - splitterWidth - minEditorWidth
        );
        const nextWidth = clamp(
          activeResize.startRightPanelWidth - dx,
          minRightPanelWidth,
          maxRightPanelWidth
        );
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

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        void saveActiveTab();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeTab, tabs]);

  return (
    <>
      {isInitializing && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#0D1B2A",
          zIndex: 9999,
          color: "#DBE4FF",
          fontFamily: "monospace",
        }}>
          <div style={{ textAlign: "center" }}>
            <h2>Inicializando YALex Studio...</h2>
            {initError && (
              <div style={{ color: "#FF6B6B", marginTop: "20px", maxWidth: "500px", wordBreak: "break-word" }}>
                <p><strong>Error:</strong></p>
                <p>{initError}</p>
              </div>
            )}
          </div>
        </div>
      )}
    <div className="shell" style={{ gridTemplateRows: `44px 1fr 6px ${outputPanelHeight}px` }}>
      <header className="topbar">
        <h1>YALex Studio</h1>
        <div className="topbar-actions">
          <button
            className="topbar-action-btn"
            type="button"
            onClick={(e) => {
              e.preventDefault();
              void saveActiveTab();
            }}
          >
            <span
              className="panel-icon topbar-icon"
              style={{
                WebkitMaskImage: `url(${saveIcon})`,
                maskImage: `url(${saveIcon})`,
              }}
            />
            Guardar
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
            ref={workbenchSplitRef}
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
                Archivo .yal
                <input
                  value={yalFilePath}
                  onChange={(event) => setYalFilePath(event.target.value)}
                  placeholder="Ruta al archivo .yal"
                />
              </label>

              <label className="field">
                Input (.txt)
                <input
                  value={inputFilePath}
                  onChange={(event) => setInputFilePath(event.target.value)}
                  placeholder="Ruta del texto de entrada"
                />
              </label>

              <label className="field">
                Output lexer
                <input
                  value={generateOutputPath}
                  onChange={(event) => setGenerateOutputPath(event.target.value)}
                  placeholder="Ruta del lexer generado"
                />
              </label>

              <button
                className="run-all-btn"
                onClick={() => void runFullPipeline()}
                disabled={isRunningAction}
              >
                {isRunningAction ? "Ejecutando..." : "Ejecutar"}
              </button>

              <button
                className="run-check-btn"
                onClick={() => void runGeneratedLexerProgram()}
                disabled={isRunningAction}
              >
                Ejecutar lexer generado
              </button>

              {validationChecks.length > 0 && (
                <section className="validation-panel">
                  <div className="validation-header">
                    <strong>{`Validación ${passedChecks}/${totalChecks}`}</strong>
                    <span>{validationRunAt ? `@ ${validationRunAt}` : ""}</span>
                  </div>
                  <div className="validation-list">
                    {validationChecks.map((check) => (
                      <div key={check.id} className={`validation-item ${check.ok ? "ok" : "fail"}`}>
                        <span className="validation-item-title">{check.label}</span>
                        <span className="validation-item-detail">{check.detail}</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <p className="command-hint">
                Ejecuta secuencialmente: Spec → AST → Construcción Directa → DFA → Tokenizar →
                Generar Lexer.
              </p>
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
            <div className="result-header">
              <div className="panel-title panel-title-tight">Resultado</div>
              {visibleResultActions.length > 0 && (
                <div className="result-tabs" role="tablist" aria-label="Etapas del pipeline">
                  {visibleResultActions.map((action) => {
                    const isActive = action === activeResultAction;
                    return (
                      <button
                        key={action}
                        role="tab"
                        type="button"
                        className={`result-tab-btn ${isActive ? "active" : ""}`}
                        aria-selected={isActive}
                        onClick={() => setActiveResultAction(action)}
                      >
                        {getActionLabel(action)}
                      </button>
                    );
                  })}
                </div>
              )}
              <div className="result-view-toggle">
                <button
                  type="button"
                  className={`result-view-btn ${resultViewMode === "json" ? "active" : ""}`}
                  onClick={() => setResultViewMode("json")}
                >
                  JSON
                </button>
                <button
                  type="button"
                  className={`result-view-btn ${resultViewMode === "graph" ? "active" : ""}`}
                  onClick={() => setResultViewMode("graph")}
                  disabled={!canRenderGraph}
                >
                  Gráfico
                </button>
                <button
                  type="button"
                  className={`result-view-btn ${resultViewMode === "code" ? "active" : ""}`}
                  onClick={() => setResultViewMode("code")}
                  disabled={!canRenderCode}
                >
                  Código Python
                </button>
                {resultViewMode === "graph" && activeResultAction === "dfa" && (
                  <>
                    <button
                      type="button"
                      className={`result-view-btn ${dfaLabelDensity === "compact" ? "active" : ""}`}
                      onClick={() => setDfaLabelDensity("compact")}
                    >
                      Compacto
                    </button>
                    <button
                      type="button"
                      className={`result-view-btn ${dfaLabelDensity === "detailed" ? "active" : ""}`}
                      onClick={() => setDfaLabelDensity("detailed")}
                    >
                      Detallado
                    </button>
                    <button
                      type="button"
                      className={`result-view-btn ${dfaEdgeLabelMode === "ranges" ? "active" : ""}`}
                      onClick={() => setDfaEdgeLabelMode("ranges")}
                    >
                      Rangos
                    </button>
                    <button
                      type="button"
                      className={`result-view-btn ${dfaEdgeLabelMode === "aliases" ? "active" : ""}`}
                      onClick={() => setDfaEdgeLabelMode("aliases")}
                    >
                      Alias
                    </button>
                  </>
                )}
              </div>
            </div>
            {resultViewMode === "graph" && canRenderGraph ? (
              <div className="result-graph-view">{renderGraphView()}</div>
            ) : resultViewMode === "code" && canRenderCode ? (
              <pre className="result-view">
                {isLoadingGeneratedCode ? "Cargando código generado..." : generatedPythonCode}
              </pre>
            ) : (
              <pre className="result-view">{activeResultText}</pre>
            )}
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
    </>
  );
}
