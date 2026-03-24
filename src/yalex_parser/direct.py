from __future__ import annotations

from dataclasses import dataclass, field

from .dfa import DFA, DFAState, DFATransition
from .regex_ast import (
    BinaryNode,
    CharSetNode,
    ConcatNode,
    IdentifierNode,
    LiteralNode,
    RegexNode,
    StringNode,
    UnaryNode,
    WildcardNode,
)


@dataclass
class DirectAcceptPosition:
    position: int
    label: str
    priority: int


@dataclass
class DirectNodeMetric:
    node_id: int
    label: str
    nullable: bool
    firstpos: set[int]
    lastpos: set[int]
    children: list[int] = field(default_factory=list)


@dataclass
class DirectArtifacts:
    dfa: DFA
    start_positions: frozenset[int]
    alphabet: list[str]
    root_nullable: bool = False
    root_firstpos: frozenset[int] = field(default_factory=frozenset)
    root_lastpos: frozenset[int] = field(default_factory=frozenset)
    followpos: dict[int, set[int]] = field(default_factory=dict)
    position_chars: dict[int, frozenset[str]] = field(default_factory=dict)
    accept_positions: list[DirectAcceptPosition] = field(default_factory=list)
    node_metrics: list[DirectNodeMetric] = field(default_factory=list)


@dataclass
class _Analysis:
    node_id: int
    nullable: bool
    firstpos: set[int]
    lastpos: set[int]


@dataclass
class _SymbolLeaf:
    chars: frozenset[str]


@dataclass
class _EndLeaf:
    label: str
    priority: int


@dataclass
class _Epsilon:
    pass


_ASCII_UNIVERSE: frozenset[str] = frozenset(chr(i) for i in range(128))


def _node_label(node) -> str:
    if isinstance(node, _Epsilon):
        return "ε"
    if isinstance(node, _SymbolLeaf):
        if len(node.chars) == 1:
            return repr(next(iter(node.chars)))
        return "SYMBOL_SET"
    if isinstance(node, _EndLeaf):
        return "$END$"
    if isinstance(node, BinaryNode):
        if node.operator in ("|", "/"):
            return "|"
        return node.operator
    if isinstance(node, UnaryNode):
        return node.operator
    if isinstance(node, ConcatNode):
        return "•"
    return type(node).__name__


def _charset_to_chars(node: CharSetNode) -> frozenset[str]:
    chars: set[str] = set(node.singles)
    for rng in node.ranges:
        lo = ord(rng.start)
        hi = ord(rng.end)
        for code in range(lo, hi + 1):
            ch = chr(code)
            if ch in _ASCII_UNIVERSE:
                chars.add(ch)

    if node.negated:
        chars = set(_ASCII_UNIVERSE) - chars

    return frozenset(chars)


def _expand_set_like(
    node: RegexNode,
    definitions: dict[str, RegexNode],
    resolution_stack: list[str],
) -> frozenset[str]:
    if isinstance(node, LiteralNode):
        return frozenset({node.value})

    if isinstance(node, StringNode):
        return frozenset(node.value)

    if isinstance(node, WildcardNode):
        return _ASCII_UNIVERSE

    if isinstance(node, CharSetNode):
        return _charset_to_chars(node)

    if isinstance(node, IdentifierNode):
        if node.name not in definitions:
            raise ValueError(f"Identificador no definido: {node.name}")
        if node.name in resolution_stack:
            cycle = " -> ".join(resolution_stack + [node.name])
            raise ValueError(f"Referencia recursiva detectada en let: {cycle}")

        resolution_stack.append(node.name)
        chars = _expand_set_like(definitions[node.name], definitions, resolution_stack)
        resolution_stack.pop()
        return chars

    if isinstance(node, BinaryNode) and node.operator in ("|", "/"):
        return _expand_set_like(node.left, definitions, resolution_stack) | _expand_set_like(
            node.right, definitions, resolution_stack
        )

    if isinstance(node, BinaryNode) and node.operator == "#":
        left = _expand_set_like(node.left, definitions, resolution_stack)
        right = _expand_set_like(node.right, definitions, resolution_stack)
        return left - right

    return frozenset()


def _normalize_node(
    node: RegexNode,
    definitions: dict[str, RegexNode],
    resolution_stack: list[str],
):
    if isinstance(node, IdentifierNode):
        if node.name not in definitions:
            raise ValueError(f"Identificador no definido: {node.name}")
        if node.name in resolution_stack:
            cycle = " -> ".join(resolution_stack + [node.name])
            raise ValueError(f"Referencia recursiva detectada en let: {cycle}")

        resolution_stack.append(node.name)
        resolved = _normalize_node(definitions[node.name], definitions, resolution_stack)
        resolution_stack.pop()
        return resolved

    if isinstance(node, LiteralNode):
        return _SymbolLeaf(chars=frozenset({node.value}))

    if isinstance(node, StringNode):
        if node.value == "":
            return _Epsilon()
        parts = [_SymbolLeaf(chars=frozenset({ch})) for ch in node.value]
        if len(parts) == 1:
            return parts[0]
        return ConcatNode(parts=parts)

    if isinstance(node, WildcardNode):
        return _SymbolLeaf(chars=_ASCII_UNIVERSE)

    if isinstance(node, CharSetNode):
        return _SymbolLeaf(chars=_charset_to_chars(node))

    if isinstance(node, BinaryNode):
        if node.operator == "#":
            return _SymbolLeaf(chars=_expand_set_like(node, definitions, resolution_stack))

        if node.operator in ("|", "/"):
            return BinaryNode(
                operator=node.operator,
                left=_normalize_node(node.left, definitions, resolution_stack),
                right=_normalize_node(node.right, definitions, resolution_stack),
            )

        raise ValueError(f"Operador binario no soportado: {node.operator}")

    if isinstance(node, UnaryNode):
        if node.operator not in ("*", "+", "?"):
            raise ValueError(f"Operador unario no soportado: {node.operator}")
        return UnaryNode(
            operator=node.operator,
            operand=_normalize_node(node.operand, definitions, resolution_stack),
        )

    if isinstance(node, ConcatNode):
        if not node.parts:
            return _Epsilon()
        normalized_parts = [_normalize_node(part, definitions, resolution_stack) for part in node.parts]
        if len(normalized_parts) == 1:
            return normalized_parts[0]
        return ConcatNode(parts=normalized_parts)

    raise ValueError(f"Nodo no soportado en método directo: {type(node).__name__}")


def _analyze(
    node,
    followpos: dict[int, set[int]],
    position_chars: dict[int, frozenset[str]],
    position_accept: dict[int, DirectAcceptPosition],
    next_position: list[int],
    node_metrics: list[DirectNodeMetric],
    next_node_id: list[int],
) -> _Analysis:
    node_id = next_node_id[0]
    next_node_id[0] += 1

    if isinstance(node, _Epsilon):
        result = _Analysis(node_id=node_id, nullable=True, firstpos=set(), lastpos=set())
        node_metrics.append(
            DirectNodeMetric(
                node_id=node_id,
                label=_node_label(node),
                nullable=result.nullable,
                firstpos=set(result.firstpos),
                lastpos=set(result.lastpos),
                children=[],
            )
        )
        return result

    if isinstance(node, _SymbolLeaf):
        pos = next_position[0]
        next_position[0] += 1
        followpos.setdefault(pos, set())
        position_chars[pos] = node.chars
        result = _Analysis(node_id=node_id, nullable=False, firstpos={pos}, lastpos={pos})
        node_metrics.append(
            DirectNodeMetric(
                node_id=node_id,
                label=_node_label(node),
                nullable=result.nullable,
                firstpos=set(result.firstpos),
                lastpos=set(result.lastpos),
                children=[],
            )
        )
        return result

    if isinstance(node, _EndLeaf):
        pos = next_position[0]
        next_position[0] += 1
        followpos.setdefault(pos, set())
        position_chars[pos] = frozenset()
        position_accept[pos] = DirectAcceptPosition(position=pos, label=node.label, priority=node.priority)
        result = _Analysis(node_id=node_id, nullable=False, firstpos={pos}, lastpos={pos})
        node_metrics.append(
            DirectNodeMetric(
                node_id=node_id,
                label=_node_label(node),
                nullable=result.nullable,
                firstpos=set(result.firstpos),
                lastpos=set(result.lastpos),
                children=[],
            )
        )
        return result

    if isinstance(node, BinaryNode) and node.operator in ("|", "/"):
        left = _analyze(
            node.left,
            followpos,
            position_chars,
            position_accept,
            next_position,
            node_metrics,
            next_node_id,
        )
        right = _analyze(
            node.right,
            followpos,
            position_chars,
            position_accept,
            next_position,
            node_metrics,
            next_node_id,
        )
        result = _Analysis(
            node_id=node_id,
            nullable=left.nullable or right.nullable,
            firstpos=left.firstpos | right.firstpos,
            lastpos=left.lastpos | right.lastpos,
        )
        node_metrics.append(
            DirectNodeMetric(
                node_id=node_id,
                label=_node_label(node),
                nullable=result.nullable,
                firstpos=set(result.firstpos),
                lastpos=set(result.lastpos),
                children=[left.node_id, right.node_id],
            )
        )
        return result

    if isinstance(node, UnaryNode):
        base = _analyze(
            node.operand,
            followpos,
            position_chars,
            position_accept,
            next_position,
            node_metrics,
            next_node_id,
        )

        if node.operator == "*":
            for p in base.lastpos:
                followpos.setdefault(p, set()).update(base.firstpos)
            result = _Analysis(
                node_id=node_id,
                nullable=True,
                firstpos=set(base.firstpos),
                lastpos=set(base.lastpos),
            )
            node_metrics.append(
                DirectNodeMetric(
                    node_id=node_id,
                    label=_node_label(node),
                    nullable=result.nullable,
                    firstpos=set(result.firstpos),
                    lastpos=set(result.lastpos),
                    children=[base.node_id],
                )
            )
            return result

        if node.operator == "+":
            for p in base.lastpos:
                followpos.setdefault(p, set()).update(base.firstpos)
            result = _Analysis(
                node_id=node_id,
                nullable=base.nullable,
                firstpos=set(base.firstpos),
                lastpos=set(base.lastpos),
            )
            node_metrics.append(
                DirectNodeMetric(
                    node_id=node_id,
                    label=_node_label(node),
                    nullable=result.nullable,
                    firstpos=set(result.firstpos),
                    lastpos=set(result.lastpos),
                    children=[base.node_id],
                )
            )
            return result

        if node.operator == "?":
            result = _Analysis(
                node_id=node_id,
                nullable=True,
                firstpos=set(base.firstpos),
                lastpos=set(base.lastpos),
            )
            node_metrics.append(
                DirectNodeMetric(
                    node_id=node_id,
                    label=_node_label(node),
                    nullable=result.nullable,
                    firstpos=set(result.firstpos),
                    lastpos=set(result.lastpos),
                    children=[base.node_id],
                )
            )
            return result

        raise ValueError(f"Operador unario no soportado: {node.operator}")

    if isinstance(node, ConcatNode):
        if not node.parts:
            result = _Analysis(node_id=node_id, nullable=True, firstpos=set(), lastpos=set())
            node_metrics.append(
                DirectNodeMetric(
                    node_id=node_id,
                    label=_node_label(node),
                    nullable=result.nullable,
                    firstpos=set(result.firstpos),
                    lastpos=set(result.lastpos),
                    children=[],
                )
            )
            return result

        analyses = [
            _analyze(
                part,
                followpos,
                position_chars,
                position_accept,
                next_position,
                node_metrics,
                next_node_id,
            )
            for part in node.parts
        ]

        for i in range(len(analyses) - 1):
            left = analyses[i]
            right = analyses[i + 1]
            for p in left.lastpos:
                followpos.setdefault(p, set()).update(right.firstpos)

        nullable = all(info.nullable for info in analyses)

        firstpos: set[int] = set()
        for info in analyses:
            firstpos.update(info.firstpos)
            if not info.nullable:
                break

        lastpos: set[int] = set()
        for info in reversed(analyses):
            lastpos.update(info.lastpos)
            if not info.nullable:
                break

        result = _Analysis(node_id=node_id, nullable=nullable, firstpos=firstpos, lastpos=lastpos)
        node_metrics.append(
            DirectNodeMetric(
                node_id=node_id,
                label=_node_label(node),
                nullable=result.nullable,
                firstpos=set(result.firstpos),
                lastpos=set(result.lastpos),
                children=[analysis.node_id for analysis in analyses],
            )
        )
        return result

    raise ValueError(f"Nodo no soportado en análisis directo: {type(node).__name__}")


def _resolve_accept(
    positions: frozenset[int],
    position_accept: dict[int, DirectAcceptPosition],
) -> tuple[bool, str | None, int | None]:
    best: DirectAcceptPosition | None = None
    for p in positions:
        if p in position_accept:
            meta = position_accept[p]
            if best is None or meta.priority < best.priority:
                best = meta

    if best is None:
        return False, None, None
    return True, best.label, best.priority


def build_direct_artifacts(
    entries: list[tuple[str, RegexNode]],
    definitions: dict[str, RegexNode] | None = None,
) -> DirectArtifacts:
    defs = definitions or {}

    if not entries:
        start_state = DFAState(id=0, nfa_states=frozenset(), is_accept=False)
        dfa = DFA(start_state=0, states=[start_state], transitions=[])
        return DirectArtifacts(dfa=dfa, start_positions=frozenset(), alphabet=[], followpos={})

    roots = []
    for priority, (label, root) in enumerate(entries):
        normalized = _normalize_node(root, defs, resolution_stack=[])
        with_end = ConcatNode(parts=[normalized, _EndLeaf(label=label, priority=priority)])
        roots.append(with_end)

    full_root = roots[0]
    for root in roots[1:]:
        full_root = BinaryNode(operator="|", left=full_root, right=root)

    followpos: dict[int, set[int]] = {}
    position_chars: dict[int, frozenset[str]] = {}
    position_accept: dict[int, DirectAcceptPosition] = {}
    node_metrics: list[DirectNodeMetric] = []
    analysis = _analyze(
        full_root,
        followpos=followpos,
        position_chars=position_chars,
        position_accept=position_accept,
        next_position=[1],
        node_metrics=node_metrics,
        next_node_id=[1],
    )

    alphabet = sorted(
        {ch for chars in position_chars.values() for ch in chars},
    )

    start_positions = frozenset(analysis.firstpos)

    state_id_by_positions: dict[frozenset[int], int] = {start_positions: 0}
    dfa_states: dict[int, DFAState] = {}
    dfa_transitions: list[DFATransition] = []
    worklist: list[frozenset[int]] = [start_positions]

    while worklist:
        current = worklist.pop()
        current_id = state_id_by_positions[current]

        is_accept, accept_label, accept_priority = _resolve_accept(current, position_accept)
        if current_id not in dfa_states:
            dfa_states[current_id] = DFAState(
                id=current_id,
                nfa_states=current,
                is_accept=is_accept,
                accept_label=accept_label,
                accept_priority=accept_priority,
            )

        for ch in alphabet:
            target_set: set[int] = set()
            for pos in current:
                chars = position_chars.get(pos, frozenset())
                if ch in chars:
                    target_set.update(followpos.get(pos, set()))

            target = frozenset(target_set)
            if not target:
                continue

            if target not in state_id_by_positions:
                target_id = len(state_id_by_positions)
                state_id_by_positions[target] = target_id
                worklist.append(target)
            else:
                target_id = state_id_by_positions[target]

            dfa_transitions.append(
                DFATransition(from_state=current_id, to_state=target_id, char=ch)
            )

    # Completar estado/metadata para estados creados pero aún no materializados
    for positions, sid in state_id_by_positions.items():
        if sid in dfa_states:
            continue
        is_accept, accept_label, accept_priority = _resolve_accept(positions, position_accept)
        dfa_states[sid] = DFAState(
            id=sid,
            nfa_states=positions,
            is_accept=is_accept,
            accept_label=accept_label,
            accept_priority=accept_priority,
        )

    dfa = DFA(
        start_state=0,
        states=sorted(dfa_states.values(), key=lambda s: s.id),
        transitions=dfa_transitions,
    )

    return DirectArtifacts(
        dfa=dfa,
        start_positions=start_positions,
        alphabet=alphabet,
        root_nullable=analysis.nullable,
        root_firstpos=frozenset(analysis.firstpos),
        root_lastpos=frozenset(analysis.lastpos),
        followpos=followpos,
        position_chars=position_chars,
        accept_positions=sorted(position_accept.values(), key=lambda x: x.position),
        node_metrics=sorted(node_metrics, key=lambda item: item.node_id),
    )


def build_direct_dfa(
    entries: list[tuple[str, RegexNode]],
    definitions: dict[str, RegexNode] | None = None,
) -> DFA:
    return build_direct_artifacts(entries, definitions).dfa


def direct_artifacts_to_dict(artifacts: DirectArtifacts) -> dict:
    return {
        "root_nullable": artifacts.root_nullable,
        "root_firstpos": sorted(artifacts.root_firstpos),
        "root_lastpos": sorted(artifacts.root_lastpos),
        "start_positions": sorted(artifacts.start_positions),
        "alphabet_size": len(artifacts.alphabet),
        "followpos": {
            str(pos): sorted(targets) for pos, targets in sorted(artifacts.followpos.items())
        },
        "positions": [
            {
                "position": pos,
                "chars": sorted(chars),
                "is_accept_marker": False,
            }
            for pos, chars in sorted(artifacts.position_chars.items())
            if chars
        ]
        + [
            {
                "position": meta.position,
                "chars": [],
                "is_accept_marker": True,
                "label": meta.label,
                "priority": meta.priority,
            }
            for meta in artifacts.accept_positions
        ],
        "node_metrics": [
            {
                "node_id": metric.node_id,
                "label": metric.label,
                "nullable": metric.nullable,
                "firstpos": sorted(metric.firstpos),
                "lastpos": sorted(metric.lastpos),
                "children": metric.children,
            }
            for metric in sorted(artifacts.node_metrics, key=lambda item: item.node_id)
        ],
    }
