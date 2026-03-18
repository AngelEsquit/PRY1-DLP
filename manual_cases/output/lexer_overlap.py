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
_ACCEPT = {"1": "__SKIP__", "2": "MINUS", "3": "INT", "4": "EQ1", "5": "GT", "6": "ID", "7": "ID", "8": "ID", "9": "ID", "10": "ID", "11": "ID", "12": "ID", "13": "IF", "14": "IFELSE", "15": "IFDEF", "16": "EQ2", "17": "EQ3", "18": "EQ4", "19": "ARROW"}
_TABLE = {"0": {"\t": 1, "\n": 1, "\r": 1, " ": 1, "-": 2, "0": 3, "1": 3, "2": 3, "3": 3, "4": 3, "5": 3, "6": 3, "7": 3, "8": 3, "9": 3, "=": 4, ">": 5, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "a": 6, "b": 6, "c": 6, "d": 6, "e": 6, "f": 6, "g": 6, "h": 6, "i": 10, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "1": {"\t": 1, "\n": 1, "\r": 1, " ": 1}, "2": {">": 19}, "3": {"0": 3, "1": 3, "2": 3, "3": 3, "4": 3, "5": 3, "6": 3, "7": 3, "8": 3, "9": 3}, "4": {"=": 16}, "6": {"0": 6, "1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "_": 6, "a": 6, "b": 6, "c": 6, "d": 6, "e": 6, "f": 6, "g": 6, "h": 6, "i": 6, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "7": {"0": 6, "1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "_": 6, "a": 6, "b": 6, "c": 6, "d": 6, "e": 6, "f": 6, "g": 6, "h": 6, "i": 6, "j": 6, "k": 6, "l": 9, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "8": {"0": 6, "1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "_": 6, "a": 6, "b": 6, "c": 6, "d": 6, "e": 12, "f": 6, "g": 6, "h": 6, "i": 6, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "9": {"0": 6, "1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "_": 6, "a": 6, "b": 6, "c": 6, "d": 6, "e": 6, "f": 6, "g": 6, "h": 6, "i": 6, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 11, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "10": {"0": 6, "1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "_": 6, "a": 6, "b": 6, "c": 6, "d": 6, "e": 6, "f": 13, "g": 6, "h": 6, "i": 6, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "11": {"0": 6, "1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "_": 6, "a": 6, "b": 6, "c": 6, "d": 6, "e": 14, "f": 6, "g": 6, "h": 6, "i": 6, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "12": {"0": 6, "1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "_": 6, "a": 6, "b": 6, "c": 6, "d": 6, "e": 6, "f": 15, "g": 6, "h": 6, "i": 6, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "13": {"0": 6, "1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "_": 6, "a": 6, "b": 6, "c": 6, "d": 8, "e": 7, "f": 6, "g": 6, "h": 6, "i": 6, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "14": {"0": 6, "1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "_": 6, "a": 6, "b": 6, "c": 6, "d": 6, "e": 6, "f": 6, "g": 6, "h": 6, "i": 6, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "15": {"0": 6, "1": 6, "2": 6, "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6, "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 6, "G": 6, "H": 6, "I": 6, "J": 6, "K": 6, "L": 6, "M": 6, "N": 6, "O": 6, "P": 6, "Q": 6, "R": 6, "S": 6, "T": 6, "U": 6, "V": 6, "W": 6, "X": 6, "Y": 6, "Z": 6, "_": 6, "a": 6, "b": 6, "c": 6, "d": 6, "e": 6, "f": 6, "g": 6, "h": 6, "i": 6, "j": 6, "k": 6, "l": 6, "m": 6, "n": 6, "o": 6, "p": 6, "q": 6, "r": 6, "s": 6, "t": 6, "u": 6, "v": 6, "w": 6, "x": 6, "y": 6, "z": 6}, "16": {"=": 17}, "17": {"=": 18}}
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
