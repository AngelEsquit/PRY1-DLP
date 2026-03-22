from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from yalex_parser import parse_regex, parse_yalex
from yalex_parser.dfa import dfa_to_table, minimize_dfa, nfa_to_dfa
from yalex_parser.simulator import tokenize
from yalex_parser.thompson import build_combined_nfa


def _build_dfa_from_spec(source: str):
    spec = parse_yalex(source)
    let_asts = {definition.name: parse_regex(definition.regex) for definition in spec.lets}
    entries: list[tuple[str, object]] = []
    if spec.rule is not None:
        for index, alternative in enumerate(spec.rule.alternatives):
            label = alternative.action.strip() if alternative.action else f"ALT_{index}"
            entries.append((label, parse_regex(alternative.regex)))

    combined = build_combined_nfa(entries, let_asts)
    return minimize_dfa(nfa_to_dfa(combined))


class TestASCIIConstraints(unittest.TestCase):
    def test_wildcard_accepts_full_ascii_range(self):
        source = """
rule tokens =
  _ { return "ANY" }
"""
        dfa = _build_dfa_from_spec(source)
        table = dfa_to_table(dfa)

        ascii_text = "".join(chr(i) for i in range(128))
        tokens, errors = tokenize(ascii_text, table["start"], table["accept"], table["table"])

        self.assertEqual(errors, [])
        self.assertEqual(len(tokens), 128)
        self.assertTrue(all(token.type == "ANY" for token in tokens))

    def test_non_ascii_characters_raise_lexical_errors(self):
        source = """
rule tokens =
  _ { return "ANY" }
"""
        dfa = _build_dfa_from_spec(source)
        table = dfa_to_table(dfa)

        text = "Añ🙂B"
        tokens, errors = tokenize(text, table["start"], table["accept"], table["table"])

        self.assertEqual([token.lexeme for token in tokens], ["A", "B"])
        self.assertEqual([error.char for error in errors], ["ñ", "🙂"])

    def test_negated_charset_is_ascii_bounded(self):
        source = """
rule tokens =
  [^'a'] { return "NOT_A" }
| 'a'    { return "A" }
"""
        dfa = _build_dfa_from_spec(source)
        table = dfa_to_table(dfa)

        tokens, errors = tokenize("ab🙂", table["start"], table["accept"], table["table"])

        self.assertEqual([token.type for token in tokens], ["A", "NOT_A"])
        self.assertEqual([error.char for error in errors], ["🙂"])


if __name__ == "__main__":
    unittest.main()
