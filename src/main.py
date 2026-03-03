from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from yalex_parser import parse_regex, parse_yalex, regex_node_to_dict


def run() -> None:
    parser = argparse.ArgumentParser(description="Parser básico para archivos YALex")
    parser.add_argument("input", type=Path, help="Ruta al archivo .yal")
    parser.add_argument(
        "--ast",
        action="store_true",
        help="También imprime el AST de regex para lets y alternativas del rule",
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

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
