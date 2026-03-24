from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

import sys

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from yalex_parser import parse_yalex, parse_regex
from yalex_parser.codegen import generate_lexer
from yalex_parser.dfa import dfa_to_table, minimize_dfa
from yalex_parser.direct import build_direct_dfa
from yalex_parser.simulator import tokenize


class TestYALexPipeline(unittest.TestCase):
    def _build_dfa_from_spec(self, source: str):
        spec = parse_yalex(source)
        let_asts = {definition.name: parse_regex(definition.regex) for definition in spec.lets}
        entries: list[tuple[str, object]] = []
        if spec.rule is not None:
            for index, alternative in enumerate(spec.rule.alternatives):
                label = alternative.action.strip() if alternative.action else f"ALT_{index}"
                entries.append((label, parse_regex(alternative.regex)))

        return minimize_dfa(build_direct_dfa(entries, let_asts))

    def test_low_medium_high_inputs_tokenize_without_errors(self):
        cases = [
            (ROOT / "tests/yal/low.yal", ROOT / "tests/input/low.txt"),
            (ROOT / "tests/yal/medium.yal", ROOT / "tests/input/medium.txt"),
            (ROOT / "tests/yal/high.yal", ROOT / "tests/input/high.txt"),
        ]

        for yal_path, input_path in cases:
            with self.subTest(yal=yal_path.name):
                spec_source = yal_path.read_text(encoding="utf-8")
                text = input_path.read_text(encoding="utf-8")
                dfa = self._build_dfa_from_spec(spec_source)
                tbl = dfa_to_table(dfa)
                tokens, errors = tokenize(text, tbl["start"], tbl["accept"], tbl["table"])
                self.assertGreater(len(tokens), 0)
                self.assertEqual(errors, [])

    def test_maximal_munch_and_priority(self):
        source = """
let letter = ['a'-'z''A'-'Z']
let ws = [' ''\\t''\\n']+

rule tokens =
  ws                           { skip() }
| \"if\"                       { return \"IF\" }
| letter (letter | '_')*       { return \"ID\" }
| \"==\"                       { return \"EQ\" }
| '='                          { return \"ASSIGN\" }
"""
        dfa = self._build_dfa_from_spec(source)
        tbl = dfa_to_table(dfa)
        tokens, errors = tokenize("if ifx == =", tbl["start"], tbl["accept"], tbl["table"])

        self.assertEqual(errors, [])
        self.assertEqual([t.type for t in tokens], ["IF", "ID", "EQ", "ASSIGN"])
        self.assertEqual([t.lexeme for t in tokens], ["if", "ifx", "==", "="])

    def test_lexical_error_reports_position(self):
        source = (ROOT / "tests/yal/low.yal").read_text(encoding="utf-8")
        dfa = self._build_dfa_from_spec(source)
        tbl = dfa_to_table(dfa)

        tokens, errors = tokenize("12 @ 3", tbl["start"], tbl["accept"], tbl["table"])

        self.assertEqual([t.type for t in tokens], ["NUMBER", "NUMBER"])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].char, "@")
        self.assertEqual((errors[0].line, errors[0].col), (1, 4))

    def test_generated_lexer_matches_runtime_tokenization(self):
        spec_source = (ROOT / "tests/yal/medium.yal").read_text(encoding="utf-8")
        input_text = (ROOT / "tests/input/medium.txt").read_text(encoding="utf-8")

        spec = parse_yalex(spec_source)
        dfa = self._build_dfa_from_spec(spec_source)
        tbl = dfa_to_table(dfa)

        tokens_runtime, errors_runtime = tokenize(
            input_text, tbl["start"], tbl["accept"], tbl["table"]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "lexer_generated.py"
            generate_lexer(dfa, spec.header, spec.trailer, output_path=out_path)

            spec_mod = importlib.util.spec_from_file_location("lexer_generated", out_path)
            assert spec_mod is not None and spec_mod.loader is not None
            module = importlib.util.module_from_spec(spec_mod)
            sys.modules["lexer_generated"] = module
            spec_mod.loader.exec_module(module)

            tokens_generated, errors_generated = module.tokenize(input_text)

        self.assertEqual(errors_runtime, [])
        self.assertEqual(errors_generated, [])
        self.assertEqual(
            [(t.type, t.lexeme, t.line, t.col) for t in tokens_runtime],
            [(t.type, t.lexeme, t.line, t.col) for t in tokens_generated],
        )

    def test_deep_nested_parentheses_regex(self):
        for depth in (1, 5, 20, 60, 120, 220):
            with self.subTest(depth=depth):
                regex = "(" * depth + "'a'" + ")" * depth
                ast = parse_regex(regex)

                dfa = minimize_dfa(build_direct_dfa([('return "A"', ast)], definitions={}))
                tbl = dfa_to_table(dfa)
                tokens, errors = tokenize("a", tbl["start"], tbl["accept"], tbl["table"])

                self.assertEqual(errors, [])
                self.assertEqual(len(tokens), 1)
                self.assertEqual(tokens[0].type, "A")

    def test_generated_lexer_cli_is_independent(self):
        spec_source = (ROOT / "tests/yal/low.yal").read_text(encoding="utf-8")
        input_text = "12+7"
        spec = parse_yalex(spec_source)
        dfa = self._build_dfa_from_spec(spec_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            lexer_path = tmp / "lexer_standalone.py"
            input_path = tmp / "input.txt"
            input_path.write_text(input_text, encoding="utf-8")
            generate_lexer(dfa, spec.header, spec.trailer, output_path=lexer_path)

            result = subprocess.run(
                [sys.executable, str(lexer_path), str(input_path)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Token('NUMBER', '12'", result.stdout)
        self.assertIn("Token('PLUS', '+'", result.stdout)
        self.assertIn("Token('NUMBER', '7'", result.stdout)

    def test_recursive_let_definition_fails(self):
        source = """
let a = b
let b = a
rule tokens =
  a { return \"A\" }
"""
        spec = parse_yalex(source)
        let_asts = {definition.name: parse_regex(definition.regex) for definition in spec.lets}

        with self.assertRaises(ValueError):
            build_direct_dfa([('return "A"', parse_regex("a"))], let_asts)


if __name__ == "__main__":
    unittest.main()
