from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from yalex_parser import (
    build_combined_nfa,
    build_thompson_nfa,
    combined_nfa_to_dict,
    nfa_to_dict,
    parse_regex,
    parse_yalex,
    regex_node_to_dict,
)
from yalex_parser.dfa import nfa_to_dfa, minimize_dfa, dfa_to_dict, dfa_to_table
from yalex_parser.simulator import tokenize
from yalex_parser.codegen import generate_lexer


def run() -> None:
    parser = argparse.ArgumentParser(description="Generador de analizadores léxicos YALex")
    parser.add_argument("input", type=Path, help="Ruta al archivo .yal")
    parser.add_argument(
        "--ast",
        action="store_true",
        help="Imprime el AST de regex para lets y alternativas del rule",
    )
    parser.add_argument(
        "--nfa",
        action="store_true",
        help="Construye e imprime AFN (Thompson) para lets y alternativas del rule",
    )
    parser.add_argument(
        "--combined-nfa",
        action="store_true",
        help="Construye e imprime el AFN combinado del rule con prioridad por orden",
    )
    parser.add_argument(
        "--dfa",
        action="store_true",
        help="Construye e imprime el AFD (subset construction + minimización)",
    )
    parser.add_argument(
        "--generate",
        type=Path,
        metavar="OUTPUT",
        help="Genera un analizador léxico autónomo en la ruta indicada",
    )
    parser.add_argument(
        "--tokenize",
        type=Path,
        metavar="INPUT_FILE",
        help="Ejecuta el análisis léxico sobre el archivo de texto indicado",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abre la interfaz gráfica",
    )
    args = parser.parse_args()

    # Si se pide la GUI, lanzar y salir
    if args.gui:
        from ui.app import YALexApp

        app = YALexApp()
        app.mainloop()
        return

    source = args.input.read_text(encoding="utf-8")
    spec = parse_yalex(source)
    output: dict = {"spec": asdict(spec)}

    # Construir let ASTs (necesarios para varias opciones)
    let_asts = {definition.name: parse_regex(definition.regex) for definition in spec.lets}

    if args.ast:
        lets_ast = [
            {
                "name": definition.name,
                "ast": regex_node_to_dict(parse_regex(definition.regex)),
            }
            for definition in spec.lets
        ]

        rule_alternatives_ast = []
        if spec.rule is not None:
            for index, alternative in enumerate(spec.rule.alternatives):
                rule_alternatives_ast.append(
                    {
                        "index": index,
                        "regex": alternative.regex,
                        "ast": regex_node_to_dict(parse_regex(alternative.regex)),
                    }
                )

        output["regex_ast"] = {
            "lets": lets_ast,
            "rule_alternatives": rule_alternatives_ast,
        }

    if args.nfa:
        lets_nfa = [
            {
                "name": definition.name,
                "nfa": nfa_to_dict(build_thompson_nfa(let_asts[definition.name], let_asts)),
            }
            for definition in spec.lets
        ]

        rule_alternatives_nfa = []
        if spec.rule is not None:
            for index, alternative in enumerate(spec.rule.alternatives):
                alt_ast = parse_regex(alternative.regex)
                rule_alternatives_nfa.append(
                    {
                        "index": index,
                        "regex": alternative.regex,
                        "nfa": nfa_to_dict(build_thompson_nfa(alt_ast, let_asts)),
                    }
                )

        output["thompson_nfa"] = {
            "lets": lets_nfa,
            "rule_alternatives": rule_alternatives_nfa,
        }

    if args.combined_nfa:
        combined_entries: list[tuple[str, object]] = []

        if spec.rule is not None:
            for index, alternative in enumerate(spec.rule.alternatives):
                label = alternative.action.strip() if alternative.action else f"ALT_{index}"
                combined_entries.append((label, parse_regex(alternative.regex)))

        output["combined_nfa"] = combined_nfa_to_dict(
            build_combined_nfa(combined_entries, let_asts)
        )

    # Construir AFD si se necesita (para --dfa, --generate o --tokenize)
    need_dfa = args.dfa or args.generate or args.tokenize
    dfa = None
    if need_dfa:
        combined_entries = []
        if spec.rule is not None:
            for index, alternative in enumerate(spec.rule.alternatives):
                label = alternative.action.strip() if alternative.action else f"ALT_{index}"
                combined_entries.append((label, parse_regex(alternative.regex)))

        combined = build_combined_nfa(combined_entries, let_asts)
        raw_dfa = nfa_to_dfa(combined)
        dfa = minimize_dfa(raw_dfa)

    if args.dfa and dfa is not None:
        output["dfa"] = dfa_to_dict(dfa)
        output["dfa_stats"] = {
            "states": len(dfa.states),
            "transitions": len(dfa.transitions),
        }

    if args.generate and dfa is not None:
        code = generate_lexer(dfa, spec.header, spec.trailer, output_path=args.generate)
        output["generated"] = {
            "path": str(args.generate),
            "size_bytes": len(code.encode("utf-8")),
        }
        print(f"Analizador léxico generado en: {args.generate}")

    if args.tokenize and dfa is not None:
        input_text = args.tokenize.read_text(encoding="utf-8")
        tbl = dfa_to_table(dfa)
        tokens, errors = tokenize(input_text, tbl["start"], tbl["accept"], tbl["table"])

        # Imprimir de forma legible
        print(f"\n{'=' * 60}")
        print(f"  Análisis léxico de: {args.tokenize}")
        print(f"{'=' * 60}\n")

        if tokens:
            print(f"  {'TOKEN':<23s} {'LEXEMA':<23s} POSICIÓN")
            print("  " + "-" * 56)
            for t in tokens:
                print(f"  {t.type:<23s} {t.lexeme!r:<23s} L{t.line}:C{t.col}")

        if errors:
            print(f"\n  ERRORES LÉXICOS ({len(errors)}):")
            for e in errors:
                print(f"    {e.message}")

        print(f"\n  Total: {len(tokens)} tokens, {len(errors)} errores\n")
        return  # No imprimir JSON cuando se tokeniza

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
