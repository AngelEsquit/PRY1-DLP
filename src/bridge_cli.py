from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from yalex_parser import (
    build_combined_nfa,
    build_thompson_nfa,
    combined_nfa_to_dict,
    dfa_to_dict,
    dfa_to_table,
    minimize_dfa,
    nfa_to_dfa,
    nfa_to_dict,
    parse_regex,
    parse_yalex,
    regex_node_to_dict,
)
from yalex_parser.codegen import generate_lexer
from yalex_parser.simulator import tokenize_with_trace


def _build_pipeline_from_source(source: str):
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


def _to_json_ready_token(token):
    return {
        "type": token.type,
        "lexeme": token.lexeme,
        "line": token.line,
        "col": token.col,
    }


def _to_json_ready_error(error):
    return {
        "char": error.char,
        "line": error.line,
        "col": error.col,
        "message": error.message,
    }


def _to_json_ready_trace(step):
    return {
        "stage": step.stage,
        "position": step.position,
        "line": step.line,
        "col": step.col,
        "state": step.state,
        "char": step.char,
        "next_state": step.next_state,
        "note": step.note,
    }


def _run_action(payload: dict) -> dict:
    action = payload.get("action")
    yal_path_raw = payload.get("yalPath")
    yal_source_raw = payload.get("yalSource")

    if action is None:
        raise ValueError("Falta campo 'action' en request")

    if yal_source_raw is not None:
        source = str(yal_source_raw)
    elif yal_path_raw:
        source = Path(yal_path_raw).read_text(encoding="utf-8")
    else:
        raise ValueError("Debe enviar 'yalPath' o 'yalSource'")

    spec, let_asts, _combined_entries, combined, dfa = _build_pipeline_from_source(source)

    if action == "spec":
        return {"spec": asdict(spec)}

    if action == "ast":
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
        return {"regex_ast": {"lets": lets_ast, "rule_alternatives": rule_alternatives_ast}}

    if action == "nfa":
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
        return {"thompson_nfa": {"lets": lets_nfa, "rule_alternatives": rule_alternatives_nfa}}

    if action == "combinedNfa":
        return {"combined_nfa": combined_nfa_to_dict(combined)}

    if action == "dfa":
        return {
            "dfa": dfa_to_dict(dfa),
            "dfa_stats": {"states": len(dfa.states), "transitions": len(dfa.transitions)},
        }

    if action == "tokenize":
        input_path_raw = payload.get("inputPath")
        input_text_raw = payload.get("inputText")
        include_trace = bool(payload.get("includeTrace", False))
        trace_limit = int(payload.get("traceLimit", 500))

        if input_text_raw is not None:
            text = str(input_text_raw)
        elif input_path_raw:
            text = Path(input_path_raw).read_text(encoding="utf-8")
        else:
            raise ValueError("Para tokenizar debe enviar 'inputPath' o 'inputText'")

        table = dfa_to_table(dfa)
        tokens, errors, trace = tokenize_with_trace(
            text,
            table["start"],
            table["accept"],
            table["table"],
            include_trace=include_trace,
        )

        trace_payload = []
        if include_trace:
            trace_payload = [_to_json_ready_trace(step) for step in trace[:trace_limit]]

        return {
            "tokens": [_to_json_ready_token(token) for token in tokens],
            "errors": [_to_json_ready_error(error) for error in errors],
            "trace": trace_payload,
        }

    if action == "generate":
        output_path_raw = payload.get("outputPath")
        if not output_path_raw:
            raise ValueError("Para generar lexer debe enviar 'outputPath'")
        output_path = Path(output_path_raw)
        code = generate_lexer(dfa, spec.header, spec.trailer, output_path=output_path)
        return {
            "outputPath": str(output_path),
            "bytes": len(code.encode("utf-8")),
        }

    raise ValueError(f"Acción no soportada: {action}")


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError("Request vacío en stdin")
        payload = json.loads(raw)
        result = _run_action(payload)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
