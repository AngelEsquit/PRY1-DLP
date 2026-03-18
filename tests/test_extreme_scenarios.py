from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from yalex_parser import parse_yalex, parse_regex
from yalex_parser.codegen import generate_lexer
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
    return minimize_dfa(nfa_to_dfa(combined)), spec


class TestExtremeScenarios(unittest.TestCase):
    def test_extreme_nested_parentheses_depths(self):
        for depth in (150, 300, 500):
            with self.subTest(depth=depth):
                regex = "(" * depth + "'x'" + ")" * depth
                ast = parse_regex(regex)
                combined = build_combined_nfa([('return "X"', ast)], definitions={})
                dfa = minimize_dfa(nfa_to_dfa(combined))
                tbl = dfa_to_table(dfa)
                tokens, errors = tokenize("x", tbl["start"], tbl["accept"], tbl["table"])
                self.assertEqual(errors, [])
                self.assertEqual(len(tokens), 1)
                self.assertEqual(tokens[0].type, "X")

    def test_extreme_many_keyword_rules_and_priority(self):
        keywords = [f"kw{i}" for i in range(120)]
        source_lines = [
            "let letter = ['a'-'z''A'-'Z']",
            "let digit = ['0'-'9']",
            "let ws = [' ''\\t''\\n']+",
            "",
            "rule tokens =",
            "  ws { skip() }",
        ]
        for kw in keywords:
            source_lines.append(f'| "{kw}" {{ return "{kw.upper()}" }}')
        source_lines.append('| letter (letter | digit | "_")* { return "ID" }')

        source = "\n".join(source_lines)
        dfa, _ = _build_dfa_from_spec(source)
        tbl = dfa_to_table(dfa)

        text = " ".join(keywords[:10] + ["kw0x", "kw10", "kw119", "random_id"])
        tokens, errors = tokenize(text, tbl["start"], tbl["accept"], tbl["table"])

        self.assertEqual(errors, [])
        expected_types = [kw.upper() for kw in keywords[:10]] + ["ID", "KW10", "KW119", "ID"]
        self.assertEqual([t.type for t in tokens], expected_types)

    def test_extreme_long_input_stream(self):
        source = (ROOT / "tests/yal/low.yal").read_text(encoding="utf-8")
        dfa, _ = _build_dfa_from_spec(source)
        tbl = dfa_to_table(dfa)

        chunk = "123+456-789*0/1 "
        repeats = 4000
        text = chunk * repeats

        tokens, errors = tokenize(text, tbl["start"], tbl["accept"], tbl["table"])

        self.assertEqual(errors, [])
        self.assertEqual(len(tokens), 9 * repeats)
        self.assertEqual(tokens[0].type, "NUMBER")
        self.assertEqual(tokens[-1].type, "NUMBER")

    def test_extreme_charset_difference(self):
        source = """
let vowels = ['a''e''i''o''u']
let ws = [' ''\\t''\\n']+

rule tokens =
  ws { skip() }
| (['a'-'z'] # ['a''e''i''o''u'])+ { return "CONS" }
| vowels+ { return "VOW" }
"""
        dfa, _ = _build_dfa_from_spec(source)
        tbl = dfa_to_table(dfa)
        tokens, errors = tokenize("bcdf aeiou zz", tbl["start"], tbl["accept"], tbl["table"])

        self.assertEqual(errors, [])
        self.assertEqual([t.type for t in tokens], ["CONS", "VOW", "CONS"])
        self.assertEqual([t.lexeme for t in tokens], ["bcdf", "aeiou", "zz"])

    def test_extreme_generated_lexer_large_input_equivalence(self):
        source = (ROOT / "tests/yal/medium.yal").read_text(encoding="utf-8")
        dfa, spec = _build_dfa_from_spec(source)
        tbl = dfa_to_table(dfa)

        line = "int var1 = 10; if (var1 >= 5) { var1 = var1 + 1; } else { var1 = var1 - 1; }\n"
        text = line * 600

        runtime_tokens, runtime_errors = tokenize(text, tbl["start"], tbl["accept"], tbl["table"])
        self.assertEqual(runtime_errors, [])

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "lexer_generated_extreme.py"
            generate_lexer(dfa, spec.header, spec.trailer, output_path=out_path)

            spec_mod = importlib.util.spec_from_file_location("lexer_generated_extreme", out_path)
            assert spec_mod is not None and spec_mod.loader is not None
            module = importlib.util.module_from_spec(spec_mod)
            sys.modules["lexer_generated_extreme"] = module
            spec_mod.loader.exec_module(module)

            generated_tokens, generated_errors = module.tokenize(text)

        self.assertEqual(generated_errors, [])
        self.assertEqual(len(generated_tokens), len(runtime_tokens))
        self.assertEqual(
            [(t.type, t.lexeme, t.line, t.col) for t in generated_tokens[:100]],
            [(t.type, t.lexeme, t.line, t.col) for t in runtime_tokens[:100]],
        )
        self.assertEqual(
            [(t.type, t.lexeme, t.line, t.col) for t in generated_tokens[-100:]],
            [(t.type, t.lexeme, t.line, t.col) for t in runtime_tokens[-100:]],
        )


if __name__ == "__main__":
    unittest.main()
