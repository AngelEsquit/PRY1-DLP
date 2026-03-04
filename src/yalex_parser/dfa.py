"""
Conversión de AFN combinado → AFD mediante el algoritmo de construcción
de subconjuntos (subset construction).

El AFD resultante preserva la metadata de aceptación (label + prioridad)
necesaria para la tokenización con maximal munch.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .thompson import AcceptMetadata, CombinedNFA, Transition


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

@dataclass
class DFAState:
    """Un estado del AFD, representado como un frozenset de estados del AFN."""
    id: int
    nfa_states: frozenset[int]
    is_accept: bool = False
    accept_label: str | None = None
    accept_priority: int | None = None


@dataclass
class DFATransition:
    from_state: int
    to_state: int
    char: str  # carácter concreto


@dataclass
class DFA:
    start_state: int
    states: list[DFAState] = field(default_factory=list)
    transitions: list[DFATransition] = field(default_factory=list)

    def get_accept_states(self) -> list[DFAState]:
        return [s for s in self.states if s.is_accept]


# ---------------------------------------------------------------------------
# Funciones auxiliares para obtener el alfabeto expandido del AFN
# ---------------------------------------------------------------------------

def _expand_charset(payload: dict) -> list[str]:
    """Devuelve la lista de caracteres concretos que un charset abarca."""
    chars: set[str] = set()
    for ch in payload.get("singles", []):
        chars.add(ch)
    for rng in payload.get("ranges", []):
        lo = ord(rng["start"])
        hi = ord(rng["end"])
        for code in range(lo, hi + 1):
            chars.add(chr(code))

    if payload.get("negated", False):
        # Complemento sobre ASCII imprimible + espacio/tab/newline
        universe = set(chr(c) for c in range(0, 128))
        chars = universe - chars

    return sorted(chars)


def _expand_wildcard() -> list[str]:
    """El wildcard '_' acepta cualquier carácter ASCII imprimible + blancos."""
    return [chr(c) for c in range(0, 128)]


def _transition_matches(t: Transition, ch: str) -> bool:
    """¿La transición *t* acepta el carácter *ch*?"""
    if t.kind == "epsilon":
        return False

    if t.kind == "char":
        return t.payload is not None and t.payload.get("value") == ch

    if t.kind == "wildcard":
        return True

    if t.kind == "charset":
        if t.payload is None:
            return False
        chars = _expand_charset(t.payload)
        return ch in chars

    if t.kind == "charset_difference":
        # left \ right – ambos deben ser charset-like
        if t.payload is None:
            return False
        left_chars = set(_expand_charset(t.payload["left"])) if "singles" in t.payload.get("left", {}) or "ranges" in t.payload.get("left", {}) else set()
        right_chars = set(_expand_charset(t.payload["right"])) if "singles" in t.payload.get("right", {}) or "ranges" in t.payload.get("right", {}) else set()
        return ch in (left_chars - right_chars)

    return False


# ---------------------------------------------------------------------------
# Algoritmo de subconjuntos
# ---------------------------------------------------------------------------

def _epsilon_closure(states: frozenset[int], transitions: list[Transition]) -> frozenset[int]:
    """Calcula la ε-clausura de un conjunto de estados."""
    stack = list(states)
    closure = set(states)

    while stack:
        s = stack.pop()
        for t in transitions:
            if t.from_state == s and t.kind == "epsilon" and t.to_state not in closure:
                closure.add(t.to_state)
                stack.append(t.to_state)

    return frozenset(closure)


def _move(states: frozenset[int], ch: str, transitions: list[Transition]) -> frozenset[int]:
    """Calcula move(states, ch): estados alcanzables consumiendo *ch*."""
    result: set[int] = set()
    for t in transitions:
        if t.from_state in states and _transition_matches(t, ch):
            result.add(t.to_state)
    return frozenset(result)


def _get_alphabet(transitions: list[Transition]) -> list[str]:
    """Extrae el alfabeto (caracteres concretos) del conjunto de transiciones."""
    chars: set[str] = set()
    for t in transitions:
        if t.kind == "char" and t.payload:
            chars.add(t.payload["value"])
        elif t.kind == "wildcard":
            chars.update(_expand_wildcard())
        elif t.kind == "charset" and t.payload:
            chars.update(_expand_charset(t.payload))
        elif t.kind == "charset_difference" and t.payload:
            left = t.payload.get("left", {})
            right = t.payload.get("right", {})
            if "singles" in left or "ranges" in left:
                left_chars = set(_expand_charset(left))
            else:
                left_chars = set()
            if "singles" in right or "ranges" in right:
                right_chars = set(_expand_charset(right))
            else:
                right_chars = set()
            chars.update(left_chars - right_chars)
    return sorted(chars)


def _resolve_accept(
    nfa_states: frozenset[int],
    accept_map: dict[int, AcceptMetadata],
) -> tuple[bool, str | None, int | None]:
    """Determina si un conjunto de estados AFN es de aceptación.

    Si hay múltiples, gana la de menor prioridad (definida primero en rule).
    """
    best: AcceptMetadata | None = None
    for s in nfa_states:
        if s in accept_map:
            meta = accept_map[s]
            if best is None or meta.priority < best.priority:
                best = meta

    if best is not None:
        return True, best.label, best.priority
    return False, None, None


def nfa_to_dfa(combined_nfa: CombinedNFA) -> DFA:
    """Convierte un CombinedNFA en un DFA mediante subset construction."""
    accept_map: dict[int, AcceptMetadata] = {
        a.state: a for a in combined_nfa.accept_states
    }
    transitions = combined_nfa.transitions
    alphabet = _get_alphabet(transitions)

    # Estado inicial del AFD
    start_closure = _epsilon_closure(frozenset({combined_nfa.start_state}), transitions)

    state_counter = 0
    nfa_to_id: dict[frozenset[int], int] = {}

    def _get_or_create(nfa_set: frozenset[int]) -> tuple[int, bool]:
        nonlocal state_counter
        if nfa_set in nfa_to_id:
            return nfa_to_id[nfa_set], False
        sid = state_counter
        state_counter += 1
        nfa_to_id[nfa_set] = sid
        return sid, True

    start_id, _ = _get_or_create(start_closure)
    is_acc, acc_label, acc_prio = _resolve_accept(start_closure, accept_map)

    dfa_states: dict[int, DFAState] = {
        start_id: DFAState(
            id=start_id,
            nfa_states=start_closure,
            is_accept=is_acc,
            accept_label=acc_label,
            accept_priority=acc_prio,
        )
    }
    dfa_transitions: list[DFATransition] = []

    worklist: list[frozenset[int]] = [start_closure]

    while worklist:
        current_nfa = worklist.pop()
        current_id = nfa_to_id[current_nfa]

        for ch in alphabet:
            moved = _move(current_nfa, ch, transitions)
            if not moved:
                continue
            target_closure = _epsilon_closure(moved, transitions)
            if not target_closure:
                continue

            target_id, is_new = _get_or_create(target_closure)
            if is_new:
                is_acc, acc_label, acc_prio = _resolve_accept(target_closure, accept_map)
                dfa_states[target_id] = DFAState(
                    id=target_id,
                    nfa_states=target_closure,
                    is_accept=is_acc,
                    accept_label=acc_label,
                    accept_priority=acc_prio,
                )
                worklist.append(target_closure)

            dfa_transitions.append(DFATransition(current_id, target_id, ch))

    return DFA(
        start_state=start_id,
        states=sorted(dfa_states.values(), key=lambda s: s.id),
        transitions=dfa_transitions,
    )


# ---------------------------------------------------------------------------
# Minimización de AFD (Hopcroft simplificado)
# ---------------------------------------------------------------------------

def minimize_dfa(dfa: DFA) -> DFA:
    """Minimiza un DFA usando el algoritmo de particiones (Hopcroft simplificado)."""
    state_ids = {s.id for s in dfa.states}
    if not state_ids:
        return dfa

    # Construir tabla de transiciones indexada
    trans_table: dict[int, dict[str, int]] = {s: {} for s in state_ids}
    alphabet: set[str] = set()
    for t in dfa.transitions:
        trans_table[t.from_state][t.char] = t.to_state
        alphabet.add(t.char)
    alphabet_list = sorted(alphabet)

    # Mapa de aceptación: state_id -> (label, priority)
    accept_info: dict[int, tuple[str | None, int | None]] = {}
    for s in dfa.states:
        if s.is_accept:
            accept_info[s.id] = (s.accept_label, s.accept_priority)

    # Partición inicial: agrupar por (is_accept, accept_label, accept_priority)
    groups: dict[tuple, set[int]] = {}
    for s in dfa.states:
        if s.is_accept:
            key = (True, s.accept_label, s.accept_priority)
        else:
            key = (False, None, None)
        groups.setdefault(key, set()).add(s.id)

    partitions: list[set[int]] = list(groups.values())

    def _find_partition(state: int) -> int:
        for idx, part in enumerate(partitions):
            if state in part:
                return idx
        return -1

    changed = True
    while changed:
        changed = False
        new_partitions: list[set[int]] = []

        for part in partitions:
            if len(part) <= 1:
                new_partitions.append(part)
                continue

            # Intentar dividir basado en las transiciones
            sub_groups: dict[tuple, set[int]] = {}
            for s in part:
                signature: list[int] = []
                for ch in alphabet_list:
                    target = trans_table[s].get(ch)
                    if target is None:
                        signature.append(-1)
                    else:
                        signature.append(_find_partition(target))
                key = tuple(signature)
                sub_groups.setdefault(key, set()).add(s)

            if len(sub_groups) > 1:
                changed = True

            new_partitions.extend(sub_groups.values())

        partitions = new_partitions

    # Construir nuevo DFA
    # Asignar IDs: el grupo que contiene el start va primero
    state_to_group: dict[int, int] = {}
    for gid, part in enumerate(partitions):
        for s in part:
            state_to_group[s] = gid

    # Re-numerar para que start sea 0
    start_group = state_to_group[dfa.start_state]
    group_remap: dict[int, int] = {}
    counter = 0
    group_remap[start_group] = counter
    counter += 1
    for gid in range(len(partitions)):
        if gid not in group_remap:
            group_remap[gid] = counter
            counter += 1

    new_states: list[DFAState] = []
    new_transitions_set: set[tuple[int, int, str]] = set()
    new_transitions: list[DFATransition] = []

    for gid, part in enumerate(partitions):
        new_id = group_remap[gid]
        representative = min(part)

        # Determinar aceptación
        is_acc = False
        acc_label = None
        acc_prio = None
        for s in part:
            if s in accept_info:
                info = accept_info[s]
                if not is_acc or (info[1] is not None and (acc_prio is None or info[1] < acc_prio)):
                    is_acc = True
                    acc_label = info[0]
                    acc_prio = info[1]

        new_states.append(DFAState(
            id=new_id,
            nfa_states=frozenset(),
            is_accept=is_acc,
            accept_label=acc_label,
            accept_priority=acc_prio,
        ))

        # Transiciones del representante
        for ch in alphabet_list:
            target = trans_table[representative].get(ch)
            if target is not None:
                new_target = group_remap[state_to_group[target]]
                key = (new_id, new_target, ch)
                if key not in new_transitions_set:
                    new_transitions_set.add(key)
                    new_transitions.append(DFATransition(new_id, new_target, ch))

    new_states.sort(key=lambda s: s.id)
    return DFA(
        start_state=0,
        states=new_states,
        transitions=new_transitions,
    )


# ---------------------------------------------------------------------------
# Serialización
# ---------------------------------------------------------------------------

def dfa_to_dict(dfa: DFA) -> dict:
    """Serializa un DFA a diccionario (JSON-friendly)."""
    return {
        "start_state": dfa.start_state,
        "states": [
            {
                "id": s.id,
                "is_accept": s.is_accept,
                "accept_label": s.accept_label,
                "accept_priority": s.accept_priority,
            }
            for s in dfa.states
        ],
        "transitions": [
            {
                "from": t.from_state,
                "to": t.to_state,
                "char": t.char,
            }
            for t in dfa.transitions
        ],
    }


def dfa_to_table(dfa: DFA) -> dict:
    """Convierte el DFA a una tabla de transiciones compacta.

    Retorna un dict con:
      - start: int
      - accept: dict[int, str]  (state_id -> label)
      - table: dict[int, dict[str, int]]  (state -> {char -> state})
    """
    accept: dict[int, str] = {}
    for s in dfa.states:
        if s.is_accept and s.accept_label is not None:
            accept[s.id] = s.accept_label

    table: dict[int, dict[str, int]] = {}
    for t in dfa.transitions:
        table.setdefault(t.from_state, {})[t.char] = t.to_state

    return {
        "start": dfa.start_state,
        "accept": accept,
        "table": table,
    }
