from __future__ import annotations

import argparse
import json
import sys
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
from yalex_parser.codegen import generate_lexer
from yalex_parser.dfa import dfa_to_dict, dfa_to_table, minimize_dfa, nfa_to_dfa
from yalex_parser.error_format import render_user_error
from yalex_parser.simulator import tokenize_with_trace


def _build_pipeline(yal_path: Path):
    source = yal_path.read_text(encoding="utf-8")
    spec = parse_yalex(source)
    let_asts = {definition.name: parse_regex(definition.regex) for definition in spec.lets}

    combined_entries: list[tuple[str, object]] = []
    if spec.rule is not None:
        for index, alternative in enumerate(spec.rule.alternatives):
            label = alternative.action.strip() if alternative.action else f"ALT_{index}"
            combined_entries.append((label, parse_regex(alternative.regex)))

    combined = build_combined_nfa(combined_entries, let_asts)
    raw_dfa = nfa_to_dfa(combined)
    dfa = minimize_dfa(raw_dfa)
    return spec, let_asts, combined_entries, combined, dfa


def _print_tokenization(tokens, errors, input_path: Path) -> None:
    print(f"\n{'=' * 60}")
    print(f"  Análisis léxico de: {input_path}")
    print(f"{'=' * 60}\n")

    if tokens:
        print(f"  {'TOKEN':<23s} {'LEXEMA':<23s} POSICIÓN")
        print("  " + "-" * 56)
        for token in tokens:
            print(f"  {token.type:<23s} {token.lexeme!r:<23s} L{token.line}:C{token.col}")

    if errors:
        print(f"\n  ERRORES LÉXICOS ({len(errors)}):")
        for error in errors:
            print(f"    {error.message}")

    print(f"\n  Total: {len(tokens)} tokens, {len(errors)} errores\n")


def _print_trace(trace, limit: int = 300) -> None:
    print("\n=== TRAZA DE TRANSICIONES / PASOS ===")
    if not trace:
        print("(sin pasos)")
        return

    shown = trace[:limit]
    for i, step in enumerate(shown, start=1):
        ch = "-"
        if step.char is not None:
            if step.char == "\n":
                ch = "'\\n'"
            elif step.char == "\t":
                ch = "'\\t'"
            elif step.char == "\r":
                ch = "'\\r'"
            else:
                ch = repr(step.char)

        next_state = "-" if step.next_state is None else str(step.next_state)
        note = step.note or ""
        print(
            f"{i:04d} | {step.stage:<11s} | pos={step.position:<5d} | L{step.line}:C{step.col:<4d} "
            f"| q={step.state:<4d} | ch={ch:<8s} | q'={next_state:<4s} | {note}"
        )

    if len(trace) > len(shown):
        print(f"... trazas truncadas: mostrando {len(shown)} de {len(trace)} pasos")


def _cli_menu() -> None:
    yal_path: Path | None = None

    while True:
        print("\n" + "=" * 70)
        print(" YALex CLI (modo menú)")
        print("=" * 70)
        print(f"Archivo .yal actual: {yal_path if yal_path else '(no seleccionado)'}")
        print("1) Seleccionar archivo .yal")
        print("2) Ver JSON de especificación")
        print("3) Ver AST de regex")
        print("4) Ver AFN (Thompson)")
        print("5) Ver AFN combinado")
        print("6) Ver AFD minimizado")
        print("7) Tokenizar archivo de texto")
        print("8) Generar lexer autónomo")
        print("0) Salir")

        op = input("Seleccione opción: ").strip()
        if op == "0":
            print("Saliendo...")
            return

        try:
            if op == "1":
                raw = input("Ruta archivo .yal: ").strip()
                if not raw:
                    print("Ruta vacía.")
                    continue
                candidate = Path(raw)
                if not candidate.exists():
                    print(f"No existe: {candidate}")
                    continue
                yal_path = candidate
                print(f"Seleccionado: {yal_path}")
                continue

            if yal_path is None:
                print("Primero seleccione un archivo .yal (opción 1).")
                continue

            spec, let_asts, combined_entries, combined, dfa = _build_pipeline(yal_path)

            if op == "2":
                print(json.dumps({"spec": asdict(spec)}, indent=2, ensure_ascii=False))

            elif op == "3":
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
                print(json.dumps({"regex_ast": {"lets": lets_ast, "rule_alternatives": rule_alternatives_ast}}, indent=2, ensure_ascii=False))

            elif op == "4":
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
                print(json.dumps({"thompson_nfa": {"lets": lets_nfa, "rule_alternatives": rule_alternatives_nfa}}, indent=2, ensure_ascii=False))

            elif op == "5":
                print(json.dumps({"combined_nfa": combined_nfa_to_dict(combined)}, indent=2, ensure_ascii=False))

            elif op == "6":
                payload = {
                    "dfa": dfa_to_dict(dfa),
                    "dfa_stats": {"states": len(dfa.states), "transitions": len(dfa.transitions)},
                }
                print(json.dumps(payload, indent=2, ensure_ascii=False))

            elif op == "7":
                raw_input = input("Ruta del archivo de texto a tokenizar: ").strip()
                if not raw_input:
                    print("Ruta vacía.")
                    continue
                input_path = Path(raw_input)
                text = input_path.read_text(encoding="utf-8")
                table = dfa_to_table(dfa)
                tokens, errors, trace = tokenize_with_trace(
                    text,
                    table["start"],
                    table["accept"],
                    table["table"],
                    include_trace=True,
                )
                _print_tokenization(tokens, errors, input_path)

                show_trace = input("¿Mostrar traza de pasos/transiciones? [s/N]: ").strip().lower()
                if show_trace in {"s", "si", "sí", "y", "yes"}:
                    _print_trace(trace)

            elif op == "8":
                raw_out = input("Ruta salida del lexer generado (.py): ").strip()
                if not raw_out:
                    print("Ruta vacía.")
                    continue
                output_path = Path(raw_out)
                code = generate_lexer(dfa, spec.header, spec.trailer, output_path=output_path)
                print(f"Analizador léxico generado en: {output_path}")
                print(f"Tamaño: {len(code.encode('utf-8'))} bytes")

            else:
                print("Opción inválida.")

        except Exception as exc:
            print(render_user_error(exc), file=sys.stderr)


def run() -> None:
    parser = argparse.ArgumentParser(description="Generador de analizadores léxicos YALex")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Ejecuta modo terminal con menú interactivo (ahora es el modo por defecto).",
    )
    args = parser.parse_args()

    if args.cli:
        _cli_menu()
        return

    # Modo por defecto: CLI interactivo.
    _cli_menu()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(render_user_error(exc), file=sys.stderr)
        sys.exit(1)
