from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RegexNode:
    pass


@dataclass
class LiteralNode(RegexNode):
    value: str


@dataclass
class WildcardNode(RegexNode):
    pass


@dataclass
class IdentifierNode(RegexNode):
    name: str


@dataclass
class StringNode(RegexNode):
    value: str


@dataclass
class CharRange:
    start: str
    end: str


@dataclass
class CharSetNode(RegexNode):
    negated: bool
    singles: list[str]
    ranges: list[CharRange]


@dataclass
class UnaryNode(RegexNode):
    operator: str
    operand: RegexNode


@dataclass
class BinaryNode(RegexNode):
    operator: str
    left: RegexNode
    right: RegexNode


@dataclass
class ConcatNode(RegexNode):
    parts: list[RegexNode]


def regex_node_to_dict(node: RegexNode) -> dict:
    if isinstance(node, LiteralNode):
        return {"type": "literal", "value": node.value}
    if isinstance(node, WildcardNode):
        return {"type": "wildcard"}
    if isinstance(node, IdentifierNode):
        return {"type": "identifier", "name": node.name}
    if isinstance(node, StringNode):
        return {"type": "string", "value": node.value}
    if isinstance(node, CharSetNode):
        return {
            "type": "charset",
            "negated": node.negated,
            "singles": node.singles,
            "ranges": [{"start": r.start, "end": r.end} for r in node.ranges],
        }
    if isinstance(node, UnaryNode):
        return {
            "type": "unary",
            "operator": node.operator,
            "operand": regex_node_to_dict(node.operand),
        }
    if isinstance(node, BinaryNode):
        return {
            "type": "binary",
            "operator": node.operator,
            "left": regex_node_to_dict(node.left),
            "right": regex_node_to_dict(node.right),
        }
    if isinstance(node, ConcatNode):
        return {"type": "concat", "parts": [regex_node_to_dict(p) for p in node.parts]}

    raise ValueError(f"Nodo no soportado: {type(node).__name__}")
