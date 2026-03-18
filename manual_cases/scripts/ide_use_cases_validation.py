from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.app import YALexApp


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(1)


def scenario_1_create_edit_compile_save() -> None:
    out_dir = ROOT / "manual_cases" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    new_file = out_dir / "uc1_new_spec.yal"
    if new_file.exists():
        new_file.unlink()

    with patch("tkinter.messagebox.showerror", lambda *a, **k: None), \
        patch("tkinter.messagebox.showinfo", lambda *a, **k: None), \
        patch("tkinter.messagebox.showwarning", lambda *a, **k: None), \
        patch("tkinter.filedialog.asksaveasfilename", side_effect=[str(new_file)]):

        app = YALexApp()
        app.withdraw()

        app._new_yal_file()
        if not new_file.exists():
            fail("UC1: no se creó archivo nuevo")

        app._txt_spec.delete("1.0", "end")
        app._txt_spec.insert(
            "1.0",
            "let ws = [' ''\\t''\\n']+\n\nrule tokens =\n  ws { skip() }\n| 'a' { return \"A\" }\n| '+' { return \"PLUS\" }\n",
        )
        app._save_current_file()
        app._compile_current_spec()

        if app._dfa is None:
            fail("UC1: compilar no produjo AFD")
        if "Compilado" not in app._status_var.get():
            fail("UC1: status no refleja compilación")

        app.destroy()

    print("[OK] UC1 create/edit/compile/save")


def scenario_2_open_and_analyze_with_trace() -> None:
    yal = ROOT / "tests" / "yal" / "medium.yal"
    inp = ROOT / "tests" / "input" / "medium.txt"

    ask_values = [str(yal), str(inp)]

    def fake_open(*args, **kwargs):
        if not ask_values:
            return ""
        return ask_values.pop(0)

    with patch("tkinter.messagebox.showerror", lambda *a, **k: None), \
        patch("tkinter.messagebox.showinfo", lambda *a, **k: None), \
        patch("tkinter.messagebox.showwarning", lambda *a, **k: None), \
        patch("tkinter.filedialog.askopenfilename", side_effect=fake_open):

        app = YALexApp()
        app.withdraw()

        app._open_existing_file()    # abre medium.yal
        app._compile_current_spec()
        app._load_input_file()       # abre medium.txt
        app._run_analysis()

        out = app._txt_output.get("1.0", "end")
        trace = app._txt_trace.get("1.0", "end")

        if "TOKENS ENCONTRADOS" not in out:
            fail("UC2: análisis no produjo tokens")
        if "ERRORES LÉXICOS" in out:
            fail("UC2: no se esperaban errores")
        if "TRAZA DE TRANSICIONES" not in trace:
            fail("UC2: no se mostró traza")

        app.destroy()

    print("[OK] UC2 open/analyze/trace")


def scenario_3_generate_and_execute_lexer() -> None:
    yal = ROOT / "tests" / "yal" / "low.yal"
    inp = ROOT / "tests" / "input" / "low.txt"
    out_lexer = ROOT / "manual_cases" / "output" / "uc3_generated_lexer.py"

    if out_lexer.exists():
        out_lexer.unlink()

    with patch("tkinter.messagebox.showerror", lambda *a, **k: None), \
        patch("tkinter.messagebox.showinfo", lambda *a, **k: None), \
        patch("tkinter.messagebox.showwarning", lambda *a, **k: None), \
        patch("tkinter.filedialog.askopenfilename", return_value=str(yal)), \
        patch("tkinter.filedialog.asksaveasfilename", return_value=str(out_lexer)):

        app = YALexApp()
        app.withdraw()

        app._open_existing_file()
        app._compile_current_spec()
        app._generate_lexer()

        if not out_lexer.exists():
            fail("UC3: no se generó lexer")

        app.destroy()

    proc = subprocess.run(
        ["python3", str(out_lexer), str(inp)],
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode != 0:
        fail("UC3: lexer generado no ejecutó correctamente")
    if "Token('NUMBER'" not in proc.stdout:
        fail("UC3: lexer generado no produjo tokens esperados")

    print("[OK] UC3 generate/execute lexer")


def main() -> None:
    scenario_1_create_edit_compile_save()
    scenario_2_open_and_analyze_with_trace()
    scenario_3_generate_and_execute_lexer()
    print("[OK] 3/3 use cases validados")


if __name__ == "__main__":
    main()
