from __future__ import annotations

from dataclasses import dataclass, field

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
    regex_node_to_dict,
)


@dataclass
class Transition:
    from_state: int
    to_state: int
    kind: str
    payload: dict | None = None


@dataclass
class NFA:
    start_state: int
    accept_state: int
    transitions: list[Transition] = field(default_factory=list)


@dataclass
class Fragment:
    start: int
    accept: int
    transitions: list[Transition] = field(default_factory=list)


def build_thompson_nfa(root: RegexNode, definitions: dict[str, RegexNode] | None = None) -> NFA:
    builder = _ThompsonBuilder(definitions or {})
    fragment = builder.build(root)
    return NFA(
        start_state=fragment.start,
        accept_state=fragment.accept,
        transitions=fragment.transitions,
    )


def nfa_to_dict(nfa: NFA) -> dict:
    states = {nfa.start_state, nfa.accept_state}
    for transition in nfa.transitions:
        states.add(transition.from_state)
        states.add(transition.to_state)

    return {
        "start_state": nfa.start_state,
        "accept_state": nfa.accept_state,
        "states": sorted(states),
        "transitions": [
            {
                "from": transition.from_state,
                "to": transition.to_state,
                "kind": transition.kind,
                "payload": transition.payload,
            }
            for transition in nfa.transitions
        ],
    }


class _ThompsonBuilder:
    def __init__(self, definitions: dict[str, RegexNode]) -> None:
        self._next_state = 0
        self._definitions = definitions
        self._resolution_stack: list[str] = []

    def _new_state(self) -> int:
        state = self._next_state
        self._next_state += 1
        return state

    def build(self, node: RegexNode) -> Fragment:
        if isinstance(node, LiteralNode):
            return self._build_literal(node.value)

        if isinstance(node, StringNode):
            return self._build_string(node.value)

        if isinstance(node, WildcardNode):
            return self._build_symbol("wildcard")

        if isinstance(node, CharSetNode):
            payload = {
                "negated": node.negated,
                "singles": node.singles,
                "ranges": [{"start": r.start, "end": r.end} for r in node.ranges],
            }
            return self._build_symbol("charset", payload)

        if isinstance(node, IdentifierNode):
            return self._build_identifier(node)

        if isinstance(node, ConcatNode):
            return self._build_concat(node)

        if isinstance(node, UnaryNode):
            return self._build_unary(node)

        if isinstance(node, BinaryNode):
            return self._build_binary(node)

        raise ValueError(f"Nodo no soportado en Thompson: {type(node).__name__}")

    def _build_literal(self, value: str) -> Fragment:
        return self._build_symbol("char", {"value": value})

    def _build_string(self, value: str) -> Fragment:
        if value == "":
            return self._build_epsilon()

        fragment = self._build_literal(value[0])
        for ch in value[1:]:
            next_fragment = self._build_literal(ch)
            fragment = self._concat_fragments(fragment, next_fragment)
        return fragment

    def _build_identifier(self, node: IdentifierNode) -> Fragment:
        if node.name not in self._definitions:
            raise ValueError(f"Identificador no definido: {node.name}")

        if node.name in self._resolution_stack:
            cycle = " -> ".join(self._resolution_stack + [node.name])
            raise ValueError(f"Referencia recursiva detectada en let: {cycle}")

        self._resolution_stack.append(node.name)
        resolved = self.build(self._definitions[node.name])
        self._resolution_stack.pop()
        return resolved

    def _build_concat(self, node: ConcatNode) -> Fragment:
        if not node.parts:
            return self._build_epsilon()

        current = self.build(node.parts[0])
        for part in node.parts[1:]:
            current = self._concat_fragments(current, self.build(part))
        return current

    def _build_unary(self, node: UnaryNode) -> Fragment:
        base = self.build(node.operand)

        if node.operator == "*":
            start = self._new_state()
            accept = self._new_state()
            transitions = [
                *base.transitions,
                Transition(start, base.start, "epsilon"),
                Transition(start, accept, "epsilon"),
                Transition(base.accept, base.start, "epsilon"),
                Transition(base.accept, accept, "epsilon"),
            ]
            return Fragment(start=start, accept=accept, transitions=transitions)

        if node.operator == "+":
            start = self._new_state()
            accept = self._new_state()
            transitions = [
                *base.transitions,
                Transition(start, base.start, "epsilon"),
                Transition(base.accept, base.start, "epsilon"),
                Transition(base.accept, accept, "epsilon"),
            ]
            return Fragment(start=start, accept=accept, transitions=transitions)

        if node.operator == "?":
            start = self._new_state()
            accept = self._new_state()
            transitions = [
                *base.transitions,
                Transition(start, base.start, "epsilon"),
                Transition(start, accept, "epsilon"),
                Transition(base.accept, accept, "epsilon"),
            ]
            return Fragment(start=start, accept=accept, transitions=transitions)

        raise ValueError(f"Operador unario no soportado: {node.operator}")

    def _build_binary(self, node: BinaryNode) -> Fragment:
        if node.operator in ("|", "/"):
            left = self.build(node.left)
            right = self.build(node.right)

            start = self._new_state()
            accept = self._new_state()
            transitions = [
                *left.transitions,
                *right.transitions,
                Transition(start, left.start, "epsilon"),
                Transition(start, right.start, "epsilon"),
                Transition(left.accept, accept, "epsilon"),
                Transition(right.accept, accept, "epsilon"),
            ]
            return Fragment(start=start, accept=accept, transitions=transitions)

        if node.operator == "#":
            start = self._new_state()
            accept = self._new_state()
            payload = {
                "left": regex_node_to_dict(node.left),
                "right": regex_node_to_dict(node.right),
            }
            return Fragment(
                start=start,
                accept=accept,
                transitions=[Transition(start, accept, "charset_difference", payload)],
            )

        raise ValueError(f"Operador binario no soportado: {node.operator}")

    def _build_symbol(self, kind: str, payload: dict | None = None) -> Fragment:
        start = self._new_state()
        accept = self._new_state()
        transition = Transition(start, accept, kind, payload)
        return Fragment(start=start, accept=accept, transitions=[transition])

    def _build_epsilon(self) -> Fragment:
        start = self._new_state()
        accept = self._new_state()
        return Fragment(
            start=start,
            accept=accept,
            transitions=[Transition(start, accept, "epsilon")],
        )

    def _concat_fragments(self, left: Fragment, right: Fragment) -> Fragment:
        transitions = [
            *left.transitions,
            *right.transitions,
            Transition(left.accept, right.start, "epsilon"),
        ]
        return Fragment(start=left.start, accept=right.accept, transitions=transitions)
