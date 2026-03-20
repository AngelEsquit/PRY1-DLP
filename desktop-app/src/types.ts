export type FileNode = {
  name: string;
  path: string;
  isDir: boolean;
};

export type OpenTab = {
  path: string;
  name: string;
  content: string;
  dirty: boolean;
};

export type YalexAction =
  | "spec"
  | "ast"
  | "nfa"
  | "combinedNfa"
  | "dfa"
  | "tokenize"
  | "generate";
