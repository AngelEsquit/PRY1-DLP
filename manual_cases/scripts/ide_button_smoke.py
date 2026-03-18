from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.app import YALexApp


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(1)


def main() -> None:
    tmp = ROOT / "manual_cases" / "output"
    tmp.mkdir(parents=True, exist_ok=True)

    new_yal = tmp / "ide_new_case.yal"
    open_yal = ROOT / "tests" / "yal" / "low.yal"
    input_txt = ROOT / "tests" / "input" / "low.txt"
    out_lexer = tmp / "ide_generated_lexer.py"

    if new_yal.exists():
        new_yal.unlink()
    if out_lexer.exists():
        out_lexer.unlink()

    askopen_values = [str(open_yal), str(input_txt)]

    def fake_askopenfilename(*args, **kwargs):
        if not askopen_values:
            return ""
        return askopen_values.pop(0)

    with patch("tkinter.messagebox.showerror", lambda *a, **k: None), \
        patch("tkinter.messagebox.showinfo", lambda *a, **k: None), \
        patch("tkinter.messagebox.showwarning", lambda *a, **k: None), \
        patch("tkinter.filedialog.asksaveasfilename", side_effect=[str(new_yal), str(out_lexer)]), \
        patch("tkinter.filedialog.askopenfilename", side_effect=fake_askopenfilename):

        app = YALexApp()
        app.withdraw()

        # Botón: Nuevo .yal
        app._new_yal_file()
        if not new_yal.exists():
            _fail("Nuevo .yal no creó archivo")

        # Botón: Abrir
        app._open_existing_file()
        if app._yal_path is None or not app._yal_path.endswith("low.yal"):
            _fail("Abrir no cargó el .yal esperado")

        # Botón: Guardar (sobre .yal actual)
        app._txt_spec.insert("end", "\n| '+' { return \"PLUS\" }\n")
        app._save_current_file()
        saved = Path(app._current_file).read_text(encoding="utf-8")
        if "PLUS" not in saved:
            _fail("Guardar no persistió cambios del editor")

        # Botón: Compilar
        app._compile_current_spec()
        if app._dfa is None or app._dfa_table is None:
            _fail("Compilar no generó AFD")

        # Botón: Cargar archivo (análisis)
        app._load_input_file()
        if "12" not in app._txt_input.get("1.0", "end"):
            _fail("Cargar archivo no llenó el input de análisis")

        # Botón: Analizar / Ejecutar análisis
        app._run_analysis()
        out = app._txt_output.get("1.0", "end")
        trace = app._txt_trace.get("1.0", "end")
        if "TOKENS ENCONTRADOS" not in out:
            _fail("Analizar no produjo salida de tokens")
        if "TRAZA DE TRANSICIONES" not in trace:
            _fail("Analizar no produjo traza")

        # Botón: Generar Lexer
        app._generate_lexer()
        if not out_lexer.exists():
            _fail("Generar Lexer no creó archivo")

        app.destroy()

    print("[OK] Smoke test IDE: botones principales funcionales")


if __name__ == "__main__":
    main()
