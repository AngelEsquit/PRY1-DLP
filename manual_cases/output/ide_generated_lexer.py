#!/usr/bin/env python3
"""
Analizador léxico generado automáticamente.
NO EDITAR — este archivo fue producido por el generador YALex.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

# ---- Header del archivo .yal ----
# (vacío)
# ---- Fin header ----


@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type!r}, {self.lexeme!r}, line={self.line}, col={self.col})"


@dataclass
class LexError:
    char: str
    line: int
    col: int
    message: str

    def __repr__(self) -> str:
        return f"LexError({self.message!r})"


# ---- Tabla del AFD ----
_START = 0
_ACCEPT = {"1": "__SKIP__", "2": "LPAREN", "3": "RPAREN", "4": "TIMES", "5": "PLUS", "6": "MINUS", "7": "DIV", "8": "NUMBER"}
_TABLE = {"0": {"\t": 1, "\n": 1, " ": 1, "(": 2, ")": 3, "*": 4, "+": 5, "-": 6, "/": 7, "0": 8, "1": 8, "2": 8, "3": 8, "4": 8, "5": 8, "6": 8, "7": 8, "8": 8, "9": 8}, "1": {"\t": 1, "\n": 1, " ": 1}, "8": {"0": 8, "1": 8, "2": 8, "3": 8, "4": 8, "5": 8, "6": 8, "7": 8, "8": 8, "9": 8}}
# ---- Fin tabla ----


def _printable(ch: str) -> str:
    if ch == "\n":
        return "\\n"
    if ch == "\t":
        return "\\t"
    if ch == "\r":
        return "\\r"
    if ch == " ":
        return "\\s"
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
            next_state = _TABLE.get(state_str, {}).get(ch)
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
                if ch == "\n":
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
                message=f"Error léxico en línea {line}, columna {col}: carácter inesperado '{_printable(bad_char)}'",
            ))
            if bad_char == "\n":
                line += 1
                col = 1
            else:
                col += 1
            pos += 1

    return tokens, errors


# ---- Trailer del archivo .yal ----
# (vacío)
# ---- Fin trailer ----


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python {sys.argv[0]} <archivo_entrada>")
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
