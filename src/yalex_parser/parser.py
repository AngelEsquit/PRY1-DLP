from __future__ import annotations

from dataclasses import dataclass

from .models import LetDefinition, RuleAlternative, RuleDefinition, YALexSpec


@dataclass
class ParseCursor:
    text: str
    pos: int = 0

    def eof(self) -> bool:
        return self.pos >= len(self.text)

    def peek(self, size: int = 1) -> str:
        return self.text[self.pos : self.pos + size]

    def skip_whitespace(self) -> None:
        while not self.eof() and self.text[self.pos].isspace():
            self.pos += 1


def parse_yalex(source: str) -> YALexSpec:
    cleaned = _remove_comments(source)
    cursor = ParseCursor(cleaned)

    spec = YALexSpec()
    cursor.skip_whitespace()

    if cursor.peek() == "{":
        spec.header = _read_braced_block(cursor)
        cursor.skip_whitespace()

    while _match_word(cursor, "let"):
        spec.lets.append(_parse_let_definition(cursor))
        cursor.skip_whitespace()

    spec.rule = _parse_rule_definition(cursor)
    cursor.skip_whitespace()

    if not cursor.eof() and cursor.peek() == "{":
        spec.trailer = _read_braced_block(cursor)
        cursor.skip_whitespace()

    return spec


def _parse_let_definition(cursor: ParseCursor) -> LetDefinition:
    _expect_word(cursor, "let")
    cursor.skip_whitespace()

    name = _read_identifier(cursor)
    cursor.skip_whitespace()
    _expect_char(cursor, "=")

    regex = _read_until_line_end(cursor).strip()
    return LetDefinition(name=name, regex=regex)


def _parse_rule_definition(cursor: ParseCursor) -> RuleDefinition:
    _expect_word(cursor, "rule")
    cursor.skip_whitespace()

    entrypoint = _read_identifier(cursor)
    cursor.skip_whitespace()

    arguments = _read_rule_arguments(cursor)
    cursor.skip_whitespace()

    _expect_char(cursor, "=")
    cursor.skip_whitespace()

    alternatives: list[RuleAlternative] = []
    while True:
        regex, action = _read_rule_alternative(cursor)
        alternatives.append(RuleAlternative(regex=regex.strip(), action=action))

        cursor.skip_whitespace()
        if cursor.eof() or cursor.peek() != "|":
            break

        cursor.pos += 1
        cursor.skip_whitespace()

    return RuleDefinition(entrypoint=entrypoint, arguments=arguments, alternatives=alternatives)


def _read_rule_arguments(cursor: ParseCursor) -> list[str]:
    arguments: list[str] = []

    if cursor.peek() != "[":
        return arguments

    cursor.pos += 1
    buffer = []
    while not cursor.eof() and cursor.peek() != "]":
        buffer.append(cursor.peek())
        cursor.pos += 1

    _expect_char(cursor, "]")
    raw_args = "".join(buffer).strip()

    if not raw_args:
        return arguments

    return [arg.strip() for arg in raw_args.split() if arg.strip()]


def _read_rule_alternative(cursor: ParseCursor) -> tuple[str, str | None]:
    regex_chars: list[str] = []
    in_single_quote = False
    in_double_quote = False
    paren_depth = 0
    bracket_depth = 0

    while not cursor.eof():
        ch = cursor.peek()

        if ch == "\\":
            regex_chars.append(ch)
            cursor.pos += 1
            if not cursor.eof():
                regex_chars.append(cursor.peek())
                cursor.pos += 1
            continue

        if ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            regex_chars.append(ch)
            cursor.pos += 1
            continue

        if ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            regex_chars.append(ch)
            cursor.pos += 1
            continue

        if not in_single_quote and not in_double_quote:
            if ch == "(":
                paren_depth += 1
                regex_chars.append(ch)
                cursor.pos += 1
                continue

            if ch == ")" and paren_depth > 0:
                paren_depth -= 1
                regex_chars.append(ch)
                cursor.pos += 1
                continue

            if ch == "[":
                bracket_depth += 1
                regex_chars.append(ch)
                cursor.pos += 1
                continue

            if ch == "]" and bracket_depth > 0:
                bracket_depth -= 1
                regex_chars.append(ch)
                cursor.pos += 1
                continue

        if (
            not in_single_quote
            and not in_double_quote
            and paren_depth == 0
            and bracket_depth == 0
            and ch in "{|\n"
        ):
            break

        regex_chars.append(ch)
        cursor.pos += 1

    regex = "".join(regex_chars).strip()

    cursor.skip_whitespace()
    action: str | None = None
    if not cursor.eof() and cursor.peek() == "{":
        action = _read_braced_block(cursor)

    return regex, action


def _remove_comments(text: str) -> str:
    result: list[str] = []
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i] == "(" and text[i + 1] == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == ")"):
                i += 1
            i += 2
            continue

        result.append(text[i])
        i += 1

    return "".join(result)


def _read_braced_block(cursor: ParseCursor) -> str:
    _expect_char(cursor, "{")
    depth = 1
    chars: list[str] = []

    while not cursor.eof() and depth > 0:
        ch = cursor.peek()
        cursor.pos += 1

        if ch == "{":
            depth += 1
            chars.append(ch)
            continue

        if ch == "}":
            depth -= 1
            if depth > 0:
                chars.append(ch)
            continue

        chars.append(ch)

    return "".join(chars).strip()


def _read_until_line_end(cursor: ParseCursor) -> str:
    chars: list[str] = []
    while not cursor.eof() and cursor.peek() != "\n":
        chars.append(cursor.peek())
        cursor.pos += 1

    if not cursor.eof() and cursor.peek() == "\n":
        cursor.pos += 1

    return "".join(chars)


def _read_identifier(cursor: ParseCursor) -> str:
    start = cursor.pos
    while not cursor.eof() and (cursor.peek().isalnum() or cursor.peek() == "_"):
        cursor.pos += 1

    return cursor.text[start:cursor.pos]


def _expect_word(cursor: ParseCursor, word: str) -> None:
    if not _match_word(cursor, word):
        raise ValueError(f"Se esperaba '{word}' en la posición {cursor.pos}")
    cursor.pos += len(word)


def _match_word(cursor: ParseCursor, word: str) -> bool:
    return cursor.text[cursor.pos : cursor.pos + len(word)] == word


def _expect_char(cursor: ParseCursor, char: str) -> None:
    if cursor.eof() or cursor.peek() != char:
        raise ValueError(f"Se esperaba '{char}' en la posición {cursor.pos}")
    cursor.pos += 1
