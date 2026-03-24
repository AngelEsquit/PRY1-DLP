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
_ACCEPT = {"1": "TEXT", "2": "__SKIP__", "3": "__SKIP__", "4": "DQUOTE", "5": "VOW", "6": "CONS"}
_TABLE = {"0": {"\u0000": 1, "\u0001": 1, "\u0002": 1, "\u0003": 1, "\u0004": 1, "\u0005": 1, "\u0006": 1, "\u0007": 1, "\b": 1, "\t": 2, "\n": 3, "\u000b": 1, "\f": 1, "\r": 3, "\u000e": 1, "\u000f": 1, "\u0010": 1, "\u0011": 1, "\u0012": 1, "\u0013": 1, "\u0014": 1, "\u0015": 1, "\u0016": 1, "\u0017": 1, "\u0018": 1, "\u0019": 1, "\u001a": 1, "\u001b": 1, "\u001c": 1, "\u001d": 1, "\u001e": 1, "\u001f": 1, " ": 2, "!": 1, "\"": 4, "#": 1, "$": 1, "%": 1, "&": 1, "'": 1, "(": 1, ")": 1, "*": 1, "+": 1, ",": 1, "-": 1, ".": 1, "/": 1, "0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1, "9": 1, ":": 1, ";": 1, "<": 1, "=": 1, ">": 1, "?": 1, "@": 1, "A": 5, "B": 6, "C": 6, "D": 6, "E": 5, "F": 6, "G": 6, "H": 6, "I": 5, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 5, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 5, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "[": 1, "\\": 1, "]": 1, "^": 1, "_": 1, "`": 1, "a": 5, "b": 6, "c": 6, "d": 6, "e": 5, "f": 6, "g": 6, "h": 6, "i": 5, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 5, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 5, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6, "{": 1, "|": 1, "}": 1, "~": 1, "": 1}, "1": {"\u0000": 1, "\u0001": 1, "\u0002": 1, "\u0003": 1, "\u0004": 1, "\u0005": 1, "\u0006": 1, "\u0007": 1, "\b": 1, "\t": 1, "\u000b": 1, "\f": 1, "\u000e": 1, "\u000f": 1, "\u0010": 1, "\u0011": 1, "\u0012": 1, "\u0013": 1, "\u0014": 1, "\u0015": 1, "\u0016": 1, "\u0017": 1, "\u0018": 1, "\u0019": 1, "\u001a": 1, "\u001b": 1, "\u001c": 1, "\u001d": 1, "\u001e": 1, "\u001f": 1, " ": 1, "!": 1, "#": 1, "$": 1, "%": 1, "&": 1, "'": 1, "(": 1, ")": 1, "*": 1, "+": 1, ",": 1, "-": 1, ".": 1, "/": 1, "0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1, "9": 1, ":": 1, ";": 1, "<": 1, "=": 1, ">": 1, "?": 1, "@": 1, "A": 1, "B": 1, "C": 1, "D": 1, "E": 1, "F": 1, "G": 1, "H": 1, "I": 1, "J": 1, "K": 1, "L": 1, "M": 1, "N": 1, "O": 1, "P": 1, "Q": 1, "R": 1, "S": 1, "T": 1, "U": 1, "V": 1, "W": 1, "X": 1, "Y": 1, "Z": 1, "[": 1, "\\": 1, "]": 1, "^": 1, "_": 1, "`": 1, "a": 1, "b": 1, "c": 1, "d": 1, "e": 1, "f": 1, "g": 1, "h": 1, "i": 1, "j": 1, "k": 1, "l": 1, "m": 1, "n": 1, "o": 1, "p": 1, "q": 1, "r": 1, "s": 1, "t": 1, "u": 1, "v": 1, "w": 1, "x": 1, "y": 1, "z": 1, "{": 1, "|": 1, "}": 1, "~": 1, "": 1}, "2": {"\u0000": 1, "\u0001": 1, "\u0002": 1, "\u0003": 1, "\u0004": 1, "\u0005": 1, "\u0006": 1, "\u0007": 1, "\b": 1, "\t": 2, "\n": 3, "\u000b": 1, "\f": 1, "\r": 3, "\u000e": 1, "\u000f": 1, "\u0010": 1, "\u0011": 1, "\u0012": 1, "\u0013": 1, "\u0014": 1, "\u0015": 1, "\u0016": 1, "\u0017": 1, "\u0018": 1, "\u0019": 1, "\u001a": 1, "\u001b": 1, "\u001c": 1, "\u001d": 1, "\u001e": 1, "\u001f": 1, " ": 2, "!": 1, "#": 1, "$": 1, "%": 1, "&": 1, "'": 1, "(": 1, ")": 1, "*": 1, "+": 1, ",": 1, "-": 1, ".": 1, "/": 1, "0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1, "9": 1, ":": 1, ";": 1, "<": 1, "=": 1, ">": 1, "?": 1, "@": 1, "A": 1, "B": 1, "C": 1, "D": 1, "E": 1, "F": 1, "G": 1, "H": 1, "I": 1, "J": 1, "K": 1, "L": 1, "M": 1, "N": 1, "O": 1, "P": 1, "Q": 1, "R": 1, "S": 1, "T": 1, "U": 1, "V": 1, "W": 1, "X": 1, "Y": 1, "Z": 1, "[": 1, "\\": 1, "]": 1, "^": 1, "_": 1, "`": 1, "a": 1, "b": 1, "c": 1, "d": 1, "e": 1, "f": 1, "g": 1, "h": 1, "i": 1, "j": 1, "k": 1, "l": 1, "m": 1, "n": 1, "o": 1, "p": 1, "q": 1, "r": 1, "s": 1, "t": 1, "u": 1, "v": 1, "w": 1, "x": 1, "y": 1, "z": 1, "{": 1, "|": 1, "}": 1, "~": 1, "": 1}, "3": {"\t": 3, "\n": 3, "\r": 3, " ": 3}, "5": {"\u0000": 1, "\u0001": 1, "\u0002": 1, "\u0003": 1, "\u0004": 1, "\u0005": 1, "\u0006": 1, "\u0007": 1, "\b": 1, "\t": 1, "\u000b": 1, "\f": 1, "\u000e": 1, "\u000f": 1, "\u0010": 1, "\u0011": 1, "\u0012": 1, "\u0013": 1, "\u0014": 1, "\u0015": 1, "\u0016": 1, "\u0017": 1, "\u0018": 1, "\u0019": 1, "\u001a": 1, "\u001b": 1, "\u001c": 1, "\u001d": 1, "\u001e": 1, "\u001f": 1, " ": 1, "!": 1, "#": 1, "$": 1, "%": 1, "&": 1, "'": 1, "(": 1, ")": 1, "*": 1, "+": 1, ",": 1, "-": 1, ".": 1, "/": 1, "0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1, "9": 1, ":": 1, ";": 1, "<": 1, "=": 1, ">": 1, "?": 1, "@": 1, "A": 5, "B": 1, "C": 1, "D": 1, "E": 5, "F": 1, "G": 1, "H": 1, "I": 5, "J": 1, "K": 1, "L": 1, "M": 1, "N": 1, "O": 5, "P": 1, "Q": 1, "R": 1, "S": 1, "T": 1, "U": 5, "V": 1, "W": 1, "X": 1, "Y": 1, "Z": 1, "[": 1, "\\": 1, "]": 1, "^": 1, "_": 1, "`": 1, "a": 5, "b": 1, "c": 1, "d": 1, "e": 5, "f": 1, "g": 1, "h": 1, "i": 5, "j": 1, "k": 1, "l": 1, "m": 1, "n": 1, "o": 5, "p": 1, "q": 1, "r": 1, "s": 1, "t": 1, "u": 5, "v": 1, "w": 1, "x": 1, "y": 1, "z": 1, "{": 1, "|": 1, "}": 1, "~": 1, "": 1}, "6": {"\u0000": 1, "\u0001": 1, "\u0002": 1, "\u0003": 1, "\u0004": 1, "\u0005": 1, "\u0006": 1, "\u0007": 1, "\b": 1, "\t": 1, "\u000b": 1, "\f": 1, "\u000e": 1, "\u000f": 1, "\u0010": 1, "\u0011": 1, "\u0012": 1, "\u0013": 1, "\u0014": 1, "\u0015": 1, "\u0016": 1, "\u0017": 1, "\u0018": 1, "\u0019": 1, "\u001a": 1, "\u001b": 1, "\u001c": 1, "\u001d": 1, "\u001e": 1, "\u001f": 1, " ": 1, "!": 1, "#": 1, "$": 1, "%": 1, "&": 1, "'": 1, "(": 1, ")": 1, "*": 1, "+": 1, ",": 1, "-": 1, ".": 1, "/": 1, "0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1, "9": 1, ":": 1, ";": 1, "<": 1, "=": 1, ">": 1, "?": 1, "@": 1, "A": 1, "B": 6, "C": 6, "D": 6, "E": 1, "F": 6, "G": 6, "H": 6, "I": 1, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 1, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 1, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "[": 1, "\\": 1, "]": 1, "^": 1, "_": 1, "`": 1, "a": 1, "b": 6, "c": 6, "d": 6, "e": 1, "f": 6, "g": 6, "h": 6, "i": 1, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 1, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 1, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6, "{": 1, "|": 1, "}": 1, "~": 1, "": 1}}
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
