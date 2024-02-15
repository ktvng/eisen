from __future__ import annotations
from typing import Any

from alpaca.clr._clr import AST, ASTToken
from alpaca.config._parser import parser as configparser
from alpaca.lexer._lexer import Lexer, Token
from alpaca.lexer._abstractcallback import AbstractCallback

class Match:
    def __init__(self, matched: bool, captures: dict[str, AST]={}) -> None:
        self.matched = matched
        self.captures = captures

    def __bool__(self) -> bool:
        return self.matched

    def __getattr__(self, __name: str) -> Any:
        return self.captures.get(__name, None)

    def to(self, pattern: str) -> AST:
        return Pattern(pattern).build(self.captures)


class Pattern:
    def __init__(self, pattern: str) -> None:
        # allow the pattern string to be multi-line by replacing newlines with spaces
        # which should be an ignored character
        self.str = pattern.replace("\n", " ")
        self.parts = self._parse_pattern(self.str)
        self.lst = ListRepresentation.construct(self.parts)

    def _parse_pattern(self, pattern: str) -> list:
        config = configparser.run("./src/alpaca/pattern/pattern.gm")
        toks = Lexer.run(pattern, config, AbstractCallback())
        return toks

    def _construct_list(self, parts: list[Token]):
        return ListRepresentation.construct(parts)

    def match(self, ast: AST) -> Match:
        return PatternMatcher.match_pattern_head(self.lst, ast)

    def map(self, ast: AST, into_pattern: str) -> list[AST]:
        return [m.to(into_pattern) for m in map(self.match, ast._list) if m]

    def find_all(self, ast: AST) -> list[AST]:
        return [child for child in ast._list if self.match(child)]

    def find_first(self, ast: AST) -> AST:
        return self.find_all(ast._list)[0]

    def build(self, lookups: dict[str, AST] = None) -> AST:
        return PatternBuilder.construct(self.lst, lookups)

class PatternBuilder:
    @staticmethod
    def construct(pattern: list, lookups: dict[str, AST] = None) -> AST:
        if lookups is None: lookups = {}
        ast_type_comp = pattern[0]
        if not isinstance(ast_type_comp, TagComponent):
            raise Exception("expected real tag component to build list, got", ast_type_comp)

        lst = []
        for comp in pattern[1: ]:
            if isinstance(comp, VarComponent):
                lst.append(lookups.get(comp.get_value()))
            elif isinstance(comp, TagComponent):
                lst.append(ASTToken(type_chain=["code"], value=comp.get_value()))
            elif isinstance(comp, ListComponent):
                lst += lookups.get(comp.get_value())
            elif isinstance(comp, list):
                lst.append(PatternBuilder.construct(comp, lookups))

        return AST(type=ast_type_comp.get_value(), lst=lst)

class PatternMatcher:
    @staticmethod
    def match_pattern_head(pattern: list, ast: AST) -> Match:
        ast_type_comp = pattern[0]
        match ast_type_comp:
            case TagComponent(): ast_type = ast_type_comp.get_value()
            case AnyTagComponent(): ast_type = None
            case _: raise Exception("expected match head to start with list type")

        if not (ast_type is None or ast.type == ast_type):
            return Match(False)

        ast_parts = list(ast._list)
        match = Match(True, {})
        for comp in pattern[1: ]:
            match comp:
                case TagComponent():
                    if not (ast_parts[0].is_token() and ast_parts[0].value == comp.get_value()):
                        return Match(False)
                    ast_parts = ast_parts[1: ]
                case VarComponent():
                    match.captures[comp.get_value()] = ast_parts[0]
                    ast_parts = ast_parts[1: ]
                case list():
                    child_match = PatternMatcher.match_pattern_head(comp, ast_parts[0])
                    if not child_match:
                        return Match(False)
                    ast_parts = ast_parts[1 :]
                    match.captures.update(child_match.captures)
                case LstComponent():
                    match.captures[comp.get_value()] = ast_parts
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
