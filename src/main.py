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


def run() -> None:
    parser = argparse.ArgumentParser(description="Parser básico para archivos YALex")
    parser.add_argument("input", type=Path, help="Ruta al archivo .yal")
    parser.add_argument(
        "--ast",
        action="store_true",
        help="También imprime el AST de regex para lets y alternativas del rule",
    )
    parser.add_argument(
        "--nfa",
        action="store_true",
        help="También construye e imprime AFN (Thompson) para lets y alternativas del rule",
    )
    parser.add_argument(
        "--combined-nfa",
        action="store_true",
        help="Construye e imprime el AFN combinado del rule con prioridad por orden",
    )
    args = parser.parse_args()

    source = args.input.read_text(encoding="utf-8")
    spec = parse_yalex(source)
    output: dict = {"spec": asdict(spec)}

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
        let_asts = {definition.name: parse_regex(definition.regex) for definition in spec.lets}

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
        let_asts = {definition.name: parse_regex(definition.regex) for definition in spec.lets}
        combined_entries: list[tuple[str, object]] = []

        if spec.rule is not None:
            for index, alternative in enumerate(spec.rule.alternatives):
                label = alternative.action.strip() if alternative.action else f"ALT_{index}"
                combined_entries.append((label, parse_regex(alternative.regex)))

        output["combined_nfa"] = combined_nfa_to_dict(
            build_combined_nfa(combined_entries, let_asts)
        )

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
