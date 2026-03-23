"""
Generador de código: produce un archivo Python autónomo que implementa
un analizador léxico basado en la tabla de transiciones del AFD.

El archivo generado NO depende del generador (yalex_parser).
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from .dfa import DFA, dfa_to_table


def _clean_action(action: str) -> str | None:
    """Procesa una acción del .yal y extrae el nombre de token.

    - 'return "TOKEN"' -> 'TOKEN'
    - 'skip()' -> None (se debe omitir)
    - cadena vacía -> None
    """
    action = action.strip()
    if not action:
        return None

    lower = action.lower()
    if lower in ("skip", "skip()", "ignore", "whitespace"):
        return None
    if "skip" in lower and ("(" in lower or lower.endswith("skip")):
        return None

    # Parse return statements without regex: return "TOKEN" or return 'TOKEN'
    stripped = action.strip()
    if stripped.startswith("return"):
        rest = stripped[len("return"):].strip()
        if len(rest) >= 2 and rest[0] in ('"', "'") and rest[-1] == rest[0]:
            return rest[1:-1]

    return action


_LEXER_TEMPLATE = textwrap.dedent('''\
    #!/usr/bin/env python3
    """
    Analizador léxico generado automáticamente.
    NO EDITAR — este archivo fue producido por el generador YALex.
    """

    from __future__ import annotations

    import sys
    from dataclasses import dataclass

    # ---- Header del archivo .yal ----
    {header}
    # ---- Fin header ----


    @dataclass
    class Token:
        type: str
        lexeme: str
        line: int
        col: int

        def __repr__(self) -> str:
            return f"Token({{self.type!r}}, {{self.lexeme!r}}, line={{self.line}}, col={{self.col}})"


    @dataclass
    class LexError:
        char: str
        line: int
        col: int
        message: str

        def __repr__(self) -> str:
            return f"LexError({{self.message!r}})"


    # ---- Tabla del AFD ----
    _START = {start}
    _ACCEPT = {accept}
    _TABLE = {table}
    # ---- Fin tabla ----


    def _printable(ch: str) -> str:
        if ch == "\\n":
            return "\\\\n"
        if ch == "\\t":
            return "\\\\t"
        if ch == "\\r":
            return "\\\\r"
        if ch == " ":
            return "\\\\s"
        return ch


    def tokenize(text: str) -> tuple[list[Token], list[LexError]]:
        """Analiza *text* y retorna (tokens, errors)."""
        tokens: list[Token] = []
        errors: list[LexError] = []

        pos = 0
        line = 1
        col = 1

        while pos < len(text):
            state = _START
            last_accept_pos = -1
            last_accept_label: str | None = None
            current = pos
            token_line = line
            token_col = col

            while current < len(text):
                ch = text[current]
                state_str = str(state)
                next_state = _TABLE.get(state_str, {{}}).get(ch)
                if next_state is None:
                    break
                state = next_state
                current += 1

                state_key = str(state)
                if state_key in _ACCEPT:
                    last_accept_pos = current
                    last_accept_label = _ACCEPT[state_key]

            if last_accept_label is not None and last_accept_pos > pos:
                lexeme = text[pos:last_accept_pos]
                if last_accept_label != "__SKIP__":
                    tokens.append(Token(
                        type=last_accept_label,
                        lexeme=lexeme,
                        line=token_line,
                        col=token_col,
                    ))
                for ch in lexeme:
                    if ch == "\\n":
                        line += 1
                        col = 1
                    else:
                        col += 1
                pos = last_accept_pos
            else:
                bad_char = text[pos]
                errors.append(LexError(
                    char=bad_char,
                    line=line,
                    col=col,
                    message=f"Error léxico en línea {{line}}, columna {{col}}: carácter inesperado '{{_printable(bad_char)}}'",
                ))
                if bad_char == "\\n":
                    line += 1
                    col = 1
                else:
                    col += 1
                pos += 1

        return tokens, errors


    # ---- Trailer del archivo .yal ----
    {trailer}
    # ---- Fin trailer ----


    def main() -> None:
        if len(sys.argv) < 2:
            print("Uso: python {{sys.argv[0]}} <archivo_entrada>")
            sys.exit(1)

        input_path = sys.argv[1]
        with open(input_path, encoding="utf-8") as f:
            text = f.read()

        tokens, errors = tokenize(text)

        for token in tokens:
            print(token)

        if errors:
            print()
            for error in errors:
                print(error.message)
            sys.exit(1)


    if __name__ == "__main__":
        main()
''')


def generate_lexer(
    dfa: DFA,
    header: str | None = None,
    trailer: str | None = None,
    output_path: str | Path | None = None,
) -> str:
    """
    Genera el código fuente Python de un analizador léxico autónomo.

    Parámetros
    ----------
    dfa : DFA
        El AFD minimizado.
    header : str | None
        Código Python del header del .yal (se copia tal cual).
    trailer : str | None
        Código Python del trailer del .yal (se copia tal cual).
    output_path : str | Path | None
        Si se proporciona, escribe el código en ese archivo.

    Retorna
    -------
    str
        Código fuente del analizador léxico generado.
    """
    tbl = dfa_to_table(dfa)

    # Pre-procesar accept labels: extraer nombre de token, marcar skips con __SKIP__
    accept_clean: dict[str, str] = {}
    for state_id, raw_action in tbl["accept"].items():
        token_name = _clean_action(raw_action)
        if token_name is not None:
            accept_clean[str(state_id)] = token_name
        else:
            # Es un skip — marcarlo para que el lexer lo reconozca pero no emita token
            accept_clean[str(state_id)] = "__SKIP__"

    # Convertir tabla a strings para JSON
    table_serialized: dict[str, dict[str, int]] = {}
    for state, transitions in tbl["table"].items():
        table_serialized[str(state)] = transitions

    header_code = header.strip() if header else "# (vacío)"
    trailer_code = trailer.strip() if trailer else "# (vacío)"

    source = _LEXER_TEMPLATE.format(
        header=header_code,
        start=tbl["start"],
        accept=json.dumps(accept_clean, ensure_ascii=False),
        table=json.dumps(table_serialized, ensure_ascii=False),
        trailer=trailer_code,
    )

    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")

    return source
