from __future__ import annotations

from dataclasses import dataclass

from .regex_ast import (
    BinaryNode,
    CharRange,
    CharSetNode,
    ConcatNode,
    IdentifierNode,
    LiteralNode,
    RegexNode,
    StringNode,
    UnaryNode,
    WildcardNode,
)


@dataclass
class RegexCursor:
    text: str
    pos: int = 0

    def eof(self) -> bool:
        return self.pos >= len(self.text)

    def peek(self) -> str:
        if self.eof():
            return ""
        return self.text[self.pos]

    def skip_whitespace(self) -> None:
        while not self.eof() and self.text[self.pos].isspace():
            self.pos += 1


def parse_regex(regex: str) -> RegexNode:
    cursor = RegexCursor(regex)
    node = _parse_union(cursor)
    cursor.skip_whitespace()
    if not cursor.eof():
        raise ValueError(f"Regex inválida, contenido restante en posición {cursor.pos}")
    return node


def _parse_union(cursor: RegexCursor) -> RegexNode:
    node = _parse_concat(cursor)
    cursor.skip_whitespace()

    while not cursor.eof() and cursor.peek() in "|/":
        op = cursor.peek()
        cursor.pos += 1
        right = _parse_concat(cursor)
        node = BinaryNode(operator=op, left=node, right=right)
        cursor.skip_whitespace()

    return node


def _parse_concat(cursor: RegexCursor) -> RegexNode:
    parts: list[RegexNode] = []

    first = _parse_repeat(cursor)
    parts.append(first)
    cursor.skip_whitespace()

    while _starts_atom(cursor):
        parts.append(_parse_repeat(cursor))
        cursor.skip_whitespace()

    if len(parts) == 1:
        return parts[0]
    return ConcatNode(parts=parts)


def _parse_repeat(cursor: RegexCursor) -> RegexNode:
    node = _parse_difference(cursor)
    cursor.skip_whitespace()

    while not cursor.eof() and cursor.peek() in "*+?":
        op = cursor.peek()
        cursor.pos += 1
        node = UnaryNode(operator=op, operand=node)
        cursor.skip_whitespace()

    return node


def _parse_difference(cursor: RegexCursor) -> RegexNode:
    node = _parse_atom(cursor)
    cursor.skip_whitespace()

    while not cursor.eof() and cursor.peek() == "#":
        cursor.pos += 1
        right = _parse_atom(cursor)
        node = BinaryNode(operator="#", left=node, right=right)
        cursor.skip_whitespace()

    return node


def _parse_atom(cursor: RegexCursor) -> RegexNode:
    cursor.skip_whitespace()
    if cursor.eof():
        raise ValueError("Regex incompleta")

    ch = cursor.peek()

    if ch == "(":
        cursor.pos += 1
        node = _parse_union(cursor)
        cursor.skip_whitespace()
        _expect_char(cursor, ")")
        return node

    if ch == "'":
        return LiteralNode(value=_read_quoted_char(cursor))

    if ch == '"':
        return StringNode(value=_read_quoted_string(cursor))

    if ch == "_":
        cursor.pos += 1
        return WildcardNode()

    if ch == "[":
        return _read_charset(cursor)

    if ch.isalpha() or ch == "_":
        return IdentifierNode(name=_read_identifier(cursor))

    raise ValueError(f"Símbolo inesperado '{ch}' en posición {cursor.pos}")


def _read_charset(cursor: RegexCursor) -> CharSetNode:
    _expect_char(cursor, "[")
    cursor.skip_whitespace()

    negated = False
    if not cursor.eof() and cursor.peek() == "^":
        negated = True
        cursor.pos += 1
        cursor.skip_whitespace()

    singles: list[str] = []
    ranges: list[CharRange] = []

    while not cursor.eof() and cursor.peek() != "]":
        cursor.skip_whitespace()
        if cursor.peek() == "]":
            break

        values = _read_charset_element(cursor)
        cursor.skip_whitespace()

        if len(values) == 1 and not cursor.eof() and cursor.peek() == "-":
            cursor.pos += 1
            cursor.skip_whitespace()
            right_values = _read_charset_element(cursor)
            if len(right_values) != 1:
                raise ValueError("Rango inválido en set de caracteres")
            ranges.append(CharRange(start=values[0], end=right_values[0]))
            cursor.skip_whitespace()
            continue

        singles.extend(values)
        cursor.skip_whitespace()

    _expect_char(cursor, "]")
    return CharSetNode(negated=negated, singles=singles, ranges=ranges)


def _read_charset_element(cursor: RegexCursor) -> list[str]:
    ch = cursor.peek()
    if ch == "'":
        return [_read_quoted_char(cursor)]
    if ch == '"':
        return list(_read_quoted_string(cursor))

    cursor.pos += 1
    return [ch]


def _read_quoted_char(cursor: RegexCursor) -> str:
    _expect_char(cursor, "'")
    if cursor.eof():
        raise ValueError("Literal de carácter incompleto")

    if cursor.peek() == "\\":
        cursor.pos += 1
        if cursor.eof():
            raise ValueError("Secuencia de escape incompleta")
        escaped = _decode_escape(cursor.peek())
        cursor.pos += 1
        _expect_char(cursor, "'")
        return escaped

    value = cursor.peek()
    cursor.pos += 1
    _expect_char(cursor, "'")
    return value


def _read_quoted_string(cursor: RegexCursor) -> str:
    _expect_char(cursor, '"')
    chars: list[str] = []

    while not cursor.eof() and cursor.peek() != '"':
        ch = cursor.peek()
        if ch == "\\":
            cursor.pos += 1
            if cursor.eof():
                raise ValueError("Secuencia de escape incompleta")
            chars.append(_decode_escape(cursor.peek()))
            cursor.pos += 1
            continue

        chars.append(ch)
        cursor.pos += 1

    _expect_char(cursor, '"')
    return "".join(chars)


def _decode_escape(ch: str) -> str:
    mapping = {
        "n": "\n",
        "t": "\t",
        "r": "\r",
        "\\": "\\",
        "\"": '"',
        "'": "'",
        "b": "\b",
        "f": "\f",
        "v": "\v",
    }
    return mapping.get(ch, ch)


def _read_identifier(cursor: RegexCursor) -> str:
    start = cursor.pos
    while not cursor.eof() and (cursor.peek().isalnum() or cursor.peek() == "_"):
        cursor.pos += 1
    return cursor.text[start:cursor.pos]


def _starts_atom(cursor: RegexCursor) -> bool:
    cursor.skip_whitespace()
    if cursor.eof():
        return False

    ch = cursor.peek()
    return ch in "('[_\"" or ch.isalpha()


def _expect_char(cursor: RegexCursor, char: str) -> None:
    if cursor.eof() or cursor.peek() != char:
        raise ValueError(f"Se esperaba '{char}' en posición {cursor.pos}")
    cursor.pos += 1
