"""
Simulador de AFD para tokenización con estrategia *maximal munch*.

Dado un DFA (tabla de transiciones) y un texto de entrada, produce la
secuencia de tokens reconocidos o reporta errores léxicos.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    col: int


@dataclass
class LexError:
    char: str
    line: int
    col: int
    message: str


@dataclass
class TraceStep:
    stage: str
    position: int
    line: int
    col: int
    state: int
    char: str | None = None
    next_state: int | None = None
    note: str | None = None


def tokenize(
    text: str,
    start: int,
    accept: dict[int, str],
    table: dict[int, dict[str, int]],
) -> tuple[list[Token], list[LexError]]:
    """
    Ejecuta el análisis léxico sobre *text* usando el AFD descrito por
    (*start*, *accept*, *table*).

    Parámetros
    ----------
    text : str
        Texto fuente a analizar.
    start : int
        Estado inicial del AFD.
    accept : dict[int, str]
        Mapa estado_aceptación → etiqueta del token.
    table : dict[int, dict[str, int]]
        Tabla de transiciones: estado → {carácter → estado_destino}.

    Retorna
    -------
    (tokens, errors)
        Lista de tokens reconocidos y lista de errores léxicos.
    """
    tokens, errors, _ = tokenize_with_trace(text, start, accept, table, include_trace=False)
    return tokens, errors


def tokenize_with_trace(
    text: str,
    start: int,
    accept: dict[int, str],
    table: dict[int, dict[str, int]],
    *,
    include_trace: bool = True,
) -> tuple[list[Token], list[LexError], list[TraceStep]]:
    tokens: list[Token] = []
    errors: list[LexError] = []
    trace: list[TraceStep] = []

    pos = 0
    line = 1
    col = 1

    while pos < len(text):
        state = start
        last_accept_pos = -1
        last_accept_label: str | None = None
        current = pos
        token_line = line
        token_col = col

        if include_trace:
            trace.append(TraceStep(
                stage="token-start",
                position=pos,
                line=line,
                col=col,
                state=state,
                note="Inicio de intento de token",
            ))

        # Avanzar consumiendo caracteres mientras haya transiciones
        while current < len(text):
            ch = text[current]
            next_state = table.get(state, {}).get(ch)
            if include_trace:
                trace.append(TraceStep(
                    stage="transition",
                    position=current,
                    line=line,
                    col=col,
                    state=state,
                    char=ch,
                    next_state=next_state,
                    note="Transición" if next_state is not None else "Sin transición",
                ))
            if next_state is None:
                break
            state = next_state
            current += 1

            # Si estamos en un estado de aceptación, registrar
            if state in accept:
                last_accept_pos = current
                last_accept_label = accept[state]
                if include_trace:
                    trace.append(TraceStep(
                        stage="accept",
                        position=current,
                        line=line,
                        col=col,
                        state=state,
                        note=f"Estado de aceptación: {accept[state]}",
                    ))

        if last_accept_label is not None and last_accept_pos > pos:
            lexeme = text[pos:last_accept_pos]

            # Solo emitir el token si la acción no es vacía / skip
            # Acciones que contienen "skip" o están vacías se ignoran
            action = last_accept_label.strip()
            if action and not _is_skip_action(action):
                token_type = _extract_token_type(action)
                tokens.append(Token(
                    type=token_type,
                    lexeme=lexeme,
                    line=token_line,
                    col=token_col,
                ))
                if include_trace:
                    trace.append(TraceStep(
                        stage="emit-token",
                        position=last_accept_pos,
                        line=token_line,
                        col=token_col,
                        state=state,
                        note=f"Emitido token {token_type}: {lexeme!r}",
                    ))
            elif include_trace:
                trace.append(TraceStep(
                    stage="skip-token",
                    position=last_accept_pos,
                    line=token_line,
                    col=token_col,
                    state=state,
                    note=f"Lexema ignorado (skip): {lexeme!r}",
                ))

            # Actualizar posición y coordenadas
            for ch in lexeme:
                if ch == "\n":
                    line += 1
                    col = 1
                else:
                    col += 1
            pos = last_accept_pos
        else:
            # Error léxico: carácter no reconocido
            bad_char = text[pos]
            errors.append(LexError(
                char=bad_char,
                line=line,
                col=col,
                message=f"Error léxico en línea {line}, columna {col}: carácter inesperado '{_printable(bad_char)}'",
            ))
            if include_trace:
                trace.append(TraceStep(
                    stage="lex-error",
                    position=pos,
                    line=line,
                    col=col,
                    state=state,
                    char=bad_char,
                    note="Error léxico: carácter inesperado",
                ))
            if bad_char == "\n":
                line += 1
                col = 1
            else:
                col += 1
            pos += 1

    return tokens, errors, trace


def _is_skip_action(action: str) -> bool:
    """Determina si una acción de regla debe ignorar el lexema (whitespace, etc.)."""
    lower = action.lower()
    # Heurísticas comunes para acciones de skip
    if lower in ("skip", "skip()", "ignore", "whitespace"):
        return True
    if "skip" in lower and ("(" in lower or lower.endswith("skip")):
        return True
    return False


def _extract_token_type(action: str) -> str:
    """Extrae el nombre del token de una acción tipo 'return \"TOKEN\"'."""
    # Parse return statements without regex: return "TOKEN" or return 'TOKEN'
    stripped = action.strip()
    if stripped.startswith("return"):
        rest = stripped[len("return"):].strip()
        if len(rest) >= 2 and rest[0] in ('"', "'") and rest[-1] == rest[0]:
            return rest[1:-1]
    # Si no matchea el patrón, devolver la acción tal cual
    return action


def _printable(ch: str) -> str:
    """Versión imprimible de un carácter."""
    if ch == "\n":
        return "\\n"
    if ch == "\t":
        return "\\t"
    if ch == "\r":
        return "\\r"
    if ch == " ":
        return "\\s"
    return ch
