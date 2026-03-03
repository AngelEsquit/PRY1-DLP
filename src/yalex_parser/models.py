from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LetDefinition:
    name: str
    regex: str


@dataclass
class RuleAlternative:
    regex: str
    action: str | None = None


@dataclass
class RuleDefinition:
    entrypoint: str
    arguments: list[str] = field(default_factory=list)
    alternatives: list[RuleAlternative] = field(default_factory=list)


@dataclass
class YALexSpec:
    header: str | None = None
    lets: list[LetDefinition] = field(default_factory=list)
    rule: RuleDefinition | None = None
    trailer: str | None = None
