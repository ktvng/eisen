from __future__ import annotations
from typing import Any

from alpaca.clr._clr import CLRList, CLRToken
from alpaca.config._parser import parser as configparser
from alpaca.lexer._lexer import Lexer, Token
from alpaca.lexer._abstractcallback import AbstractCallback

class Match:
    def __init__(self, matched: bool, captures: dict[str, CLRList]={}) -> None:
        self.matched = matched
        self.captures = captures

    def __bool__(self) -> bool:
        return self.matched

    def __getattr__(self, __name: str) -> Any:
        return self.captures.get(__name, None)

    def to(self, pattern: str) -> CLRList:
        return Pattern(pattern)._build(self.captures)


class Pattern:
    def __init__(self, pattern: str) -> None:
        self.str = pattern
        self.parts = self._parse_pattern(pattern)
        self.lst = ListRepresentation.construct(self.parts)

    def _parse_pattern(self, pattern: str) -> list:
        config = configparser.run("./src/alpaca/pattern/pattern.gm")
        toks = Lexer.run(pattern, config, AbstractCallback())
        return toks

    def _construct_list(self, parts: list[Token]):
        return ListRepresentation.construct(parts)

    def match(self, asl: CLRList) -> Match:
        return PatternMatcher.match_pattern_head(self.lst, asl)

    def map(self, asl: CLRList, into_pattern: str) -> list[CLRList]:
        return [m.to(into_pattern) for m in map(self.match, asl._list) if m]

    def find_all(self, asl: CLRList) -> list[CLRList]:
        return [child for child in asl._list if self.match(child)]

    def find_first(self, asl: CLRList) -> CLRList:
        return self.find_all(asl._list)[0]

    def _build(self, lookups: dict[str, CLRList]) -> CLRList:
        return PatternBuilder.construct(self.lst, lookups)

class PatternBuilder:
    @staticmethod
    def construct(pattern: list, lookups: dict[str, CLRList]) -> CLRList:
        asl_type_comp = pattern[0]
        if not isinstance(asl_type_comp, TagComponent):
            raise Exception("expected real tag component to build list")

        lst = []
        for comp in pattern[1: ]:
            if isinstance(comp, VarComponent):
                lst.append(lookups.get(comp.get_value()))
            elif isinstance(comp, TagComponent):
                lst.append(CLRToken(type_chain=["code"], value=comp.get_value()))
            elif isinstance(comp, ListComponent):
                lst.append(lookups.get(comp.get_value()))
                lst += lookups.get(comp.get_value())
            elif isinstance(comp, list):
                lst.append(PatternBuilder.construct(comp, lookups))

        return CLRList(type=asl_type_comp.get_value(), lst=lst)

class PatternMatcher:
    @staticmethod
    def match_pattern_head(pattern: list, asl: CLRList) -> Match:
        asl_type_comp = pattern[0]
        asl_type = None
        if isinstance(asl_type_comp, TagComponent):
            asl_type = asl_type_comp.get_value()
        elif isinstance(asl_type_comp, AnyTagComponent):
            asl_type = None
        else:
            raise Exception("expected match head to start with list type")

        if not (asl_type is None or asl.type == asl_type):
            return Match(False)

        asl_parts = list(asl._list)
        match = Match(True, {})
        for comp in pattern[1: ]:
            if isinstance(comp, TagComponent):
                if not (asl_parts[0].is_token() and asl_parts[0].value == comp.get_value()):
                    return Match(False)
                asl_parts = asl_parts[1: ]
            if isinstance(comp, VarComponent):
                match.captures[comp.get_value()] = asl_parts[0]
                asl_parts = asl_parts[1: ]
            if isinstance(comp, list):
                child_match = PatternMatcher.match_pattern_head(comp, asl_parts[0])
                if not child_match:
                    return Match(False)
                asl_parts = asl_parts[1 :]
                match.captures.update(child_match.captures)
            if isinstance(comp, LstComponent):
                match.captures[comp.get_value()] = asl_parts
                return match
        return match

class ListComponent:
    def __init__(self, type: str, value: str) -> None:
        self.type = type
        self.value = value

    def is_var(self) -> bool:
        return self.type == "var"

    def is_tag(self) -> bool:
        return self.type == "tag"

    def is_lst(self) -> bool:
        return self.type == "lst"

    def get_type(self) -> str:
        return self.type

    def get_value(self) -> str:
        pass

    def __str__(self) -> str:
        return self.value

class VarComponent(ListComponent):
    def __init__(self, type: str, value: str) -> None:
        super().__init__(type, value)

    def get_value(self) -> str:
        return self.value

class TagComponent(ListComponent):
    def __init__(self, type: str, value: str) -> None:
        super().__init__(type, value)

    def get_value(self) -> str:
        return self.value[1: ]

class LstComponent(ListComponent):
    def __init__(self, type: str, value: str) -> None:
        super().__init__(type, value)

    def get_value(self) -> str:
        return self.value[: -3]

class AnyTagComponent(ListComponent):
    def __init__(self, type: str, value: str) -> None:
        super().__init__(type, value)

    def get_value(self) -> str:
        return self.value

class ListRepresentation:
    @staticmethod
    def construct(parts: list[Token]):
        lst, _ = ListRepresentation._construct(parts)
        return lst

    @staticmethod
    def _construct(parts: list[Token]) -> tuple[list, list[Token]]:
        lst: list = []
        while parts:
            if parts[0].type == "(":
                child_lst, parts = ListRepresentation._construct(parts[1:])
                if not lst: lst = child_lst
                else: lst.append(child_lst)
            elif parts[0].type == "var":
                lst.append(VarComponent(parts[0].type, parts[0].value))
                parts = parts[1: ]
            elif parts[0].type == "lst":
                lst.append(LstComponent(parts[0].type, parts[0].value))
                parts = parts[1: ]
            elif parts[0].type == "tag":
                lst.append(TagComponent(parts[0].type, parts[0].value))
                parts = parts[1: ]
            elif parts[0].type == "any":
                lst.append(AnyTagComponent(parts[0].type, parts[0].value))
                parts = parts[1: ]
            elif parts[0].type == ")":
                return lst, parts[1: ]
        return lst, parts

    @staticmethod
    def print_list_rep(listrep: list):
        if not isinstance(listrep, list):
            return str(listrep)
        parts = [ListRepresentation.print_list_rep(x) for x in listrep]
        return "(" + " ".join(parts) + ")"
