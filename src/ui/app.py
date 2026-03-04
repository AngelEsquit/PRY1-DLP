"""
Interfaz gráfica del generador de analizadores léxicos YALex.

Permite:
  1. Cargar un archivo .yal
  2. Visualizar el diagrama de transición de estados (AFD)
  3. Generar el analizador léxico autónomo
  4. Ejecutar el análisis léxico sobre un archivo de texto
  5. Mostrar tokens identificados o errores léxicos
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path

# Agregar src/ al path para imports
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from yalex_parser import parse_yalex, parse_regex
from yalex_parser.thompson import build_combined_nfa
from yalex_parser.dfa import nfa_to_dfa, minimize_dfa, dfa_to_table, DFA
from yalex_parser.codegen import generate_lexer
from yalex_parser.simulator import tokenize


# ---------------------------------------------------------------------------
# Colores y estilo
# ---------------------------------------------------------------------------
BG = "#1e1e2e"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
ACCENT2 = "#a6e3a1"
ERROR_COLOR = "#f38ba8"
SURFACE = "#313244"
SURFACE2 = "#45475a"
FONT_MONO = ("Consolas", 11)
FONT_LABEL = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI", 14, "bold")


class YALexApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YALex — Generador de Analizadores Léxicos")
        self.geometry("1200x800")
        self.configure(bg=BG)
        self.minsize(900, 600)

        # Estado
        self._yal_path: str | None = None
        self._dfa: DFA | None = None
        self._dfa_table: dict | None = None
        self._header: str | None = None
        self._trailer: str | None = None

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # ---- Barra superior ----
        top = tk.Frame(self, bg=SURFACE, pady=8, padx=12)
        top.pack(fill=tk.X)

        tk.Label(top, text="YALex Generator", font=FONT_TITLE, bg=SURFACE, fg=ACCENT).pack(side=tk.LEFT)

        btn_frame = tk.Frame(top, bg=SURFACE)
        btn_frame.pack(side=tk.RIGHT)

        self._btn_load = self._make_button(btn_frame, "Cargar .yal", self._load_yal)
        self._btn_load.pack(side=tk.LEFT, padx=4)

        self._btn_generate = self._make_button(btn_frame, "Generar Lexer", self._generate_lexer)
        self._btn_generate.pack(side=tk.LEFT, padx=4)

        self._btn_analyze = self._make_button(btn_frame, "Analizar Texto", self._analyze_text)
        self._btn_analyze.pack(side=tk.LEFT, padx=4)

        # ---- Status bar ----
        self._status_var = tk.StringVar(value="Listo. Cargue un archivo .yal para comenzar.")
        status_bar = tk.Label(self, textvariable=self._status_var, bg=SURFACE2, fg=FG,
                              anchor=tk.W, padx=8, pady=4, font=FONT_LABEL)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # ---- Notebook (pestañas) ----
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=SURFACE, foreground=FG,
                        padding=[12, 6], font=FONT_LABEL)
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab 1: Especificación .yal
        self._tab_spec = tk.Frame(self._notebook, bg=BG)
        self._notebook.add(self._tab_spec, text=" Especificación ")
        self._txt_spec = self._make_text(self._tab_spec)
        self._txt_spec.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tab 2: Diagrama de transiciones (canvas)
        self._tab_diagram = tk.Frame(self._notebook, bg=BG)
        self._notebook.add(self._tab_diagram, text=" Diagrama AFD ")
        self._build_diagram_tab()

        # Tab 3: Código generado
        self._tab_code = tk.Frame(self._notebook, bg=BG)
        self._notebook.add(self._tab_code, text=" Código Generado ")
        self._txt_code = self._make_text(self._tab_code)
        self._txt_code.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tab 4: Análisis léxico
        self._tab_analysis = tk.Frame(self._notebook, bg=BG)
        self._notebook.add(self._tab_analysis, text=" Análisis Léxico ")
        self._build_analysis_tab()

    def _build_diagram_tab(self) -> None:
        ctrl = tk.Frame(self._tab_diagram, bg=BG)
        ctrl.pack(fill=tk.X, padx=4, pady=4)
        tk.Label(ctrl, text="Diagrama de transiciones del AFD minimizado",
                 bg=BG, fg=ACCENT, font=FONT_LABEL).pack(side=tk.LEFT)

        # Canvas con scroll
        container = tk.Frame(self._tab_diagram, bg=BG)
        container.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._canvas = tk.Canvas(container, bg="#181825", highlightthickness=0)
        h_scroll = tk.Scrollbar(container, orient=tk.HORIZONTAL, command=self._canvas.xview)
        v_scroll = tk.Scrollbar(container, orient=tk.VERTICAL, command=self._canvas.yview)
        self._canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _build_analysis_tab(self) -> None:
        paned = tk.PanedWindow(self._tab_analysis, orient=tk.HORIZONTAL, bg=SURFACE2,
                               sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Panel izquierdo: entrada
        left = tk.Frame(paned, bg=BG)
        paned.add(left, width=500)
        tk.Label(left, text="Texto de entrada", bg=BG, fg=ACCENT, font=FONT_LABEL).pack(anchor=tk.W, padx=4, pady=(4, 0))

        input_btn_frame = tk.Frame(left, bg=BG)
        input_btn_frame.pack(fill=tk.X, padx=4, pady=2)
        self._make_button(input_btn_frame, "Cargar archivo", self._load_input_file).pack(side=tk.LEFT)
        self._make_button(input_btn_frame, "Ejecutar análisis", self._run_analysis).pack(side=tk.LEFT, padx=4)

        self._txt_input = self._make_text(left)
        self._txt_input.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Panel derecho: resultado
        right = tk.Frame(paned, bg=BG)
        paned.add(right, width=500)
        tk.Label(right, text="Resultado", bg=BG, fg=ACCENT2, font=FONT_LABEL).pack(anchor=tk.W, padx=4, pady=(4, 0))
        self._txt_output = self._make_text(right)
        self._txt_output.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # -------------------------------------------------------------- Widgets
    def _make_button(self, parent: tk.Widget, text: str, command) -> tk.Button:
        return tk.Button(parent, text=text, command=command,
                         bg=ACCENT, fg=BG, activebackground=ACCENT2,
                         activeforeground=BG, font=FONT_LABEL, bd=0,
                         padx=12, pady=4, cursor="hand2")

    def _make_text(self, parent: tk.Widget) -> scrolledtext.ScrolledText:
        txt = scrolledtext.ScrolledText(parent, bg="#181825", fg=FG,
                                        insertbackground=FG, font=FONT_MONO,
                                        bd=0, padx=8, pady=8, wrap=tk.NONE)
        return txt

    # ------------------------------------------------------------ Acciones
    def _load_yal(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar archivo YALex",
            filetypes=[("YALex files", "*.yal"), ("Todos", "*.*")],
        )
        if not path:
            return

        self._yal_path = path
        try:
            source = Path(path).read_text(encoding="utf-8")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")
            return

        # Mostrar en pestaña de especificación
        self._txt_spec.delete("1.0", tk.END)
        self._txt_spec.insert("1.0", source)

        # Parsear y construir AFD
        try:
            spec = parse_yalex(source)
            self._header = spec.header
            self._trailer = spec.trailer

            let_asts = {d.name: parse_regex(d.regex) for d in spec.lets}

            entries = []
            if spec.rule:
                for idx, alt in enumerate(spec.rule.alternatives):
                    label = alt.action.strip() if alt.action else f"ALT_{idx}"
                    entries.append((label, parse_regex(alt.regex)))

            combined = build_combined_nfa(entries, let_asts)
            dfa = nfa_to_dfa(combined)
            self._dfa = minimize_dfa(dfa)
            self._dfa_table = dfa_to_table(self._dfa)

            self._status_var.set(f"Cargado: {Path(path).name} — "
                                 f"{len(self._dfa.states)} estados AFD, "
                                 f"{len(self._dfa.transitions)} transiciones")
            self._draw_diagram()

            # Generar código y mostrarlo
            code = generate_lexer(self._dfa, self._header, self._trailer)
            self._txt_code.delete("1.0", tk.END)
            self._txt_code.insert("1.0", code)

        except Exception as e:
            messagebox.showerror("Error al procesar", str(e))
            self._status_var.set(f"Error: {e}")

    def _generate_lexer(self) -> None:
        if self._dfa is None:
            messagebox.showwarning("Aviso", "Primero cargue un archivo .yal")
            return

        path = filedialog.asksaveasfilename(
            title="Guardar analizador léxico",
            defaultextension=".py",
            filetypes=[("Python", "*.py"), ("Todos", "*.*")],
        )
        if not path:
            return

        try:
            generate_lexer(self._dfa, self._header, self._trailer, output_path=path)
            self._status_var.set(f"Lexer generado: {path}")
            messagebox.showinfo("Éxito", f"Analizador léxico guardado en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _analyze_text(self) -> None:
        self._notebook.select(self._tab_analysis)

    def _load_input_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de entrada",
            filetypes=[("Text files", "*.txt"), ("Todos", "*.*")],
        )
        if not path:
            return

        try:
            text = Path(path).read_text(encoding="utf-8")
            self._txt_input.delete("1.0", tk.END)
            self._txt_input.insert("1.0", text)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _run_analysis(self) -> None:
        if self._dfa_table is None:
            messagebox.showwarning("Aviso", "Primero cargue un archivo .yal")
            return

        text = self._txt_input.get("1.0", tk.END)
        if not text.strip():
            messagebox.showwarning("Aviso", "Ingrese o cargue texto para analizar")
            return

        tbl = self._dfa_table
        # Convertir claves a strings para compatibilidad
        accept_str = {str(k): v for k, v in tbl["accept"].items()}
        table_str: dict[str, dict[str, int]] = {}
        for state, trans in tbl["table"].items():
            table_str[str(state)] = trans

        # Usar el simulador con claves numéricas
        tokens, errors = tokenize(
            text,
            tbl["start"],
            tbl["accept"],
            tbl["table"],
        )

        self._txt_output.delete("1.0", tk.END)

        if tokens:
            self._txt_output.insert(tk.END, "=== TOKENS ENCONTRADOS ===\n\n")
            for tok in tokens:
                self._txt_output.insert(
                    tk.END,
                    f"  {tok.type:<20s}  {tok.lexeme!r:<20s}  (línea {tok.line}, col {tok.col})\n",
                )

        if errors:
            self._txt_output.insert(tk.END, "\n=== ERRORES LÉXICOS ===\n\n")
            for err in errors:
                self._txt_output.insert(tk.END, f"  {err.message}\n")

        if not tokens and not errors:
            self._txt_output.insert(tk.END, "(entrada vacía o solo whitespace)")

        n_tok = len(tokens)
        n_err = len(errors)
        self._status_var.set(f"Análisis completo: {n_tok} tokens, {n_err} errores")

    # ----------------------------------------------------------- Diagrama
    def _draw_diagram(self) -> None:
        """Dibuja el diagrama de transiciones del AFD en el canvas."""
        self._canvas.delete("all")
        if self._dfa is None:
            return

        import math

        states = self._dfa.states
        n = len(states)
        if n == 0:
            return

        # Posicionar estados en una cuadrícula
        cols = max(1, int(math.ceil(math.sqrt(n))))
        rows = max(1, (n + cols - 1) // cols)
        spacing_x = 180
        spacing_y = 140
        margin = 80
        radius = 30

        positions: dict[int, tuple[int, int]] = {}
        for i, st in enumerate(states):
            row = i // cols
            col = i % cols
            x = margin + col * spacing_x
            y = margin + row * spacing_y
            positions[st.id] = (x, y)

        # Agrupar transiciones por (from, to)
        edge_labels: dict[tuple[int, int], list[str]] = {}
        for t in self._dfa.transitions:
            key = (t.from_state, t.to_state)
            edge_labels.setdefault(key, []).append(t.char)

        # Dibujar transiciones
        for (src, dst), chars in edge_labels.items():
            label = self._compress_chars(chars)
            x1, y1 = positions[src]
            x2, y2 = positions[dst]

            if src == dst:
                # Self-loop
                self._canvas.create_arc(
                    x1 - radius - 10, y1 - radius - 30,
                    x1 + radius + 10, y1 - 10,
                    start=200, extent=140, style=tk.ARC,
                    outline=SURFACE2, width=1,
                )
                self._canvas.create_text(
                    x1, y1 - radius - 22,
                    text=label, fill=FG, font=("Consolas", 7),
                    anchor=tk.S,
                )
            else:
                # Flecha
                dx = x2 - x1
                dy = y2 - y1
                dist = math.sqrt(dx * dx + dy * dy)
                if dist == 0:
                    continue
                ux, uy = dx / dist, dy / dist

                sx = x1 + ux * radius
                sy = y1 + uy * radius
                ex = x2 - ux * radius
                ey = y2 - uy * radius

                self._canvas.create_line(
                    sx, sy, ex, ey,
                    arrow=tk.LAST, fill=SURFACE2, width=1,
                    arrowshape=(8, 10, 4),
                )
                mx = (sx + ex) / 2
                my = (sy + ey) / 2
                # Offset perpendicular para la etiqueta
                px, py = -uy * 12, ux * 12
                self._canvas.create_text(
                    mx + px, my + py,
                    text=label, fill=FG, font=("Consolas", 7),
                )

        # Dibujar flecha de inicio
        sx, sy = positions[self._dfa.start_state]
        self._canvas.create_line(
            sx - radius - 30, sy, sx - radius, sy,
            arrow=tk.LAST, fill=ACCENT, width=2,
            arrowshape=(8, 10, 4),
        )

        # Dibujar estados
        for st in states:
            x, y = positions[st.id]
            outline_color = ACCENT2 if st.is_accept else ACCENT
            fill_color = SURFACE

            self._canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                outline=outline_color, width=2, fill=fill_color,
            )
            if st.is_accept:
                # Doble círculo
                r2 = radius - 5
                self._canvas.create_oval(
                    x - r2, y - r2, x + r2, y + r2,
                    outline=outline_color, width=1, fill=fill_color,
                )

            self._canvas.create_text(
                x, y, text=str(st.id), fill=FG, font=("Consolas", 10, "bold"),
            )

            if st.is_accept and st.accept_label:
                self._canvas.create_text(
                    x, y + radius + 12,
                    text=st.accept_label, fill=ACCENT2, font=("Consolas", 8),
                )

        # Ajustar scrollregion
        total_w = margin * 2 + cols * spacing_x
        total_h = margin * 2 + rows * spacing_y
        self._canvas.configure(scrollregion=(0, 0, total_w, total_h))

    @staticmethod
    def _compress_chars(chars: list[str]) -> str:
        """Comprime lista de caracteres a una representación legible."""
        if len(chars) > 10:
            # Intentar rangos
            codes = sorted(set(ord(c) for c in chars))
            parts = []
            i = 0
            while i < len(codes):
                j = i
                while j + 1 < len(codes) and codes[j + 1] == codes[j] + 1:
                    j += 1
                if j - i >= 2:
                    parts.append(f"{chr(codes[i])}-{chr(codes[j])}")
                else:
                    for k in range(i, j + 1):
                        c = chr(codes[k])
                        if c == ' ':
                            parts.append("\\s")
                        elif c == '\n':
                            parts.append("\\n")
                        elif c == '\t':
                            parts.append("\\t")
                        else:
                            parts.append(c)
                i = j + 1
            return ",".join(parts)

        result = []
        for c in sorted(set(chars)):
            if c == ' ':
                result.append("\\s")
            elif c == '\n':
                result.append("\\n")
            elif c == '\t':
                result.append("\\t")
            else:
                result.append(c)
        return ",".join(result)


def main() -> None:
    app = YALexApp()
    app.mainloop()


if __name__ == "__main__":
    main()
